import socket
import time

from PyQt5 import QtWidgets, QtCore, QtGui

class WhirligigTimecodeClient(QtCore.QThread):

    def __init__(self,
            timecode_callback=None,
            pause_callback=None,
            video_callback=None):
        super().__init__(parent=None)
        self.timecode_callback = timecode_callback
        self.pause_callback = pause_callback
        self.video_callback = video_callback

    #: connection state changed signal with status string
    connectionChanged = QtCore.pyqtSignal(str)

    def run(self):
        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(('127.0.0.1', 2000))
                    self.connectionChanged.emit('connected')
                    update_time = round(time.time() * 1000)
                    while True:
                        data = s.recv(1024)
                        if not data:
                            if round(time.time() * 1000) > update_time + 4000: break
                            continue
                        update_time = round(time.time() * 1000)
                        data = data.decode('utf-8')
                        if data.startswith('P'):
                            timecode = float(''.join(data[1:]).strip())
                            if self.pause_callback is not None: self.pause_callback(False)
                            if self.timecode_callback is not None: self.timecode_callback(timecode)
                        elif data.startswith('S'):
                            if self.pause_callback is not None: self.pause_callback(True)
                        elif data.startswith('C'):
                            video_file = ''.join(data[1:]).strip().split('\n')[0].replace('"','')
                            if self.video_callback is not None: self.video_callback(video_file)
                        else:
                            print('ERROR: Timecode option not implemented')
            except:
                self.connectionChanged.emit('disconnected')
                if self.pause_callback is not None: self.pause_callback(True)
                time.sleep(1)
