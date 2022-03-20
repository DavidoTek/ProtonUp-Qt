[![Downloads](https://img.shields.io/github/downloads/DavidoTek/ProtonUp-Qt/total.svg)](https://github.com/DavidoTek/ProtonUp-Qt/releases)
[![License](https://img.shields.io/github/license/DavidoTek/ProtonUp-Qt)](https://github.com/DavidoTek/ProtonUp-Qt/blob/main/LICENSE)
[![Build AppImage CI](https://github.com/DavidoTek/ProtonUp-Qt/actions/workflows/appimage-ci.yml/badge.svg)](https://github.com/DavidoTek/ProtonUp-Qt/actions/workflows/appimage-ci.yml)

# ProtonUp-Qt
Install and manage [Proton-GE](https://github.com/GloriousEggroll/proton-ge-custom) and [Luxtorpeda](https://github.com/luxtorpeda-dev/luxtorpeda) for Steam and [Wine-GE](https://github.com/GloriousEggroll/wine-ge-custom) for Lutris with this graphical user interface. Based on AUNaseef's [ProtonUp](https://github.com/AUNaseef/protonup), made with Python 3 and Qt 6.  

**Download from Flathub or as AppImage (portable):**  
[<img height="56px" src="https://flathub.org/assets/badges/flathub-badge-en.png" alt="Download from Flathub" />](https://flathub.org/apps/details/net.davidotek.pupgui2) [<img height="56px" src="https://raw.githubusercontent.com/srevinsaju/get-appimage/master/static/badges/get-appimage-branding-dark.png" alt="Download AppImage" />](https://github.com/DavidoTek/ProtonUp-Qt/releases)  
Also available on AUR, maintained by yochananmarqos: https://aur.archlinux.org/packages/protonup-qt


![ProtonUp-Qt Screenshot](.github/images/pupgui2-screenshot2.png)

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

## Translate ProtonUp-Qt
1. Generate an empty translation file *or* download it from [here](https://github.com/DavidoTek/ProtonUp-Qt/blob/main/i18n/pupgui2_de.ts).
2. Install [Qt Linguist](https://flathub.org/apps/details/io.qt.Linguist) (alternatively: edit the **.ts** file using a text editor).
3. Open the translation file (.ts) with Qt Linguist and translate the app.
4. Submit the translation:  
   a) Simple method: Upload the **.ts** file [here](https://gist.github.com/) and [create a new issue](https://github.com/DavidoTek/ProtonUp-Qt/issues/new?labels=translation&title=Translation:%20language) with a link to your translation.  
   b) Alternatively, compile the .ts file to .qm and create a PR with the translation (include both the .ts and .qm file).

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
