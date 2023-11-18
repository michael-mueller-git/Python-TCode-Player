import os
import time
import platform
import serial.tools.list_ports
import pynput.keyboard
import json
from queue import Queue
from threading import Thread

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
        self.auto_connect = ""
        self.load_config()
        self.use_keyboard_shortcuts = False
        self.keypress_queue = Queue(maxsize=32)
        self.listener = pynput.keyboard.Listener(
            on_press = self.on_key_press,
            on_release = None
        )
        self.should_exit = False
        self.listener.start()
        self.gamepad_thread = Thread(target=self.gamepad_event_loop)
        self.gamepad_thread.start()
        if self.ui.portsComboBox.count() > 0:
            for i in range(self.ui.portsComboBox.count()):
                dev = self.ui.portsComboBox.itemText(i)
                if dev != "" and dev == self.auto_connect:
                    print("auto-connect", dev)
                    self.ui.portsComboBox.setCurrentIndex(i)
                    self.__osr2_connect()
                    break

    def __del__(self):
        self.should_exit = True
        self.listener.stop()


    def gamepad_event_loop(self):
        try:
            from tcode_player.inputs import get_gamepad
            while not self.should_exit:
                events = get_gamepad()
                for event in events:
                    if self.should_exit:
                        break
                    if event.ev_type == "Sync":
                        continue
                    if True:
                        if event.ev_type == "Absolute":
                            if event.code == "ABS_Z":
                                if event.state in [127, 128, 129]:
                                    continue

                    # print("[DEBUG]", event.ev_type, event.code, event.state)

                    if str(event.code) == "BTN_BASE" and event.state == 1:
                        self.ui.lowerLimitSpinBox.setValue(max((0, self.ui.lowerLimitSpinBox.value() - 5)))
                    if str(event.code) == "BTN_BASE2" and event.state == 1:
                        self.ui.upperLimitSpinBox.setValue(max((0, self.ui.upperLimitSpinBox.value() - 5, self.ui.lowerLimitSpinBox.value())))
                    if str(event.code) == "BTN_TOP2" and event.state == 1:
                        self.ui.lowerLimitSpinBox.setValue(min((99, self.ui.lowerLimitSpinBox.value() + 5, self.ui.upperLimitSpinBox.value())))
                    if str(event.code) == "BTN_PINKIE" and event.state == 1:
                        self.ui.upperLimitSpinBox.setValue(min((99, self.ui.upperLimitSpinBox.value() + 5)))
                    if str(event.code) == "ABS_Y" and event.state == 0:
                        self.tcode_controler.set_position(self.tcode_controler.position() + 20, respect_limits=False)
                    if str(event.code) == "ABS_Y" and event.state == 255:
                        self.tcode_controler.set_position(self.tcode_controler.position() - 20, respect_limits=False)
                    if str(event.code) == "ABS_X" and event.state == 255:
                        self.ui.strokesSpinBox.setValue(self.ui.strokesSpinBox.value()+2)
                    if str(event.code) == "ABS_X" and event.state == 0:
                        self.ui.strokesSpinBox.setValue(self.ui.strokesSpinBox.value()-2)
                    if str(event.code) == "BTN_TRIGGER" and event.state == 1:
                        if self.ui.simulatorStartStopButton.text() != 'start':
                            if self.ui.simulatorGroupBox.isEnabled():
                                self.__start_stop_stroke_simulator()
                        selected = self.ui.simulatorModeComboBox.currentText()
                        items = [self.ui.simulatorModeComboBox.itemText(i) for i in range(self.ui.simulatorModeComboBox.count())]
                        new_idx = (items.index(selected) + 1) % self.ui.simulatorModeComboBox.count()
                        self.ui.simulatorModeComboBox.setCurrentIndex(new_idx)
                        print(selected, new_idx)
                    if str(event.code) == "BTN_THUMB2" and event.state == 1:
                        if self.ui.simulatorGroupBox.isEnabled():
                            self.__start_stop_stroke_simulator()
                        else:
                            print("simulator not available")

        except Exception as ex:
            print(ex)
            print("Gamepad not found")

    def load_config(self):
        if not os.path.exists("./config.json"):
            print("config not found")
            return

        print("load config")
        with open("./config.json", "r") as f:
            config = json.load(f)

        if "lowerLimit" in config:
            self.ui.lowerLimitSpinBox.setValue(config["lowerLimit"])

        if "upperLimit" in config:
            self.ui.upperLimitSpinBox.setValue(config["upperLimit"])

        if "offset" in config:
            self.ui.offsetSlider.setValue(config["offset"])

        if "speedLimit" in config:
            self.ui.speedLimitSpinBox.setValue(config["speedLimit"])

        if "strokes" in config:
            self.ui.strokesSpinBox.setValue(config["strokes"])

        if "connect" in config:
            self.auto_connect = config["connect"]


    def on_key_press(self, key: pynput.keyboard.Key) -> None:
        """ Our key press handle to register the key presses

        Args:
            key (pynput.keyboard.Key): the pressed key
        """
        key_str = '{0}'.format(key)
        def was_key(k):
            return key_str == "'"+k[0]+"'"

        if self.use_keyboard_shortcuts:
            if was_key('q'):
                self.ui.lowerLimitSpinBox.setValue(min((99, self.ui.lowerLimitSpinBox.value() + 5, self.ui.upperLimitSpinBox.value())))
            elif was_key('a'):
                self.ui.lowerLimitSpinBox.setValue(max((0, self.ui.lowerLimitSpinBox.value() - 5)))
            elif was_key('w'):
                self.ui.upperLimitSpinBox.setValue(min((99, self.ui.upperLimitSpinBox.value() + 5)))
            elif was_key('s'):
                self.ui.upperLimitSpinBox.setValue(max((0, self.ui.upperLimitSpinBox.value() - 5, self.ui.lowerLimitSpinBox.value())))

        if not self.keypress_queue.full():
            self.keypress_queue.put(key)

    def show(self):
        self.form.show()

    def __setup_variables(self):
        self.simulator = None

    def __setup_comboboxes(self):
        self.ui.simulatorModeComboBox.addItems([
            "linear",
            "random",
            "2xDown",
            "2xUp",
            "sequence_001",
            "sequence_002"
        ])

    def __add_ui_bindings(self):
        self.ui.osr2ConnectButton.clicked.connect(self.__osr2_connect)
        self.ui.simulatorStartStopButton.clicked.connect(self.__start_stop_stroke_simulator)
        self.ui.lowerLimitSpinBox.valueChanged.connect(lambda val: self.tcode_controler.set_lower_limit(val))
        self.ui.upperLimitSpinBox.valueChanged.connect(lambda val: self.tcode_controler.set_upper_limit(val))
        self.ui.speedLimitSpinBox.valueChanged.connect(lambda val: self.tcode_controler.set_speed_limit(val))
        self.ui.position0Button.clicked.connect(lambda: self.tcode_controler.set_position(0, respect_limits=False))
        self.ui.position20Button.clicked.connect(lambda: self.tcode_controler.set_position(20, respect_limits=False))
        self.ui.position40Button.clicked.connect(lambda: self.tcode_controler.set_position(40, respect_limits=False))
        self.ui.position60Button.clicked.connect(lambda: self.tcode_controler.set_position(60, respect_limits=False))
        self.ui.position80Button.clicked.connect(lambda: self.tcode_controler.set_position(80, respect_limits=False))
        self.ui.position100Button.clicked.connect(lambda: self.tcode_controler.set_position(100, respect_limits=False))
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
            # if self.simulator is not None:
                # self.simulator.stop()
            # self.ui.simulatorStartStopButton.setText('start')
            # self.ui.simulatorGroupBox.setEnabled(False)
            # self.ui.positionGroupBox.setEnabled(False)
            pass
        elif status == 'pause':
            # self.ui.simulatorGroupBox.setEnabled(True)
            # self.ui.positionGroupBox.setEnabled(True)
            pass
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
            if self.simulator is not None:
                self.simulator.stop()

    def __start_stop_stroke_simulator(self):
        if self.ui.simulatorStartStopButton.text() == 'start':
            print("start simulator")
            self.ui.simulatorStartStopButton.setText('stop')
            self.simulator = StrokeSimulator(
                    self.tcode_controler.set_position,
                    strokes_per_minute=self.ui.strokesSpinBox.value(),
                    mode=self.ui.simulatorModeComboBox.currentText()
                )
            self.simulator.start()
        else:
            print("stop simulator")
            self.ui.simulatorStartStopButton.setText('start')
            if self.simulator is not None: self.simulator.stop()
