
import time

from PyQt5 import QtWidgets, QtCore, QtGui

class StrokeSimulator(QtCore.QThread):

    def __init__(self, set_position_callback, strokes_per_minute=30):
        super().__init__(parent=None)
        self.set_position_callback = set_position_callback
        self.strokes_per_minute = strokes_per_minute
        self.cycle_counter = 0
        self.stop_simulator = False

    def set_strokes(self, strokes_per_minute):
        self.strokes_per_minute = strokes_per_minute

    def stop(self):
        self.stop_simulator = True

    def run(self):
        while not self.stop_simulator:
            self.cycle_counter += 1
            self.set_position_callback(position=99,
                    interval=round(float(60)/self.strokes_per_minute*1000/2),
                    respect_limits=True)
            time.sleep(60/self.strokes_per_minute/2)
            if self.stop_simulator: break
            self.set_position_callback(position=0,
                    interval=round(float(60)/self.strokes_per_minute*1000/2),
                    respect_limits=True)
            time.sleep(60/self.strokes_per_minute/2)

