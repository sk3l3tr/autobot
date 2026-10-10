import pyautogui
from typing import Protocol

# Definimos la interfaz de controlador de sistema
class ISystemController(Protocol):
    def click(self, x: int, y: int):
        ...

    def delay(self, seconds: float):
        ...

# Implementación usando pyautogui
def _click(x: int, y: int):
    pyautogui.click(x, y)

def _delay(seconds: float):
    pyautogui.sleep(seconds)

class PyAutoGuiController:
    def click(self, x: int, y: int):
        _click(x, y)

    def delay(self, seconds: float):
        _delay(seconds)

# Factory para obtener el controlador adecuado
def get_system_controller() -> ISystemController:
    # Por ahora, usar PyAutoGUI para todas las plataformas
    return PyAutoGuiController()