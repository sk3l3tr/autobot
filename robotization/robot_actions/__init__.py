import pkgutil
import importlib

# Registro dinámico de comandos
typedef = dict[str, type]
registry: typedef = {}

def register(action_name: str, cls: type):
    registry[action_name] = cls

# Auto-importar todos los módulos del paquete para poblar el registro
def _load_actions():
    for finder, name, ispkg in pkgutil.iter_modules(__path__):
        importlib.import_module(f"{__name__}.{name}")

_load_actions()