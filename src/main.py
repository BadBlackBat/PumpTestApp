import sys
import os
import ctypes
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFontDatabase
from .gui import MainWindow
from . import database as db
from . import styles

RESOURCES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')


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


def load_custom_fonts():
    """Регистрирует шрифт из resources/terminator.ttf в приложении и
    сохраняет РЕАЛЬНОЕ имя семейства (то, как его распознал сам Qt - оно
    не всегда совпадает с тем, что показывают сторонние инструменты) в
    styles.TERMINATOR_FONT_FAMILY, чтобы gui.py могло его использовать.
    Нужно вызывать ПОСЛЕ создания QApplication, но ДО создания MainWindow
    (иначе верхняя панель уже построится со старым шрифтом).

    Печатает в консоль, что именно пошло не так, если шрифт не
    применился - файл не найден / Qt не смог его загрузить / и т.д."""
    styles.TERMINATOR_FONT_FAMILY = None

    font_path = os.path.join(RESOURCES_DIR, 'terminator.ttf')
    if not os.path.exists(font_path):
        print(f"[шрифт] Файл не найден: {font_path}")
        return

    font_id = QFontDatabase.addApplicationFont(font_path)
    if font_id == -1:
        print(f"[шрифт] Qt не смог загрузить файл шрифта: {font_path}")
        return

    families = QFontDatabase.applicationFontFamilies(font_id)
    if not families:
        print("[шрифт] Шрифт загружен, но Qt не сообщил имя семейства")
        return

    styles.TERMINATOR_FONT_FAMILY = families[0]


def set_app_user_model_id():
    """Задаёт Windows отдельный 'Application User Model ID' для этого
    процесса. Без этого Windows часто группирует окно под системным
    значком python.exe/pythonw.exe в панели задач - собственный значок
    окна (setWindowIcon) при этом может так и не появиться в панели
    задач, даже если корректно показывается в Alt+Tab и в углу заголовка
    окна. Нужно вызывать ДО создания любых окон. Работает только на
    Windows - на других ОС просто ничего не делает."""
    if sys.platform != "win32":
        return
    try:
        app_id = "PumpTestApp.LabRulevogoUpravleniya.1"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass


def main():
    db.init_db()

    set_app_user_model_id()

    # Поддержка масштабирования Windows (125%/150%/200%) и разных DPI -
    # флаги обязательно нужно выставить ДО создания QApplication
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    load_custom_fonts()
    window = MainWindow()
    window.show()
    apply_title_bar_color(window)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()