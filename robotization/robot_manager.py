import os
import threading

from robotization.robot_file_ops import RobotFileOps
from robotization.workflow_engine import WorkflowEngine
from robotization.system_controller import get_system_controller

from loguru import logger

from path_provider import PathProvider

class RobotManager:
    def __init__(self):
        self.automations_dir = PathProvider.robot_dir()
        self.file_ops = RobotFileOps()
        self.controller = get_system_controller()
        self._stop_event = threading.Event()

        # ─── Configuración de Loguru ────────────────────────────────────────────────
        # Carpeta de logs junto al script
        _logs_dir = PathProvider.get_logs_dir()
        os.makedirs(_logs_dir, exist_ok=True)

        # Eliminamos el sink por defecto y añadimos uno a fichero con rotación y retención
        logger.remove()
        logger.add(
            os.path.join(_logs_dir, "r0b0t_m4n4g3r.log"),
            rotation="1 MB",      # rota cada X MB
            retention=3,           # conserva los últimos X archivos
            format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}"
        )
        # ─────────────────────────────────────────────────────────────────────────────

    @staticmethod
    def normalize_automation_name(name: str) -> str:
        if not name.endswith('.yaml'):
            return f'{name}.yaml'
        return name

    def list_automations(self) -> list[str]:
        return sorted(
            os.path.splitext(filename)[0]
            for filename in os.listdir(self.automations_dir)
            if filename.lower().endswith('.yaml')
            and os.path.isfile(os.path.join(self.automations_dir, filename))
        )

    def run_automation(self, name) -> bool:
        name = self.normalize_automation_name(name)
        self._stop_event.clear()

        path = os.path.join(self.automations_dir, name)
        if not os.path.isfile(path):
            logger.info(f'[ROBOT] Manager could not find the automation named {name} at {self.automations_dir}')
            print(f'[ROBOT] Manager could not find the automation named {name} at {self.automations_dir}')
            return False

        steps = self.file_ops.load(path)
        engine = WorkflowEngine(steps, self.controller, stop_event=self._stop_event)

        logger.info(f'\nRunning {name} 🚀​')
        print(f'\nRunning {name} 🚀​')
        result = engine.run()
        return result or self._stop_event.is_set()

    def stop_automation(self) -> None:
        logger.info("[ROBOT] Stop requested for current automation")
        self._stop_event.set()
    
    def delete(self, name) -> bool:
        name = self.normalize_automation_name(name)
        
        path = os.path.join(self.automations_dir, name)
        if not os.path.isfile(path):
            logger.info(f'Manager could not find the automation named {name} at {self.automations_dir}')
            return False
        
        os.remove(path)
        logger.info(f"The file '{path}' has been deleted")
        return True
