# Hivemind Drone - container image for headless Linux hosts (e.g. TrueNAS SCALE)
#
# Displays are driven directly through the kernel DRM/KMS interface (no X11):
#   DISPLAY_BACKEND=sway  (default) a minimal Wayland compositor owns the GPU and
#                         every MPV instance is placed on its own output.
#   DISPLAY_BACKEND=drm   each MPV instance drives a connector directly
#                         (only one MPV per GPU card can do this at a time).
FROM python:3.12-slim-trixie

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    DISPLAY_BACKEND=sway \
    MPV_HOME=/config/mpv \
    XDG_RUNTIME_DIR=/tmp/xdg-runtime \
    TZ=Etc/UTC

# mpv/ffmpeg for playback, Mesa (GL/EGL/VA-API) for GPU output and hardware
# decoding, ALSA for audio, sway + libseat for the multi-display compositor,
# tini as a minimal init that reaps zombies and forwards signals.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        mpv \
        ffmpeg \
        libgl1-mesa-dri \
        libegl1 \
        libgles2 \
        libdrm2 \
        mesa-va-drivers \
        intel-media-va-driver \
        libasound2t64 \
        alsa-utils \
        sway \
        libseat1 \
        tini \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

# 568 is the default "apps" user/group on TrueNAS SCALE.
ARG APP_UID=568
ARG APP_GID=568
RUN groupadd --gid "${APP_GID}" drone \
    && useradd --uid "${APP_UID}" --gid "${APP_GID}" --groups video,audio \
        --home-dir /home/drone --create-home --shell /usr/sbin/nologin drone

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# The application reads ./settings.json and ./.env relative to /app; point them
# at the persistent /config volume. The entrypoint seeds /config on first start.
# Code stays root-owned; only the /app directory itself is writable because the
# player writes its overlay.raw scratch file to the working directory.
RUN ln -sf /config/settings.json /app/settings.json \
    && ln -sf /config/.env /app/.env \
    && chmod 0755 /app/docker/entrypoint.sh \
    && mkdir -p /config /media \
    && chown drone:drone /app /config

USER drone

VOLUME ["/config"]
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/player/status', timeout=4)" || exit 1

ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/app/docker/entrypoint.sh"]
CMD ["python", "main.py"]
