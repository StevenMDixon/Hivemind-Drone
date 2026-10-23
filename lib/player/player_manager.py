from dotenv import load_dotenv
import os
import requests
import json
import threading
from datetime import datetime
from lib.player.player_factory import create_players_async, create_player

load_dotenv()

HOST_NAME = os.getenv("HostName")
TARGET_URL = os.getenv("HivemindUrl")
SCHEDULE_PATH = "/api/drone/schedules/"
REGISTER_PATH = "/api/drone/register"
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

        self.players = create_players_async(self.map_device_to_schedule())

    def start(self):
        self.stop_event.clear()

        self.thread = threading.Thread(
            target=self.run,
            daemon=True
        )

        self.thread.start()

    def map_device_to_schedule(self):
        schedule_map = {}

        for schedule in self.schedule_data or []:
            station_number = schedule['stationNumber']
            schedule_map[int(station_number)] = schedule

        mapping = []
        for device in self.device_info:
            station_number = device['stationNumber']
            
            if int(station_number) in schedule_map:
                mapping.append({
                    'device': device,
                    'schedule': schedule_map[int(station_number)]
                })
            else:
                mapping.append({
                    'device': device,
                    'schedule': None
                })
        return mapping  

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
                        player['player'].load_schedule(player['schedule'])
                    if player['action'] == 'remove':
                        player['player'].shutdown()
                        self.players.remove(player['player'])
                    if player['action'] == 'new':
                        self.players.append(create_player(player['stationData']))

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
        
        try:
            response = requests.get(TARGET_URL + SCHEDULE_PATH + str(id) + query)
            if response.status_code == 200:
                return response.json()
        except requests.RequestException as e:
            print("Error fetching drone data:", e)
        return None

    def get_drone_info_from_server(self, hostname):
        payload = {
            "hostName": hostname
        }

        try:
            response = requests.post(TARGET_URL + REGISTER_PATH, json=payload)
            if response.status_code == 200:
                return response.json()
        except requests.RequestException as e:
            print("Error registering drone:", e)
        return {'id': None}
    
    def players_to_update(self, newSchedule):
        results = []

        for player in self.players:
            currentStationNumber = player.device_info['stationNumber']
            matchedPlayer = next((item for item in newSchedule if int(item.get('stationNumber')) == int(currentStationNumber)), None)
            print(matchedPlayer['stationNumber'])
            if matchedPlayer is None:
                results.append({'player': player, 'action': 'remove', 'schedule': None})

        for item in newSchedule:
            currentStationNumber = int(item.get('stationNumber'))
            print(currentStationNumber)
            matchedPlayer = next((p for p in self.players if int(p.device_info['stationNumber']) == int(currentStationNumber)), None)
            print(matchedPlayer)
            
            schedule_data = json.loads(item.get('scheduleJson'))

            if matchedPlayer and matchedPlayer.schedule != schedule_data['Items']:
                results.append({'player': matchedPlayer, 'action': 'update', 'schedule': schedule_data['Items']})

            elif not matchedPlayer:
                results.append({'player': None, 'action': 'new', 'schedule': None, 'stationData': item})

        return results
    