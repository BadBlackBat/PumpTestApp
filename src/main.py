# import sys
# from PyQt5.QtCore import Qt
# from PyQt5.QtWidgets import QApplication
# from .gui import MainWindow
# from . import database as db

# def main():
#     db.init_db()

#     # Поддержка масштабирования Windows (125%/150%/200%) и разных DPI -
#     # флаги обязательно нужно выставить ДО создания QApplication
#     QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
#     QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

#     app = QApplication(sys.argv)
#     window = MainWindow()
#     window.show()
#     sys.exit(app.exec_())

# if __name__ == "__main__":
#     main()

import sys
import ctypes
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from .gui import MainWindow
from . import database as db
from . import styles


def _set_dwm_color_attribute(hwnd, attribute, rgb):
    """Общий хелпер для покраски системных элементов окна через DWM -
    и заголовка (DWMWA_CAPTION_COLOR), и рамки (DWMWA_BORDER_COLOR)
    используют один и тот же вызов, отличается только номер атрибута."""
    r, g, b = rgb
    # COLORREF Windows хранит цвет как 0x00BBGGRR (младший байт - R),
    # а не привычный порядок RGB - собираем значение вручную
    colorref = ctypes.c_int(r | (g << 8) | (b << 16))
    ctypes.windll.dwmapi.DwmSetWindowAttribute(
        hwnd, attribute, ctypes.byref(colorref), ctypes.sizeof(colorref)
    )


def apply_title_bar_color(window):
    """Красит системную строку заголовка окна (значок, свернуть/
    развернуть/закрыть) и тонкую рамку по периметру окна в тот же
    графитовый оттенок, что и верхняя панель/статус-бар - через
    нативный API Windows (DWM). Работает ТОЛЬКО на Windows 11 (сборка
    22000 и новее) - на Windows 10 и любой другой ОС атрибут просто не
    поддерживается, вызов тихо ничего не делает, окно остаётся обычным.
    """
    if sys.platform != "win32":
        return
    hwnd = ctypes.c_void_p(int(window.winId()))
    DWMWA_BORDER_COLOR = 34
    DWMWA_CAPTION_COLOR = 35
    try:
        _set_dwm_color_attribute(hwnd, DWMWA_CAPTION_COLOR, styles.TITLE_BAR_COLOR_RGB)
    except Exception:
        # Windows 10 или более старая, либо dwmapi недоступна - не критично,
        # просто оставляем заголовок окна стандартным
        pass
    try:
        _set_dwm_color_attribute(hwnd, DWMWA_BORDER_COLOR, styles.WINDOW_BORDER_COLOR_RGB)
    except Exception:
        pass


def main():
    db.init_db()

    # Поддержка масштабирования Windows (125%/150%/200%) и разных DPI -
    # флаги обязательно нужно выставить ДО создания QApplication
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    apply_title_bar_color(window)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()