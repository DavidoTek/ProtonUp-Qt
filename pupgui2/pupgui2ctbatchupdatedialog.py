from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from util import sort_compatibility_tool_names, list_installed_ctools, install_directory
from util import steam_update_ctool

class PupguiCtBatchUpdateDialog(QDialog):

    batch_update_complete = Signal(bool)

    def __init__(self, parent=None, games=[], vdf_dir=''):
        super(PupguiCtBatchUpdateDialog, self).__init__(parent)
        self.games = games
        self.vdf_dir = vdf_dir

        self.ctools = sort_compatibility_tool_names(list_installed_ctools(install_directory()))

        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle(self.tr('Batch update'))
        self.setModal(True)

        formLayout = QFormLayout()
        self.comboNewCtool = QComboBox()
        self.btnBatchUpdate = QPushButton(self.tr('Batch update'))
        formLayout.addRow(QLabel(self.tr('New version:')), self.comboNewCtool)
        formLayout.addWidget(self.btnBatchUpdate)
        self.setLayout(formLayout)

        for ctool in self.ctools:
            if 'Proton' in ctool:
                self.comboNewCtool.addItem(ctool)
        self.btnBatchUpdate.clicked.connect(self.btn_batch_update_clicked)

        self.show()
    
    def btn_batch_update_clicked(self):
        self.update_games_to_ctool(self.comboNewCtool.currentText())
        self.batch_update_complete.emit(True)
        self.close()
    
    def update_games_to_ctool(self, ctool):
        for game in self.games:
            steam_update_ctool(game, ctool, self.vdf_dir)
