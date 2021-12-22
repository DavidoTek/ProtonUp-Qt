[![Downloads](https://img.shields.io/github/downloads/DavidoTek/ProtonUp-Qt/total.svg)](https://github.com/DavidoTek/ProtonUp-Qt/releases)
[![License](https://img.shields.io/github/license/DavidoTek/ProtonUp-Qt)](https://github.com/DavidoTek/ProtonUp-Qt/blob/main/LICENSE)
[![Build AppImage CI](https://github.com/DavidoTek/ProtonUp-Qt/actions/workflows/appimage-ci.yml/badge.svg)](https://github.com/DavidoTek/ProtonUp-Qt/actions/workflows/appimage-ci.yml)

# ProtonUp-Qt
Qt-based graphical user interface to install and manage [Proton-GE](https://github.com/GloriousEggroll/proton-ge-custom) installations for Steam and [Wine-GE](https://github.com/GloriousEggroll/wine-ge-custom) installations for Lutris. Based on AUNaseef's [ProtonUp](https://github.com/AUNaseef/protonup).

[<img height="56px" src="https://flathub.org/assets/badges/flathub-badge-en.png" alt="Download from Flathub" />](https://flathub.org/apps/details/net.davidotek.pupgui2) [<img height="56px" src="https://raw.githubusercontent.com/srevinsaju/get-appimage/master/static/badges/get-appimage-branding-dark.png" alt="Download AppImage" />](https://github.com/DavidoTek/ProtonUp-Qt/releases) 


![ProtonUp-Qt Screenshot](screenshot1.png)

## Run from source
### Install dependencies
`pip3 install -r ./requirements.txt`
### Run ProtonUp-Qt
`python3 pupgui2/pupgui2.py`

## Build AppImage
### Install dependencies
1. Install appimage-builder: https://appimage-builder.readthedocs.io/en/latest/intro/install.html  
### Build AppImage
`appimage-builder`

## Licensing
Project|License
-------|--------
ProtonUp-Qt|GPL-3.0
[ProtonUp](https://pypi.org/project/protonup/)|GPL-3.0
[PySide6](https://pypi.org/project/PySide6/)|LGPL-3.0/GPL-2.0
[inputs](https://pypi.org/project/inputs/)|BSD
[pyxdg](https://pypi.org/project/pyxdg/)|LGPLv2
[vdf](https://pypi.org/project/vdf/)|MIT
[requests](https://pypi.org/project/requests/)|Apache 2.0
