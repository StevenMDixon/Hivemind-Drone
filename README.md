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