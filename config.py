from dataclasses import dataclass
import os, shutil, yaml
from typing import Any, Type
from path_provider import PathProvider

@dataclass
class Configuration:
    # SERVER
    SERVER_PORT: int = 5555
    SERVER_DEBUG_ENABLED: bool = False

    # SSCA
    SSCA_HOST: str = ""
    SSCA_PORT: int = 0

    # WEBHOOK
    WEBHOOK_API_KEY: str = ""
    WEBHOOK_TOKEN: str = ""
    WEBHOOK_ACTIVE: bool = False

    # SCHEDULER
    DIGEST_FILE_FREQUENCY: int = 5
    MISFIRE_GRACE_TIME: int = 5

    @staticmethod
    def _convert_type(val: Any, typ: Type) -> Any:
        if val is None:
            return None
        # Boolean conversion
        if typ is bool:
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.lower() in ("true", "1", "yes", "on")
            return bool(val)
        # Integer conversion
        if typ is int:
            try:
                return int(val)
            except (ValueError, TypeError):
                return val
        # Float conversion
        if typ is float:
            try:
                return float(val)
            except (ValueError, TypeError):
                return val
        # String conversion
        if typ is str:
            return str(val)
        # Fallback
        return val

    @classmethod
    def from_yaml(cls) -> 'Configuration':
        # Rutas
        config_dir      = PathProvider.config_dir()
        config_path  = PathProvider.get_config_file("config.yaml")
        default_path = PathProvider.get_config_file("default_config.yaml")

        # Asegurarse de que existe el directorio
        os.makedirs(config_dir, exist_ok=True)

        # Si no existe config.yaml, crearla a partir de default_config.yaml
        if not os.path.isfile(config_path):
            if not os.path.isfile(default_path):
                raise FileNotFoundError(
                    f"Falta default_config.yaml en {default_path}"
                )
            shutil.copy(default_path, config_path)

        # Cargar la configuración
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or []


        # Parse each section and block to extract option values
        values = {}
        for section in data or []:
            for block in section.get('blocks', []):
                for opt in block.get('options', []):
                    key = opt.get('id')
                    val = opt.get('value')
                    if key in cls.__annotations__:
                        val = cls._convert_type(val, cls.__annotations__[key])
                        values[key] = val
        return cls(**values)
