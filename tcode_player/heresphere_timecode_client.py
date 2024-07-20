import socket
import time
import os
import json

from urllib.parse import unquote

from PyQt5 import QtWidgets, QtCore, QtGui

class HereSphereTimecodeClient(QtCore.QThread):

    def __init__(self,
            ipTextEdit,
            portSpinBox,
            pathPrefixEdit,
            timecode_callback=None,
            pause_callback=None,
            video_callback=None):
        super().__init__(parent=None)
        self.ipTextEdit = ipTextEdit
        self.portSpinBox = portSpinBox
        self.pathPrefixEdit = pathPrefixEdit,
        self.timecode_callback = timecode_callback
        self.pause_callback = pause_callback
        self.video_callback = video_callback

    #: connection state changed signal with status string
    connectionChanged = QtCore.pyqtSignal(str)

    def run(self):
        print("Run HereSphere Receiver")
        while True:                
            ip = self.ipTextEdit.text().strip()
            port = self.portSpinBox.value() 
            print("try connect", ip, port)
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(3.0) 
                    s.connect((ip, port))
                    self.connectionChanged.emit('connected')
                    while True:
                        data = s.recv(1024)
                        if not data:
                            print("no data")
                            break

                        expected_len = data[0] + (data[1] << 8) + (data[2] << 16) + (data[3] << 24)
                        print(expected_len)
                        
                        data = data[4:]
                        data = data.decode('utf-8')
                        content = json.loads(data)
                        if "currentTime" in content:
                            if self.timecode_callback is not None: self.timecode_callback(content["currentTime"])
                        if "playerState" in content:
                            if self.pause_callback is not None: self.pause_callback(content["playerState"] == 1)
                        if "resource" in content:
                            resource = unquote(content["resource"])
                            path = resource.split("/", 3)[-1]
                            if self.video_callback is not None: self.video_callback(os.path.join(self.pathPrefixEdit.text().strip(), path))
            except:
                self.connectionChanged.emit('disconnected')
                if self.pause_callback is not None: self.pause_callback(True)
                time.sleep(1)
