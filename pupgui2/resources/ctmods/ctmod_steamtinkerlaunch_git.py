# pupgui2 compatibility tools module
# SteamTinkerLaunch-git
# Copyright (C) 2021 DavidoTek, partially based on AUNaseef's protonup

import requests
from .ctmod_steamtinkerlaunch import CtInstaller as stlCtInstaller

from PySide6.QtCore import QCoreApplication

CT_NAME = 'SteamTinkerLaunch-git'
CT_LAUNCHERS = ['steam', 'advmode', 'native-only']
CT_DESCRIPTION = {}
CT_DESCRIPTION['en'] = QCoreApplication.instance().translate('ctmod_steamtinkerlaunch_git', '''
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
More information is available on the SteamTinkerLaunch Installation wiki page.
<br/><br/>
SteamTinkerLaunch has a number of <b>Optional Dependencies</b> which have to be installed separately for extra functionality. Please see the Optional Dependencies section
of the SteamTinkerLaunch Installation guide on its GitHub page..''')
CT_DESCRIPTION['zh_TW'] = '''
與 Steam 用戶端一起使用的 Linux 包裝工具，它允許對 Proton 和本機 Linux 遊戲的遊戲工具進行簡單的圖形配置。
<br/><br/>
在 <b>Steam Deck</b> 上，將為您安裝相關的依賴項。 如果您不是用 Steam Deck，<b>請確保您已安裝以下依賴項</b>：
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
SteamTinkerLaunch 安裝 wiki 頁面上提供了更多資訊。
<br/><br/>
SteamTinkerLaunch 有許多<b>可選依賴項</b>，必須單獨安裝才能獲得額外功能。 請參閱其 GitHub 頁面上 SteamTinkerLaunch 安裝指南的可選依賴項部分。'''

class CtInstaller(stlCtInstaller):

    def __init__(self, main_window = None):
        super().__init__(main_window, allow_git=True)
