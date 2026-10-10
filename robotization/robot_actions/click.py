from robotization.system_controller import ISystemController
from robotization.robot_actions import register

class ClickCommand:
    def __init__(self, controller: ISystemController, x: int, y: int, after: float = 0.0):
        self.controller = controller
        self.x = x
        self.y = y
        self.after = after

    def execute(self):
        # Realizar click
        print(f"[ROBOT] Click at x:{self.x}, y:{self.y}")
        self.controller.click(self.x, self.y)
        # Si after > 0, esperar ese tiempo
        if self.after and self.after > 0:
            print(f"[ROBOT] Click delay {self.after}s apply")
            self.controller.delay(self.after)

# Registrar la acción
register('click', ClickCommand)