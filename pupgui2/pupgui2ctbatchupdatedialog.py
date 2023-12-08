import pkgutil

from PySide6.QtCore import Signal, Qt, QObject, QDataStream, QByteArray
from PySide6.QtWidgets import QLabel, QFormLayout
from PySide6.QtUiTools import QUiLoader

from pupgui2.steamutil import is_steam_running, steam_update_ctool
from pupgui2.util import sort_compatibility_tool_names, list_installed_ctools, install_directory


class PupguiCtBatchUpdateDialog(QObject):

    batch_update_complete = Signal(bool)

    def __init__(self, parent=None, current_ctool_name: str='', games=[], steam_config_folder=''):
        super(PupguiCtBatchUpdateDialog, self).__init__(parent)
        self.games = games
        self.steam_config_folder = steam_config_folder

        self.ctools = sort_compatibility_tool_names(list_installed_ctools(install_directory()), reverse=True)

        self.load_ui()
        self.setup_ui(current_ctool_name)
        self.ui.show()

    def load_ui(self):
        data = pkgutil.get_data(__name__, 'resources/ui/pupgui2_ctbatchupdatedialog.ui')
        ui_file = QDataStream(QByteArray(data))
        self.ui = QUiLoader().load(ui_file.device())

    def setup_ui(self, current_ctool_name: str):
        # Doing ctool checks here instead of before showing the batch update button on ctinfo dialog covers case where
        # compatibility tool may have been available but then was removed (maybe manually?) -- Is potentially just more robust
        combobox_ctools = [ctool for ctool in self.ctools if 'Proton' in ctool and current_ctool_name not in ctool]
        self.ui.comboNewCtool.addItems(combobox_ctools)
        self.ui.oldVersionText.setText(f' {current_ctool_name}')

        # Batch update only disabled when no ctools installed
        # Not disabled when Steam Client is running because it can be closed while this dialog is open 
        self.ui.comboNewCtool.setEnabled(len(combobox_ctools) > 0)
        self.ui.btnBatchUpdate.setEnabled(len(combobox_ctools) > 0)
        
        self.ui.btnBatchUpdate.clicked.connect(self.btn_batch_update_clicked)
        self.ui.btnClose.clicked.connect(lambda: self.ui.close())

        if len(combobox_ctools) <= 0:  # No ctools to migrate to installed
            self.add_warning_message(self.tr('No supported compatibility tools found.'), self.ui.formLayout, stylesheet='QLabel { color: red; }')
        elif is_steam_running():  # Steam is running so any writes to config.vdf will get overwritten on Steam Client exit
            self.add_warning_message(self.tr('Warning: Close the Steam Client beforehand.'), self.ui.formLayout)
        else:  # Spacer label
            self.ui.formLayout.addRow(QLabel())

    def add_warning_message(self, msg: str, layout, stylesheet: str = 'QLabel { color: orange; }'):
        """
        Add a QLabel warning message with a default Orange stylesheet to display a warning message in a Layout.
        """

        lblWarning = QLabel(msg)
        lblWarning.setAlignment(Qt.AlignCenter)
        lblWarning.setStyleSheet(stylesheet)
        layout.addRow(lblWarning)

    def btn_batch_update_clicked(self):
        self.update_games_to_ctool(self.ui.comboNewCtool.currentText())
        self.batch_update_complete.emit(True)
        self.ui.close()

    def update_games_to_ctool(self, ctool):
        for game in self.games:
            steam_update_ctool(game, ctool, self.steam_config_folder)
