# pupgui2 compatibility tools module
# SteamTinkerLaunch
# Copyright (C) 2021 DavidoTek, partially based on AUNaseef's protonup

import datetime, locale, os, requests, shutil, subprocess, tarfile

from PySide6.QtCore import QObject, QCoreApplication, Signal, Property
from PySide6.QtWidgets import QMessageBox

from pupgui2 import constants
from pupgui2.datastructures import MsgBoxType, MsgBoxResult
from pupgui2.steamutil import get_fish_user_paths, remove_steamtinkerlaunch, get_external_steamtinkerlaunch_intall
from pupgui2.util import host_which, config_advanced_mode
from pupgui2.util import ghapi_rlcheck


CT_NAME = 'SteamTinkerLaunch'
CT_LAUNCHERS = ['steam', 'native-only']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_steamtinkerlaunch', '''
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
of the SteamTinkerLaunch Installation guide on its GitHub page..''')}


class CtInstaller(QObject):

    BUFFER_SIZE = 4096
    CT_URL = 'https://api.github.com/repos/sonic2kk/steamtinkerlaunch/releases'
    CT_BRANCHES_URL = 'https://api.github.com/repos/sonic2kk/steamtinkerlaunch/branches'
    CT_GH_URL = 'https://github.com/sonic2kk/steamtinkerlaunch'
    CT_INFO_URL = CT_GH_URL + '/releases/tag/'

    p_download_progress_percent = 0
    download_progress_percent = Signal(float)
    message_box_message = Signal((str, str, QMessageBox.Icon))
    question_box_message = Signal((str, str, str, MsgBoxType, QMessageBox.Icon))


    def __init__(self, main_window = None, allow_git=False):
        super(CtInstaller, self).__init__()
        self.p_download_canceled = False
        self.remove_existing_installation = False
        self.main_window = main_window
        self.rs = main_window.rs or requests.Session()
        self.allow_git = allow_git
        proc_prefix = ['flatpak-spawn', '--host'] if os.path.exists('/.flatpak-info') else []
        self.distinfo = subprocess.run(
            proc_prefix + ['cat', '/etc/lsb-release', '/etc/os-release'],
            universal_newlines=True,
            stdout=subprocess.PIPE
            ).stdout.strip().lower()

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
            return {'version': tag, 'download': f'https://github.com/sonic2kk/steamtinkerlaunch/archive/{tag}.tar.gz'}

        url = self.CT_URL + (f'/tags/{tag}' if tag else '/latest')
        data = self.rs.get(url).json()
        if 'tag_name' not in data:
            return None

        return {'version': data['tag_name'], 'download': data['tarball_url'] if 'tarball_url' in data else None}

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
                yad_ver = float(f'{yad_vers[0]}.{yad_vers[1]}')
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
        msg = QCoreApplication.instance().translate('ctmod_steamtinkerlaunch', 'You have several unmet dependencies for SteamTinkerLaunch.\n\n')
        msg += '\n'.join([f'{dep_name}: {"found" if is_dep_met else "missing"}' for (dep_name, is_dep_met) in deps_met.items()])
        msg += QCoreApplication.instance().translate('ctmod_steamtinkerlaunch', '\n\nInstallation will be cancelled.')
        self.message_box_message.emit(QCoreApplication.instance().translate('ctmod_steamtinkerlaunch', 'Missing dependencies!'), msg, QMessageBox.Warning)

        return False  # Installation would fail without dependencies.

    def fetch_releases(self, count=100):
        """
        List available releases or available branches for SteamTinkerLaunch-git
        Return Type: str[]
        """
        main_branch = 'master'
        j = ghapi_rlcheck(self.rs.get(f'{self.CT_URL}?per_page={str(count)}').json())
        if 'message' in j:
            return []
        branches = [branch['name'] for branch in self.rs.get(self.CT_BRANCHES_URL).json()] if self.allow_git else [release['tag_name'] for release in j]
        if self.allow_git and main_branch in branches:
            branches.insert(0, branches.pop(branches.index(main_branch)))  # Force main branch to top of list

        return branches

    def get_tool(self, version, install_dir, temp_dir):
        """
        Download and install the compatibility tool
        Return Type: bool
        """

        has_existing_install = False

        # If there's an existing STL installation that isn't installed by ProtonUp-Qt, ask the user if they still want to install
        has_external_install = get_external_steamtinkerlaunch_intall(os.path.join(install_dir, 'SteamTinkerLaunch'))
        if has_external_install:
            print('Non-ProtonUp-Qt installation of SteamTinkerLaunch detected. Asking the user what they want to do...')
            self.question_box_message.emit(
                QCoreApplication.instance().translate('ctmod_steamtinkerlaunch', 'Existing SteamTinkerLaunch Installation'),
                QCoreApplication.instance().translate('ctmod_steamtinkerlaunch', 'It looks like you have an existing SteamTinkerLaunch installation at \'{EXTERNAL_INSTALL_PATH}\' that was not installed by ProtonUp-Qt.\n\nReinstalling SteamTinkerLaunch with ProtonUp-Qt will move your installation folder to \'{STL_INSTALL_PATH}\'.\n\nYou may also choose to remove your existing installation, if ProtonUp-Qt has write access to this folder. Do you want to continue installing SteamTinkerLaunch? (This will not affect any existing SteamTinkerLaunch configuration.)').format(EXTERNAL_INSTALL_PATH=has_external_install, STL_INSTALL_PATH=constants.STEAM_STL_INSTALL_PATH),
                QCoreApplication.instance().translate('ctmod_steamtinkerlaunch' ,'Remove existing SteamTinkerLaunch installation'),
                MsgBoxType.OK_CANCEL_CB,
                QMessageBox.Warning
            )

            remove_existing_installation_result = self.main_window.get_msgcb_answer()
            if remove_existing_installation_result.button_clicked == MsgBoxResult.BUTTON_OK:
                # Remove the Non-ProtonUp-Qt SteamTinkerLaunch if the user checked the box (disabled by default)
                print('User opted to continue installing SteamTinkerLaunch.')
                if remove_existing_installation_result.is_checked:
                    # This will show a warning dialog if it can't be removed, but uninstallation will continue
                    # The user was previously asked if they wanted to stop installation, so there is no need to pause installation and ask again
                    print('User opted to remove the existing SteamTinkerLaunch installation as well - Attempting to do so')
                    remove_steamtinkerlaunch(compat_folder=os.path.join(install_dir, 'SteamTinkerLaunch'), remove_config=False, ctmod_object=self)

                # Nothing more to do here, just continue with the rest of the installation as normal
            else:
                # Don't remove anything
                print('User opted to not continue installing SteamTinkerLaunch. Aborting...')
                return False

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
            if os.path.exists(constants.STEAM_STL_INSTALL_PATH) and len(os.listdir(constants.STEAM_STL_INSTALL_PATH)) > 0:
                has_existing_install = True  # This will also be True for users who installed normally on Steam Deck, but not sure how to differentiate between PUPQT and manual Steam Deck installs
                remove_steamtinkerlaunch(remove_config=False, ctmod_object=self)
            
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
            # Dialog warning - Only warn on new installs or overwritten manual installs
            # For background see this issue: https://github.com/DavidoTek/ProtonUp-Qt/issues/127
            should_show_shellmod_dialog = has_external_install or not has_existing_install
            should_add_path = True

            # Checkbox is only shown to users who have ProtonUp-Qt Advanced mode enalbed
            if should_show_shellmod_dialog:
                shellmod_msgbox_type = MsgBoxType.OK_CANCEL_CB_CHECKED if config_advanced_mode() == 'enabled' else MsgBoxType.OK_CANCEL
                self.question_box_message.emit(
                    QCoreApplication.instance().translate('ctmod_steamtinkerlaunch', 'Add SteamTinkerLaunch to PATH'),
                    QCoreApplication.instance().translate('ctmod_steamtinkerlaunch', 'By default, ProtonUp-Qt will add SteamTinkerLaunch to all available Shell paths. This makes it easier to use with native Linux games. It also enables SteamTinkerLaunch commands from anywhere in the command line.\n\nSome users may not want this functionality. Do you want to continue installing SteamTinkerLaunch?'),
                    QCoreApplication.instance().translate('ctmod_steamtinkerlaunch', 'Allow PATH modification'),
                    shellmod_msgbox_type,
                    QMessageBox.Warning
                )

                shellmod_msgbox_result = self.main_window.get_msgcb_answer()
                if shellmod_msgbox_result.button_clicked == MsgBoxResult.BUTTON_CANCEL:
                    # Cancel installation after shell modification warning
                    print('User asked to cancel installation. Not installing SteamTinkerLaunch...')
                    should_add_path = False  # Shouldn't matter since installation will end here, but setting for completeness
                    remove_steamtinkerlaunch(remove_config=False, ctmod_object=self)  # shouldn't need compat_folder arg     -     (compat_folder=os.path.join(install_dir, 'SteamTinkerLaunch'))
                    self.__set_download_progress_percent(-2)
                    return
                elif not shellmod_msgbox_result.is_checked and shellmod_msgbox_result.button_clicked == MsgBoxResult.BUTTON_OK:
                    # Continue installation but skip adding to PATH
                    print('User asked not to add SteamTinkerLaunch to shell paths, skipping...')
                    should_add_path = False
                else:
                    should_add_path = True  # Probably won't get here anyway, but set to True to be sure

            if should_add_path:
                # Add to shell PATH 
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

        protondir = os.path.join(install_dir, 'SteamTinkerLaunch')

        # We can't use the version arg to this method because we need to list the PROGVERS stored by the SteamTinkerLaunch script
        if os.path.exists(protondir):
            # Get PROGVERS from STL script
            stl_filename = 'steamtinkerlaunch'
            stl_ver = ''
            with open(os.path.join(protondir, stl_filename)) as stl_script:
                for i, line in enumerate(stl_script):
                    if 'PROGVERS' in line:
                        stl_ver = line.split('=')[1].replace('"', '')  # E.g. turn `PROGVERS="v12.0"` into `v12.0`
                        
                        print(f'Storing SteamTinkerLaunch version from STL script file as {stl_ver}')

                        # Write version to file
                        with open(os.path.join(protondir, 'VERSION.txt'), 'w') as f:
                            f.write(stl_ver)
                            f.write('\n')
                        
                        break
                    
                    if i > 19:
                        print("Couldn't find SteamTinkerLaunch version in script file, quitting...")
                        break

        self.__set_download_progress_percent(100)
        print('Successfully installed SteamTinkerLaunch!')
        return True
    
    def get_info_url(self, version):
        """
        Return link with GitHub release page.
        If SteamTinkerLaunch-git, returns the project homepage.

        Return Type: str
        """

        return self.CT_GH_URL if self.allow_git else self.CT_INFO_URL + version    
