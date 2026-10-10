import os, sys, shutil, hashlib

APP_NAME = "Autobot"

# ---------- utilidades runtime (evitar bloqueo de _MEI) ----------
def resource_path(rel: str) -> str:
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, rel)
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, rel)

def _sha256(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def install_bundled_binary(rel_src: str, subdir: str = "bin") -> str:
    """
    Copia un binario del bundle (_MEI) a %LOCALAPPDATA%\\Autobot\\bin (o ~/.Autobot/bin en *nix)
    y devuelve su ruta final.
    """
    src = resource_path(rel_src)
    dst_root = os.path.join(os.getenv("LOCALAPPDATA", os.path.expanduser("~")), APP_NAME, subdir)
    os.makedirs(dst_root, exist_ok=True)
    dst = os.path.join(dst_root, os.path.basename(rel_src))
    if not os.path.exists(dst) or _sha256(src) != _sha256(dst):
        shutil.copy2(src, dst)
    try:
        os.chmod(dst, os.stat(dst).st_mode | 0o111)  # permisos de ejecución (inofensivo en Windows)
    except Exception:
        pass
    return dst

# ---------- preparación binarios externos FUERA de _MEI ----------
def prepare_external_binaries():
    """
    Copia binarios empaquetados (p. ej. webhook_agent) a carpeta persistente
    y expone rutas por variables de entorno para que ProcessManager las use.
    """
    bin_dir = os.path.join(os.getenv("LOCALAPPDATA", os.path.expanduser("~")), APP_NAME, "bin")
    os.makedirs(bin_dir, exist_ok=True)

    exe_name = "webhook_agent.exe" if os.name == "nt" else "webhook_agent"
    rel = os.path.join("files", "bin", exe_name)
    try:
        installed_webhook = install_bundled_binary(rel, subdir="bin")
        os.environ["Autobot_BIN_DIR"] = bin_dir
        os.environ["Autobot_WEBHOOK_AGENT"] = installed_webhook
    except FileNotFoundError:
        pass
