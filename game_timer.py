import time

class GameTimer:
    def __init__(self, duration_secs):
        self.duration_secs = duration_secs
        self.start_time = None

    def start(self):
        self.start_time = time.time()

    def is_running(self):
        return self.remaining_time() > 0

    def remaining_time(self):
        if self.start_time is None:
            return self.duration_secs
        remaining = self.duration_secs - int(time.time() - self.start_time)
        return max(0, remaining)