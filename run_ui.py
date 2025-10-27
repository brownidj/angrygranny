import os
import sys

from PySide6.QtCore import QFile
from PySide6.QtCore import QLibraryInfo
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QWidget

# Force Qt to the correct plugin folders
plugins = QLibraryInfo.path(QLibraryInfo.PluginsPath)
if plugins:
    os.environ.setdefault("QT_PLUGIN_PATH", plugins)
    os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", os.path.join(plugins, "platforms"))

def main():
    app = QApplication(sys.argv)
    loader = QUiLoader()
    ui_file = QFile("ui/form.ui")
    ui_file.open(QFile.ReadOnly)
    window = loader.load(ui_file)
    ui_file.close()

    if isinstance(window, QWidget):
        window.show()
    else:
        print("Error: UI file did not load correctly.")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
