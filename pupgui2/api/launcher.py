from PySide6.QtGui import QIcon


class Launcher:
    
    def __init__(self, base_dir: str, launcher_name: str, display_name: str, install_type: str, icon_name: str, config_dir: str):
        """
        Defines a game launcher for ProtonUp-Qt

        Parameters
        ----------
        base_dir : str
            Launcher-specific base directory, e.g. ~/.steam/root or ~/.local/share/lutris
        launcher_name : str
            Internal launcher name. Options: steam, lutris, heroic, bottles
        display_name : str
            Display name, e.g. Steam Flatpak
        install_type : str
            How the launcher is installed. Options: native, flatpak, snap
        icon_name : str
            Name of the launcher icon. Should be resolvable using QIcon.fromTheme()
        config_dir : str
            Launcher-specific configuration directory, e.g. ~/.steam/root/config or ~/.config/lutris
        """

        self.base_dir = base_dir
        self.launcher_name = launcher_name
        self.display_name = display_name
        self.install_type = install_type
        self.icon_name = icon_name
        self.config_dir = config_dir

    def get_display_name(self):
        """ Returns the display name of the launcher. Example: 'Steam Flatpak' """
        pass

    def get_launcher_name(self):
        """ Returns the name of the launcher. Example: steam """
        pass

    def get_install_type(self):
        """ Returns the install type of the launcher. Example: flatpak """
        pass

    def get_base_dir(self):
        """ Returns the base directory of the launcher. Example: '~/.steam/root' """
        pass

    def get_config_dir(self):
        """ Returns the configuration directory of the launcher. Example: ~/.config/lutris """
        pass

    def get_icon_name(self):
        """ Returns the icon name of the launcher """
        pass

    def get_qicon(self, fallback: QIcon=None):
        """ Returns the launcher icon as QIcon if found, QIcon(null) otherwise """
        if fallback:
            return QIcon.fromTheme(self.icon_name, fallback)
        return QIcon.fromTheme(self.icon_name)
