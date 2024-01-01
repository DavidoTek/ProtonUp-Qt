import sys
import logging
import traceback

from types import TracebackType

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QMessageBox, QApplication


class PupguiExceptionHandler(QObject):
    exception = Signal(type, BaseException, TracebackType)

    def __init__(self, parent):
        self.logger = logging.getLogger(type(self).__name__)
        super(PupguiExceptionHandler, self).__init__(parent)
        sys.excepthook = self._excepthook
        self.exception.connect(self._on_exception)

    def _excepthook(self, exc_type: type, exc_value: BaseException, exc_tb: TracebackType):
        self.exception.emit(exc_type, exc_value, exc_tb)

    @Slot(type, BaseException, TracebackType)
    def _on_exception(self, exc_type: type, exc_value: BaseException, exc_tb: TracebackType):
        message = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

        self.logger.fatal(message)
        QMessageBox.critical(None, exc_type.__name__, message)
        QApplication.quit()
