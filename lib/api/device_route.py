from flask import Blueprint, json, jsonify, request
import os

def create_device_blue_print(display_provider):
    device_bp = Blueprint('device', __name__, url_prefix='/device')

    @device_bp.route('/available-displays', methods=['GET'])
    def get_available_displays():
        print("Discovering devices...")
        displays = display_provider.discover_displays()
        return jsonify(displays)

    @device_bp.route('/current', methods=['GET'])
    def get_current_display():
        with open('settings.json', 'r', encoding='utf-8') as file:
            deviceInfo = json.load(file)
            return jsonify(deviceInfo['devices'])

    return device_bp