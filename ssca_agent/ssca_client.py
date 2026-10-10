import socket
import threading
import json

class SSCAClient:
    def __init__(self, host, port, actions=None):
        self.host = host
        self.port = port
        self.actions = actions or {}
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        try:
            self.client_socket.connect((self.host, self.port))
            print(f"[SCCA][CLI] Connected with server at {self.host}:{self.port}")
            listener = threading.Thread(target=self.listen_to_server, daemon=True)
            listener.start()
        except Exception as e:
            print(f"[SCCA][CLI] Error: Could not connect to the server: {e}")

    def listen_to_server(self):
        try:
            while True:
                raw = self.client_socket.recv(4096)
                if not raw:
                    # servidor cerró la conexión
                    break

                text = raw.decode('utf-8').strip()
                # Parseamos únicamente JSON
                try:
                    msg = json.loads(text)
                    cmd    = msg['action']
                    kwargs = msg.get('kwargs', {})  # {} por defecto
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"[SCCA][CLI] Error: invalid message: {e}")
                    continue

                action = self.actions.get(cmd.lower())
                if not action:
                    print(f"[SCCA][CLI] Warning: Unknown command: {cmd}")
                    continue

                # Llamada dinámica usando solo kwargs
                try:
                    action(**kwargs)
                except TypeError as e:
                    print(f"[SCCA][CLI] Error: invalid args for '{cmd}': {e}")

        except Exception as e:
            print(f"[SCCA][CLI] Error: Error receiving messages: {e}")
        finally:
            self.client_socket.close()
            print("[SCCA][CLI] Client disconnected")
