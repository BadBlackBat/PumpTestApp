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
"""

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
def _brushed_metal_gradient(light, dark, bands=16):
    stops = []
    for i in range(bands):
        pos = i / (bands - 1)
        color = light if i % 2 == 0 else dark
        stops.append(f"stop:{pos:.3f} {color}")
    return "qlineargradient(x1:0, y1:0, x2:1, y2:0, " + ", ".join(stops) + ")"

_ALUMINUM_NORMAL = _brushed_metal_gradient("#c9cdd2", "#a6aab0")
_ALUMINUM_HOVER = _brushed_metal_gradient("#aeb2b8", "#8b8f95")

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

# Основная таблица списка насосов: центрирование текста в ячейках и
# жирные заголовки колонок.
#
# ВАЖНО: сюда сознательно НЕ добавляется правило "QTableWidget::item:selected"
# - выделение строки реализовано отдельно, через два полупрозрачных
# оверлея (наведение/выделение) поверх таблицы + кастомный делегат
# _NoSelectionPaintDelegate (см. left_panel.py), который отключает
# штатную заливку выделения Qt. Если добавить сюда фон для :selected -
# он будет конфликтовать с этой логикой и перекрывать анимированный цвет.
LEFT_PANEL_TABLE_STYLE = """
    QTableWidget::item {
        text-align: center;
    }
    QHeaderView::section {
        font-weight: bold;
    }
"""


# ============================================================
# ПРАВАЯ ПАНЕЛЬ (widgets/right_panel.py)
# Просмотр протокола проверки, графики, сравнение дублей
# ============================================================

# Рамка вокруг всей правой панели (QScrollArea рисует её сама по себе, по
# умолчанию - блёклым системным серым; перекрашиваем в тон общей
# графитовой палитры, чтобы не выбивалась на фоне остального оформления)
RIGHT_PANEL_SCROLL_STYLE = "QScrollArea { border: 1px solid #4a4d52; border-radius: 4px; }"

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

# Текст-подсказка ("Выберите насос для просмотра протокола") поверх
# киберпанк-градиента выше - светящийся голубой неон, тот же оттенок,
# что и акцентная подсветка статус-бара/верхней панели (единая палитра)
RIGHT_PANEL_LOGO_TEXT_STYLE = """
    color: #7de8ff;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 14pt;
    letter-spacing: 1px;
"""

# Индикатор "Загрузка протокола..." - показывается на время построения
# таблиц и графиков matplotlib (эта операция синхронная и заметна по
# времени), чтобы пользователю было очевидно, что идёт загрузка, а не
# зависание программы
RIGHT_PANEL_LOADING_STYLE = (
    "background-color: #f0f0f0; border: 1px solid #ccc; padding: 20px; color: #555;"
)

# Легенда с пояснением цветовой подсветки несоответствий техническим
# требованиям (текстовая строка под таблицами протокола)
RIGHT_PANEL_LEGEND_STYLE = "background-color: #f0f0f0; padding: 5px;"

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
RIGHT_PANEL_STATS_TEXT_STYLE = "background-color: white; padding: 10px;"

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
    QWidget#topBar QPushButton {
        background-color: transparent;
        border: none;
        font-size: 14pt;
        padding: 2px 6px;
        color: #e8eaed;
    }
    QWidget#topBar QPushButton:hover {
        background-color: rgba(255, 255, 255, 40);
        border-radius: 4px;
    }
"""

# Логотип-надпись "Лаборатория Рулевого Управления" - современный
# читаемый шрифт (Segoe UI - системный шрифт Windows, гарантированно
# поддерживает кириллицу, выглядит аккуратнее и современнее Arial),
# светлый цвет (панель теперь тёмная, тёмно-синий текст на ней было бы
# не видно) и лёгкий трекинг букв для более стильного вида
TOP_BAR_LOGO_STYLE = """
    color: #f2f4f6;
    font-family: "Terminator Real NFI RUS", "Segoe UI", Arial, sans-serif;
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