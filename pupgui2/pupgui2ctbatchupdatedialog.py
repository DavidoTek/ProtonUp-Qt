from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QComboBox, QFormLayout

from pupgui2.steamutil import is_steam_running, steam_update_ctool
from pupgui2.util import sort_compatibility_tool_names, list_installed_ctools, install_directory


class PupguiCtBatchUpdateDialog(QDialog):

    batch_update_complete = Signal(bool)

    def __init__(self, parent=None, current_ctool_name: str='', games=[], steam_config_folder=''):
        super(PupguiCtBatchUpdateDialog, self).__init__(parent)
        self.games = games
        self.steam_config_folder = steam_config_folder

        self.ctools = sort_compatibility_tool_names(list_installed_ctools(install_directory()), reverse=True)

        self.setup_ui(current_ctool_name)

    def setup_ui(self, current_ctool_name: str):
        self.setWindowTitle(self.tr('Batch update'))
        self.setModal(True)

        formLayout = QFormLayout()
        self.comboNewCtool = QComboBox()
        self.btnBatchUpdate = QPushButton(self.tr('Batch update'))
        self.btnClose = QPushButton(self.tr('Close'))
        formLayout.addRow(QLabel(self.tr('New version:')), self.comboNewCtool)
        formLayout.addWidget(self.btnBatchUpdate)
        formLayout.addWidget(self.btnClose)
        self.setLayout(formLayout)

        combobox_ctools = [ctool for ctool in self.ctools if 'Proton' in ctool and current_ctool_name not in ctool]
        self.comboNewCtool.addItems(combobox_ctools)

        self.comboNewCtool.setEnabled(len(combobox_ctools) > 0)
        self.btnBatchUpdate.setEnabled(len(combobox_ctools) > 0)

        self.btnBatchUpdate.clicked.connect(self.btn_batch_update_clicked)
        self.btnClose.clicked.connect(lambda: self.close())

        if len(combobox_ctools) <= 0:
            self.add_warning_message('No supported compatibility tools found.', formLayout)
        elif is_steam_running():
            self.add_warning_message('Close the Steam Client beforehand.', formLayout)

        self.show()
    
    def add_warning_message(self, msg: str, layout: QFormLayout, stylesheet: str = 'QLabel { color: orange; }'):
        """
        Add a QLabel warning message with a default Orange stylesheet to display a warning message in a FormLayout.
        """

        lblWarning = QLabel(self.tr('{MSG}'.format(MSG=msg)))
        lblWarning.setStyleSheet(stylesheet)
        layout.addRow(lblWarning)

    def btn_batch_update_clicked(self):
        self.update_games_to_ctool(self.comboNewCtool.currentText())
        self.batch_update_complete.emit(True)
        self.close()

    def update_games_to_ctool(self, ctool):
        for game in self.games:
            steam_update_ctool(game, ctool, self.steam_config_folder)
