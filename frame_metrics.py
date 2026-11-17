"""Small rolling timing window. Display FPS counts only newly drawn frames."""
from collections import deque


class FrameMetrics:
    def __init__(self):
        self.presented = deque(maxlen=60)
        self.timings = {}

    def record(self, name, milliseconds):
        self.timings.setdefault(name, deque(maxlen=60)).append(milliseconds)

    def present(self, now):
        self.presented.append(now)

    @property
    def fps(self):
        if len(self.presented) < 2:
            return 0.0
        elapsed = self.presented[-1] - self.presented[0]
        return (len(self.presented)-1)/elapsed if elapsed > 0 else 0.0

    def report(self):
        values = ' '.join(f'{name}={sum(samples)/len(samples):.1f}ms'
                          for name,samples in self.timings.items() if samples)
        return f'display_fps={self.fps:.1f} {values}'
