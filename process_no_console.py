
import os, subprocess


CREATE_NO_WINDOW      = 0x08000000
DETACHED_PROCESS      = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200  # opcional, útil para no heredar señales

def _apply_no_console_kwargs(kwargs: dict) -> dict:
    if os.name != "nt":
        return kwargs
    kw = dict(kwargs)
    # STARTUPINFO oculto
    si = kw.get("startupinfo") or subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0  # SW_HIDE
    kw["startupinfo"] = si

    # Nunca crear/adjuntar consola
    flags = kw.get("creationflags", 0)
    flags |= (CREATE_NO_WINDOW | DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP)
    kw["creationflags"] = flags

    # Redirigir SIEMPRE IO para no heredar consola de nadie
    kw.setdefault("stdin", subprocess.DEVNULL)
    kw.setdefault("stdout", subprocess.DEVNULL)
    kw.setdefault("stderr", subprocess.DEVNULL)

    # shell=True también queda oculto con los flags de arriba
    return kw

# Parche global de subprocess (evita consolas aunque otro módulo use subprocess a pelo)
def _patch_subprocess_no_console():
    if os.name != "nt" or os.environ.get("AUTOBOT_NO_PATCH_SUBPROCESS") == "1":
        return

    _orig_run = subprocess.run
    _orig_popen = subprocess.Popen

    def _patched_run(*args, **kwargs):
        return _orig_run(*args, **_apply_no_console_kwargs(kwargs))

    class _PatchedPopen(subprocess.Popen):
        def __init__(self, args, **kwargs):
            super().__init__(args, **_apply_no_console_kwargs(kwargs))

    subprocess.run = _patched_run    # type: ignore
    subprocess.Popen = _PatchedPopen # type: ignore

    # ---- IMPORTANTE: evitar cmd.exe de os.system (pestañea) ----
    import os as _os
    _orig_system = _os.system
    def _silent_system(cmd):
        # replicamos semántica de retorno de os.system
        res = subprocess.run(cmd, shell=True, check=False, **_apply_no_console_kwargs({}))
        # os.system retorna (exitcode << 8) en *nix; en Win vale con exit code directo
        return res.returncode
    _os.system = _silent_system