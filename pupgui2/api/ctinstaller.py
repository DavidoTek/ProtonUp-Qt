from typing import List

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from pupgui2.api.compattool import CompatTool
from pupgui2.datastructures import MsgBoxType, MsgBoxResult


class CtInstaller(QObject):
    """ Defines an interface/template for a ctmod CtInstaller """

    download_progress_percent = Signal(int)
    message_box_message = Signal(str, str, QMessageBox.Icon)
    question_box_message = Signal(str, str, str, MsgBoxType, QMessageBox.Icon)

    def is_system_compatible(self) -> bool:
        """ Returns true if the system is compatible. May display dialogs """
        pass

    def fetch_releases(self, count=100) -> List[CompatTool]:
        """ Fetches a list of releases """
        pass

    def get_tool(self, tool: CompatTool, temp_dir: str) -> CompatTool:
        """ Downloads and install the given compatibilty tool. May display dialogs. """
        version = tool.get_version()
        install_dir = tool.get_install_dir()

    def get_info_url(self):
        """ Returns a URL with information about the (current version of the) compatibility tool """
        pass

    def get_installed_versions(self) -> List[CompatTool]:
        """ Returns a list of installed versions of the compatibility tool """
        pass

    def get_newest_release(self) -> CompatTool:
        """ Returns a CompatTool with the version set to the newest available """
        pass

    def compare_tool_versions(a: CompatTool, b: CompatTool):
        """
        Compares the version of the two given compatibility tools
        Returns  1 if a is newer than b
        Returns  0 if a is the same version as b
        Returns -1 if a is older than b
        Returns -2 if there was an error (e.g. wrong CtInstaller)
        """
        pass

    def uninstall_tool(self, tool: CompatTool) -> bool:
        """ Uninstalls the given compatibilty tool. May display dialogs. """
        pass
