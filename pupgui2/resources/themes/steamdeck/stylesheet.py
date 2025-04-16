import os

import qstylizer.style
from PySide6.QtGui import QColor
from PySide6.scripts.pyside_tool import qt_tool_wrapper

verbose = True
compressLevel = 6
compressAlgo = "zlib"
compressThreshold = 0

color = QColor("#EEEEEE")
background_color_base = QColor("#171D25")
background_color_item = QColor("#282D36")
background_color_hover = QColor("#464D58")
background_color_pressed = QColor("#393F49")
background_color_disabled = QColor("#1D2026")

border_radius_base = 2

margin_min = 1

padding_min = 1
padding_base = 8
padding_item = 4

subcontrol_width_base = 18
subcontrol_width_sbar = subcontrol_width_base + padding_min
subcontrol_width_sbar_control = subcontrol_width_base - padding_min

style = qstylizer.style.StyleSheet()

style.QWidget.setValues(
    color=color.name(),
    backgroundColor=background_color_base.name(),
    fontWeight=300,
)

for widget in (
    style.QPushButton,
    style.QListWidget,
    style.QComboBox,
    style.QToolButton,
    style.QLineEdit,
    style.QHeaderView.section,
):
    widget.setValues(
        backgroundColor=background_color_item.name(),
        border=None,
        borderRadius=f"{border_radius_base}px",
        padding=f"{padding_base}px",
    )

style.QListWidget.item.setValues(padding=f"{padding_item}px")
style.QPushButton.hover.setValues(backgroundColor=background_color_hover.name())
style.QPushButton.pressed.setValues(backgroundColor=background_color_pressed.name())
style.QPushButton.disabled.setValues(backgroundColor=background_color_disabled.name())

style.QHeaderView.setValues(padding=f"{padding_min}px")
style.QHeaderView.section.setValues(
    padding=f"{padding_item}px",
    backgroundColor=background_color_item.darker(125).name(),
)
style.QHeaderView.section.horizontal.setValues(marginLeft="0px", marginRight="2px")
style.QHeaderView.section.vertical.setValues(marginTop="0px", marginBottom="2px")
style.QTableView.item.setValues(marginLeft="1px")

style.QComboBox.dropDown.setValues(
    subcontrolOrigin="border",
    subcontrolPosition="top right",
    padding=f"{padding_item / 2}px",
    paddingRight=f"{padding_item}px",
    border=None,
    borderRadius=f"{border_radius_base}px",
    width=f"{subcontrol_width_base - 2}px",
    image='url(":/resources/themes/steamdeck/icon-drop-down.svg")',
)

style.QScrollBar.setValues(
    padding=f"{padding_min}px",
    borderRadius=f"{border_radius_base}px",
    backgroundColor="transparent",
)
style.QScrollBar.vertical.setValues(
    margin=f"{subcontrol_width_sbar}px 0px",
    width=f"{subcontrol_width_sbar}px",
)
style.QScrollBar.horizontal.setValues(
    margin=f"0px {subcontrol_width_sbar}px",
    height=f"{subcontrol_width_sbar}px",
)

for subcontrol in (
    style.QScrollBar.addLine.vertical,
    style.QScrollBar.subLine.vertical,
    style.QScrollBar.addLine.horizontal,
    style.QScrollBar.subLine.horizontal,
):
    subcontrol.setValues(
        margin=f"{margin_min}px",
        border=None,
        borderRadius=f"{border_radius_base}px",
        width=f"{subcontrol_width_sbar_control}px",
        height=f"{subcontrol_width_sbar_control}px",
        backgroundColor=background_color_item.name(),
        subcontrolOrigin="margin",
    )
style.QScrollBar.addLine.vertical.subcontrolPosition.setValue("bottom")
style.QScrollBar.subLine.vertical.subcontrolPosition.setValue("top")
style.QScrollBar.addLine.horizontal.subcontrolPosition.setValue("right")
style.QScrollBar.subLine.horizontal.subcontrolPosition.setValue("left")
style.QScrollBar.handle.setValues(
    backgroundColor=background_color_item.name(),
    borderRadius=f"{border_radius_base}px",
    minWidth="30px",
    minHeight="30px",
)
scrollbar_arrow_style = {
    "width": "13px",
    "height": "13px",
}
style.QScrollBar.upArrow.setValues(
    **scrollbar_arrow_style,
    image='url(":/resources/themes/steamdeck/icon-up-arrow.svg")',
)
style.QScrollBar.downArrow.setValues(
    **scrollbar_arrow_style,
    image='url(":/resources/themes/steamdeck/icon-down-arrow.svg")',
)


if __name__ == "__main__":
    with open(os.path.join(os.path.dirname(__file__), "stylesheet.qss"), "w", encoding="utf-8") as stylesheet:
        stylesheet.write(f'/* This file is auto-generated from "{os.path.basename(__file__)}" */\n')
        stylesheet.write(f'/* DO NOT EDIT!!! */\n\n')
        stylesheet.write(style.toString())

    qt_tool_wrapper(
        "rcc",
        [
            "-g",
            "python",
            "--compress", str(compressLevel),
            "--compress-algo", compressAlgo,
            "--threshold", str(compressThreshold),
            "--verbose" if verbose else "",
            os.path.join(os.path.dirname(__file__), "stylesheet.qrc"),
            "-o", os.path.join(os.path.dirname(__file__), "__init__.py"),
        ],
        True,
    )
