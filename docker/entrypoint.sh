#!/usr/bin/env bash
# Container entrypoint for Hivemind Drone.
#  1. Seeds /config with default settings.json, .env, mpv and sway configs.
#  2. Optionally starts the sway Wayland compositor (DISPLAY_BACKEND=sway).
#  3. Runs the application command (default: python main.py).
set -euo pipefail

CONFIG_DIR=/config
DEFAULTS_DIR=/app/docker/defaults
DISPLAY_BACKEND="${DISPLAY_BACKEND:-sway}"

log() { echo "[entrypoint] $*"; }

seed() {
    local src="$1" dest="$2"
    if [ ! -e "$dest" ]; then
        if cp -r "$src" "$dest" 2>/dev/null; then
            log "Created default $dest"
        else
            log "WARNING: could not create $dest (is /config writable by uid $(id -u)?)"
        fi
    fi
}

seed "$DEFAULTS_DIR/settings.json" "$CONFIG_DIR/settings.json"
seed "$DEFAULTS_DIR/.env" "$CONFIG_DIR/.env"
seed "$DEFAULTS_DIR/mpv" "$CONFIG_DIR/mpv"
seed "$DEFAULTS_DIR/sway" "$CONFIG_DIR/sway"

if [ ! -f "$CONFIG_DIR/settings.json" ]; then
    log "ERROR: $CONFIG_DIR/settings.json is missing. Mount a config directory at $CONFIG_DIR."
    exit 1
fi

mkdir -p "$XDG_RUNTIME_DIR"
chmod 0700 "$XDG_RUNTIME_DIR"

case "$DISPLAY_BACKEND" in
    sway)
        # No logind/seatd inside the container: open DRM devices directly.
        export LIBSEAT_BACKEND="${LIBSEAT_BACKEND:-noop}"
        # Output only; no keyboard/mouse is required.
        export WLR_BACKENDS="${WLR_BACKENDS:-drm}"
        export WLR_LIBINPUT_NO_DEVICES=1
        SWAY_CONFIG="${SWAY_CONFIG:-$CONFIG_DIR/sway/config}"

        log "Starting sway (WLR_BACKENDS=$WLR_BACKENDS, config=$SWAY_CONFIG)"
        sway --config "$SWAY_CONFIG" &
        SWAY_PID=$!

        WAYLAND_DISPLAY=""
        for _ in $(seq 1 100); do
            if ! kill -0 "$SWAY_PID" 2>/dev/null; then
                log "ERROR: sway exited during startup. Check /dev/dri access and the sway config."
                exit 1
            fi
            for sock in "$XDG_RUNTIME_DIR"/wayland-*; do
                case "$sock" in *.lock|*'*') continue ;; esac
                if [ -S "$sock" ]; then
                    WAYLAND_DISPLAY="$(basename "$sock")"
                    break 2
                fi
            done
            sleep 0.2
        done

        if [ -z "$WAYLAND_DISPLAY" ]; then
            log "ERROR: sway did not create a Wayland socket within 20s."
            kill "$SWAY_PID" 2>/dev/null || true
            exit 1
        fi
        export WAYLAND_DISPLAY
        log "sway is running on WAYLAND_DISPLAY=$WAYLAND_DISPLAY"

        log "Starting: $*"
        "$@" &
        APP_PID=$!

        shutdown() {
            kill -TERM "$APP_PID" 2>/dev/null || true
            wait "$APP_PID" 2>/dev/null || true
            kill -TERM "$SWAY_PID" 2>/dev/null || true
            wait "$SWAY_PID" 2>/dev/null || true
        }
        trap 'shutdown; exit 143' TERM INT

        # Stop the container if either the application or the compositor exits.
        set +e
        wait -n "$APP_PID" "$SWAY_PID"
        status=$?
        set -e
        if ! kill -0 "$SWAY_PID" 2>/dev/null; then
            log "sway exited (status $status); stopping."
        else
            log "Application exited (status $status); stopping."
        fi
        shutdown
        exit "$status"
        ;;
    drm|none)
        log "DISPLAY_BACKEND=$DISPLAY_BACKEND; starting: $*"
        exec "$@"
        ;;
    *)
        log "ERROR: unknown DISPLAY_BACKEND '$DISPLAY_BACKEND' (expected sway, drm or none)"
        exit 1
        ;;
esac
