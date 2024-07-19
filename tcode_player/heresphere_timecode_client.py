import socket
import time
import json

from urllib.parse import unquote

from PyQt5 import QtWidgets, QtCore, QtGui

class HereSphereTimecodeClient(QtCore.QThread):

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
                    s.connect(('10.0.6.100', 23554))
                    self.connectionChanged.emit('connected')
                    update_time = round(time.time() * 1000)
                    while True:
                        data = s.recv(1024)
                        if not data:
                            print("no data")
                            break
                            if round(time.time() * 1000) > update_time + 4000: break
                            continue


                        expected_len = data[0] + (data[1] << 8) + (data[2] << 16) + (data[3] << 24)
                        print(expected_len)
                        
                        data = data[4:]
                        update_time = round(time.time() * 1000)
                        data = data.decode('utf-8')
                        content = json.loads(data)
                        if "currentTime" in content:
                            if self.timecode_callback is not None: self.timecode_callback(content["currentTime"])
                        if "playerState" in content:
                            if self.pause_callback is not None: self.pause_callback(content["playerState"] == 1)
                        if "resource" in content:
                            resource = unquote(content["resource"])
                            path = resource.split("/", 3)[-1]
                            if self.video_callback is not None: self.video_callback("/mnt/" + path)
            except:
                self.connectionChanged.emit('disconnected')
                if self.pause_callback is not None: self.pause_callback(True)
                time.sleep(1)
