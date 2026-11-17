"""Synthetic scheduling benchmark; does not measure the user's camera or Tk FPS.

Run from the project root: venv/bin/python scripts/benchmark_video_pipeline.py
Simulates a 30 FPS source, 20 ms detection, and 4 ms drawing.
"""
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from camera_stream import CameraStream


class SyntheticCamera:
    def __init__(self):
        self.next_frame = time.monotonic() + 1/30
        self.frame = np.zeros((96,96,3),dtype=np.uint8)
    def isOpened(self): return True
    def read(self):
        time.sleep(max(0,self.next_frame-time.monotonic()))
        self.next_frame=max(self.next_frame+1/30,time.monotonic())
        return True,self.frame
    def release(self): pass


class SyntheticDetector:
    def process(self, frame):
        time.sleep(.020)
        return SimpleNamespace(detections=[])
    def close(self): pass


def old_loop(seconds):
    camera,detector=SyntheticCamera(),SyntheticDetector()
    start=time.monotonic(); count=0; blocked=[]
    while time.monotonic()-start < seconds:
        began=time.monotonic()
        _,frame=camera.read(); detector.process(frame); time.sleep(.004)
        blocked.append((time.monotonic()-began)*1000)
        count+=1
        time.sleep(.020)
    return count/(time.monotonic()-start),sum(blocked)/len(blocked)


def new_loop(seconds):
    stream=CameraStream(SyntheticCamera,SyntheticDetector)
    stream.start(); sequence=0;count=0; blocked=[]
    start=time.monotonic()
    try:
        while time.monotonic()-start < seconds:
            began=time.monotonic()
            packet=stream.latest(sequence)
            if packet is None:
                time.sleep(.008)
                continue
            sequence=packet.sequence
            time.sleep(.004)
            work=time.monotonic()-began
            blocked.append(work*1000);count+=1
            time.sleep(max(.001,1/30-work))
        return count/(time.monotonic()-start),sum(blocked)/len(blocked)
    finally:
        stream.stop();stream._thread.join(2)


if __name__=='__main__':
    print('SYNTHETIC ONLY: 30 FPS source / 20 ms detector / 4 ms renderer')
    old=old_loop(2);new=new_loop(2)
    print(f'Old serial loop: {old[0]:.1f} displayed FPS; {old[1]:.1f} ms callback work')
    print(f'New worker loop: {new[0]:.1f} displayed FPS; {new[1]:.1f} ms callback work')
    print('This is a scheduling comparison, not a live camera/Tk/DeepFace measurement.')
