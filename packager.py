#!/usr/bin/env python3
import os, sys, platform, subprocess, shutil

# -------------- CONFIGURACIÓN --------------
APP_NAME = "Autobot"
APP_AUTHOR = "SK3L3TØR"

# Rutas relativas al proyecto (ajustar si cambian)
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
FILES_DIR = os.path.join(ROOT_DIR, "files")
PYINSTALLER_SPEC = None  # Lo generaremos sobre la marcha

# Carpeta donde PyInstaller dejará los artefactos
DIST_DIR = os.path.join(ROOT_DIR, "dist")
BUILD_DIR = os.path.join(ROOT_DIR, "build")
SPEC_DIR = os.path.join(ROOT_DIR, "spec")

# Nombre de la carpeta Angular dentro de files/www
NG_OUTPUT_RELATIVE = os.path.join("www", "autobot-console", "browser")

def print_header():
    ascii_art = r"""
 █████  ██    ██ ████████  ██████  ██████   ██████  ████████ 
██   ██ ██    ██    ██    ██  ████ ██   ██ ██  ████    ██    
███████ ██    ██    ██    ██ ██ ██ ██████  ██ ██ ██    ██    
██   ██ ██    ██    ██    ████  ██ ██   ██ ████  ██    ██    
██   ██  ██████     ██     ██████  ██████   ██████     ██    
                                                                    
    .--.      .--.                          .--.      .--.  
:::::::.\::::::::.\::::::::[v3.1.2]::.\::::::::.\::::::::.\:
--'      `--'      `--'                `--'      `--'      `
    """
    print(ascii_art)


def run_command(cmd, cwd=None, env=None):
    print(f">>> Executing: {' '.join(cmd)} (cwd={cwd or os.getcwd()})")
    try:
        subprocess.check_call(cmd, cwd=cwd, env=env)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Execution error: {' '.join(cmd)}\n  Exit code: {e.returncode}")
        sys.exit(1)

def choose_webhook_binary():
    os_name = platform.system()
    if os_name == "Windows":
        src = os.path.join(FILES_DIR, "bin", "webhook_agent-win.exe")
        dst_name = "webhook_agent.exe"
    elif os_name == "Darwin":
        src = os.path.join(FILES_DIR, "bin",  "webhook_agent-macos")
        dst_name = "webhook_agent"
    elif os_name == "Linux":
        src = os.path.join(FILES_DIR, "bin", "webhook_agent-linux")
        dst_name = "webhook_agent"
    else:
        print(f"[WARN] Unknown platform'{os_name}'. webhook_agent binary will not be copied.")
        return None

    if not os.path.isfile(src):
        print(f"[ERROR] webhook_agent binary not found at: {src}")
        sys.exit(1)

    return dst_name


def collect_datas():
    datas = []

    # 1) Copiar toda la carpeta 'files' 
    #   → En el bundle, quedará en 'files/*'
    src_files = os.path.join(ROOT_DIR, "files")
    if os.path.isdir(src_files):
        datas.append(f"{src_files}{os.pathsep}files")
    else:
        print(f"[WARNING] The folder 'files/' does not exists.")
    
    # 2) Copiar carpeta 'ssca_agent/' completa (para que el ejecutable pueda lanzar ssca_agent/main.py)
    src_ssca = os.path.join(ROOT_DIR, "ssca_agent")
    if os.path.isdir(src_ssca):
        datas.append(f"{src_ssca}{os.pathsep}ssca_agent")
    else:
        print(f"[WARNING] 'ssca_agent/' does not exists.")

    # 3) Copiar carpeta 'backend/' completa
    src_backend = os.path.join(ROOT_DIR, "backend")
    if os.path.isdir(src_backend):
        datas.append(f"{src_backend}{os.pathsep}backend")
    else:
        print(f"[WARNING] 'backend/' does not exists.")

    # 4) Copiar carpeta 'scheduler/' completa
    src_sched = os.path.join(ROOT_DIR, "scheduler")
    if os.path.isdir(src_sched):
        datas.append(f"{src_sched}{os.pathsep}scheduler")
    else:
        print(f"[WARNING] 'scheduler/' does not exists.")

    # 5) Copiar carpeta 'robotization/' completa
    src_sched = os.path.join(ROOT_DIR, "robotization")
    if os.path.isdir(src_sched):
        datas.append(f"{src_sched}{os.pathsep}robotization")
    else:
        print(f"[WARNING] 'robotization/' does not exists.")

    # 6) Copiar ficheros en ./
    # path_provider.py
    for fname in ("process_manager.py", "config.py", "process_killer.py", "kiosk.py"):
        full = os.path.join(ROOT_DIR, fname)
        if os.path.isfile(full):
            datas.append(f"{full}{os.pathsep}{fname}")
        else:
            print(f"[WARNING]'{fname}' does not exists.")

    return datas


def build_with_pyinstaller():
    print("\nPackaging with PyInstaller...")

    # 2) detecta el icono según plataforma
    if sys.platform == "win32":
        icon_file = os.path.join(ROOT_DIR, "resources", "icon.ico")
    else:
        icon_file = os.path.join(ROOT_DIR, "resources", "icon.icns")

    # 1) Asegurar que pyinstaller esté instalado
    try:
        import PyInstaller
    except ImportError:
        print("[ERROR] PyInstaller no está instalado. Instala con: pip install pyinstaller")
        sys.exit(1)

    # Directorios de salida de PyInstaller
    if os.path.isdir(DIST_DIR):
        shutil.rmtree(DIST_DIR)
    if os.path.isdir(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    if os.path.isdir(SPEC_DIR):
        shutil.rmtree(SPEC_DIR)
    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(SPEC_DIR, exist_ok=True)

    # Base de comando PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noupx",                                                                      # Para eliminar detección como malware
        "--noconfirm",
        "--clean",
        f"--icon={icon_file}",
        "--log-level=WARN",
        "--onefile",                                                                    # --onedir para debubbing, --onefile para release
        "--windowed",
        "--osx-bundle-identifier=com.sk3l3t0r.autobot",
        f"--name={APP_NAME}",                                                           # Nombre base del ejecutable
        "--hidden-import=webview",                                                      # Para PyWebView (kiosk.py)
        "--hidden-import=flask_cors",                                                   # Por si Flask-CORS no se detecta solo
        f"--paths={ROOT_DIR}",                                                          # Asegura que tu raíz del proyecto esté en sys.path al analizar,
        f"--version-file={os.path.join(ROOT_DIR, 'resources', 'version_info.txt')}"     # Fichero de versiones y metadatos
    ]

    # 2) Incluir todos los datos (carpetas/archivos)
    # ==== EXTRA PARA WINDOWS: dependencias problemáticas ====
    if sys.platform == "win32":
        # Multiprocessing/pywin32 y dinámicos comunes en automatización GUI
        win_hidden = [
            "multiprocessing.popen_spawn_win32",
            "win32timezone",
            "pkg_resources",  # por si usamos entry points/metadata
        ]
        for m in win_hidden:
            cmd.append(f"--hidden-import={m}")

        # Recoge submódulos + data + binarios de libs típicas de GUI/visión
        collect_all_pkgs = [
            "pyautogui",
            "pywin32",      # win32api/win32con/… y DLLs
        ]
        for p in collect_all_pkgs:
            cmd.append(f"--collect-all={p}")  # requiere PyInstaller 6.x

        # Si usas tesseract-ocr o similares, añade su ruta bin como add-binary
        # cmd.append("--add-binary=C:\\ruta\\a\\tesseract.exe;tesseract")

    datas = collect_datas()
    for d in datas:
        cmd.append(f"--add-data={d}")

    # 4) Entry point
    cmd.append(os.path.join(ROOT_DIR, "main.py"))

    # 5) Ejecutamos PyInstaller
    run_command(cmd, cwd=ROOT_DIR)

def _move_build_folders():
    _final_dist_folder: str = "distribution"
    _routes_to_move = ["Autobot.spec", "build", "spec", "dist"]

    print(f'Moving generated files/folders into {_final_dist_folder}...')
    if os.path.exists(_final_dist_folder):
        shutil.rmtree(_final_dist_folder)

    os.makedirs(_final_dist_folder, exist_ok=True)

    for _route in _routes_to_move:
        _destination_path = f"{_final_dist_folder}/{_route}"
        _source_route_exists = os.path.exists(_route)

        if _source_route_exists:
            shutil.move(_route, _destination_path)

def main():
    # Python >= 3.9
    if sys.version_info < (3, 9):
        print("[ERROR] Necesitas Python 3.9 o superior para empaquetar.")
        sys.exit(1)

    print_header()
    print(f"Detected platform: {platform.system()} (arch: {platform.machine()})")

    # pyinstaller
    build_with_pyinstaller()

    # move files
    _move_build_folders()

    print("\nCompleted! Your app is located here:")
    if platform.system() == "Windows":
        print("  distribution/dist/Autobot.exe")
    else:
        print("  distribution/dist/Autobot.app" if platform.system() == "Darwin" else "  distribution/dist/Autobot")


if __name__ == "__main__":
    main()