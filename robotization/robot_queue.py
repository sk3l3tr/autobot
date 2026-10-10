import multiprocessing, threading
from queue import Empty, Queue

multiprocessing.set_start_method('spawn', force=True)
from loguru import logger

from robotization.robot_manager import RobotManager

class RobotQueue:    
    _instance = None

    def __new__(cls, robot_manager: RobotManager):
        cls.robot_manager = robot_manager

        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._queue = Queue()
        worker = threading.Thread(target=self._worker, daemon=True)
        worker.start()

    def enqueue(self, name: str):
        logger.info(f"[QUEUE] Enqueue robot: {name}")
        self._queue.put(name)

    def stop_all(self):
        logger.info("[QUEUE] Stop requested. Cancelling current automation and clearing queue.")
        self.robot_manager.stop_automation()

        cleared = 0
        while True:
            try:
                self._queue.get_nowait()
            except Empty:
                break
            else:
                self._queue.task_done()
                cleared += 1

        logger.info(f"[QUEUE] Cleared {cleared} queued automation(s).")

    def _worker(self):
        while True:
            name = self._queue.get()
            try:
                logger.info(f"[QUEUE] Unenqueue robot and execute: {name}")
                success = self.robot_manager.run_automation(name)
                if not success:
                    logger.warning(f"[QUEUE] The robot {name} could not be executed.")
            except Exception as e:
                logger.error(f"[QUEUE] Error when executing {name}: {e}")
            finally:
                self._queue.task_done()
