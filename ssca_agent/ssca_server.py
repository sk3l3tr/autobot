import socket, threading , os

from loguru import logger

from path_provider import PathProvider

# SERVER SOCKET COMMUNICATION AGENT (SSCA)
class SSCAServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.clients = []
        self.lock = threading.Lock()
        self.shutdown_flag = threading.Event()
        self.server_socket = None

    def start(self):
        # ─── Configuración de Loguru ────────────────────────────────────────────────
        # Carpeta de logs junto al script
        _logs_dir = PathProvider.get_logs_dir()
        os.makedirs(_logs_dir, exist_ok=True)

        # Eliminamos el sink por defecto y añadimos uno a fichero con rotación y retención
        logger.remove()
        logger.add(
            os.path.join(_logs_dir, "ssc4_s3rv3r.log"),
            rotation="1 MB",      # rota cada X MB
            retention=3,          # conserva los últimos X archivos
            format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}"
        )
        # ─────────────────────────────────────────────────────────────────────────────

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        self.server_socket.settimeout(1.0)  # Non-blocking accept
        logger.info(f"[SSCA] Listening at {self.host}:{self.port}")

        try:
            while not self.shutdown_flag.is_set():
                try:
                    conn, addr = self.server_socket.accept()
                    logger.info(f"[SSCA] New connection: {addr}")
                    with self.lock:
                        self.clients.append(conn)
                    t = threading.Thread(target=self.handle_client,
                                         args=(conn, addr),
                                         daemon=True)
                    t.start()
                except socket.timeout:
                    continue
        finally:
            self.shutdown()

    def handle_client(self, conn, addr):
        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                # <-- decodificamos primero
                message = data.decode('utf-8').strip()
                logger.info(f"[SSCA] Received '{message}' from {addr}")
                self.broadcast(message, conn)
        except Exception as e:
            logger.error(f"[SSCA] Error handling client {addr}: {e}")
        finally:
            with self.lock:
                if conn in self.clients:
                    self.clients.remove(conn)
            conn.close()
            logger.info(f"[SSCA] {addr} disconnected")

    def broadcast(self, message, sender_conn):
        with self.lock:
            for client in list(self.clients):
                if client is not sender_conn:
                    try:
                        # como `message` ya es str, lo codificamos aquí
                        client.sendall(message.encode('utf-8'))
                    except Exception as e:
                        logger.error(f"[SSCA] Error sending to a client: {e}")
                        client.close()
                        self.clients.remove(client)
    
    def shutdown(self):
        """Gracefully shutdown the server"""
        self.shutdown_flag.set()
        with self.lock:
            for client in list(self.clients):
                try:
                    client.close()
                except Exception:
                    pass
            self.clients.clear()
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        logger.info("[SSCA] Server shutdown complete")
