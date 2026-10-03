from threading import Timer
import subprocess
import os

from urllib.parse import urljoin
from pathlib import Path
from python_mpv_jsonipc import MPV
from datetime import datetime
from PIL import Image

class MPVPlayer:

    def __init__(self, mpv_socket, device_info, schedule_data, mountPath, startTime, StandbyUrl):
        self.socket = mpv_socket
        self.mounted_path = mountPath
        self.standby_url = StandbyUrl

        self.schedule = schedule_data
        self.start_time = startTime

        self.bug_display = True 
        self.bug_id = 1
        self.rating_display = True
        self.rating_id = 2
        self.bug_id = 1

        if os.path.exists(mpv_socket):
            os.remove(mpv_socket)

        self.device_info = device_info

        self._create_process()

        self.load_schedule(schedule_data)

        self.add_listeners()

    def handle_aspect_ratio(self, hasBlackBars):
        if(hasBlackBars):
            self.player.command("set_property", "video-aspect-override", 4 / 3)
            self.player.command("set_property", "video-scale-x", "1.333333333")
        else:
            self.player.command("set_property", "video-aspect-override", -1)
            self.player.command("set_property", "video-scale-x", "1.0")

    def handle_bug(self, hasBug):
        if(hasBug):
            relative_path = "./resources/bug_overlays/White_TV-Y_icon.png"
            overlay_data = self.get_overlay_data(relative_path)
            self.player.command("overlay_add", self.bug_id, 100, 50,  overlay_data.pixel_data, 0, "bgra", overlay_data.width, overlay_data.height, overlay_data.stride)
            self.bug_display = True
        else:
            self.player.command("overlay_remove", self.bug_id)
            self.bug_display = False

    def handle_rating(self, rating):
        if(rating != ""):
            relative_path = f"./resources/rating_overlays/png/{rating.replace('_', '-')} icon.png"
            print(relative_path)
            overlay_data = self.get_overlay_data(relative_path)
            self.player.command("overlay_add", self.rating_id, 100, 50,  overlay_data.pixel_data, 0, "bgra", overlay_data.width, overlay_data.height, overlay_data.stride)
            self.rating_display = True

            duration = 15 
            Timer(
                duration,
                lambda: self.handle_rating(""),
            ).start()
        else:
            self.player.command("overlay_remove", self.rating_id)
            self.rating_display = False

    def add_listeners(self):
        @self.player.property_observer("playlist-pos")
        def playlist_changed(name, value):
            if(name == "playlist-pos" and value > -1):
                current_item = self.schedule[value] if value < len(self.schedule) else None

                hasBlackBars = current_item.get('hasBlackBars') if current_item else False
                self.handle_aspect_ratio(hasBlackBars)

                hasRating = current_item.get('rating') if current_item else False
                self.handle_rating(hasRating)

                hasBug = current_item.get('hasBug') if current_item else False
                self.handle_bug(hasBug)

            print("Now playing:", value)

        @self.player.event_callback("shutdown")
        def on_shutdown(event):
            print("MPV is shutting down")

        # @self.player.event_callback("end-file")
        # def on_end_file(event):
        #     reason = event.get("reason")
        #     print("end-file event:", reason)

    def load_schedule(self, schedule_data):
        currentTime = datetime.now()
        #daily_start_time = datetime.now().replace(hour=self.start_time.hour, minute=self.start_time.minute, second=self.start_time.second)
        daily_start_time = datetime.now()
        ff_time = (currentTime - daily_start_time).total_seconds()

        print(f"currentTime: {currentTime}")
        print(f"daily_start_time: {daily_start_time}")
        print(f"ff_time: {ff_time}")

        files_loaded = 0

        if ff_time < 0:
            self.player.command(
                "loadfile", 
                f"{self.standby_url}",
                "replace",
                -1,
                {
                    "image-display-duration": f"{ff_time * -1}"
                }
            )
            
            print(f"Fast-forwarded time applied: {ff_time * -1}")
            ff_time = 0
            files_loaded += 1

        schedule_duration = 0;
        for item in schedule_data:
            startTime = item.get('startTime') /1000 if item.get('startTime') else 0
            endTime = item.get('stopTime') / 1000 if item.get('stopTime') else 0

            duration = endTime - startTime
            schedule_duration += duration

            if(ff_time > duration):
                ff_time -= duration
                print(f"Skipping item {files_loaded}:{duration} due to fast-forward time: {ff_time}")
                continue

            if(ff_time > 0):
                startTime = startTime + ff_time
                # print(f"Adjusted start time: {startTime}, end time: {endTime}, duration: {duration}")
                ff_time = 0

            try:
                se_command = f"start={startTime},length={endTime - startTime}"

                if 'http' in item.get('path', ''):
                    se_command = f"demuxer-readahead-secs=0,demuxer-lavf-o=live_start_index=0,length={endTime - startTime}" 
                    print(f"Scheduling item {se_command}");

                self.player.command(
                        "loadfile", 
                        self.process_path(item),
                        "replace" if files_loaded == 0 else "append",
                        -1,
                        se_command
                        )
                files_loaded += 1
            except Exception as e:
                print(f"Error scheduling item {files_loaded}: {e}")

        if files_loaded == 0 or schedule_duration < 86400:
            self.player.command(
                "loadfile", 
                f"{self.standby_url}",
                "replace" if files_loaded == 0 else "append",
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

        self.bug_display = False
        self.rating_display = False

        self.add_listeners()

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


    def process_path(self, item):
        if 'http' in item.get('path', ''):
            return item.get('path')
        return os.path.join(self.mounted_path, item.get('path').lstrip('/')) if item.get('path') else None

    class OverlayData:
        def __init__(self, pixel_data, width, height, stride):
            self.pixel_data = pixel_data
            self.width = width
            self.height = height
            self.stride = stride

    def get_overlay_data(self, path):
    
        # Load and decode the PNG.
        image = Image.open(path).convert("RGBA")

        width = 128  # Set the desired width for the overlay
        ratio = width / image.width
        height = round(image.height * ratio)

        image = image.resize((width, height), Image.Resampling.LANCZOS)
        
        width, height = image.size

         # RGBA -> BGRA
        r, g, b, a = image.split()
        a = a.point(lambda i: i * 0.5)
        image = Image.merge("RGBA", (b, g, r, a))

        pixel_data = image.tobytes()

        # Each row is width * 4 bytes for BGRA.
        stride = width * 4

        overlay_file = Path("overlay.raw")
        overlay_file.write_bytes(pixel_data)

        return self.OverlayData(
            pixel_data=str(overlay_file),
            width=width,
            height=height,
            stride=stride
        )