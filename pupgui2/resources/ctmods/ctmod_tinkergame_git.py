# pupgui2 compatibility tools module
# TinkerGame-git
# Copyright (C) 2021 DavidoTek, partially based on AUNaseef's protonup

from PySide6.QtCore import QCoreApplication

from pupgui2.resources.ctmods.ctmod_tinkergame import CtInstaller as tgCtInstaller


CT_NAME = 'TinkerGame-git'
CT_LAUNCHERS = ['steam', 'advmode', 'native-only']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_tinkergame_git', '''
<b>Git release - May be unstable</b>
<br/><br/>
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
More information is available on the TinkerGame Installation wiki page.
<br/><br/>
TinkerGame has a number of <b>Optional Dependencies</b> which have to be installed separately for extra functionality. Please see the Optional Dependencies section
of the TinkerGame Installation guide on its GitHub page.''')}


class CtInstaller(tgCtInstaller):

    def __init__(self, main_window = None):
        super().__init__(main_window, allow_git=True)
