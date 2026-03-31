"""
VoiceLocal — Push-to-talk Speech-to-Text
Запускает трей + главное окно.
"""

import sys
import os

# Portable Python: добавить site-packages в путь
_base = os.path.dirname(os.path.abspath(__file__))
_portable = os.path.join(_base, "python", "Lib", "site-packages")
if os.path.isdir(_portable) and _portable not in sys.path:
    sys.path.insert(0, _portable)

# CUDA portable
_cuda = os.path.join(_base, "cuda")
if os.path.isdir(_cuda):
    os.environ["PATH"] = _cuda + ";" + os.environ.get("PATH", "")

import multiprocessing
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from app.main_window import MainWindow
from app.tray import TrayIcon


def main():
    multiprocessing.freeze_support()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow()
    tray = TrayIcon(window, app)
    window._tray = tray
    tray.show()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
