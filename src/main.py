import sys
import os

# Добавляем папку src в sys.path, чтобы импорты работали
sys.path.insert(0, os.path.dirname(__file__))

from PyQt5.QtWidgets import QApplication
from gui import MainWindow
import database as db

def main():
    db.init_db()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()