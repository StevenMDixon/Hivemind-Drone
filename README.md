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