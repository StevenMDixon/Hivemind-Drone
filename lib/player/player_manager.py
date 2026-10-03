from dotenv import load_dotenv
import os
import requests
import json
from python_mpv_jsonipc import MPV
import threading
from datetime import datetime
from lib.player.mpv_player import MPVPlayer
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

HOST_NAME = os.getenv("HostName")
TARGET_URL = os.getenv("HivemindUrl")
SCHEDULE_PATH = "/api/drone/schedules/"
REGISTER_PATH = "/api/drone/register"
MOUNTED_PATH = os.getenv("MountedPath")
STANDBY_URL = os.getenv("StandbyUrl")
POLLING_DELAY = int(os.getenv("PollingDelay", 15))

class PlayerManager:
    def __init__(self):
        self.device_info = None
        self.schedule_data = None
        self.players = []

        self.stop_event = threading.Event()
        self.thread = None

        with open('settings.json', 'r', encoding='utf-8') as file:
            deviceInfo = json.load(file)
            self.device_info = deviceInfo['devices']

        self.drone_info = self.get_drone_info_from_server(HOST_NAME)
        self.schedule_data = self.get_drone_data_from_server(self.drone_info['id']) or []

        self.create_players_async(self.schedule_data)

    def start(self):
        self.stop_event.clear()

        self.thread = threading.Thread(
            target=self.run,
            daemon=True
        )

        self.thread.start()

    def run(self):
        while not self.stop_event.is_set():
            try:
                self.poll()
            except Exception as e:
                print(f"PlayerManager error: {e}")

            self.stop_event.wait(POLLING_DELAY)

    def shutdown(self):
        self.stop_event.set()

        if self.thread is not None:
            self.thread.join(timeout=5)

        for player in self.players:
            player.shutdown()

        self.players.clear()

    def poll(self):
            currentData = self.get_drone_data_from_server(self.drone_info['id']) or []

            updated = currentData != self.schedule_data

            # Did we update?
            if updated:
                print("Schedule data updated")

                # we only want to change the players if the schedule has actually been updated
                players_to_update = self.players_to_update(currentData)
                
                for player in players_to_update:
                    if player['action'] == 'update':
                        print(f"updating")
                        player['player'].load_schedule(player['schedule']['items'])
                    if player['action'] == 'remove':
                        player['player'].shutdown()
                        self.players.remove(player['player'])
                    if player['action'] == 'new':
                        self.players.append(self.create_player(player['schedule']))

                self.schedule_data = currentData
                return


            print("polling for player status updates")
            #Check players' status and update schedule if needed
            for player in self.players:
                if player is  not None and not player.isActive():
                    print(f"Player is not active, resetting Player")
                    player.reset_player()

    def get_player_status(self):
        results = {}
        for i, player in enumerate(self.players):
            if player is None:
                continue
            status = 'active' if player.isActive() else 'inactive'
            results[f'player_{i}'] = status
            print(f"Player status: {status}")
        return results

    def kill_players(self):
        for player in self.players:
            if(player):
                player.shutdown()
        self.players.clear()

    def start_player_by_id(self, station_id: int):
        for player in self.players:
            if player.device_info['stationNumber'] == station_id:
                player.play()

    def start_players(self):
        for player in self.players:
            if(player):
                player.play()

    def stop_players(self):
        for player in self.players:
            if(player):
                player.stop_player()

    def stop_player_by_id(self, station_id: int):
        for player in self.players:
            if player.device_info['stationNumber'] == station_id:
                if(player):
                    player.stop_player()

    def restart_players(self):
        for player in self.players:
            if(player):
                player.reset_player()

    def restart_player_by_id(self, station_id: int):
        for player in self.players:
            if player.device_info['stationNumber'] == station_id:
                if(player):
                    player.reset_player()

    def get_drone_data_from_server(self, id):
        query = f'?date={datetime.now().strftime("%Y-%m-%d")}'
    
        response = requests.get(TARGET_URL + SCHEDULE_PATH + str(id) + query)
        if response.status_code == 200:
            return response.json()
        return None

    def get_drone_info_from_server(self, hostname):
        payload = {
            "hostName": hostname
        }

        print("Registering drone with hostname:", hostname)
        print("Payload for registration:", payload)
        print("Target URL for registration:", TARGET_URL + REGISTER_PATH)
        print(payload)

        response = requests.post(TARGET_URL + REGISTER_PATH, json=payload)
        if response.status_code == 200:
            return response.json()
        return {'id': None}

    def create_players_async(self, scheduleData):
        with ThreadPoolExecutor(max_workers=len(scheduleData)) as executor:
            self.players = list(executor.map(lambda item: self.create_player(item), scheduleData))

    def create_player(self, item):
        stationNumber = int(item.get('stationNumber'))
        scheduleJson = json.loads(item.get('scheduleJson')) if item.get('scheduleJson') else None
        startTime = datetime.strptime(scheduleJson.get('startTime'), "%H:%M:%S").time() if scheduleJson.get('startTime') else datetime.now().time()

        mpv_socket = f"/tmp/channel-tv{stationNumber}-mpv.sock"

        if os.path.exists(mpv_socket):
            os.remove(mpv_socket)

        currentDevice = next((u for u in self.device_info if u['stationNumber'] == stationNumber), None)

        if(currentDevice != None):
            return MPVPlayer(mpv_socket=mpv_socket, device_info=currentDevice, schedule_data=scheduleJson.get('items') if scheduleJson else None, mountPath=MOUNTED_PATH, startTime=startTime, StandbyUrl=STANDBY_URL)

    def players_to_update(self, newSchedule):
        results = []

        for player in self.players:
            currentStationNumber = player.device_info['stationNumber']
            matchedPlayer = next((item for item in newSchedule if int(item.get('stationNumber')) == currentStationNumber), None)
            if matchedPlayer is None:
                results.append({'player': player, 'action': 'remove', 'schedule': None})

        for item in newSchedule:
            currentStationNumber = int(item.get('stationNumber'))
            
            matchedPlayer = next((p for p in self.players if p.device_info['stationNumber'] == currentStationNumber), None)

            newSchedule = json.loads(item.get('scheduleJson'))

            if matchedPlayer and matchedPlayer.schedule != newSchedule['items']:
                results.append({'player': matchedPlayer, 'action': 'update', 'schedule': newSchedule})

            elif not matchedPlayer:
                results.append({'player': None, 'action': 'new', 'schedule': item})

        return results
    