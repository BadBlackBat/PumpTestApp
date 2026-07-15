# import sys
# from PyQt5.QtWidgets import QApplication
# from .gui import MainWindow
# from . import database as db

# def main():
#     db.init_db()
#     app = QApplication(sys.argv)
#     window = MainWindow()
#     window.show()
#     sys.exit(app.exec_())

# if __name__ == "__main__":
#     main()

import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from .gui import MainWindow
from . import database as db

def main():
    db.init_db()

    # Поддержка масштабирования Windows (125%/150%/200%) и разных DPI -
    # флаги обязательно нужно выставить ДО создания QApplication
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()