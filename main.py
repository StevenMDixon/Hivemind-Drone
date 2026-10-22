from dotenv import load_dotenv
from flask import Flask
import os
import atexit
from lib.api.player_route import create_player_blue_print
from lib.player.player_manager import PlayerManager

from lib.api.device_route import create_device_blue_print

from lib.display.display_provider import DisplayProvider

from dotenv import load_dotenv
load_dotenv()

PORT = int(os.getenv("PORT", 5000))

app = Flask(__name__)

player = PlayerManager()
atexit.register(player.shutdown)

player.start()

app.register_blueprint(create_player_blue_print(player))

display_provider = DisplayProvider()
app.register_blueprint(create_device_blue_print(display_provider))
print(app.url_map)
os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=PORT)