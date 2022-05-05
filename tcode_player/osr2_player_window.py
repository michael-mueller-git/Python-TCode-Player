import os
import time
import platform
import serial.tools.list_ports
import pynput.keyboard
from queue import Queue

from PyQt5 import QtWidgets, QtCore, QtGui

import tcode_player.osr2_player_view as osr2_player_view


from tcode_player.osr2_tcode_controler import OSR2TCodeControler
from tcode_player.stroke_simulator import StrokeSimulator

if platform.system() == 'Windows':
    print('windows environment')
    PLAYER = 'Whirligig'
else:
    print('develop environment')
    PLAYER = 'MPV'

if PLAYER == 'Whirligig':
    from tcode_player.whirligig_timecode_client import WhirligigTimecodeClient
elif PLAYER == 'MPV':
    from tcode_player.mpv_timecode_client import MPVTimecodeClient

class OSR2PlayerWindow(object):

    def __init__(self, *args, **kwargs):
        self.ui = osr2_player_view.Ui_Form()
        self.form = QtWidgets.QWidget()
        self.ui.setupUi(self.form)
        self.form.setWindowTitle("OSR2 Player")
        self.__setup_comboboxes()
        self.__setup_variables()
        self.__start_background_tasks()
        self.__add_ui_bindings()
        self.__refresh_serial_port_list()
        self.ui.offsetSlider.setValue(0)
        self.keypress_queue = Queue(maxsize=32)
        self.listener = pynput.keyboard.Listener(
            on_press = self.on_key_press,
            on_release = None
        )
        self.listener.start()

    def __del__(self):
        self.listener.stop()

    def on_key_press(self, key: pynput.keyboard.Key) -> None:
        """ Our key press handle to register the key presses

        Args:
            key (pynput.keyboard.Key): the pressed key
        """
        key_str = '{0}'.format(key)
        def was_key(k):
            return key_str == "'"+k[0]+"'"

        if was_key('q'):
            self.ui.lowerLimitSpinBox.setValue(min((99, self.ui.lowerLimitSpinBox.value() + 5, self.ui.upperLimitSpinBox.value())))
        elif was_key('a'):
            self.ui.lowerLimitSpinBox.setValue(max((0, self.ui.lowerLimitSpinBox.value() - 5)))
        elif was_key('w'):
            self.ui.upperLimitSpinBox.setValue(min((99, self.ui.upperLimitSpinBox.value() + 5)))
        elif was_key('s'):
            self.ui.upperLimitSpinBox.setValue(max((0, self.ui.upperLimitSpinBox.value() - 5, self.ui.lowerLimitSpinBox.value())))
        elif not self.keypress_queue.full():
            self.keypress_queue.put(key)

    def show(self):
        self.form.show()

    def __setup_variables(self):
        self.simulator = None

    def __setup_comboboxes(self):
        self.ui.simulatorModeComboBox.addItems([
            "linear",
            "random",
            "sequence_001",
            "sequence_002"
        ])

    def __add_ui_bindings(self):
        self.ui.osr2ConnectButton.clicked.connect(self.__osr2_connect)
        self.ui.simulatorStartStopButton.clicked.connect(self.__start_stop_stroke_simulator)
        self.ui.lowerLimitSpinBox.valueChanged.connect(lambda val: self.tcode_controler.set_lower_limit(val))
        self.ui.upperLimitSpinBox.valueChanged.connect(lambda val: self.tcode_controler.set_upper_limit(val))
        self.ui.speedLimitSpinBox.valueChanged.connect(lambda val: self.tcode_controler.set_speed_limit(val))
        self.ui.position0Button.clicked.connect(lambda: self.tcode_controler.set_position(0))
        self.ui.position20Button.clicked.connect(lambda: self.tcode_controler.set_position(20))
        self.ui.position40Button.clicked.connect(lambda: self.tcode_controler.set_position(40))
        self.ui.position60Button.clicked.connect(lambda: self.tcode_controler.set_position(60))
        self.ui.position80Button.clicked.connect(lambda: self.tcode_controler.set_position(80))
        self.ui.position100Button.clicked.connect(lambda: self.tcode_controler.set_position(100))
        self.ui.refreshPortsButton.clicked.connect(lambda: self.__refresh_serial_port_list())
        self.ui.offsetSlider.valueChanged.connect(self.__on_offset_change)
        self.ui.halfStrokeCheckBox.stateChanged.connect(lambda x: self.tcode_controler.half_stroke_speed_handler(x))
        self.ui.strokesSpinBox.valueChanged.connect(lambda val: self.simulator.set_strokes(val) if self.simulator is not None else None)

    def __refresh_serial_port_list(self):
        self.ui.portsComboBox.clear()
        self.ui.portsComboBox.addItems([port for port, desc, hwid in serial.tools.list_ports.comports()])

    def __on_offset_change(self, value):
        self.ui.offsetLabel.setText(str('' if value < 1 else '+') +  str(value) + ' ms')
        self.tcode_controler.set_offset(value)

    def __start_background_tasks(self):
        self.tcode_controler = OSR2TCodeControler(
                self.ui.lowerLimitSpinBox.value(),
                self.ui.upperLimitSpinBox.value(),
                self.ui.speedLimitSpinBox.value(),
                PLAYER == 'Whirligig',
                self.ui.halfStrokeCheckBox.isChecked())
        if PLAYER == 'Whirligig':
            self.timecode_client = WhirligigTimecodeClient(
                    timecode_callback=self.tcode_controler.timecode_handler,
                    pause_callback=self.tcode_controler.pause_handler,
                    video_callback=self.tcode_controler.video_handler)
        elif PLAYER == 'MPV':
            self.timecode_client = MPVTimecodeClient(
                    timecode_callback=self.tcode_controler.timecode_handler,
                    pause_callback=self.tcode_controler.pause_handler,
                    video_callback=self.tcode_controler.video_handler,
                    speed_callback=self.tcode_controler.speed_handler)
        else:
            print('ERROR: Player', PLAYER, 'not implemented')
            exit()
        self.tcode_controler.funscriptChanged.connect(lambda txt: self.ui.funscriptLabel.setText(os.path.basename(txt)))
        self.tcode_controler.playerStatusChanged.connect(self.__player_status_changed)
        self.timecode_client.connectionChanged.connect(lambda txt: self.ui.whirligigTimeserverLabel.setText(txt))
        self.tcode_controler.start()
        self.timecode_client.start()

    def __player_status_changed(self, status):
        if status == 'play':
            if self.simulator is not None: self.simulator.stop()
            self.ui.simulatorStartStopButton.setText('start')
            self.ui.simulatorGroupBox.setEnabled(False)
            self.ui.positionGroupBox.setEnabled(False)
        elif status == 'pause':
            self.ui.simulatorGroupBox.setEnabled(True)
            self.ui.positionGroupBox.setEnabled(True)
        else:
            print('ERROR: status not implemented')

        self.ui.playerStatusLabel.setText(status)


    def __osr2_connect(self):
        if self.ui.osr2ConnectButton.text() == 'connect' and len(self.ui.portsComboBox.currentText()) > 2:
            # connect to OSR2
            self.ui.osr2ConnectButton.setText('disconnect')
            self.ui.refreshPortsButton.setEnabled(False)
            self.ui.portsComboBox.setEnabled(False)
            self.ui.positionGroupBox.setEnabled(True)
            self.ui.simulatorGroupBox.setEnabled(True)
            self.tcode_controler.set_serial_port(self.ui.portsComboBox.currentText())
        else:
            # disconnect the OSR2
            self.ui.osr2ConnectButton.setText('connect')
            self.ui.refreshPortsButton.setEnabled(True)
            self.ui.portsComboBox.setEnabled(True)
            self.ui.positionGroupBox.setEnabled(False)
            self.ui.simulatorGroupBox.setEnabled(False)
            self.tcode_controler.set_serial_port(None)

    def __start_stop_stroke_simulator(self):
        if self.ui.simulatorStartStopButton.text() == 'start':
            self.ui.simulatorStartStopButton.setText('stop')
            self.simulator = StrokeSimulator(
                    self.tcode_controler.set_position,
                    strokes_per_minute=self.ui.strokesSpinBox.value(),
                    mode=self.ui.simulatorModeComboBox.currentText()
                )
            self.simulator.start()
        else:
            self.ui.simulatorStartStopButton.setText('start')
            if self.simulator is not None: self.simulator.stop()
