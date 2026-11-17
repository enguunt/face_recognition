"""FACEVISION entry point: the old interface is replaced by the minimal app.

Run: python facevision.py
The implementation lives in facevision_light_minimal.py to avoid duplicate code.
"""
import tkinter as tk
from facevision_light_minimal import App


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
