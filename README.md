# HiveMind - Drone

This program is meant to serve as the media player portion of Hivemind, essentially turning whatever device it is deployed on into a drone!

## Requirements
1. A device with a network connection
2. MPV installed on said device
3. Python
4. A HiveMind Instance running somewhere

## Setup

1. Configure your device. (See Setting up the PI section below, for tips)
2. Mount Your Drive (Network or otherwise)
3. Clone this repo (to your desktop?)
4. Navigate to the scripts file and run `setup.sh`, this will install the requirements and set the appropriate venv
5. update `.env` (see the .env section)
6. update `settings.json` (see the settings.json section)
7. run `python main.py`

* Note: If you want to play youtube videos via mpv, you will need to install yt-dlp: `sudo apt install mpv yt-dlp`

### .env options
    ```
    HostName=DESKTOP-BNGTCFF
    Port=5000
    HivemindUrl = http://localhost:32770
    MountedPath = F:/Test/
    ```
`HostName` should match the Drones Hostname
`Port` is the port the Drones server will run on, this allows HiveMind to control it remotely
`HiveMindUrl` is the url of your local HiveMind instance
`MountedPath` is the Path your media is at
`StandbyUrl` Image that is shown when no media is loaded

### settings.json options
``` JSON
{
    "devices": [
        {
            "stationNumber": 1,
            "screen": 0,
            "audioDevice": "wasapi/{6edc04f6-f8ba-4066-b28f-22036b0ca9f3}"
        },
        {
            "stationNumber": 2,
            "screen": 1,
            "audioDevice": "wasapi/{41446bc0-bc9b-489c-82e1-cf1fdb000053}"
        }
    ]
}
```

It is possible that the machine your are deploying this to has multiple displays, this software is able to use these.
`StationNumber` Will match a Station assigned to this drone in HiveMind
`screen` is the index of your displays
`audioDevice` is the name of the audio device you want to target for playback use `mpv --audio-device=help` to get a list of these
`mpvArgs` (optional) is a list of extra command line arguments passed to that station's mpv process, e.g. `["--title=hivemind-station-1", "--fs-screen-name=HDMI-A-1"]`

## Running in Docker (TrueNAS SCALE)

The repository ships a `Dockerfile`, a `docker-compose.yml` and container defaults under `docker/` so a drone can run as a container on a headless Linux host such as TrueNAS SCALE 25.04, driving physical displays connected to the host GPU. The Windows / Raspberry Pi workflow above is unchanged.

### How the container works

* Entry point: `tini` -> `docker/entrypoint.sh` -> `python main.py` (the same entry point as a normal install; Flask listens on port `5000`).
* There is no X server. Video goes straight to the GPU through Linux DRM/KMS; Windows `wasapi/...` audio devices do not exist on Linux, audio goes through ALSA (`alsa/...` devices).
* `DISPLAY_BACKEND` selects how displays are driven:
  * `sway` (default) - the entrypoint starts the [sway](https://swaywm.org/) Wayland compositor as a kiosk on the DRM device, and every mpv instance is a Wayland client. sway's config moves each station window (matched by `--title`) fullscreen onto its own output. **Use this for two displays on one GPU.** Only one process can be DRM master of a GPU at a time, so two mpv instances cannot drive two connectors of the same card directly.
  * `drm` - each mpv instance drives a connector directly (`--gpu-context=drm --drm-device=... --drm-connector=...`). Only works with **one display per GPU card** (e.g. iGPU + discrete GPU). See `docker/defaults/settings.drm.example.json`.
  * `none` - just run the application (for debugging).
* The container runs as the unprivileged user `568:568` (TrueNAS `apps`). It does **not** need `privileged: true`; it only needs the `/dev/dri` and `/dev/snd` devices and membership in the host groups that own them.

### Volumes and configuration

| Container path | Purpose |
| --- | --- |
| `/config` | Persistent configuration. Must be writable by UID 568. Seeded on first start if files are missing. |
| `/config/settings.json` | Station definitions (same format as above, plus optional `mpvArgs`). |
| `/config/.env` | Same keys as the `.env` above. Values from the compose `environment:` section take precedence. |
| `/config/mpv/mpv.conf` | Global mpv options (`vo`, `hwdec`, `ao`, ...). `MPV_HOME=/config/mpv`. |
| `/config/sway/config` | Output layout and station-to-output mapping for `DISPLAY_BACKEND=sway`. |
| `/media` | Your media library. Set `MountedPath=/media/` so schedule paths resolve inside the container. |

Default container `settings.json` (two stations, two HDMI outputs on one GPU):
``` JSON
{
    "devices": [
        { "stationNumber": 1, "screen": 0, "audioDevice": "alsa/hdmi:CARD=PCH,DEV=0",
          "mpvArgs": ["--title=hivemind-station-1", "--fs-screen-name=HDMI-A-1"] },
        { "stationNumber": 2, "screen": 1, "audioDevice": "alsa/hdmi:CARD=PCH,DEV=1",
          "mpvArgs": ["--title=hivemind-station-2", "--fs-screen-name=HDMI-A-2"] }
    ]
}
```
The matching `/config/sway/config` pins workspace 1 to `HDMI-A-1` and workspace 2 to `HDMI-A-2` and moves `hivemind-station-N` windows there fullscreen. Change the connector names to match your hardware.

Environment variables understood by the container:

| Variable | Default | Description |
| --- | --- | --- |
| `DISPLAY_BACKEND` | `sway` | `sway`, `drm` or `none` |
| `HostName`, `HivemindUrl`, `MountedPath`, `StandbyUrl`, `PollingDelay` | from `/config/.env` | Application settings (see `.env options`) |
| `TZ` | `Etc/UTC` | Time zone; schedules use local time |
| `WLR_DRM_DEVICES` | all GPUs | Restrict sway to a GPU, e.g. `/dev/dri/card0` |
| `WLR_RENDERER` | auto | Set to `pixman` for GPUs without OpenGL ES support |

### Published image (GitHub Container Registry)

The `Docker publish` workflow (`.github/workflows/docker-publish.yml`) builds the `Dockerfile` for `linux/amd64` and publishes it to `ghcr.io/stevenmdixon/hivemind-drone`:

| Trigger | Tags pushed |
| --- | --- |
| Push to `main` | `latest`, `sha-<short commit>` |
| Push of a `v*` tag (e.g. `v1.0.0`) | `v1.0.0`, `sha-<short commit>` |
| Manual run (Actions -> Docker publish -> Run workflow) | `sha-<short commit>` (plus `latest` when run on `main`) |

The image is only pushed if the build succeeds. To cut a release:
```bash
git tag v1.0.0
git push origin v1.0.0
```

Pull the image:
```bash
docker pull ghcr.io/stevenmdixon/hivemind-drone:latest   # tracks main
docker pull ghcr.io/stevenmdixon/hivemind-drone:v1.0.0   # pinned release
```

New GHCR packages are private by default. After the first successful run, either make the package public (GitHub profile -> Packages -> `hivemind-drone` -> Package settings -> Change visibility) or add a registry credential in TrueNAS (Apps -> Configuration -> Manage Container Image Registries, registry `ghcr.io`, your GitHub username and a personal access token with the `read:packages` scope).

To deploy the published image, use `docker-compose.yml` as-is but delete the `build: .` line so TrueNAS pulls `image:` instead of building. Pin a release by changing `image:` to e.g. `ghcr.io/stevenmdixon/hivemind-drone:v1.0.0`. To update a deployment on `latest`, pull again and recreate the container (TrueNAS: Apps -> hivemind-drone -> Update / Pull Images; shell: `docker compose pull && docker compose up -d`).

### Build and publish manually

```bash
# Build (TrueNAS SCALE is x86_64)
docker build --platform linux/amd64 -t ghcr.io/stevenmdixon/hivemind-drone:latest .

# Publish to GitHub Container Registry (token needs the write:packages scope)
echo "$GHCR_TOKEN" | docker login ghcr.io -u StevenMDixon --password-stdin
docker push ghcr.io/stevenmdixon/hivemind-drone:latest
```
Make the package public in GitHub (Packages -> Package settings) or add registry credentials in TrueNAS (Apps -> Configuration -> Manage Container Image Registries).

### Deploy on TrueNAS SCALE 25.04

1. **Find the display and audio hardware** in the TrueNAS shell:
   ```bash
   ls -l /dev/dri /dev/snd
   stat -c '%g %n' /dev/dri/* /dev/snd/*                                   # GIDs for group_add
   for p in /sys/class/drm/card*-*; do echo "$(basename $p) $(cat $p/status)"; done   # connector names
   cat /proc/asound/cards                                                   # ALSA card names
   ```
   Make sure the GPU is not isolated for VMs (System -> Advanced -> Isolated GPU Devices).
2. **Create datasets**, e.g. `tank/apps/hivemind-drone/config`, and give UID/GID 568 (`apps`) write access to the config dataset and read access to the media dataset.
3. **Install the app**: Apps -> Discover Apps -> ⋮ -> *Install via YAML*, paste `docker-compose.yml` (remove the `build:` line), and adjust `HivemindUrl`, `HostName`, `TZ`, the host paths and the `group_add` GIDs from step 1.
4. **First start** seeds `/config`. Edit `/config/settings.json` and `/config/sway/config` with your connector names (e.g. `HDMI-A-1`, `DP-1`) and audio devices, then restart the app.
5. **List audio devices** from inside the running container and copy the right `alsa/...` names into `audioDevice`:
   ```bash
   docker exec hivemind-drone mpv --audio-device=help
   docker exec hivemind-drone aplay -L
   ```
6. **Check status**: `docker logs hivemind-drone` and `http://<truenas-ip>:5000/player/status`.

You can also deploy from the TrueNAS shell with `docker compose up -d` in a directory containing `docker-compose.yml`.

### Known limitations

* Physical display output has only been validated against a virtual KMS device and sway's headless backend; connector names, modes, hardware decoding and HDMI audio must be verified on the real host.
* NVIDIA GPUs need the proprietary driver with `nvidia-drm.modeset=1` and are not covered by this image (Mesa only). Intel and AMD GPUs are recommended.
* With `DISPLAY_BACKEND=drm`, a second mpv on the same GPU fails with `Failed to acquire DRM master: Permission denied`; use `sway` instead.
* HDMI audio device numbers (`DEV=`) do not always follow connector order; test each output.
* Only one process can be DRM master of a GPU; if anything else on the host holds it, sway cannot start.

## Setting up a raspberry pi

We need to setup the the rpi 4 to output composite signal for our rf modulator.

Always upgrade your firmware before doing this, there used to be a slowdown issue that was resolved for the rpi 4 models.
You may have to connect to hdmi to do this part, check out the rpi docs to update your firmware.

In config.txt

Change 
```
# Enable DRM VC4 V3D driver
dtoverlay=vc4-kms-v3d
```
To
```
# Enable DRM VC4 V3D driver
dtoverlay=vc4-kms-v3d,composite
```

Then add this anywhere
```
enable_tvout=1
```
This will disable hdmi out, you can try autodetect but i found it is not reliable

sdtv_mode = 0 is for NTSC, there a ton of other modes to choose from check the official docs for those values

In cmdline.txt add this to the end

```
video=Composite-1:720x480@60ie
```

you can add `,margin_left=10,margin_right=10,margin_top=32,margin_bottom=32` to the end of the line above but it will have negative effects on vlc

You may need to edit your margins. YMMV.

Also depending on your composite cables red and yellow may be swapped.

If you are planning on connecting the pis to other network items make sure to set the hostname!

If you are planning on running media from an attached drive/usb, make sure to go into File_manager -> edit -> preference -> volumn management and deselect show available options.. Otherwise everytime you swap in a new drive you will get a popup