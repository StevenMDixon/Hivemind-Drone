from flask import Blueprint, jsonify, request

def create_player_blue_print(player):
    player_bp = Blueprint('player', __name__, url_prefix='/player')

    @player_bp.route('/start')
    def start_player() -> str:
        player.start_players()
        return jsonify({"status": "started"})

    @player_bp.route('/start/<int:station_id>')
    def start_player_by_id(station_id: int) -> str:
        player.start_player_by_id(station_id)
        return jsonify({"status": "started"})

    @player_bp.route('/stop')
    def stop_player() -> str:
        player.stop_players()
        return jsonify({"status": "stopped"})

    @player_bp.route('/stop<int:station_id>')
    def stop_player_by_id(station_id: int) -> str:
        player.stop_player_by_id(station_id)
        return jsonify({"status": "stopped"})

    @player_bp.route('/status')
    def get_player_status() -> str:
        return jsonify(player.get_player_status())

    # @player_bp.route('/kill')
    # def kill_player() -> str:
    #     player.kill_players()
    #     return jsonify({"status": "killed"})

    @player_bp.route('/restart')
    def restart_player() -> str:
        player.restart_players()
        return jsonify({"status": "restarted"})

    @player_bp.route('/restart/<int:station_id>')
    def restart_player_by_id(station_id: int) -> str:
        player.restart_player_by_id(station_id)
        return jsonify({"status": "restarted"})

    return player_bp