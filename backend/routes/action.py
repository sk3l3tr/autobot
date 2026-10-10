from flask import Blueprint, request, jsonify, current_app
import socket, json, webbrowser

action_bp = Blueprint('action', __name__)

# Send orders to the local socket from Angular
@action_bp.route('/action', methods=['POST'])
def action():
    args = current_app.config['CUSTOM_ARGS']

    try:
        # 1. Leemos y validamos el JSON entrante
        data = request.get_json(force=True)
        action_name = data.get('action')
        if not action_name:
            return jsonify(error='Action not provided'), 400

        # 2. Construimos el payload con action + kwargs (vacío si no hay)
        payload = {
            'action': action_name,
            'kwargs': data.get('kwargs', {})
        }
        message = json.dumps(payload)

        # 3. Enviamos por socket al backend TCP
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((args.socket_host, args.socket_port))
            s.sendall(message.encode('utf-8'))

        return jsonify(status='OK'), 200

    except ConnectionRefusedError:
        return jsonify(error='Could not connect to the server', message="Could not connect to SSCA server."), 500

    except json.JSONDecodeError:
        return jsonify(error='Invalid JSON'), 400

    except Exception as e:
        return jsonify(error=f'{str(e)}'), 500
    
@action_bp.route('/open-url', methods=['POST'])
def open_url():
    try:
        data = request.get_json(force=True)
        url = data.get('url')
        if not url:
            return jsonify(error='URL not provided'), 400
        
        webbrowser.open(url)
        return jsonify(status='OK'), 200
    except Exception as e:
        return jsonify(error=f'{str(e)}'), 500