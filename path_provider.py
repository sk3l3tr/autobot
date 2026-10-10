# path_provider.py
import glob, shutil, json, os, sys, platform, time
from platformdirs import user_data_dir, user_log_dir

APP_NAME   = "Autobot"
APP_AUTHOR = "Autobot"  # En Windows aparece como %APPDATA%\Autobot\Autobot
APP_DATA_SCHEMA_VERSION = "1"   # súbelo cuando cambies estructura inicial

class PathProvider:

    def ensure_user_data_initialized(self):
        marker = os.path.join(self.data_root(), ".initialized.json")
        if os.path.exists(marker):
            try:
                meta = json.load(open(marker, "r", encoding="utf-8"))
                if meta.get("schema_version") == APP_DATA_SCHEMA_VERSION:
                    return  # ✅ ya está
            except Exception:
                pass
        
        # copia config inicial
        src_cfg_dir = os.path.join(self.base_resources(), "files", "config")
        dst_cfg_dir = self.config_dir()
        if os.path.isdir(src_cfg_dir):
            for f in glob.glob(os.path.join(src_cfg_dir, "*")):
                dst = os.path.join(dst_cfg_dir, os.path.basename(f))
                if not os.path.exists(dst):
                    shutil.copy2(f, dst)

        # copia jobs iniciales
        src_jobs_dir = os.path.join(self.base_resources(), "files", "jobs")
        dst_jobs_dir = self.jobs_dir()
        if os.path.isdir(src_jobs_dir):
            for f in glob.glob(os.path.join(src_jobs_dir, "*")):
                dst = os.path.join(dst_jobs_dir, os.path.basename(f))
                if not os.path.exists(dst):
                    shutil.copy2(f, dst)

        # NO copiar automations salvo que tengas plantillas
        os.makedirs(self.robot_dir(), exist_ok=True)

        json.dump(
            {"schema_version": APP_DATA_SCHEMA_VERSION, "ts": time.time()},
            open(marker, "w", encoding="utf-8")
        )


    @staticmethod
    def base_path():
        if getattr(sys, "frozen", False):
            return getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
        return os.path.abspath(os.path.dirname(__file__))

    @staticmethod
    def base_resources():
        if getattr(sys, "frozen", False):
            exe_dir = PathProvider.base_path()
            if sys.platform == "darwin":
                # .app/Contents/MacOS → ../Resources (solo lectura)
                return os.path.abspath(os.path.join(exe_dir, "..", "Resources"))
            else:
                return exe_dir  # carpeta temporal en --onefile (solo lectura efectiva)
        return os.path.abspath(os.path.dirname(__file__))

    # --- NUEVO: raíz de datos de usuario (persistente y escribible) ---
    @staticmethod
    def data_root():
        # Win:  %APPDATA%\Autobot\Autobot
        # macOS: ~/Library/Application Support/Autobot
        # Linux: ~/.local/share/Autobot
        p = user_data_dir(APP_NAME, APP_AUTHOR)
        os.makedirs(p, exist_ok=True)
        return p

    @staticmethod
    def get_logs_dir():
        p = user_log_dir(APP_NAME, APP_AUTHOR)
        os.makedirs(p, exist_ok=True)
        return p

    # --- Todas estas rutas deben pasar a data_root() ---
    @staticmethod
    def robot_dir():
        p = os.path.join(PathProvider.data_root(), "automations")
        os.makedirs(p, exist_ok=True)
        return p

    @staticmethod
    def config_dir():
        p = os.path.join(PathProvider.data_root(), "config")
        os.makedirs(p, exist_ok=True)
        return p

    @staticmethod
    def jobs_dir():
        p = os.path.join(PathProvider.data_root(), "jobs")
        os.makedirs(p, exist_ok=True)
        return p

    @staticmethod
    def get_config_file(filename="config.yaml"):
        return os.path.join(PathProvider.config_dir(), filename)

    @staticmethod
    def get_rules_file():
        return os.path.join(PathProvider.config_dir(), "rules.json")

    @staticmethod
    def get_jobs_file(filename="jobs.yaml"):
        return os.path.join(PathProvider.jobs_dir(), filename)

    # --- Binarios/estáticos: seguir leyendo desde recursos empaquetados ---
    @staticmethod
    def bin_dir():
        return os.path.join(PathProvider.base_resources(), "files", "bin")

    @staticmethod
    def get_webhook_binary():
        base = PathProvider.base_resources()
        os_name = platform.system()
        if os_name == "Windows":
            return os.path.join(base, "files", "bin", "webhook_agent-win.exe")
        elif os_name == "Darwin":
            return os.path.join(base, "files", "bin", "webhook_agent-macos")
        else:
            return os.path.join(base, "files", "bin", "webhook_agent-linux")

    @staticmethod
    def www_static_dir():
        return os.path.join(PathProvider.base_resources(), "files", "www", "autobot-console")

    @staticmethod
    def ssca_agent_script():
        return os.path.join(PathProvider.base_resources(), "ssca_agent", "main.py")

    @staticmethod
    def backend_script():
        return os.path.join(PathProvider.base_resources(), "backend", "main.py")

    @staticmethod
    def scheduler_script():
        return os.path.join(PathProvider.base_resources(), "scheduler", "main.py")

    @staticmethod
    def kiosk_script():
        return os.path.join(PathProvider.base_resources(), "kiosk.py")

    @staticmethod
    def robot_recorder_script():
        return os.path.join(PathProvider.base_resources(), "robotization", "robot_recorder.py")
