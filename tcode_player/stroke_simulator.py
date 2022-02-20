
import time
import random

from PyQt5 import QtWidgets, QtCore, QtGui

class StrokeSimulator(QtCore.QThread):

    def __init__(self, set_position_callback, strokes_per_minute=30, mode='linear'):
        super().__init__(parent=None)
        self.mode = mode
        self.set_position_callback = set_position_callback
        self.strokes_per_minute = strokes_per_minute
        self.cycle_counter = 0
        self.stop_simulator = False

    def set_strokes(self, strokes_per_minute):
        self.strokes_per_minute = strokes_per_minute

    def stop(self):
        self.stop_simulator = True

    def play_linear(self):
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

    def rand_speed_by_distance(self, distance, speed_delta):
        mul = 100.0/max((2, distance))
        return random.randint(int(max((speed_delta, self.strokes_per_minute*mul - speed_delta))), int(self.strokes_per_minute*mul + speed_delta))


    def play_random(self):
        min_delta = 17
        speed_delta = int(self.strokes_per_minute / 30) # +-30%
        current_pos = 50
        max_top_pos = 80
        while not self.stop_simulator:
            self.cycle_counter += 1
            rand_top_pos = random.randint(min_delta, max_top_pos)
            rand_up_speed = self.rand_speed_by_distance(abs(rand_top_pos - current_pos), speed_delta)
            # print('up:', rand_top_pos, rand_up_speed)
            self.set_position_callback(position=rand_top_pos,
                    interval=round(float(60)/rand_up_speed*1000/2),
                    respect_limits=False)
            time.sleep(60/rand_up_speed/2)
            current_pos = rand_top_pos
            if self.stop_simulator: break
            rand_bottom_pos = random.randint(0, max((1, rand_top_pos - min_delta - 1)))
            rand_down_speed = self.rand_speed_by_distance(abs(rand_bottom_pos - current_pos), speed_delta)
            # print('down:', rand_bottom_pos, rand_down_speed)
            self.set_position_callback(position=rand_bottom_pos,
                    interval=round(float(60)/rand_down_speed*1000/2),
                    respect_limits=False)
            time.sleep(60/rand_down_speed/2)
            current_pos = rand_bottom_pos

    def run(self):
        print('simulator mode', self.mode)
        if self.mode == 'random':
            self.play_random()
        else:
            self.play_linear()

