import sys
from PyQt5.QtWidgets import QApplication
from .gui import MainWindow
from . import database as db

def main():
    db.init_db()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()