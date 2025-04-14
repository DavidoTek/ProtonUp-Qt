import os

from PySide6.scripts.pyside_tool import qt_tool_wrapper

verbose = True
compressLevel = 6
compressAlgo = "zstd"
compressThreshold = 0

if __name__ == "__main__":
    qt_tool_wrapper(
        "rcc",
        [
            "-g", "python",
            "--compress", str(compressLevel),
            "--compress-algo", compressAlgo,
            "--threshold", str(compressThreshold),
            "--verbose" if verbose else "",
            os.path.join(os.path.dirname(__file__), "stylesheet.qrc"),
            "-o", os.path.join(os.path.dirname(__file__), "__init__.py"),
        ],
        True
    )
