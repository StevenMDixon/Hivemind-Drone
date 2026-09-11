import subprocess
import os
from python_mpv_jsonipc import MPV
from datetime import datetime


class MPVPlayer:

    def __init__(self, mpv_socket, device_info, schedule_data, mountPath, startTime, StandbyUrl):
        self.socket = mpv_socket
        self.mounted_path = mountPath
        self.standby_url = StandbyUrl

        self.schedule = schedule_data
        self.start_time = startTime

        if os.path.exists(mpv_socket):
            os.remove(mpv_socket)

        self.device_info = device_info

        self._create_process()

        self.load_schedule(schedule_data)

        self.add_listeners()
      

    def add_listeners(self):
        @self.player.property_observer("playlist-pos")
        def playlist_changed(name, value):
            print("Now playing:", value)

        @self.player.event_callback("shutdown")
        def on_shutdown(event):
            print("MPV is shutting down")

        @self.player.event_callback("end-file")
        def on_end_file(event):
            reason = event.get("reason")
            print("MPV is shutting down due to end-file event:", reason)

    def load_schedule(self, schedule_data):
        currentTime = datetime.now()
        daily_start_time = datetime.now().replace(hour=self.start_time.hour, minute=self.start_time.minute, second=self.start_time.second)
        ff_time = (currentTime - daily_start_time).total_seconds() if currentTime > daily_start_time else 0

        print(f"currentTime: {currentTime}")
        print(f"daily_start_time: {daily_start_time}")
        print(f"ff_time: {ff_time}")

        files_loaded = 0
        
        for item in schedule_data:
            startTime = item.get('startTime') /1000 if item.get('startTime') else 0
            endTime = item.get('stopTime') / 1000 if item.get('stopTime') else 0

            duration = endTime - startTime

            if(ff_time > duration):
                ff_time -= duration
                continue

            # options = []
            if(ff_time > 0):
                startTime = startTime + ff_time
                # print(f"Adjusted start time: {startTime}, end time: {endTime}, duration: {duration}")
                ff_time = 0

            try:
                self.player.command(
                        "loadfile", 
                        os.path.join(self.mounted_path, item.get('path').lstrip('/')) if item.get('path') else None,
                        "replace" if files_loaded == 0 else "append",
                        -1,
                        f"start={startTime},length={endTime - startTime}"
                        )
                files_loaded += 1
            except Exception as e:
                print(f"Error scheduling item {files_loaded}: {e}")

        if files_loaded == 0:
            self.player.command(
                "loadfile", 
                f"{self.standby_url}",
                "replace",
                -1,
                {
                "image-display-duration": "86400" #A full day
                }
                )

    def play(self):
        self.player.command("set_property", "pause", False)

    def isActive(self):
        return self.process.poll() is None 

    def _create_process(self):
        loudnorm_params = "lavfi=[loudnorm=I=-16:TP=-1.5:LRA=11]"
        self.process = subprocess.Popen([
                        "mpv",
                        "--fullscreen",
                        "--idle=yes",
                        f"--input-ipc-server={self.socket}",
                        f"--af={loudnorm_params}", 
                        f"--audio-device={self.device_info['audioDevice']}",
                        f"--screen={self.device_info['screen']}", 
                    ])
        
        self.player = MPV(start_mpv=False, ipc_socket=self.socket)

    def reset_player(self):
        if self.isActive():
            self.process.terminate()
            self.process.wait()

        if os.path.exists(self.socket):
            os.remove(self.socket)

        self._create_process()

        self.load_schedule(self.schedule)

    def stop_player(self):
        if self.isActive():
            self.player.command("set_property", "pause", True)

    def shutdown(self):
        print("Cleaning up player...")
        self.player.command("quit")
        self.process.terminate()
        self.process.wait()

        if os.path.exists(self.socket):
            os.remove(self.socket)