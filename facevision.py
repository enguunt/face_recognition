"""FACEVISION GUI entry point (also used by PyInstaller on Windows)."""
from pathlib import Path
import shutil
import sys
import tkinter as tk


def _prepare_bundled_models():
    """Install packaged, public FaceNet weights for offline EXE use, if supplied.

    Doesn't overwrite existing weights in the user's profile.
    """
    package_dir = getattr(sys, '_MEIPASS', None)
    if not package_dir:
        return
    bundled = Path(package_dir) / 'bundled_facevision_weights'
    if not bundled.is_dir():
        return
    target = Path.home() / '.deepface' / 'weights'
    try:
        target.mkdir(parents=True, exist_ok=True)
        for source in bundled.iterdir():
            if source.is_file():
                output = target / source.name
                if not output.exists():
                    shutil.copy2(source, output)
    except OSError as exc:
        print('FaceNet жингийн хуулбар үүсгэх боломжгүй:', exc)


def main():
    _prepare_bundled_models()
    from facevision_light_minimal import App
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
