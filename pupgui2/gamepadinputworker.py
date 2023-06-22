from PySide6.QtCore import Qt, QThread, Signal


class GamepadInputWorker(QThread):
    
    press_virtual_key = Signal(int, Qt.KeyboardModifiers)

    def __init__(self):
        super().__init__()
        self.reset_pos = 0

    def run(self):
        try:
            import inputs

            while not self.isInterruptionRequested():
                events = inputs.get_gamepad()
                for event in events:
                    if event.code in ['ABS_HAT0Y', 'ABS_HAT0X']:
                        if event.state == -1:
                            self.press_virtual_key.emit(Qt.Key_Tab, Qt.ShiftModifier)
                        elif event.state == 1:
                            self.press_virtual_key.emit(Qt.Key_Tab, Qt.NoModifier)

                    elif event.code == 'BTN_SOUTH' and event.state == 1:
                        self.press_virtual_key.emit(Qt.Key_Space, Qt.NoModifier)
                    elif event.code == 'BTN_EAST' and event.state == 1:
                        self.press_virtual_key.emit(Qt.Key_Enter, Qt.NoModifier)

                    elif event.code in ['ABS_Y', 'ABS_RY']:
                        if event.state > -1800 and event.state < 1800:
                            self.reset_pos = True
                        elif event.state < 0:
                            if self.reset_pos:
                                self.press_virtual_key.emit(Qt.Key_Up, Qt.NoModifier)
                                self.reset_pos = False
                        elif event.state > 0:
                            if self.reset_pos:
                                self.press_virtual_key.emit(Qt.Key_Down, Qt.NoModifier)
                                self.reset_pos = False
                    elif event.code in ['ABS_X', 'ABS_RX']:
                        if event.state > -1800 and event.state < 1800:
                            self.reset_pos = True
                        elif event.state < 0:
                            if self.reset_pos:
                                self.press_virtual_key.emit(Qt.Key_Left, Qt.NoModifier)
                                self.reset_pos = False
                        elif event.state > 0:
                            if self.reset_pos:
                                self.press_virtual_key.emit(Qt.Key_Right, Qt.NoModifier)
                                self.reset_pos = False
        except Exception as e:
            print('Gamepad error:', e)

    def stop(self):
        self.requestInterruption()
        self.setTerminationEnabled(True)
        self.terminate()
        self.wait()
