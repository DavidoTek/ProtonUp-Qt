import pkgutil

from PySide6.QtCore import QDataStream, QByteArray, QObject
from PySide6.QtUiTools import QUiLoader

from pupgui2.util import config_github_access_token, config_gitlab_access_token


class PupguiGitAccessTokenDialog(QObject):

    def __init__(self, parent=None):
        super(PupguiGitAccessTokenDialog, self).__init__(parent)

        self.load_ui()
        self.setup_ui()
        self.ui.show()

    def load_ui(self):
        data = pkgutil.get_data(__name__, 'resources/ui/pupgui2_gitaccesstokendialog.ui')
        ui_file = QDataStream(QByteArray(data))
        loader = QUiLoader()
        self.ui = loader.load(ui_file.device())

    def setup_ui(self):
        self.ui.txtGitHubToken.setText(config_github_access_token())
        self.ui.txtGitLabToken.setText(config_gitlab_access_token())

        self.ui.btnSave.clicked.connect(self.btn_save_clicked)
        self.ui.btnClose.clicked.connect(self.ui.close)

    def btn_save_clicked(self):
        github_token = self.ui.txtGitHubToken.text()
        gitlab_token = self.ui.txtGitLabToken.text()

        config_github_access_token(github_token)
        config_gitlab_access_token(gitlab_token)

        self.ui.close()
