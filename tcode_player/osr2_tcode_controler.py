import time
import os
import json
import threading
import statistics
import serial  # pyserial
from threading import Thread

from PyQt5 import QtWidgets, QtCore, QtGui

class OSR2TCodeControler(QtCore.QThread):

    def __init__(self, lower_limit, upper_limit, speed_limit, calculate_player_speed=False, half_stroke_speed=False):
        super().__init__(parent=None)
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit
        self.speed_limit = speed_limit
        self.serial_device = None
        self.video_pause = True
        self.player_speed = 1.0
        self.offset = 0
        self.mutex = threading.Lock()
        self.timecode = -1
        self.timecode_diffs = []
        self.last_timecode = 0
        self.last_actions_idx = 0
        self.update_time = self.__millis()
        self.last_exec_time = self.__millis()
        self.funsctipt_file = ''
        self.funscript_data = {'actions':[]}
        self.MAX_INTERVAL = 50
        self.calculate_player_speed = calculate_player_speed
        self.half_stroke_speed = half_stroke_speed
        self.last_pos = 50


    def __del__(self):
        try:
            if self.serial_device is not None:
                self.serial_device.close()
        except:
            pass

    #: funscript changed signal with status string
    funscriptChanged = QtCore.pyqtSignal(str)

    #: video player status changed signal with status string
    playerStatusChanged = QtCore.pyqtSignal(str)

    def position(self):
        return self.last_pos

    def set_serial_port(self, port):
        if port is None or port == '':
            self.serial_device = None
        else:
            self.serial_device = serial.Serial(
                port=port,
                baudrate=115200,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            try: self.serial_device.open()
            except: pass

    def __millis(self):
        return round(time.time() * 1000)

    def half_stroke_speed_handler(self, half_stroke_speed):
        print(str('enable' if half_stroke_speed else 'disable') + ' half stroke speed')
        self.half_stroke_speed = half_stroke_speed
        self.__load_funscript()

    def set_upper_limit(self, value):
        value = min((99, value))
        if self.lower_limit < value: self.upper_limit = value

    def set_lower_limit(self, value):
        value = max((0, value))
        if self.upper_limit > value: self.lower_limit = value

    def set_speed_limit(self, value):
        value = max((0, value))
        self.speed_limit = value

    def get_speed(self, position, interval_in_ms):
        return 1000.0 * abs(position - self.last_pos) / interval_in_ms

    def limit_speed(self, position, interval_in_ms):
        delta = self.speed_limit * interval_in_ms / 1000.0
        return max((self.last_pos - delta, 0)) if position < self.last_pos else min((99, self.last_pos + delta))

    def set_position(self, position, interval=750, respect_limits=True):
        if interval < self.MAX_INTERVAL: return
        if self.serial_device is not None and self.serial_device.isOpen():
            if respect_limits:
                position = self.lower_limit + abs(self.upper_limit - self.lower_limit)/100.0  * position

                speed = self.get_speed(position, interval)
                if speed > self.speed_limit and self.speed_limit > 0:
                    position = self.limit_speed(position, interval)

            position = round(position)
            self.last_pos = position
            if position > 99:
                position = 99
            if position < 0:
                position = 0
            # print('set position', position)
            self.serial_device.write(
                    bytes('L0' + str(position % 100).zfill(2) + '5I' + str(interval) + '\r\n', 'utf-8')
                    )

    def set_offset(self, milliseconds):
        self.offset = milliseconds

    def pause_handler(self, pause):
        if pause is None or pause == True:
            if self.video_pause == False:
                self.timecode_diffs = []
                self.playerStatusChanged.emit('pause')
                self.video_pause = True
        else:
            if self.video_pause == True:
                self.playerStatusChanged.emit('play')
                self.video_pause = False

    def __determine_player_speed(self):
        if len(self.timecode_diffs) < 10: return
        speeds = [x[0] / x[1] for x in self.timecode_diffs if x[0] > 0 and x[1] > 0]
        if len(speeds) < 10: return
        speed = sum(speeds) / float(len(speeds))
        if 0.2 < speed < 1.8:
            self.player_speed = speed if abs(speed-1.0) > 0.05 else 1.0

    def timecode_handler(self, timecode):
        if timecode is None:
            self.timecode = -1
            self.timecode_diffs = []
            return
        timecode = round(timecode * 1000)
        now = self.__millis()
        if self.timecode > 0:
            if self.timecode > timecode:
                self.timecode_diffs = []
            else:
                self.timecode_diffs.append([timecode - self.timecode, now - self.update_time])
            if len(self.timecode_diffs) > 16:
                del self.timecode_diffs[0]

        self.mutex.acquire()
        self.timecode, self.update_time = timecode, now
        self.mutex.release()
        if self.calculate_player_speed: self.__determine_player_speed()

    def speed_handler(self, player_speed):
        self.calculate_player_speed = False
        self.player_speed = 1.0 if player_speed is None else player_speed

    def __load_funscript(self):
        self.mutex.acquire()
        self.timecode = -1
        self.timecode_diffs = []
        self.last_timecode = 0
        self.last_actions_idx = 0
        self.last_exec_time = self.__millis()
        self.update_time = self.__millis()

        if self.funsctipt_file != "" and os.path.exists(self.funsctipt_file):
            with open(self.funsctipt_file, 'r') as json_file:
                self.funscript_data = json.loads(json_file.read())
            if len(self.funscript_data['actions']) > 4:

                if self.half_stroke_speed:
                    old_actions = self.funscript_data['actions']
                    self.funscript_data['actions'] = []
                    for i in range(0, len(old_actions)-4, 4):
                        self.funscript_data['actions'].append({
                            'pos': min(([x['pos'] for x in old_actions[i:i+4]])),
                            'at': old_actions[i]['at']
                            })
                        self.funscript_data['actions'].append({
                            'pos': max(([x['pos'] for x in old_actions[i:i+4]])),
                            'at': old_actions[i+2]['at']
                            })

                    if len(old_actions) % 4 >= 2:
                        self.funscript_data['actions'].append({
                            'pos': min(([x['pos'] for x in old_actions[-2:]])),
                            'at': old_actions[-2]['at']
                            })

                # insert first point at last to get continius movement for video loops
                self.funscript_data['actions'].append({
                    'pos': self.funscript_data['actions'][0]['pos'],
                    'at': self.funscript_data['actions'][-1]['at'] + \
                            min((self.funscript_data['actions'][-1]['at'] - self.funscript_data['actions'][-2]['at'], 1000))
                    })
                # insert first key as duplicate to make our algorithm work at the real first element
                self.funscript_data['actions'].insert(0, {
                    'pos': self.funscript_data['actions'][0]['pos'],
                    'at': self.funscript_data['actions'][0]['at'] - min((self.offset, 1))
                    })
        else:
            self.funscript_data = {'actions':[]}
        self.mutex.release()

    def video_handler(self, video_file):
        if video_file is None:
            self.funsctipt_file = ''
            return

        funsctipt = ''.join(video_file[:-4]) + '.funscript'
        self.funsctipt_file = funsctipt if os.path.exists(funsctipt) else ''
        self.__load_funscript()

        self.funscriptChanged.emit(self.funsctipt_file if self.funsctipt_file != '' else 'none')

    def run(self):
        while True:
            if self.video_pause or self.funsctipt_file == '' or self.timecode < 0:
                time.sleep(0.1)
                self.last_exec_time = self.__millis()
                continue

            exec_diff = (self.__millis() - self.last_exec_time) * self.player_speed
            self.last_exec_time = self.__millis()

            self.mutex.acquire()
            interpolated_time = round(self.timecode + self.offset + self.player_speed * (self.__millis() - self.update_time))
            self.mutex.release()

            # player jump and loop detection (min 500 ms difference)
            if self.last_timecode > interpolated_time+500:
                self.last_timecode = 0
                self.last_actions_idx = 0
            self.last_timecode = interpolated_time

            action_pos, action_time = None, None
            for i in range(
                    max((0, min((len(self.funscript_data['actions'])-1, self.last_actions_idx+1)) )),
                    len(self.funscript_data['actions'])-1
                    ):
                if self.funscript_data['actions'][i]['at'] < interpolated_time + int(0.5*exec_diff):
                    action_pos = self.funscript_data['actions'][i+1]['pos']
                    action_time = self.funscript_data['actions'][i+1]['at'] - self.funscript_data['actions'][i]['at']
                    self.last_actions_idx = i
                elif self.funscript_data['actions'][i]['at'] >= interpolated_time + int(0.5*exec_diff): break

            if action_pos is not None and action_time is not None:
                if self.funscript_data['inverted'] == True: action_pos = 100 - action_pos
                action_pos = int(action_pos/100*(self.upper_limit - self.lower_limit) + self.lower_limit)
                action_time = int(action_time * 1.0/self.player_speed)
                self.set_position(action_pos, action_time)

            time.sleep(0.001)


