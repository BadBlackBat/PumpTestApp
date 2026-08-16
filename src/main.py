import sys
import os
import ctypes
from PyQt5.QtCore import Qt, QPropertyAnimation
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFontDatabase
from .gui import MainWindow
from . import database as db
from . import styles
from . import db_sync
from . import auth
from .widgets.dialogs import _DialogBackgroundManager
from . import app_paths

RESOURCES_DIR = app_paths.get_resources_dir()


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


def compute_ui_scale():
    """Определяет коэффициент масштабирования интерфейса по реальному
    физическому разрешению экрана - НЕ то же самое, что процент
    масштабирования Windows (Панель управления -> Экран): у ноутбука с
    экраном 1366x768 он вполне может быть выставлен как обычные 100%,
    хотя фактического места на экране физически меньше, чем на эталоне.

    Программа спроектирована с расчётом на экран 1920x1080 - это
    "эталонный" масштаб 1.0, ничего не меняется на таких экранах и
    больше. На меньших экранах коэффициент пропорционально уменьшается
    (но никогда не увеличивается на больших). Нижняя граница 0.85 -
    дальше текст рисковал бы стать нечитаемым.

    В отличие от более ранней попытки - НЕ устанавливает никакую
    переменную окружения и не трогает системный DPI-механизм Qt вообще
    (тот способ на практике непредсказуемо взаимодействовал с реальными
    DPI-настройками конкретных компьютеров и ломал интерфейс). Просто
    возвращает число - применяется вручную к шрифту приложения и
    конкретным размерам виджетов (см. styles.set_ui_scale/scaled).

    ВАЖНО: используется GetDeviceCaps (DESKTOPHORZRES/DESKTOPVERTRES), а
    НЕ GetSystemMetrics - тот возвращает уже виртуализированное DPI-
    масштабированием Windows "логическое" разрешение, которое оказывается
    заниженным на ЛЮБОМ мониторе с масштабированием выше 100% в настройках
    Windows (а это сегодня норма практически везде, а не редкость) - из-за
    этого коэффициент раньше некорректно занижался даже на эталонном
    мониторе, для которого масштаб должен был оставаться ровно 1.0.
    GetDeviceCaps с этими константами специально предназначен для
    получения именно физического разрешения, в обход этой виртуализации.

    Экран узнаём до создания QApplication, тем же способом, что уже
    используется в set_app_user_model_id(). На других ОС возвращает 1.0
    без изменений."""
    if sys.platform != "win32":
        return 1.0
    try:
        DESKTOPHORZRES, DESKTOPVERTRES = 118, 117
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        hdc = user32.GetDC(0)
        if not hdc:
            return 1.0
        try:
            width = gdi32.GetDeviceCaps(hdc, DESKTOPHORZRES)
            height = gdi32.GetDeviceCaps(hdc, DESKTOPVERTRES)
        finally:
            user32.ReleaseDC(0, hdc)
        if width <= 0 or height <= 0:
            return 1.0
    except Exception:
        return 1.0

    BASELINE_WIDTH, BASELINE_HEIGHT = 1920, 1080
    scale = min(width / BASELINE_WIDTH, height / BASELINE_HEIGHT, 1.0)
    scale = max(0.85, scale)
    print(f"[масштаб интерфейса] физическое разрешение экрана: {width}x{height}, коэффициент: {scale:.3f}")
    return scale


def main():
    # Если установщик оставил временный резервный пароль открытым
    # текстом - хешируем его и сохраняем как обычный, удаляем временный
    # файл. Безопасно вызывать при каждом запуске - если временного
    # файла нет (обычная ситуация после первого запуска), ничего не
    # происходит.
    auth.process_pending_password()

    # Сверка с сетевой базой (если включён сетевой режим - иначе
    # ничего не делает и не влияет на локальный режим) - обязательно
    # ДО init_db(), чтобы миграция схемы применилась к финальной версии
    # локального файла, даже если её только что скопировали с сети
    sync_status, sync_message = db_sync.check_and_sync_at_startup()

    db.init_db()
    _DialogBackgroundManager.load_settings()
    styles.load_theme_setting()
    styles.set_ui_scale(compute_ui_scale())

    set_app_user_model_id()

    # Поддержка масштабирования Windows (125%/150%/200%) и разных DPI -
    # флаги обязательно нужно выставить ДО создания QApplication
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # Масштабируем общий шрифт приложения под UI_SCALE - самый заметный
    # и широкий по охвату эффект (затрагивает практически весь текст, у
    # которого нет собственного, явно заданного размера шрифта). Чисто
    # шрифтовое масштабирование средствами самого Qt (QFont), без
    # какого-либо DPI-механизма - предсказуемо и не зависит от системных
    # настроек масштабирования конкретного компьютера.
    if styles.UI_SCALE != 1.0:
        base_font = app.font()
        base_font.setPointSizeF(base_font.pointSizeF() * styles.UI_SCALE)
        app.setFont(base_font)

    load_custom_fonts()
    window = MainWindow()

    # Индикатор режима базы данных (Network/Local/Offline/Full offline)
    # в панели фильтров
    window.left_panel.set_db_status(db_sync.get_indicator_mode(sync_status))

    # Плавное появление окна - от полностью прозрачного к обычному виду.
    # Ссылку на анимацию храним в самом окне (window._startup_fade_anim) -
    # иначе сборщик мусора Python мог бы удалить объект анимации сразу
    # после этой функции, до того как она успеет доиграть.
    window.setWindowOpacity(0.0)
    window.showMaximized()
    apply_title_bar_color(window)
    window._startup_fade_anim = QPropertyAnimation(window, b"windowOpacity", window)
    window._startup_fade_anim.setDuration(300)
    window._startup_fade_anim.setStartValue(0.0)
    window._startup_fade_anim.setEndValue(1.0)
    window._startup_fade_anim.start()

    if sync_message:
        from .widgets.dialogs import GlowMessageDialog
        if sync_status == 'network_unreachable':
            GlowMessageDialog.show_error(window, "База данных", sync_message)
        else:
            GlowMessageDialog.show_success(window, "База данных", sync_message)

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()