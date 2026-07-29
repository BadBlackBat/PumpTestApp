# -*- coding: utf-8 -*-
"""
styles.py - централизованное хранилище всех стилей оформления (QSS)
приложения PumpTestApp.

Смысл файла: раньше строки стилей были разбросаны прямо по виджетам в
left_panel.py / right_panel.py / dialogs.py / gui.py / status_bar.py -
чтобы поменять оформление, приходилось искать нужную строчку по всем
файлам. Теперь все стили собраны здесь, разбиты по разделам согласно
тому, к какому модулю/виджету они относятся, и снабжены комментариями.

Как этим пользоваться:
    from . import styles
    self.table.setStyleSheet(styles.LEFT_PANEL_TABLE_STYLE)
"""

# ============================================================
# ПЕРЕКЛЮЧЕНИЕ ТЕМЫ (тёмная/светлая)
# ============================================================
# CURRENT_THEME - единственный источник истины о текущей теме на весь
# рантайм приложения. Меняется только через gui.py: MainWindow.apply_theme().
# Остальные модули просто читают его через функции ниже (get_*), а не
# проверяют флаг напрямую - так при добавлении новых тем не придётся
# искать все места со сравнением строки.
CURRENT_THEME = 'dark'  # 'dark' или 'light'


def is_light_theme():
    return CURRENT_THEME == 'light'


def load_theme_setting():
    """Загружает сохранённую тему - вызывать один раз при запуске
    программы, до создания главного окна (см. main.py)."""
    global CURRENT_THEME
    from PyQt5.QtCore import QSettings
    settings = QSettings("PumpTestApp", "MainSettings")
    CURRENT_THEME = settings.value("app_theme", "dark", type=str)


def save_theme_setting():
    """Сохраняет текущую тему - вызывается из gui.py при каждом
    переключении, чтобы при следующем запуске программа открылась в
    той же теме."""
    from PyQt5.QtCore import QSettings
    settings = QSettings("PumpTestApp", "MainSettings")
    settings.setValue("app_theme", CURRENT_THEME)


def get_top_bar_style():
    return TOP_BAR_STYLE_LIGHT if is_light_theme() else TOP_BAR_STYLE


def get_top_bar_logo_style():
    return TOP_BAR_LOGO_STYLE_BASE_LIGHT if is_light_theme() else TOP_BAR_LOGO_STYLE_BASE


def get_status_bar_style():
    return STATUS_BAR_STYLE_LIGHT if is_light_theme() else STATUS_BAR_STYLE


def get_glow_shadow_params():
    """(радиус размытия, альфа-канал 0-255) для тени панелей (_GlowFrame).

    На светлой теме тень заметно мягче и прозрачнее тёмной - у
    QGraphicsDropShadowEffect есть особенность: он строит тень по
    прямоугольному силуэту виджета, не зная о скруглении углов через
    QSS border-radius - из-за этого в самих скруглённых углах панели
    "протекает" немного тени. На тёмной теме это было незаметно (тень
    тёмная - панель тёмная), на светлой стало заметно - полностью убрать
    эту особенность рискованно (можно сломать отрисовку, как уже было
    с WA_NoSystemBackground), поэтому смягчаем тень, а не убираем совсем."""
    if is_light_theme():
        return 26, 100
    return LEFT_PANEL_GLOW_SHADOW_BLUR, 150


def get_glow_panel_style():
    """Базовый (без свечения/блика по краям - это рисуется отдельно в
    _GlowFrame.paintEvent) фон панели - графит для тёмной темы, мягкий
    длинный серебристый градиент для светлой."""
    return LEFT_PANEL_FILTER_PANEL_STYLE_LIGHT if is_light_theme() else LEFT_PANEL_FILTER_PANEL_STYLE


def get_title_bar_rgb():
    return TITLE_BAR_COLOR_RGB_LIGHT if is_light_theme() else TITLE_BAR_COLOR_RGB


def get_window_border_rgb():
    return WINDOW_BORDER_COLOR_RGB_LIGHT if is_light_theme() else WINDOW_BORDER_COLOR_RGB


def get_top_bar_icon_normal_color():
    return TOP_BAR_ICON_COLOR_NORMAL_LIGHT if is_light_theme() else TOP_BAR_ICON_COLOR_NORMAL


def get_top_bar_icon_hover_color():
    return TOP_BAR_ICON_COLOR_HOVER_LIGHT if is_light_theme() else TOP_BAR_ICON_COLOR_HOVER


def get_accent_color_rgb():
    """Акцентный цвет по умолчанию (RGB-кортеж) - фирменный бирюзовый на
    тёмной теме (там он реально "светится" на графите), тёмно-стальной
    бирюзовый на светлой (обычный яркий неон на светлом фоне не
    читается как свечение - нужен цвет поконтрастнее и потемнее)."""
    return LEFT_PANEL_ACCENT_COLOR_LIGHT if is_light_theme() else LEFT_PANEL_GLOW_COLOR


def get_accent_color_hex():
    """То же самое, но строкой "#rrggbb" - для мест, где QSS собирается
    строкой (ховер-рамки кнопок, полей ввода и т.д.)."""
    r, g, b = get_accent_color_rgb()
    return f"#{r:02x}{g:02x}{b:02x}"


def get_dialog_text_color():
    """Основной цвет текста в диалогах - светлый на тёмной теме (как и
    было, #e8eaed), наш графитовый на светлой (на серебристом фоне
    светлый текст просто не виден)."""
    return LEFT_PANEL_TEXT_COLOR_LIGHT if is_light_theme() else "#e8eaed"


import re as _re


def retheme_stylesheet(css):
    """Заменяет в уже готовой строке QSS цвета тёмной темы на цвета
    текущей активной темы. Работает как "постобработка" уже собранной
    строки стиля (см. _GlowDialog.showEvent, LeftPanel.refresh_theme) -
    вместо того чтобы искать и переписывать каждое из полусотни мест в
    исходном коде, где цвет мог быть зашит буквально в setStyleSheet().

    На тёмной теме ничего не меняет - возвращает css как есть."""
    if not css or not is_light_theme():
        return css
    accent_hex = get_accent_color_hex()
    text_hex = LEFT_PANEL_TEXT_COLOR_LIGHT

    # Текст (аккуратно: именно "color:", а не "background-color:")
    css = _re.sub(r'(?<!background-)\bcolor\s*:\s*#e8eaed', f'color: {text_hex}', css)
    css = _re.sub(r'(?<!background-)\bcolor\s*:\s*#ffffff', f'color: {text_hex}', css)
    css = _re.sub(r'(?<!background-)\bcolor\s*:\s*#fff\b', f'color: {text_hex}', css)
    css = _re.sub(r'(?<!background-)\bcolor\s*:\s*#f2f4f6', f'color: {text_hex}', css)

    # Акцентный бирюзовый (рамки при наведении/фокусе, выделение) ->
    # тёмно-стальной, контрастный на светлом фоне
    css = css.replace('#4fd1ff', accent_hex)
    css = css.replace('#7de0ff', accent_hex)
    css = css.replace('#8fe3ff', accent_hex)  # светлый оттенок ховера (поле поиска и т.п.)

    # То же самое, но в rgba(79, 209, 255, X) - используется для лёгкой
    # полупрозрачной подсветки фона при наведении (сохраняем альфа-канал,
    # меняем только сам цвет)
    accent_r, accent_g, accent_b = get_accent_color_rgb()
    css = _re.sub(
        r'rgba\(\s*79\s*,\s*209\s*,\s*255\s*,\s*(\d+)\s*\)',
        lambda m: f'rgba({accent_r}, {accent_g}, {accent_b}, {m.group(1)})',
        css
    )

    # Тёмный графитовый фон выпадающих списков/попапов -> светлый алюминий.
    # ВАЖНО: заменяем только когда это именно ФОН (background/
    # background-color), а не текст (color: #2b2d31 - это наш же
    # графитовый ЦВЕТ ТЕКСТА кнопок, его трогать нельзя - раньше здесь
    # была ошибка именно в этом: слепая замена превращала текст кнопок
    # в светлый, вместо того чтобы остаться графитовым)
    css = _re.sub(r'background(-color)?\s*:\s*#2b2d31',
                  lambda m: f'background{m.group(1) or ""}: #eef0f2', css)

    # Тёмный графитовый фон заголовков таблиц (во всех диалогах -
    # добавление насоса, редактирование, модификации и т.д.) -> светлый
    # алюминий, в тон остальным светлым заголовкам
    css = _re.sub(r'background(-color)?\s*:\s*#3a3d42',
                  lambda m: f'background{m.group(1) or ""}: #eef0f2', css)

    # Заголовки основной таблицы списка насосов -> ещё более светлый,
    # гладкий вариант (п.8 - "в стиле наших новых светлых кнопок")
    css = css.replace(_TABLE_HEADER_ALUMINUM, _TABLE_HEADER_ALUMINUM_LIGHT)

    # Алюминиевый градиент кнопок -> более гладкий и светлый вариант
    # (нужно подставлять уже готовые строки, т.к. это не просто цвет, а
    # целая строка qlineargradient(...))
    css = css.replace(_ALUMINUM_NORMAL, _ALUMINUM_NORMAL_LIGHT)
    css = css.replace(_ALUMINUM_HOVER, _ALUMINUM_HOVER_LIGHT)

    # Выпадающий список (фильтры) - при наведении на пункт (не
    # обязательно выбранный) текст становится серебристым - такого
    # правила в исходном (тёмном) стиле не было, добавляем отдельно
    if 'QAbstractItemView' in css and 'QComboBox' in css:
        css += """
    QComboBox QAbstractItemView::item:hover {
        color: #e9ebee;
    }
"""

    return css


def retheme_widget_tree(root_widget):
    """Проходит по root_widget и всем его дочерним виджетам, перекрашивая
    их QSS под текущую тему. Используется при переключении темы - и для
    диалогов (см. _GlowDialog.showEvent), и для постоянных панелей вроде
    левой панели (см. LeftPanel.refresh_theme).

    ВАЖНО: у каждого виджета при первой встрече запоминается его
    ИСХОДНЫЙ (написанный в коде, всегда "тёмный") стиль - в свойстве
    "_original_stylesheet". Тема каждый раз пересчитывается именно от
    этого сохранённого оригинала, а не от уже применённого стиля -
    иначе (как было раньше) переключение тёмная->светлая->тёмная не
    отменяло бы перекраску: retheme_stylesheet() ничего не делает на
    тёмной теме, поэтому виджет так и оставался бы светлым навсегда."""
    from PyQt5.QtWidgets import QWidget
    widgets = [root_widget] + root_widget.findChildren(QWidget)
    for w in widgets:
        # Виджеты с собственным механизмом темизации (_GlowFrame,
        # _GlowLine, _IconButton) пропускаем - иначе общий обход
        # конфликтовал бы с их refresh_all() (см. подробное объяснение
        # в _GlowFrame.__init__, left_panel.py)
        if w.property("_self_themed"):
            continue
        original = w.property("_original_stylesheet")
        if original is None:
            original = w.styleSheet()
            w.setProperty("_original_stylesheet", original)
        if original:
            new_sheet = retheme_stylesheet(original)
            if new_sheet != w.styleSheet():
                w.setStyleSheet(new_sheet)


# --- Светлая тема: серебристый алюминий (вариант 1) ---
# Отличие от градиента на кнопках (см. алюминиевые константы кнопок
# дальше по файлу) - переход здесь специально длиннее и мягче, без
# резких граней между цветовыми остановками, чтобы не выглядеть "как
# кнопка", а читаться как большая цельная панель.
LEFT_PANEL_FILTER_PANEL_STYLE_LIGHT = """
    QFrame#filtersPanel {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #fcfdfe, stop:0.35 #eef0f2, stop:0.7 #dde1e5, stop:1 #ced2d7);
        border-radius: 10px;
    }
"""

# Акцент для светлой темы - глубокий стальной бирюзовый (тот же тон, что
# уже используется для линий MIN/MAX на графиках - #0d7a99), НЕ яркий
# неон: на светлом фоне яркий неон просто не читается как "свечение"
LEFT_PANEL_ACCENT_COLOR_LIGHT = (13, 122, 153)
LEFT_PANEL_TEXT_COLOR_LIGHT = "#2b2d31"  # наш графитовый - на светлом фоне используется как цвет текста

TOP_BAR_STYLE_LIGHT = """
    QWidget#topBar {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #fcfdfe, stop:0.45 #e9ebee, stop:1 #d2d6db);
        border-bottom-left-radius: 10px;
        border-bottom-right-radius: 10px;
        border-bottom: 1px solid #b7bcc2;
    }
"""
TOP_BAR_LOGO_STYLE_BASE_LIGHT = """
    color: #2b2d31;
    letter-spacing: 1.5px;
"""

STATUS_BAR_STYLE_LIGHT = """
    QStatusBar {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #d2d6db, stop:0.45 #e9ebee, stop:1 #fcfdfe);
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
        border-top: 1px solid #b7bcc2;
    }
    QStatusBar QLabel {
        color: #2b2d31;
        font-family: "Consolas", "Courier New", monospace;
        font-size: 9pt;
        letter-spacing: 1px;
        background: transparent;
    }
    QStatusBar::item {
        border: none;
    }
"""

TITLE_BAR_COLOR_RGB_LIGHT = (0xe9, 0xeb, 0xee)
WINDOW_BORDER_COLOR_RGB_LIGHT = (0xb7, 0xbc, 0xc2)

TOP_BAR_ICON_COLOR_NORMAL_LIGHT = "#6b6f75"
TOP_BAR_ICON_COLOR_HOVER_LIGHT = "#0d7a99"

"""
Важно: это ЧИСТЫЙ ПЕРЕНОС существующих стилей без каких-либо визуальных
изменений - значения цветов/отступов/шрифтов везде оставлены точно
такими же, какими были в коде до переноса.

Стиль каждого виджета вешается ЛОКАЛЬНО - через setStyleSheet() на
конкретный виджет (self.table, self.status_bar и т.д.), а не глобально
на всё приложение. Поэтому стили разных частей интерфейса (статус-бар,
верхняя панель, левая и правая панели) можно спокойно дорабатывать по
отдельности, не рискуя случайно затронуть остальные - они физически не
пересекаются.
"""



# ============================================================
# ЛЕВАЯ ПАНЕЛЬ (widgets/left_panel.py)
# Список насосов, фильтры, пагинация, статистика по заказу
# ============================================================

# Голубая плашка со статистикой по выбранному заказу (появляется над
# таблицей списка, когда в фильтре выбран конкретный заказ) - теперь в
# общей графитовой палитре с бирюзовой окантовкой, вместо прежней
# светло-голубой (не сочеталась с остальным тёмным оформлением)
LEFT_PANEL_STATS_LABEL_STYLE = """
    background-color: #2b2d31;
    border: 1px solid #4fd1ff;
    border-radius: 6px;
    padding: 6px;
    margin: 5px 0px;
    color: #ffffff;
    font-size: 10pt;
"""

# --- Панель фильтров целиком (см. класс _GlowFrame в left_panel.py) ---
# Графитовый фон с лёгким градиентом + скруглённые углы. Само бирюзовое
# свечение по краям рисуется отдельно, вручную через QPainter в
# _GlowFrame.paintEvent - QSS не умеет "гаснущее к углам" свечение.
LEFT_PANEL_FILTER_PANEL_STYLE = """
    QFrame#filtersPanel {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #3a3d42, stop:1 #202225);
        border-radius: 10px;
    }
"""
LEFT_PANEL_GLOW_COLOR = (79, 209, 255)   # тот же акцентный бирюзовый, что и везде в приложении
LEFT_PANEL_GLOW_THICKNESS = 3            # толщина светящейся полосы, px
LEFT_PANEL_GLOW_SHADOW_BLUR = 22         # радиус размытия тени панели (со всех сторон)

# Подпись фильтра ("Вердикт:", "Тип:" и т.п.) внутри чипа - белый текст,
# обычной (не жирной) насыщенности
LEFT_PANEL_FILTER_LABEL_STYLE = "color: #ffffff; font-weight: normal; font-size: 9pt;"

# Подпись "Поиск:" - крупнее и жирнее обычных подписей фильтров (сам
# поиск - главный, самый часто используемый фильтр в панели)
LEFT_PANEL_SEARCH_LABEL_STYLE = "color: #ffffff; font-weight: bold; font-size: 11pt;"

# "Чип" - лёгкая полупрозрачная подложка, объединяющая подпись фильтра с
# её виджетом в одну визуальную группу (чтобы не выглядели разбросанными
# по панели). Используется для Вердикт/Тип/Герметичность/Заказ/дат
LEFT_PANEL_CHIP_STYLE = """
    QFrame {
        background-color: rgba(255, 255, 255, 20);
        border-radius: 6px;
    }
"""

# Выпадающие списки фильтров и поля дат - вместо стандартной синей
# подсветки Qt при наведении/раскрытии используем фирменный бирюзовый
# (и в самом поле, и в его выпадающем списке - see selection-background)
LEFT_PANEL_COMBO_STYLE = """
    QComboBox, QDateEdit {
        background-color: rgba(255, 255, 255, 15);
        border: 1px solid #7a7f87;
        border-radius: 4px;
        color: #ffffff;
        padding: 1px 6px;
    }
    QComboBox:hover, QDateEdit:hover {
        border: 1px solid #4fd1ff;
        background-color: rgba(79, 209, 255, 30);
    }
    QComboBox::drop-down, QDateEdit::drop-down {
        border: none;
    }
    QComboBox QAbstractItemView {
        background-color: #2b2d31;
        color: #ffffff;
        selection-background-color: #4fd1ff;
        selection-color: #1c1e21;
        outline: none;
    }
    QComboBox QAbstractItemView QScrollBar:vertical {
        background: #2b2d31;
        width: 10px;
        margin: 2px;
        border-radius: 5px;
    }
    QComboBox QAbstractItemView QScrollBar::handle:vertical {
        background: #4fd1ff;
        min-height: 24px;
        border-radius: 5px;
    }
    QComboBox QAbstractItemView QScrollBar::handle:vertical:hover {
        background: #7de0ff;
    }
    QComboBox QAbstractItemView QScrollBar::add-line:vertical,
    QComboBox QAbstractItemView QScrollBar::sub-line:vertical {
        height: 0px;
        border: none;
        background: none;
    }
    QComboBox QAbstractItemView QScrollBar::add-page:vertical,
    QComboBox QAbstractItemView QScrollBar::sub-page:vertical {
        background: transparent;
    }
"""

# Всплывающий календарь QDateEdit - по умолчанию у него получался чёрный
# фон, на котором не видно чисел (наследовал что-то из общей тёмной темы,
# но не полностью). Явно красим сам календарь в графит/хром с читаемым
# светлым текстом и бирюзовым выделением текущего/выбранного дня.
LEFT_PANEL_CALENDAR_STYLE = """
    QCalendarWidget QWidget {
        background-color: #3a3d42;
        color: #ffffff;
    }
    QCalendarWidget QToolButton {
        background-color: #3a3d42;
        color: #ffffff;
        border: none;
        border-radius: 4px;
        padding: 4px;
    }
    QCalendarWidget QToolButton:hover {
        background-color: rgba(79, 209, 255, 60);
    }
    QCalendarWidget QMenu {
        background-color: #2b2d31;
        color: #ffffff;
    }
    QCalendarWidget QSpinBox {
        background-color: #2b2d31;
        color: #ffffff;
        selection-background-color: #4fd1ff;
    }
    QCalendarWidget QAbstractItemView:enabled {
        background-color: #2b2d31;
        color: #ffffff;
        selection-background-color: #4fd1ff;
        selection-color: #1c1e21;
    }
    QCalendarWidget QAbstractItemView:disabled {
        color: #6b6f75;
    }
    QCalendarWidget QAbstractItemView::item:hover {
        background-color: rgba(79, 209, 255, 60);
    }
    QCalendarWidget QHeaderView {
        background-color: #2b2d31;
    }
    QCalendarWidget QHeaderView::section {
        background-color: #2b2d31;
        color: #e8eaed;
        border: none;
        padding: 4px;
    }
    QCalendarWidget QToolButton#qt_calendar_monthbutton {
        padding-right: 16px;
    }
"""


def apply_calendar_style(calendar_widget):
    """Применяет оформление к всплывающему календарю QDateEdit под
    текущую тему.

    На тёмной теме - тёмная стилизация через QSS, палитру и явный
    формат текста дней недели (как и было). На светлой теме - календарь
    возвращается к простому нативному светлому виду (тот, что был у
    него изначально) - никакой специальной стилизации не требуется,
    она и была нужна только для того, чтобы вписать календарь в тёмную
    тему приложения.

    У QCalendarWidget есть свой, отдельный от QSS и палитры механизм
    именно для будних/выходных дней - setWeekdayTextFormat(). Именно он
    красил субботу/воскресенье в красный цвет по умолчанию (поэтому они
    были видны), а будние дни оставались белым текстом по умолчанию на
    белом фоне - ни стиль, ни палитра его не переопределяют, нужно
    менять специально через этот метод."""
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QPalette, QColor, QTextCharFormat

    if is_light_theme():
        # Светлая тема - вместо "сброса" стиля (не сработало надёжно -
        # зона с числами оставалась тёмной, судя по всему, из-за
        # унаследованной откуда-то стилизации) явно задаём полный набор
        # светлых стилей, так же подробно, как и для тёмной темы ниже
        calendar_widget.setStyleSheet("""
            QCalendarWidget QWidget {
                background-color: #ffffff;
                color: #2b2d31;
            }
            QCalendarWidget QToolButton {
                background-color: #ffffff;
                color: #2b2d31;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: rgba(13, 122, 153, 40);
            }
            QCalendarWidget QMenu {
                background-color: #ffffff;
                color: #2b2d31;
            }
            QCalendarWidget QSpinBox {
                background-color: #ffffff;
                color: #2b2d31;
                selection-background-color: #0d7a99;
            }
            QCalendarWidget QAbstractItemView:enabled {
                background-color: #ffffff;
                color: #2b2d31;
                selection-background-color: #0d7a99;
                selection-color: #ffffff;
            }
            QCalendarWidget QAbstractItemView:disabled {
                color: #b0b4b9;
            }
            QCalendarWidget QHeaderView {
                background-color: #ffffff;
            }
            QCalendarWidget QHeaderView::section {
                background-color: #ffffff;
                color: #2b2d31;
                border: none;
                padding: 4px;
            }
            QCalendarWidget QToolButton#qt_calendar_monthbutton {
                padding-right: 16px;
            }
        """)
        palette = calendar_widget.palette()
        palette.setColor(QPalette.WindowText, QColor("#2b2d31"))
        palette.setColor(QPalette.Window, QColor("#ffffff"))
        palette.setColor(QPalette.Text, QColor("#2b2d31"))
        palette.setColor(QPalette.Base, QColor("#ffffff"))
        palette.setColor(QPalette.ButtonText, QColor("#2b2d31"))
        calendar_widget.setPalette(palette)

        weekday_format = QTextCharFormat()
        weekday_format.setForeground(QColor("#2b2d31"))
        for day in (Qt.Monday, Qt.Tuesday, Qt.Wednesday, Qt.Thursday, Qt.Friday):
            calendar_widget.setWeekdayTextFormat(day, weekday_format)

        weekend_format = QTextCharFormat()
        weekend_format.setForeground(QColor("#c0392b"))
        for day in (Qt.Saturday, Qt.Sunday):
            calendar_widget.setWeekdayTextFormat(day, weekend_format)
        nav_icon_color = "#2b2d31"
    else:
        calendar_widget.setStyleSheet(LEFT_PANEL_CALENDAR_STYLE)
        palette = calendar_widget.palette()
        palette.setColor(QPalette.WindowText, QColor("#e8eaed"))
        palette.setColor(QPalette.Window, QColor("#2b2d31"))
        palette.setColor(QPalette.Text, QColor("#ffffff"))
        palette.setColor(QPalette.Base, QColor("#2b2d31"))
        palette.setColor(QPalette.ButtonText, QColor("#e8eaed"))
        calendar_widget.setPalette(palette)

        weekday_format = QTextCharFormat()
        weekday_format.setForeground(QColor("#00ccf0"))
        for day in (Qt.Monday, Qt.Tuesday, Qt.Wednesday, Qt.Thursday, Qt.Friday):
            calendar_widget.setWeekdayTextFormat(day, weekday_format)

        weekend_format = QTextCharFormat()
        weekend_format.setForeground(QColor("#ff8080"))  # мягче чистого красного - читаемо на тёмном фоне
        for day in (Qt.Saturday, Qt.Sunday):
            calendar_widget.setWeekdayTextFormat(day, weekend_format)
        nav_icon_color = "#e8eaed"

    # Кнопки "предыдущий/следующий месяц" - у Qt это документированные,
    # стабильные внутренние имена объектов, официальный способ их найти
    # и настроить. Заменяем стандартные (зелёные) стрелки на свои
    # аккуратные шевроны в тон текущей теме.
    import os
    from PyQt5.QtWidgets import QToolButton
    from PyQt5.QtCore import QSize
    from . import icon_utils
    icons_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'icons')
    prev_btn = calendar_widget.findChild(QToolButton, "qt_calendar_prevmonth")
    next_btn = calendar_widget.findChild(QToolButton, "qt_calendar_nextmonth")
    prev_icon_path = os.path.join(icons_dir, 'calendar_prev.svg')
    next_icon_path = os.path.join(icons_dir, 'calendar_next.svg')
    if prev_btn is not None and os.path.exists(prev_icon_path):
        prev_btn.setIcon(icon_utils.tinted_icon(prev_icon_path, nav_icon_color, 14))
        prev_btn.setIconSize(QSize(14, 14))
        prev_btn.setText("")
    if next_btn is not None and os.path.exists(next_icon_path):
        next_btn.setIcon(icon_utils.tinted_icon(next_icon_path, nav_icon_color, 14))
        next_btn.setIconSize(QSize(14, 14))
        next_btn.setText("")

    # Ховер на отдельных ячейках с числами не проявлялся - вероятная
    # причина: у внутренней таблицы календаря не включено отслеживание
    # движения мыши без нажатой кнопки, из-за чего QSS ":hover" на
    # ячейках просто не получал события для срабатывания
    from PyQt5.QtWidgets import QTableView
    calendar_view = calendar_widget.findChild(QTableView)
    if calendar_view is not None:
        calendar_view.setMouseTracking(True)
        viewport = calendar_view.viewport()
        if viewport is not None:
            viewport.setMouseTracking(True)

# --- Поле ввода пароля - почти прозрачное (чуть отличается от фона
# диалога), с тем же принципом наведения/фокуса, что и у строки поиска
# насоса: лёгкая подсветка при наведении, более явная - в фокусе ---
PASSWORD_INPUT_STYLE = """
    QLineEdit {
        background-color: rgba(255, 255, 255, 12);
        border: 1px solid #6b6f75;
        border-radius: 4px;
        color: #e8eaed;
        padding: 4px 8px;
    }
    QLineEdit:hover {
        border: 1px solid #8fe3ff;
        background-color: rgba(79, 209, 255, 25);
    }
    QLineEdit:focus {
        border: 2px solid #4fd1ff;
        background-color: rgba(79, 209, 255, 40);
    }
"""

PASSWORD_INPUT_STYLE_LIGHT = """
    QLineEdit {
        background-color: rgba(43, 45, 49, 10);
        border: 1px solid #b7bcc2;
        border-radius: 4px;
        color: #2b2d31;
        padding: 4px 8px;
    }
    QLineEdit:hover {
        border: 1px solid #0d7a99;
        background-color: rgba(13, 122, 153, 25);
    }
    QLineEdit:focus {
        border: 2px solid #0d7a99;
        background-color: rgba(13, 122, 153, 40);
    }
"""


def get_password_input_style():
    return PASSWORD_INPUT_STYLE_LIGHT if is_light_theme() else PASSWORD_INPUT_STYLE


# --- Строка поиска: не как обычное поле ввода, а просто нижнее
# подчёркивание контрастным цветом. При наведении - лёгкая подсветка,
# в фокусе - явный бирюзовый акцент. Шрифт - жирный моноширинный
# (Consolas - тот же "терминаторский" стиль, что и в статус-баре):
# номера насосов только латиница+цифры, моноширинный шрифт для них
# отлично подходит ---
LEFT_PANEL_SEARCH_INPUT_STYLE = """
    QLineEdit#searchInput {
        background: transparent;
        border: none;
        border-bottom: 2px solid #7a7f87;
        color: #ffffff;
        font-family: "Consolas", monospace;
        font-weight: bold;
        font-size: 11pt;
        padding: 4px 2px;
    }
    QLineEdit#searchInput:hover {
        border-bottom: 2px solid #8fe3ff;
        background-color: rgba(79, 209, 255, 25);
    }
    QLineEdit#searchInput:focus {
        border-bottom: 3px solid #4fd1ff;
        background-color: rgba(79, 209, 255, 40);
    }
"""

# --- Кнопка "Сбросить фильтры": не должна выглядеть как обычная кнопка -
# фон под шлифованный алюминий (сымитирован повторяющимся многостопным
# градиентом - светлые/тёмные полоски подряд, без готовой картинки-
# текстуры). При наведении - контур становится ярко-бирюзовым, фон
# слегка темнее.
#
# Почему алюминий, а не карбон: карбоновая (диагональная плетёная)
# текстура плохо имитируется одним градиентом - потребовалась бы
# отдельная картинка с узором. Плюс шлифованный металл лучше сочетается
# с уже устоявшейся графитовой/хромовой палитрой всего приложения
# (статус-бар, верхняя панель) - карбон выглядел бы отдельным, чужеродным
# акцентом на их фоне.
def _brushed_metal_gradient(light, dark, bands=16, horizontal_bands=False):
    """direction по умолчанию даёт вертикальные полосы (текстура "растёт"
    слева направо - как на кнопках). horizontal_bands=True даёт полосы
    горизонтальные (текстура "растёт" сверху вниз)."""
    stops = []
    for i in range(bands):
        pos = i / (bands - 1)
        color = light if i % 2 == 0 else dark
        stops.append(f"stop:{pos:.3f} {color}")
    if horizontal_bands:
        coords = "x1:0, y1:0, x2:0, y2:1"
    else:
        coords = "x1:0, y1:0, x2:1, y2:0"
    return f"qlineargradient({coords}, " + ", ".join(stops) + ")"

_ALUMINUM_NORMAL = _brushed_metal_gradient("#c9cdd2", "#a6aab0")
_ALUMINUM_HOVER = _brushed_metal_gradient("#aeb2b8", "#8b8f95")

# Светлая тема - тот же приём, но заметно глаже (меньше полос - мягче
# переход между ними) и светлее тон, чтобы кнопка не выглядела резкой
# полосатой вставкой на итак уже светлом серебристом фоне
_ALUMINUM_NORMAL_LIGHT = _brushed_metal_gradient("#f5f6f8", "#e6e8eb", bands=6)
_ALUMINUM_HOVER_LIGHT = _brushed_metal_gradient("#eef0f2", "#dadde1", bands=6)

LEFT_PANEL_RESET_BTN_STYLE = f"""
    QPushButton#chromeButton {{
        background: {_ALUMINUM_NORMAL};
        border: 1px solid #6b6f75;
        border-radius: 4px;
        color: #2b2d31;
        font-weight: bold;
        padding: 2px 16px;
    }}
    QPushButton#chromeButton:hover {{
        background: {_ALUMINUM_HOVER};
        border: 2px solid #4fd1ff;
    }}
"""

# Кнопки пагинации (◀ ▶) - тот же алюминиевый стиль, но сама кнопка
# компактнее, а стрелка внутри - крупнее, для лучшей читаемости
LEFT_PANEL_PAGINATION_BTN_STYLE = f"""
    QPushButton#chromeButton {{
        background: {_ALUMINUM_NORMAL};
        border: 1px solid #6b6f75;
        border-radius: 4px;
        color: #2b2d31;
        font-weight: bold;
        font-size: 13pt;
        padding: 0px;
    }}
    QPushButton#chromeButton:hover {{
        background: {_ALUMINUM_HOVER};
        border: 2px solid #4fd1ff;
    }}
"""

# Чекбокс "Дубли" - увеличенный квадрат-индикатор, заливается фирменным
# бирюзовым при отметке (упрощённая замена "кастомной галочки" - без
# готовой картинки с глифом самой галочки закрашенный квадрат читается
# как чек-индикатор так же ясно, но надёжнее рисуется в любой теме)
LEFT_PANEL_CHECKBOX_STYLE = """
    QCheckBox {
        color: #ffffff;
        font-size: 10.5pt;
        spacing: 8px;
    }
    QCheckBox::indicator {
        width: 15px;
        height: 15px;
        border: 2px solid #7a7f87;
        border-radius: 4px;
        background: transparent;
    }
    QCheckBox::indicator:hover {
        border: 2px solid #8fe3ff;
    }
    QCheckBox::indicator:checked {
        background-color: #4fd1ff;
        border: 2px solid #4fd1ff;
    }
"""

# Основная таблица списка насосов: центрирование текста в ячейках,
# заголовки колонок оформлены под кнопки (тот же алюминиевый градиент,
# но горизонтальными полосами и более мягким, размытым переходом), при
# наведении на заголовок - фирменная бирюзовая подсветка вместо
# стандартной синей. Пустое пространство таблицы (где нет строк) -
# светлый алюминий (светлее, чем у кнопок, чтобы не сливаться с ними),
# тоже горизонтальными полосами.
#
# ВАЖНО: сюда сознательно НЕ добавляется правило "QTableWidget::item:selected"
# - выделение строки реализовано отдельно, через два полупрозрачных
# оверлея (наведение/выделение) поверх таблицы + кастомный делегат
# _NoSelectionPaintDelegate (см. left_panel.py), который отключает
# штатную заливку выделения Qt. Если добавить сюда фон для :selected -
# он будет конфликтовать с этой логикой и перекрывать анимированный цвет.
_TABLE_LIGHT_ALUMINUM = _brushed_metal_gradient(
    "#eef0f2", "#d8dade", bands=20, horizontal_bands=True
)
# Заголовки - горизонтальные полосы, мало полос и близкие по тону цвета =
# более мягкий, размытый переход (меньше полос - каждая шире, границы
# между ними менее заметны)
_TABLE_HEADER_ALUMINUM = _brushed_metal_gradient(
    "#c3c7cc", "#b2b6bb", bands=6, horizontal_bands=True
)
# Ещё светлее и глаже - специально для светлой темы (п.8: "в стиле наших
# новых светлых кнопок")
_TABLE_HEADER_ALUMINUM_LIGHT = _brushed_metal_gradient(
    "#fafbfc", "#eef0f2", bands=6, horizontal_bands=True
)


def build_left_panel_table_style(arrow_down_path=None, arrow_up_path=None, header_font_family=None):
    """Стиль таблицы списка насосов. Стрелки сортировки - отдельными
    картинками (см. resources/arrow_*_red.png), т.к. одним QSS крупнее и
    краснее штатную стрелку не сделать - нужна собственная картинка.
    Если пути не переданы (например, файлы почему-то не найдены) -
    правила для стрелок просто не добавляются, Qt покажет свою обычную.

    header_font_family - шрифт заголовков ЗАДАЁТСЯ ПРЯМО В QSS (а не
    только через setFont() в коде) - на практике надёжнее: если
    полагаться только на setFont(), стилевой лист таблицы иногда
    перебивает шрифт секции заголовка при повторной перерисовке."""
    arrow_rules = ""
    if arrow_down_path and arrow_up_path:
        arrow_rules = f"""
    QHeaderView::down-arrow {{
        image: url({arrow_down_path});
        width: 12px;
        height: 12px;
    }}
    QHeaderView::up-arrow {{
        image: url({arrow_up_path});
        width: 12px;
        height: 12px;
    }}
"""
    font_rule = ""
    if header_font_family:
        font_rule = f'font-family: "{header_font_family}", Arial, sans-serif;'

    return f"""
    QTableWidget {{
        background: {_TABLE_LIGHT_ALUMINUM};
        gridline-color: #b0b4b9;
        border: 1px solid #c5c8cc;
        border-radius: 8px;
    }}
    QTableWidget::item {{
        text-align: center;
    }}
    QHeaderView::section {{
        background: {_TABLE_HEADER_ALUMINUM};
        color: #2b2d31;
        font-weight: bold;
        {font_rule}
        border: 1px solid #6b6f75;
        padding: 2px 4px;
    }}
    QHeaderView::section:first {{
        border-top-left-radius: 8px;
    }}
    QHeaderView::section:last {{
        border-top-right-radius: 8px;
    }}
    QHeaderView::section:hover {{
        background-color: #4fd1ff;
        color: #0d1b2a;
    }}
{arrow_rules}
"""


# ============================================================
# ПРАВАЯ ПАНЕЛЬ (widgets/right_panel.py)
# Просмотр протокола проверки, графики, сравнение дублей
# ============================================================

# Рамка вокруг области прокрутки правой панели больше не нужна здесь -
# теперь её обрамляет _GlowFrame (тот же графитовый контур с бирюзовым
# свечением, что и у левой панели). Собственное скругление у самой
# QScrollArea оставлено - смягчает переход к внешней скруглённой рамке
# (тот же приём, что и у таблицы в левой панели)
RIGHT_PANEL_SCROLL_STYLE = """
    QScrollArea {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #ffffff, stop:0.5 #f4f5f7, stop:1 #eceef1);
        border: 1px solid #9a9ea4;
        border-radius: 8px;
    }
    QScrollArea > QWidget#qt_scrollarea_viewport {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #ffffff, stop:0.5 #f4f5f7, stop:1 #eceef1);
    }
"""

# Светлая тема - без тонкой рамки (визуально выбивалась из общего вида
# на светлом фоне) - взамен программно добавляется мягкая тень (см.
# right_panel.py, apply_scroll_area_theme)
RIGHT_PANEL_SCROLL_STYLE_LIGHT = """
    QScrollArea {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #ffffff, stop:0.5 #f4f5f7, stop:1 #eceef1);
        border: none;
        border-radius: 8px;
    }
    QScrollArea > QWidget#qt_scrollarea_viewport {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #ffffff, stop:0.5 #f4f5f7, stop:1 #eceef1);
    }
"""


def get_right_panel_scroll_style():
    return RIGHT_PANEL_SCROLL_STYLE_LIGHT if is_light_theme() else RIGHT_PANEL_SCROLL_STYLE

# Заглушка-логотип по центру правой панели - показывается, пока не
# выбран ни один насос (и пока не идёт загрузка протокола). Без фона и
# рамки - просто отступ вокруг картинки и текста. Привязан к objectName
# ("logoContainer" - см. right_panel.py), чтобы стиль применялся только
# к самому контейнеру, а не "протекал" на дочерние QLabel внутри него
# (иначе, например, у картинки и у текста появлялись бы свои рамки).
RIGHT_PANEL_LOGO_STYLE = """
    QWidget#logoContainer {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #05050d,
            stop:0.5 #0d1b3e,
            stop:1 #1b0f3e);
        border: 1px solid #4fd1ff;
        border-radius: 12px;
        padding: 40px;
    }
"""

# Светлая тема - нарядный светлый градиент вместо "киберпанк" тёмного,
# графитовый текст вместо неонового
RIGHT_PANEL_LOGO_STYLE_LIGHT = """
    QWidget#logoContainer {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #fdfefe,
            stop:0.45 #eef1f5,
            stop:1 #dbe1e8);
        border: 1px solid #b7bcc2;
        border-radius: 12px;
        padding: 40px;
    }
"""


def get_right_panel_logo_style():
    return RIGHT_PANEL_LOGO_STYLE_LIGHT if is_light_theme() else RIGHT_PANEL_LOGO_STYLE

# Текст-подсказка ("Выберите насос для просмотра протокола") поверх
# киберпанк-градиента выше - светящийся голубой неон, тот же оттенок,
# что и акцентная подсветка статус-бара/верхней панели (единая палитра)
RIGHT_PANEL_LOGO_TEXT_STYLE = """
    color: #7de8ff;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 16pt;
    letter-spacing: 1px;
"""

RIGHT_PANEL_LOGO_TEXT_STYLE_LIGHT = """
    color: #2b2d31;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 16pt;
    letter-spacing: 1px;
"""


def get_right_panel_logo_text_style():
    return RIGHT_PANEL_LOGO_TEXT_STYLE_LIGHT if is_light_theme() else RIGHT_PANEL_LOGO_TEXT_STYLE


def get_watermark_color():
    """Цвет водяного знака (силуэт насоса) за текстом-заглушкой
    "Выберите насос" - светлый на тёмной теме, тёмный на светлой.
    Полупрозрачный (alpha ~24 из 255, ~9%) - едва заметный, ненавязчивый
    силуэт, а не бросающийся в глаза рисунок."""
    return (58, 61, 66, 24) if is_light_theme() else (232, 234, 237, 24)


# Индикатор "Загрузка протокола..." - показывается на время построения
# таблиц и графиков matplotlib (эта операция синхронная и заметна по
# времени), чтобы пользователю было очевидно, что идёт загрузка, а не
# зависание программы. Без рамки/фона - просто отступ вокруг иконки и
# текста. Привязан к objectName ("loadingContainer" - см. right_panel.py),
# чтобы стиль не "протекал" на дочерние иконку и текст по отдельности
# (та же история, что раньше была с логотипом-заглушкой).
RIGHT_PANEL_LOADING_STYLE = """
    QWidget#loadingContainer {
        padding: 20px;
    }
"""
RIGHT_PANEL_LOADING_TEXT_STYLE = "color: #555;"

# Легенда с пояснением цветовой подсветки несоответствий техническим
# требованиям (текстовая строка под таблицами протокола)
RIGHT_PANEL_LEGEND_STYLE = "background-color: transparent; padding: 5px;"

# Общий фон-подложка для панели таблиц испытаний (tables_panel) И для
# отдельной панели герметичности (seal_panel) - используется ОДНА И ТА
# ЖЕ строка для обеих панелей, чтобы они визуально читались как единое
# целое ("одна общая панель", а не два разных блока)
RIGHT_PANEL_CARD_STYLE = (
    "QFrame { background-color: #f2f5f7; "
    "border: 1px solid #d5dbe0; border-radius: 4px; }"
)

# Подложка текстового блока сводной статистики по базе (кнопка "📊" в
# верхней панели, метод display_statistics)
RIGHT_PANEL_STATS_TEXT_STYLE = "background: transparent; color: #e8eaed; padding: 4px;"

# Тёмно-синий фон на весь блок статистики - тот же градиент, что и у
# логотипа-заглушки при запуске программы (просто на большую область)
RIGHT_PANEL_STATS_BG_STYLE = """
    QWidget#statsBackground {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #05050d,
            stop:0.5 #0d1b3e,
            stop:1 #1b0f3e);
        border-radius: 12px;
    }
"""

# Светлая тема - тот же светлый градиент, что и у заглушки-логотипа
# правой панели (RIGHT_PANEL_LOGO_STYLE_LIGHT) - используется и для
# статистики, и для снимка протокола "по высоте" (оба показываются в
# одном и том же widget#statsBackground)
RIGHT_PANEL_STATS_BG_STYLE_LIGHT = """
    QWidget#statsBackground {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #fdfefe,
            stop:0.45 #eef1f5,
            stop:1 #dbe1e8);
        border-radius: 12px;
    }
"""


def get_right_panel_stats_bg_style():
    return RIGHT_PANEL_STATS_BG_STYLE_LIGHT if is_light_theme() else RIGHT_PANEL_STATS_BG_STYLE

# Тулбар matplotlib (зум/панорама/сброс масштаба кнопкой "Home") над
# каждым графиком - убираем внутренние отступы/рамку, чтобы тулбар не
# съедал лишнее место у самого графика
RIGHT_PANEL_GRAPH_TOOLBAR_STYLE = (
    "QToolBar { spacing: 0px; padding: 0px; margin: 0px; border: 0px; }"
)


# ============================================================
# ДИАЛОГИ (widgets/dialogs.py)
# Добавление/редактирование модификаций и протоколов насосов
# ============================================================

# Жирный подзаголовок раздела внутри AddModificationDialog - например,
# заголовки "Испытание 1", "Проверка на герметичность" и т.п. С отступом
# сверху (эти разделы там расположены вертикально, друг под другом)
DIALOG_SECTION_TITLE_STYLE = "font-weight: bold; margin-top: 10px;"

# Тот же жирный подзаголовок, но БЕЗ отступа сверху - используется в
# AddPumpDialog и EditPumpDialog, где заголовки испытаний/герметичности
# расположены более плотно (в горизонтальный ряд колонок)
DIALOG_SECTION_TITLE_STYLE_COMPACT = "font-weight: bold;"


# ============================================================
# ГЛАВНОЕ ОКНО / ВЕРХНЯЯ ПАНЕЛЬ (gui.py)
# ============================================================

# --- Верхняя панель (виджет с objectName "topBar") - в стиле статус-бара,
# только зеркально: скруглены НИЖНИЕ углы (верхние примыкают к самому
# краю окна), тень уходит ВНИЗ (панель как будто нависает над рабочей
# областью сверху), градиент - тот же тёмный графит/хром, что и у
# статус-бара, но перевёрнутый: темнее у внешнего края окна (сверху),
# светлее у рабочей области (снизу) - зеркально тому, как устроен
# статус-бар (см. STATUS_BAR_STYLE) ---

# Высота верхней панели - примерно в 1.5 раза больше статус-бара
# (STATUS_BAR_HEIGHT = 44, отсюда 44 * 1.5 = 66; число задано явно, а не
# вычислением от STATUS_BAR_HEIGHT, т.к. та константа объявлена ниже по
# файлу, в разделе статус-бара)
TOP_BAR_HEIGHT = 66

TOP_BAR_STYLE = """
    QWidget#topBar {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #17181a,
            stop:0.45 #303236,
            stop:1 #55585e);
        border-bottom-left-radius: 10px;
        border-bottom-right-radius: 10px;
        border-bottom: 1px solid #6a6d73;
    }
"""

# Логотип-надпись "Лаборатория Рулевого Управления" - современный
# читаемый шрифт (Segoe UI - системный шрифт Windows, гарантированно
# поддерживает кириллицу, выглядит аккуратнее и современнее Arial),
# светлый цвет (панель теперь тёмная, тёмно-синий текст на ней было бы
# не видно) и лёгкий трекинг букв для более стильного вида.
#
# Само имя семейства шрифта сюда НЕ зашито - оно определяется в рантайме
# (см. main.py, load_custom_fonts) и подставляется в gui.py, т.к. имя,
# которое видят сторонние инструменты (например, дизайнер шрифта), не
# всегда совпадает с тем, как его распознаёт сам Qt после загрузки.
TERMINATOR_FONT_FAMILY = None  # заполняется в main.py при старте

TOP_BAR_LOGO_STYLE_BASE = """
    color: #f2f4f6;
    letter-spacing: 1.5px;
"""

# Параметры "нависающей тени" верхней панели (QGraphicsDropShadowEffect) -
# зеркально статус-бару: тень уходит ВНИЗ (положительный Y), подчёркивая,
# что панель нависает над рабочей областью сверху
TOP_BAR_SHADOW_BLUR_RADIUS = 20
TOP_BAR_SHADOW_COLOR = (0, 0, 0, 170)   # RGBA
TOP_BAR_SHADOW_OFFSET = (0, 3)

# Цвет заголовка окна (системная строка со значком/свёрнуть/развернуть/
# закрыть) - тон из той же графитовой палитры, что и верхняя панель/
# статус-бар (обновлено вместе с переходом верхней панели на тёмную
# тему - раньше здесь был более светлый оттенок первой версии панели).
# Красится через нативный Windows API (см. main.py,
# apply_title_bar_color) - работает ТОЛЬКО на Windows 11 (build 22000 и
# новее); на Windows 10 и других ОС просто тихо не применяется, окно
# остаётся стандартным.
TITLE_BAR_COLOR_RGB = (0x30, 0x32, 0x36)

# Цвет тонкой рамки по периметру всего окна программы (не заголовок, а
# именно боковые/нижняя грани окна) - тот же тон, что и перекрашенная
# рамка правой панели (RIGHT_PANEL_SCROLL_STYLE), для единообразия.
# Тоже через нативный DWM API - те же ограничения (Windows 11+).
WINDOW_BORDER_COLOR_RGB = (0x4a, 0x4d, 0x52)


# ============================================================
# СТАТУС-БАР (widgets/status_bar.py)
# ============================================================

# Отступ слева у надписи "Выбран образец: ..." - чтобы текст не был
# приклеен вплотную к левому краю окна
STATUS_BAR_SELECTED_LABEL_STYLE = "padding-left: 10px; font-size: 11pt;"

# Отступ справа у правого блока (счётчик + дата обновления) - в px,
# задаётся через contentsMargins самого layout-контейнера (см.
# status_bar.py), а не через QSS padding: обычный QWidget без фона не
# всегда корректно применяет padding из стилевого листа. Отступ - на
# КОНТЕЙНЕР целиком, а не на отдельную строку, иначе верхняя и нижняя
# строки заканчивались бы не вровень друг с другом
STATUS_BAR_RIGHT_MARGIN = 10

# --- "HUD"-оформление статус-бара (тёмная панель-графит, парящая над
# содержимым окна) ---
#
# Общий вид: тёмный металлический градиент (графит/хром), скруглённые
# верхние углы (нижние остаются острыми - они и так примыкают к самому
# краю окна, скругление там просто не будет видно), светлый моноширинный
# шрифт с поддержкой кириллицы (Consolas - в стиле показаний терминала/
# HUD, что-то среднее между Fallout Pip-Boy и терминатор-стилем), и
# "тень", создающая ощущение отдельной панели, нависающей над окном
# (см. STATUS_BAR_SHADOW_* ниже - применяется программно через
# QGraphicsDropShadowEffect, т.к. box-shadow в QSS не поддерживается).

# Высота статус-бара - панель второстепенная, поэтому не слишком высокая,
# но всё же с запасом под 2 строки текста (было ~24px по умолчанию)
STATUS_BAR_HEIGHT = 44

# Основной QSS статус-бара: градиент графит/тёмный хром сверху вниз,
# скруглённые верхние углы, светлый моноширинный текст
STATUS_BAR_STYLE = """
    QStatusBar {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #55585e,
            stop:0.45 #303236,
            stop:1 #17181a);
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
        border-top: 1px solid #6a6d73;
    }
    QStatusBar QLabel {
        color: #e8eaed;
        font-family: "Consolas", "Courier New", monospace;
        font-size: 9pt;
        letter-spacing: 1px;
        background: transparent;
    }
    QStatusBar::item {
        border: none;
    }
"""

# Цвет светящейся полосы-акцента по центру статус-бара (см. класс
# _GlowLine в status_bar.py) - холодное голубое свечение в духе HUD
# терминатора, хорошо смотрится на графитовом фоне
STATUS_BAR_GLOW_COLOR = (79, 209, 255)   # RGB
STATUS_BAR_GLOW_MAX_ALPHA = 190          # яркость свечения в центре полосы
STATUS_BAR_GLOW_HEIGHT = 2               # толщина полосы, px

# Параметры "парящей тени" статус-бара (QGraphicsDropShadowEffect) -
# тень уходит немного ВВЕРХ (отрицательный Y), подчёркивая, что панель
# как будто нависает над содержимым окна, а не просто прижата ко дну
STATUS_BAR_SHADOW_BLUR_RADIUS = 20
STATUS_BAR_SHADOW_COLOR = (0, 0, 0, 170)   # RGBA
STATUS_BAR_SHADOW_OFFSET = (0, -3)


# ============================================================
# ИКОНКИ ВЕРХНЕЙ ПАНЕЛИ (SVG, перекрашиваются в рантайме - см. icon_utils.py)
# ============================================================

# Кнопки "Статистика"/"Настройки"/"Печать" - серые по умолчанию, при
# наведении заливаются фирменным бирюзовым
TOP_BAR_ICON_COLOR_NORMAL = "#a8acb2"
TOP_BAR_ICON_COLOR_HOVER = "#4fd1ff"

# Кнопка смены темы - две иконки на одной кнопке (день/ночь). Активная -
# бирюзовая, неактивная - тёмно-серая; при наведении именно на
# неактивную иконку она слегка подсвечивается (промежуточный, более
# светлый серый - не полный бирюзовый, чтобы не путать с активной)
THEME_ICON_ACTIVE_COLOR = "#4fd1ff"
THEME_ICON_INACTIVE_COLOR = "#5a5d63"
THEME_ICON_INACTIVE_HOVER_COLOR = "#8a8e94"

# Иконка загрузки протокола (песочные часы) - чёрная, без перекраски,
# как на исходной картинке
LOADING_ICON_COLOR = "#1c1e21"