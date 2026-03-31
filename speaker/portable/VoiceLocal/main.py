"""
VoiceLocal — Push-to-talk Speech-to-Text
"""

import sys
import os
import logging

_base = os.path.dirname(os.path.abspath(__file__))

# Portable Python
_portable = os.path.join(_base, "python", "Lib", "site-packages")
if os.path.isdir(_portable) and _portable not in sys.path:
    sys.path.insert(0, _portable)

# CUDA portable
_cuda = os.path.join(_base, "cuda")
if os.path.isdir(_cuda):
    os.environ["PATH"] = _cuda + ";" + os.environ.get("PATH", "")

# Логирование в voice.log
logging.basicConfig(
    filename=os.path.join(_base, "voice.log"),
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%H:%M:%S",
    encoding="utf-8",
)

import multiprocessing
from PyQt6.QtWidgets import QApplication
from app.main_window import MainWindow
from app.tray import TrayIcon


def main():
    multiprocessing.freeze_support()
    logging.info("[START] VoiceLocal запущен")

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
