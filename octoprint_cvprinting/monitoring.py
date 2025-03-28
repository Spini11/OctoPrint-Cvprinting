import multiprocessing
import time
from . import visionModule

class Monitoring:
    _queue = None
    _visionModule = None
    _webcam = None
    _running = None

    def __init__(self, queue, baseFolder, webcam, running):
        self._queue = queue
        self._visionModule = visionModule.visionModule(baseFolder)
        self._webcam = webcam
        self._running = running
        self.monitor()
    
    def monitor(self):
        while self._running.value:
            time.sleep(4)
            image, result = self._visionModule.CheckImage(self._webcam.get("snapshotUrl"))
            if result == 1:
                self._queue.put(("ERROR", {"message": "Error getting image"}))
            elif result == 2:
                self._queue.put(("ERROR", {"message": "Error loading image"}))
            elif not result:
                self._queue.put(("RESULT", None))
            else:
                self._queue.put(("RESULT", {"image": image, "result": result}))
            time.sleep(1)
        return