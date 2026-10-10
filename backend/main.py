import argparse, os, multiprocessing, uuid, logging
multiprocessing.set_start_method('spawn', force=True)

from flask import Flask, jsonify, send_from_directory
from loguru import logger
from flask_cors import CORS

from path_provider import PathProvider

from .routes.action import action_bp
from .routes.config import config_bp
from .routes.robot import robot_bp
from .routes.schedule import schedule_bp
from .routes.logs import logs_bp

class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())

def main():
    parser = argparse.ArgumentParser()

    # server params
    parser.add_argument('--port', type=int)
    parser.add_argument('--static-folder', type=str)
    parser.add_argument('--jobs-file-path', type=str)
    parser.add_argument('--robots-dir-path', type=str)
    parser.add_argument('--cors-origin', action='append', required=True)
    parser.add_argument('--debug', action='store_true')

    # socket params
    parser.add_argument('--socket-host', type=str)
    parser.add_argument('--socket-port', type=int)

    args = parser.parse_args()

    logger.info("[BACKEND] Starting application ...")
    app = create_app(args)
    app.run(port=args.port, debug=args.debug, use_reloader=False)

def create_app(args):
    prefix = '/api'
    blueprints = [
        config_bp,
        action_bp,
        robot_bp,
        schedule_bp,
        logs_bp,
    ]

    app = Flask(__name__, static_folder=args.static_folder)
    CORS(app, resources={r"/*": {"origins": args.cors_origin}})

    # --- Logger cofig ---
    logs_path = PathProvider.get_logs_dir()
    os.makedirs(logs_path, exist_ok=True)
    log_file = os.path.join(logs_path, "fl4sk.log")

    # Quitar el sink por defecto (stderr) y añadir nuestro fichero
    logger.remove()
    logger.add(
        log_file,
        rotation="1 MB",     # rota cada X MB
        retention=3,          # conserva últimos X archivos
        format="{time:YYYY-MM-DD HH:mm:ss} {level:<8} {message}"
    )

    # Interceptar todo el logging de Python y reenviarlo a Loguru
    intercept = InterceptHandler()
    logging.root.handlers = [intercept]
    logging.root.setLevel(logging.INFO)

    # Flask logger → Loguru
    app.logger.handlers = [intercept]
    app.logger.setLevel(logging.INFO)

    # Werkzeug (requests) → Loguru
    werk = logging.getLogger("werkzeug")
    werk.handlers = [intercept]
    werk.setLevel(logging.INFO)
    # -----------------------------------

    # Guardamos la configuración personalizada en app.config
    app.config['CUSTOM_ARGS'] = args

    # Blueprint register
    for endpoint in blueprints:
        app.register_blueprint(endpoint, url_prefix=prefix)

    static_path = os.path.abspath(args.static_folder)

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_static(path):
        full_path = os.path.join(static_path, path)
        if path != "" and os.path.exists(full_path):
            return send_from_directory(static_path, path)
        if "." in path:
            return jsonify(error="Static files not found"), 404
        return send_from_directory(static_path, 'index.html')

    return app



if __name__ == '__main__' and multiprocessing.current_process().name == "MainProcess":
    multiprocessing.freeze_support()
    main()