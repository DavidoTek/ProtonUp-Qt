from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QComboBox, QFormLayout

from pupgui2.steamutil import is_steam_running, steam_update_ctool
from pupgui2.util import sort_compatibility_tool_names, list_installed_ctools, install_directory


class PupguiCtBatchUpdateDialog(QDialog):

    batch_update_complete = Signal(bool)

    def __init__(self, parent=None, games=[], steam_config_folder=''):
        super(PupguiCtBatchUpdateDialog, self).__init__(parent)
        self.games = games
        self.steam_config_folder = steam_config_folder

        self.ctools = sort_compatibility_tool_names(list_installed_ctools(install_directory()), reverse=True)

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

        if is_steam_running():
            lblSteamRunningWarning = QLabel(self.tr('Close the Steam client beforehand.'))
            lblSteamRunningWarning.setStyleSheet('QLabel { color: orange; }')
            formLayout.addRow(lblSteamRunningWarning)

        self.show()
    
    def btn_batch_update_clicked(self):
        self.update_games_to_ctool(self.comboNewCtool.currentText())
        self.batch_update_complete.emit(True)
        self.close()

    def update_games_to_ctool(self, ctool):
        for game in self.games:
            steam_update_ctool(game, ctool, self.steam_config_folder)
