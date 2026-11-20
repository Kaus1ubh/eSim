"""Construct the real eSim 2.5 main window using an offscreen Qt platform.

Run with the installed eSim virtual environment's Python, from src/frontEnd.
This verifies GUI startup only; it does not validate external simulators.
"""
import os
from pathlib import Path
import sys

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, os.getcwd())
from PyQt5 import QtWidgets
import Application

app = QtWidgets.QApplication(['task4-gui-smoke'])
window = Application.Application()
app.processEvents()
assert window.isVisible()
assert window.windowTitle() == 'eSim-2.5', window.windowTitle()
image = Path('/tmp/task4-evidence/16-esim-main-window-' + os.environ.get('TASK4_ENV', 'patched') + '.png')
assert window.grab().save(str(image))
print('MAIN_WINDOW_TITLE=' + window.windowTitle())
print('MAIN_WINDOW_VISIBLE=' + str(window.isVisible()))
print('SCREENSHOT=' + str(image))
window.deleteLater()
app.processEvents()
app.quit()
