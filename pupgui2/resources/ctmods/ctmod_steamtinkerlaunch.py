# pupgui2 compatibility tools module
# SteamTinkerLaunch
# Copyright (C) 2021 DavidoTek, partially based on AUNaseef's protonup

import datetime, locale, os, requests, shutil, subprocess, tarfile
from PySide6.QtCore import *
from PySide6.QtWidgets import QMessageBox
from ...steamutil import get_fish_user_paths, remove_steamtinkerlaunch, get_external_steamtinkerlaunch_intall
from ... import constants
from ...util import host_which

CT_NAME = 'SteamTinkerLaunch'
CT_LAUNCHERS = ['steam', 'native-only']
CT_DESCRIPTION = {}
CT_DESCRIPTION['en'] = '''
Linux wrapper tool for use with the Steam client which allows for easy graphical configuration of game tools for Proton and native Linux games.
<br/><br/>
On <b>Steam Deck</b>, relevant dependencies will be installed for you. If you are not on Steam Deck, <b>ensure you have the following dependencies installed</b>:
<ul>
  <li>awk (or gawk)</li>
  <li>bash</li>
  <li>git</li>
  <li>pgrep</li>
  <li>unzip</li>
  <li>wget</li>
  <li>xdotool</li>
  <li>xprop</li>
  <li>xrandr</li>
  <li>xwininfo</li>
  <li>xxd</li>
  <li>Yad >= <b>v7.2</b></li>
</ul>
More information is available on the SteamTinkerLaunch Installation wiki page.
<br/><br/>
SteamTinkerLaunch has a number of <b>Optional Dependencies</b> which have to be installed separately for extra functionality. Please see the Optional Dependencies section
of the SteamTinkerLaunch Installation guide on its GitHub page..'''


class CtInstaller(QObject):

    BUFFER_SIZE = 4096
    CT_URL = 'https://api.github.com/repos/frostworx/steamtinkerlaunch/releases'
    CT_BRANCHES_URL = 'https://api.github.com/repos/frostworx/steamtinkerlaunch/branches'
    CT_GH_URL = 'https://github.com/frostworx/steamtinkerlaunch'
    CT_INFO_URL = CT_GH_URL + '/releases/tag/'

    p_download_progress_percent = 0
    download_progress_percent = Signal(float)
    message_box_message = Signal(str, str, QMessageBox.Icon)

    def __init__(self, rs : requests.Session = None, allow_git=False):
        super(CtInstaller, self).__init__()
        self.p_download_canceled = False
        self.rs = rs if rs else requests.Session()
        self.allow_git = allow_git
        proc_prefix = ['flatpak-spawn', '--host'] if os.path.exists('/.flatpak-info') else []
        self.distinfo = subprocess.run(proc_prefix + ['cat', '/etc/lsb-release'], universal_newlines=True, stdout=subprocess.PIPE).stdout.strip().lower()

    def get_download_canceled(self):
        return self.p_download_canceled

    def set_download_canceled(self, val):
        self.p_download_canceled = val

    download_canceled = Property(bool, get_download_canceled, set_download_canceled)

    def __set_download_progress_percent(self, value : int):
        if self.p_download_progress_percent == value:
            return
        self.p_download_progress_percent = value
        self.download_progress_percent.emit(value)

    def __download(self, url, destination):
        """
        Download files from url to destination
        Return Type: bool
        """
        try:
            # Sometimes we don't get Content-Length in the header
            # Add a loop to retry until we get Content-Length
            retries = 10
            for _ in range(retries):
                file = self.rs.get(url, stream=True)
                if 'Content-Length' in file.headers:
                    break
            else:
                print('Could not download SteamTinkerLaunch. Please try again.')
                return False
        except OSError:
            return False

        self.__set_download_progress_percent(1) # 1 download started
        f_size = int(file.headers.get('content-length'))
        c_count = int(f_size / self.BUFFER_SIZE)
        c_current = 1
        destination = os.path.expanduser(destination)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(destination, 'wb') as dest:
            for chunk in file.iter_content(chunk_size=self.BUFFER_SIZE):
                if self.download_canceled:
                    self.download_canceled = False
                    self.__set_download_progress_percent(-2) # -2 download canceled
                    return False
                if chunk:
                    dest.write(chunk)
                    dest.flush()
                self.__set_download_progress_percent(int(min(c_current / c_count * 98.0, 98.0))) # 1-98, 100 after extract
                c_current += 1
        self.__set_download_progress_percent(99) # 99 download complete
        return True

    def __fetch_github_data(self, tag):
        """
        Fetch GitHub release information
        Return Type: dict
        Content(s):
            'version', 'download'
        """
        if self.allow_git:
            values = { 'version': tag, 'download': f'https://github.com/frostworx/steamtinkerlaunch/archive/{tag}.tar.gz'}
        else:
            url = self.CT_URL + (f'/tags/{tag}' if tag else '/latest')
            data = self.rs.get(url).json()
            if 'tag_name' not in data:
                return None

            values = {'version': data['tag_name']}
            values['download'] = data['tarball_url'] if 'tarball_url' in data else None
            
        return values

    def __stl_config_change_language(self, stl_cfg_path: str, lang_file: str) -> bool:
        """
        Change the language in the SteamTinkerLaunch global.conf configuration
        Example: __stl_config_change_language('~/.config/steamtinkerlaunch', 'german.txt')
        Return Type: bool
        """
        stl_global_conf = os.path.join(os.path.expanduser(stl_cfg_path), 'global.conf')
        new_lang = lang_file.replace('.txt', '')

        if not os.path.isfile(stl_global_conf):
            return False

        with open(stl_global_conf, 'r+') as f:
            c = f.readlines()
            f.seek(0)
            for line in c:
                if line.startswith('STLLANG'):
                    f.write(f'STLLANG="{new_lang}"\n')
                else:
                    f.write(line)

        return True

    def is_system_compatible(self):
        """
        Are the system requirements met?
        Return Type: bool
        """
        # Possibly excuse some of these if not on Steam Deck and ignore if Flatpak
        proc_prefix = ['flatpak-spawn', '--host'] if os.path.exists('/.flatpak-info') else []
        yad_exe = host_which('yad')
        if yad_exe:
            try:
                yad_vers = subprocess.run(proc_prefix + ['yad', '--version'], universal_newlines=True, stdout=subprocess.PIPE).stdout.strip().split(' ')[0].split('.')
                yad_ver = float(yad_vers[0] + '.' + yad_vers[1])
            except Exception as e:
                print('STL is_system_compatible Could not parse yad version:', e)
                yad_ver = 0.0

        # Don't check dependencies on Steam Deck, STL will manage dependencies itself in that case
        deps_met = {}
        if "steamos" not in self.distinfo:
            deps_met = {
                'awk-gawk': host_which('awk') or host_which('gawk'),
                'git': host_which('git'),
                'pgrep': host_which('pgrep'),
                'unzip': host_which('unzip'),
                'wget': host_which('wget'),
                'xdotool': host_which('xdotool'),
                'xprop': host_which('xprop'),
                'xrandr': host_which('xrandr'),
                'xxd': host_which('xxd'),
                'xwinfo': host_which('xwininfo'),
                'yad >= 7.2': yad_exe and yad_ver >= 7.2
            }

        if all(deps_met.values()):
            return True
        msg = 'You have several unmet dependencies for SteamTinkerLaunch.\n\n'
        msg += '\n'.join([ f'{dep_name}: {("missing" if not is_dep_met else "found")}' for (dep_name, is_dep_met) in deps_met.items()])
        msg += '\n\nInstallation will be cancelled.'
        self.message_box_message.emit('Missing dependencies!', msg, QMessageBox.Warning)

        return False  # Installation would fail without dependencies.

    def fetch_releases(self, count=100):
        """
        List available releases
        Return Type: str[]
        """

        return [branch['name'] for branch in self.rs.get(self.CT_BRANCHES_URL).json()] if self.allow_git else [release['tag_name'] for release in self.rs.get(self.CT_URL + '?per_page=' + str(count)).json()]

    def get_tool(self, version, install_dir, temp_dir):
        """
        Download and install the compatibility tool
        Return Type: bool
        """

        # If there's an existing STL installation that isn't installed by ProtonUp-Qt, ask the user if they still want to install
        has_external_install = get_external_steamtinkerlaunch_intall(install_dir)
        if has_external_install:
            mb = QMessageBox()
            mb.setWindowTitle(QObject.tr('Existing SteamTinkerLaunch Installation'))
            mb.setText(QObject.tr(f'It looks like you have an existing SteamTinkerLaunch installation at \'{has_external_install}\' on your system that was not installed by ProtonUp-Qt.\n \
                                    Reinstalling SteamTinkerLaunch with ProtonUp-Qt will move your installation folder to {constants.STEAM_STL_INSTALL_PATH}. Do you wish to continue? (This will not affect your SteamTinkerLaunch configuration.)'))
            mb.addButton(QMessageBox.Yes)
            mb.addButton(QMessageBox.No)
            mb.setDefaultButton(QMessageBox.No)
            accept = mb.exec()

            if not accept:
                print('Cancelling SteamTinkerLaunch installation...')
                return False
        # User said Yes to installing anyway

        print('Downloading SteamTinkerLaunch...')

        data = self.__fetch_github_data(version)
        if not data or 'download' not in data:
            return False

        destination = temp_dir
        destination += data['download'].split('/')[-1]
        destination = destination

        if not self.__download(url=data['download'], destination=destination):
            return False

        with tarfile.open(destination, "r:gz") as tar:
            print('Extracting SteamTinkerLaunch...')
            if os.path.exists(constants.STEAM_STL_INSTALL_PATH):
                remove_steamtinkerlaunch(remove_config=False)
            
            if not os.path.exists(constants.STEAM_STL_INSTALL_PATH):
                os.mkdir(constants.STEAM_STL_INSTALL_PATH)
            os.chdir(constants.STEAM_STL_INSTALL_PATH)

            tar.extractall(constants.STEAM_STL_INSTALL_PATH)

            tarname = tar.getnames()[0]
            
            # Location of SteamTinkerLaunch script to add to path later
            old_stl_path = os.path.join(constants.STEAM_STL_INSTALL_PATH, tarname)
            stl_path = os.path.join(constants.STEAM_STL_INSTALL_PATH, 'prefix')

            # Rename folder ~/stl/<tarname> to ~/stl/prefix
            os.rename(old_stl_path, stl_path)

            os.chdir(stl_path)

            # ProtonUp-Qt Flatpak: Run STL on host system
            stl_proc_prefix = ['flatpak-spawn', '--host'] if os.path.exists('/.flatpak-info') else []

            # If on Steam Deck, run script for initial Steam Deck config
            # On Steam Deck, STL is installed to "/home/deck/stl/prefix"
            self.__set_download_progress_percent(99.5) # 99.5 installing tool
            print('Setting up SteamTinkerLaunch...')
            if "steamos" in self.distinfo:
                subprocess.run(['chmod', '+x', 'steamtinkerlaunch'])
                subprocess.run(stl_proc_prefix + ['./steamtinkerlaunch'])

                # Change location of STL script to add to path as this is different on Steam Deck 
                stl_path = os.path.join(constants.STEAM_STL_INSTALL_PATH, 'prefix')

                # Change to STL prefix dir on Steam Deck so that the compatibility tool is symlinked correctly
                os.chdir(stl_path)
            else:
                # Get STL language and default to 'en_US' if the language is not available
                # This step should not be necessary on Steam Deck
                syslang = locale.getdefaultlocale()[0] or 'en_US'
                stl_langs = {
                    'de_DE': 'german.txt',
                    'en_GB': 'englishUK.txt',
                    'en_US': 'english.txt',
                    'fr_FR': 'french.txt',
                    'il_IL': 'italian.txt',
                    'nl_NL': 'dutch.txt',
                    'pl_PL': 'polish.txt',
                    'ru_RU': 'russian.txt',
                    'zh_CN': 'chinese.txt',
                }
                stl_lang = stl_langs[syslang] if syslang in stl_langs else stl_langs['en_US']
                stl_lang_path = os.path.join(constants.STEAM_STL_CONFIG_PATH, 'lang')

                # Generate config file structure and copy relevant lang file
                os.makedirs(stl_lang_path, exist_ok=True)
                if not os.path.isfile(os.path.join(stl_lang_path, 'english.txt')):
                    shutil.copyfile('lang/english.txt', os.path.join(stl_lang_path, 'english.txt'))
                if not os.path.isfile(os.path.join(stl_lang_path, stl_lang)):
                    shutil.copyfile(f'lang/{stl_lang}', os.path.join(stl_lang_path, stl_lang))
                subprocess.run(stl_proc_prefix + ['./steamtinkerlaunch', f'lang={stl_lang.replace(".txt", "")}'])
                self.__stl_config_change_language(constants.STEAM_STL_CONFIG_PATH, stl_lang)

            # Add SteamTinkerLaunch to all available shell paths (native Linux)
            print('Adding SteamTinkerLaunch to shell paths...')
            pup_stl_path_date = f'# Added by ProtonUp-Qt on {datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")}'
            pup_stl_path_line = f'if [ -d "{stl_path}" ]; then export PATH="$PATH:{stl_path}"; fi'
            present_shell_files = [
                os.path.join(os.path.expanduser('~'), f) for f in os.listdir(os.path.expanduser('~')) if os.path.isfile(os.path.join(os.path.expanduser('~'), f)) and f in constants.STEAM_STL_SHELL_FILES
            ]
            if os.path.exists(constants.STEAM_STL_FISH_VARIABLES):
                present_shell_files.append(constants.STEAM_STL_FISH_VARIABLES)

            for shell_file in present_shell_files:
                with open(shell_file, 'r+') as mfile:
                    stl_already_in_path = constants.STEAM_STL_INSTALL_PATH in [line for line in mfile.readlines()]
                    if not stl_already_in_path:
                        # Add Fish user path, preserving any existing paths 
                        if 'fish' in mfile.name:
                            mfile.seek(0)
                            curr_fish_user_paths = get_fish_user_paths(mfile)
                            curr_fish_user_paths.insert(0, stl_path)
                            updated_fish_user_paths = '\\x1e'.join(curr_fish_user_paths)
                            pup_stl_path_line = f'SETUVAR fish_user_paths:{updated_fish_user_paths}'

                            mfile.seek(0)
                            new_fish_contents = ''.join([line for line in mfile.readlines() if 'fish_user_paths:' not in line])
                            mfile.seek(0)
                            mfile.write(new_fish_contents)
                        
                        mfile.write(f'\n{pup_stl_path_date}\n{pup_stl_path_line}\n')

            # Install Compatibility Tool (Proton games)
            print('Adding SteamTinkerLaunch as a compatibility tool...')
            subprocess.run(stl_proc_prefix + ['./steamtinkerlaunch', 'compat', 'add'])

            os.chdir(os.path.expanduser('~'))

        self.__set_download_progress_percent(100)

        print('Successfully installed SteamTinkerLaunch!')

        return True
    
    def get_info_url(self, version):
        """
        Return link with GitHub release page.
        If SteamTinkerLaunch-git, returns the project homepage.

        Return Type: str
        """
        return self.CT_INFO_URL + version if not self.allow_git else self.CT_GH_URL    
