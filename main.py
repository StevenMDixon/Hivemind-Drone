from flask import Flask
import os
import atexit
from lib.api.player_route import create_player_blue_print
from lib.player.player_manager import PlayerManager

app = Flask(__name__)

player = PlayerManager()
atexit.register(player.shutdown)

player.start()

app.register_blueprint(create_player_blue_print(player))

os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)