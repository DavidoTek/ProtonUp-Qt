#!/bin/bash
# ProtonUp-Qt - Script for compiling all .ts translation files to .qm files
BASE_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && cd .. && pwd )
TS_FILES="$BASE_DIR/i18n/*.ts"

for ts in $TS_FILES
do
    lang=$(sed 's/.ts//g' <<< "$(basename $ts)")
    qm="$BASE_DIR/pupgui2/resources/i18n/$lang.qm"
    pyside6-lrelease $ts -qm $qm
done
