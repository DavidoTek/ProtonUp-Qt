from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from util import config_custom_install_location


class PupguiCustomInstallDirectoryDialog(QDialog):

    def __init__(self, parent=None):
        super(PupguiCustomInstallDirectoryDialog, self).__init__(parent)

        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle(self.tr('Custom Install Directory'))
        self.setModal(True)

        self.show()
