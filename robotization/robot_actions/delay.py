from robotization.system_controller import ISystemController
from robotization.robot_actions import register
import random

class DelayCommand:
    def __init__(self, controller: ISystemController, seconds: float = 0.0, random_min: float = 0.0, random_max: float = 0.0):
        self.controller = controller
        self.seconds = seconds
        self.random_min = random_min
        self.random_max = random_max

    def execute(self):
        # Calcular tiempo de espera
        if self.random_min is not None and self.random_max is not None and self.random_max > self.random_min:
            delay = random.uniform(self.random_min, self.random_max)
        else:
            delay = self.seconds
        
        print(f"[ROBOT] Delay of {delay}s apply")
        self.controller.delay(delay)

# Registrar la acción
register('delay', DelayCommand)