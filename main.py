import sys
from tcode_player.osr2_player_window import OSR2PlayerWindow

from PyQt5 import QtCore, QtGui, QtWidgets

if __name__ == '__main__' :
    app = QtWidgets.QApplication(sys.argv)
    widget = OSR2PlayerWindow()
    widget.show()
    sys.exit(app.exec_())
