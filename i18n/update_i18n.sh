#!/bin/bash
# ProtonUp-Qt - Script for updating the .ts translation files from the sources
BASE_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && cd .. && pwd )
TS_FILES="$BASE_DIR/i18n/*.ts"

SOURCES="$BASE_DIR/pupgui2/*.py $BASE_DIR/pupgui2/resources/ctmods/*.py $BASE_DIR/pupgui2/resources/ui/*.ui"

for ts in $TS_FILES
do
    pyside6-lupdate $SOURCES -ts $ts
done
