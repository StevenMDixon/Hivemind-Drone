from datetime import datetime
from flask import json
from lib.player.mpv_player import MPVPlayer
from concurrent.futures import ThreadPoolExecutor
import os
from dotenv import load_dotenv

load_dotenv()

MOUNTED_PATH = os.getenv("MountedPath")
STANDBY_URL = os.getenv("StandbyUrl")


def create_players_async(scheduleData):
        with ThreadPoolExecutor(max_workers=len(scheduleData)) as executor:
            return list(executor.map(lambda item: create_player(item), scheduleData))

def create_player(item):
    device = item['device']
    schedule = item['schedule'] if 'schedule' in item else None
    stationNumber = int(device.get('stationNumber'))
    
    startTime = datetime.now().time()

    scheduleItems = []

    if(schedule is not None):
        scheduleJson = json.loads(schedule.get('scheduleJson')) if schedule.get('scheduleJson') is not None else None

        if scheduleJson is not None:
            startTime = datetime.strptime(scheduleJson.get('StartTime'), "%H:%M:%S").time() if scheduleJson.get('StartTime') else datetime.now().time()
            scheduleItems = scheduleJson.get('Items')
            
    mpv_socket = f"/tmp/channel-tv{stationNumber}-mpv.sock"

    if os.path.exists(mpv_socket):
        os.remove(mpv_socket)

    print(MOUNTED_PATH)
    currentDevice = device
    return MPVPlayer(mpv_socket=mpv_socket, device_info=currentDevice, schedule_data=scheduleItems, mountPath=MOUNTED_PATH, startTime=startTime, StandbyUrl=STANDBY_URL)
