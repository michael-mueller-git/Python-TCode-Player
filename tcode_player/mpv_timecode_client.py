import platform
import time

from python_mpv_jsonipc import MPV  # python-mpv-jsonipc
from PyQt5 import QtWidgets, QtCore, QtGui

class MPVTimecodeClient(QtCore.QThread):

    def __init__(self,
            timecode_callback=None,
            pause_callback=None,
            video_callback=None,
            speed_callback=None):
        super().__init__(parent=None)
        self.timecode_callback = timecode_callback
        self.pause_callback = pause_callback
        self.video_callback = video_callback
        self.speed_callback = speed_callback

    #: connection state changed signal with status string
    connectionChanged = QtCore.pyqtSignal(str)

    def run(self):

        self.is_running = True

        def handle_quit():
            print('quit mpv')
            self.is_running = False

        if platform.system() == 'Windows':
            mpv = MPV(start_mpv=True, ipc_socket='\\.\pipe\mpv-pipe', quit_callback=handle_quit)
        else:
            mpv = MPV(start_mpv=True, ipc_socket='/tmp/mpv-socket', quit_callback=handle_quit)

        self.connectionChanged.emit('connected')

        # use mpv --list-properties
        @mpv.property_observer("pause")
        @mpv.property_observer("time-pos")
        @mpv.property_observer("path")
        @mpv.property_observer("speed")
        def handle_mpv_property(name, value):
            # print('DEBUG', name, value)
            if name == 'pause':
                if self.pause_callback is not None: self.pause_callback(value)
            elif name == 'time-pos':
                if self.timecode_callback is not None: self.timecode_callback(value)
            elif name == 'path':
                if self.video_callback is not None: self.video_callback(value)
            elif name == 'speed':
                if self.speed_callback is not None: self.speed_callback(value)
            else:
                print('MPV property', name, 'not implemented')

        while self.is_running: time.sleep(1)
        self.connectionChanged.emit('disconnected')
