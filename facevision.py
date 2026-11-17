"""Start the current local FACEVISION minimal application."""
import tkinter as tk
from facevision_light_minimal import App


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
