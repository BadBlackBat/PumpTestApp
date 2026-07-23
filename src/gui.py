import sys
import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QMessageBox, QInputDialog, QLineEdit,
    QDialog, QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QApplication, QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QRectF, QEvent, QSize, pyqtSignal

from PyQt5.QtGui import QFont, QPainter, QColor, QIcon, QPixmap
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog, QPrintPreviewWidget

from .widgets.left_panel import LeftPanel
from .widgets.right_panel import RightPanel
from .widgets.status_bar import StatusBar, _GlowLine
from .widgets.dialogs import PasswordDialog, AddModificationDialog, AddOrderDialog, SettingsDialog, AddPumpDialog, _clamp_to_screen, GlowMessageDialog, PrintChoiceDialog
from . import database as db
from . import excel_importer as importer
from . import utils
from . import styles
from . import icon_utils

from datetime import datetime
from .widgets.dialogs import EditPumpDialog
import json

# Папка с изображениями (значок окна, логотип) - лежит рядом с исходниками,
# в src/resources/
RESOURCES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')
ICON_PATH = os.path.join(RESOURCES_DIR, 'icon.ico')
ICONS_DIR = os.path.join(RESOURCES_DIR, 'icons')


class _IconButton(QPushButton):
    """Кнопка-иконка без рамки и фона - просто картинка. По умолчанию
    серая, при наведении перекрашивается в фирменный бирюзовый (см.
    icon_utils.py - перекраска происходит рендером в pixmap, а не через
    QSS, т.к. QSS не умеет менять цвет содержимого произвольной SVG)."""
    def __init__(self, svg_path, size=22, tooltip="", parent=None):
        super().__init__(parent)
        self._size = size
        self._normal_icon = icon_utils.tinted_icon(svg_path, styles.TOP_BAR_ICON_COLOR_NORMAL, size)
        self._hover_icon = icon_utils.tinted_icon(svg_path, styles.TOP_BAR_ICON_COLOR_HOVER, size)
        self.setIcon(self._normal_icon)
        self.setIconSize(QSize(size, size))
        self.setFlat(True)
        self.setStyleSheet(
            "QPushButton { border: none; background: transparent; padding: 4px; }"
        )
        self.setCursor(Qt.PointingHandCursor)
        if tooltip:
            self.setToolTip(tooltip)
        self._active = False  # принудительно подсвечена (не зависит от наведения мыши)

    def set_active(self, active):
        """Держит иконку подсвеченной (как при наведении), пока active=True,
        независимо от того, где сейчас курсор мыши - используется, чтобы
        показать, что связанное с кнопкой окно/режим сейчас открыто."""
        self._active = active
        self.setIcon(self._hover_icon if active else self._normal_icon)

    def enterEvent(self, event):
        self.setIcon(self._hover_icon)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self._active:
            self.setIcon(self._normal_icon)
        super().leaveEvent(event)


class _ThemeToggleButton(QWidget):
    """Кнопка смены темы - две иконки (день/ночь) на одном виджете.
    Активная (текущая тема) - бирюзовая, вторая - тёмно-серая ("неактивная").
    Клик меняет их местами. Наведение на НЕАКТИВНУЮ иконку слегка её
    подсвечивает (промежуточный серый, не полный бирюзовый - чтобы не
    путать с активной)."""
    theme_changed = pyqtSignal(bool)  # True - дневная тема, False - ночная

    def __init__(self, day_svg, night_svg, size=22, inactive_size=16, night_inactive_size=13, tooltip="", parent=None):
        super().__init__(parent)
        self._day_svg = day_svg
        self._night_svg = night_svg
        self._size = size
        self._inactive_size = inactive_size
        self._night_inactive_size = night_inactive_size
        self._is_day = True

        # Разные SVG могут иметь разный "запас" пустого поля внутри своего
        # холста - при одинаковом заявленном размере рендера видимая
        # картинка выходит разного размера (луна визуально крупнее
        # солнца). Меряем реальное заполнение каждой иконки один раз и
        # считаем коэффициент, чтобы это выровнять.
        day_fill = icon_utils.content_fill_ratio(day_svg)
        night_fill = icon_utils.content_fill_ratio(night_svg)
        biggest_fill = max(day_fill, night_fill)
        self._day_factor = biggest_fill / day_fill
        self._night_factor = biggest_fill / night_fill

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        self.day_label = QLabel()
        self.night_label = QLabel()
        self.day_label.setFixedSize(size, size)
        self.night_label.setFixedSize(size, size)
        self.day_label.setAlignment(Qt.AlignCenter)
        self.night_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.day_label)
        layout.addWidget(self.night_label)

        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        if tooltip:
            self.setToolTip(tooltip)
        self._refresh_icons()

    def _refresh_icons(self, day_hover=False, night_hover=False):
        active = styles.THEME_ICON_ACTIVE_COLOR
        inactive = styles.THEME_ICON_INACTIVE_COLOR
        inactive_hover = styles.THEME_ICON_INACTIVE_HOVER_COLOR

        day_color = active if self._is_day else (inactive_hover if day_hover else inactive)
        night_color = (inactive_hover if night_hover else inactive) if self._is_day else active

        # Активная иконка (текущая тема) рендерится крупнее, неактивная -
        # заметно мельче; лейблы остаются фиксированного размера (под
        # активную), меньшая картинка центрируется внутри той же коробки.
        # Коэффициенты _day_factor/_night_factor компенсируют разницу в
        # "заполненности" самих исходных SVG.
        day_size = int((self._size if self._is_day else self._inactive_size) * self._day_factor)
        night_size = int((self._size if not self._is_day else self._night_inactive_size) * self._night_factor)

        self.day_label.setPixmap(icon_utils.tinted_pixmap(self._day_svg, day_color, day_size))
        self.night_label.setPixmap(icon_utils.tinted_pixmap(self._night_svg, night_color, night_size))

    def mousePressEvent(self, event):
        self._is_day = not self._is_day
        self._refresh_icons()
        self.theme_changed.emit(self._is_day)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Определяем, над какой из двух иконок сейчас курсор, и слегка
        # подсвечиваем её, только если она НЕ активная в данный момент
        over_day = event.x() < self.day_label.width() + 3
        day_hover = over_day and not self._is_day
        night_hover = (not over_day) and self._is_day
        self._refresh_icons(day_hover, night_hover)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._refresh_icons()
        super().leaveEvent(event)


class _TopBar(QWidget):
    """Верхняя панель - оформлена в стиле статус-бара, только зеркально:
    скруглены нижние углы, тень уходит вниз, светящаяся полоса-акцент
    лежит вдоль НИЖНЕГО края (у статус-бара - вдоль верхнего)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._glow_line = _GlowLine(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        h = styles.STATUS_BAR_GLOW_HEIGHT
        self._glow_line.setGeometry(0, self.height() - h, self.width(), h)
        self._glow_line.raise_()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("База данных проверок насосов ГУР")
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))
        self._setup_window_geometry()

        self.current_selected_pump = None
        self.current_filters = None
        
        central = QWidget()
        self.setCentralWidget(central)
        outer_layout = QVBoxLayout(central)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Внутренний контейнер с обычными отступами - сюда идёт всё,
        # КРОМЕ верхней панели (сплиттер, статус-бар и т.д.). Сама верхняя
        # панель кладётся прямо во внешний layout без отступов, чтобы
        # доставать до самых краёв окна - точно как у статус-бара, которым
        # управляет сам QMainWindow
        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Верхняя панель с логотипом и кнопками - оформлена в стиле
        # статус-бара (тот же тёмный графит), только зеркально
        top_bar_widget = _TopBar()
        top_bar_widget.setObjectName("topBar")
        # Обычный QWidget (в отличие от QStatusBar/QPushButton/QFrame) не
        # рисует фон/рамку из QSS без этого атрибута - без него весь
        # градиент из TOP_BAR_STYLE молча игнорировался бы при отрисовке
        top_bar_widget.setAttribute(Qt.WA_StyledBackground, True)
        top_bar_widget.setFixedHeight(styles.TOP_BAR_HEIGHT)
        top_bar_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        top_bar_widget.setStyleSheet(styles.TOP_BAR_STYLE)

        top_layout = QHBoxLayout(top_bar_widget)
        top_layout.setContentsMargins(14, 6, 14, 6)
        top_layout.setSpacing(10)

        # Добавляем растяжение слева, чтобы центрировать логотип
        top_layout.addStretch()

        # Картинка логотипа - перед текстовой надписью
        logo_image_label = QLabel()
        logo_path = os.path.join(RESOURCES_DIR, 'logo.png')
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaledToHeight(48, Qt.SmoothTransformation)
                logo_image_label.setPixmap(pixmap)
        top_layout.addWidget(logo_image_label)

        # Логотип (текст) - современный светлый шрифт, крупнее прежнего.
        # Имя шрифта берём из того, что реально определил Qt при загрузке
        # (см. main.py, load_custom_fonts) - если по какой-то причине
        # кастомный шрифт не загрузился, тихо остаёмся на Segoe UI
        logo_label = QLabel("Лаборатория Рулевого Управления")
        logo_label.setAlignment(Qt.AlignCenter)
        font_family = getattr(styles, 'TERMINATOR_FONT_FAMILY', None) or "Segoe UI"
        logo_label.setFont(QFont(font_family, 16, QFont.Bold))
        logo_label.setStyleSheet(
            styles.TOP_BAR_LOGO_STYLE_BASE
            + f'font-family: "{font_family}", "Segoe UI", Arial, sans-serif;'
        )
        top_layout.addWidget(logo_label)

        # Растяжение между логотипом и кнопками
        top_layout.addStretch()

        # Кнопки
        self.btn_hide_protocol = _IconButton(os.path.join(ICONS_DIR, 'hide_protocol.svg'), tooltip="Скрыть протокол")
        self.btn_hide_protocol.clicked.connect(self.on_hide_protocol_clicked)
        self.btn_hide_protocol.hide()
        top_layout.addWidget(self.btn_hide_protocol)

        self.btn_export_pdf = _IconButton(os.path.join(ICONS_DIR, 'export_pdf.svg'), tooltip="Экспорт в PDF")
        self.btn_export_pdf.clicked.connect(self.on_export_pdf_clicked)
        self.btn_export_pdf.hide()
        top_layout.addWidget(self.btn_export_pdf)

        self.btn_fit_view = _IconButton(os.path.join(ICONS_DIR, 'fit_view.svg'), tooltip="Уместить протокол по высоте")
        self.btn_fit_view.clicked.connect(self.on_fit_view_clicked)
        self.btn_fit_view.hide()
        top_layout.addWidget(self.btn_fit_view)

        self.btn_stats_minus = _IconButton(os.path.join(ICONS_DIR, 'zoom_out.svg'), tooltip="Уменьшить масштаб статистики")
        self.btn_stats_minus.clicked.connect(lambda: self.right_panel._zoom_stats(1 / 1.15))
        self.btn_stats_minus.hide()
        top_layout.addWidget(self.btn_stats_minus)

        self.btn_stats_plus = _IconButton(os.path.join(ICONS_DIR, 'zoom_in.svg'), tooltip="Увеличить масштаб статистики")
        self.btn_stats_plus.clicked.connect(lambda: self.right_panel._zoom_stats(1.15))
        self.btn_stats_plus.hide()
        top_layout.addWidget(self.btn_stats_plus)

        top_layout.addSpacing(8)  # небольшой отступ перед статистикой

        self.btn_stats = _IconButton(os.path.join(ICONS_DIR, 'statistics.svg'), tooltip="Статистика")
        self.btn_stats.clicked.connect(self.toggle_statistics)
        top_layout.addWidget(self.btn_stats)

        btn_theme = _ThemeToggleButton(
            os.path.join(ICONS_DIR, 'theme-day.svg'),
            os.path.join(ICONS_DIR, 'theme-night.svg'),
            tooltip="Смена темы"
        )
        self.btn_settings = _IconButton(os.path.join(ICONS_DIR, 'settings_2.svg'), tooltip="Настройки")
        btn_print = _IconButton(os.path.join(ICONS_DIR, 'print.svg'), tooltip="Печать")

        # Подключаем
        btn_theme.theme_changed.connect(
            lambda is_day: QMessageBox.information(self, "Тема", "Функция будет реализована позже")
        )
        self.btn_settings.clicked.connect(self.open_settings)
        btn_print.clicked.connect(self.on_print_requested)

        top_layout.addWidget(btn_theme)
        top_layout.addWidget(self.btn_settings)
        top_layout.addWidget(btn_print)

        # Тень, приподнимающая панель над рабочей областью - зеркально
        # статус-бару, уходит ВНИЗ (панель как будто нависает над окном)
        shadow = QGraphicsDropShadowEffect(top_bar_widget)
        shadow.setBlurRadius(styles.TOP_BAR_SHADOW_BLUR_RADIUS)
        shadow.setColor(QColor(*styles.TOP_BAR_SHADOW_COLOR))
        shadow.setOffset(*styles.TOP_BAR_SHADOW_OFFSET)
        top_bar_widget.setGraphicsEffect(shadow)

        outer_layout.addWidget(top_bar_widget)
        outer_layout.addWidget(content_widget)
        
        # Сплиттер
        self.splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter)
        self.splitter.setHandleWidth(0)
        
        # Левая панель
        self.left_panel = LeftPanel()
        self.left_panel.pump_selected.connect(self.on_pump_selected)
        self.left_panel.pump_status_selected.connect(self.on_pump_status_selected)
        self.left_panel.group_selected.connect(self.on_group_selected)
        self.left_panel.request_import.connect(self.on_import_requested)
        self.left_panel.request_add.connect(self.on_add_requested)
        self.left_panel.request_delete.connect(self.on_delete_requested)
        self.left_panel.request_edit.connect(self.on_edit_requested)
        self.left_panel.filters_applied.connect(self.update_status)
        self.splitter.addWidget(self.left_panel)
        
        # Правая панель
        self.right_panel = RightPanel()
        self.splitter.addWidget(self.right_panel)
        self.showing_stats = False

        self.right_panel.clear_requested.connect(self.on_clear_requested)
        self.right_panel.mode_changed.connect(self.on_right_panel_mode_changed)
        
        # Пропорции - при первом запуске левая панель сжата до минимальной
        # ширины, нужной блоку фильтров (а не растянута на 40% экрана) -
        # остальное место отдаётся правой панели с протоколом
        self._apply_minimal_left_width()
        
        # Статусная строка
        self.status_bar = StatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status()
        
        # Загрузка данных
        self.left_panel.load_data()
    
    def reset_layout_to_default(self):
        """Возвращает интерфейс к исходному виду, как при запуске:
        компактный (сокращённый) список слева и видимая правая панель,
        со стандартными пропорциями сплиттера 40/60."""
        if not self.left_panel.compact_mode:
            # Снимаем расширенный режим (это само по себе меняет сплиттер,
            # но ниже мы всё равно принудительно зададим правильные пропорции)
            self.left_panel.btn_view_toggle.setChecked(False)
        self.splitter.setSizes([int(self.width() * 0.4), int(self.width() * 0.6)])

    def _setup_window_geometry(self):
        """Считает размер и позицию окна от реальной доступной области
        экрана (а не от жёстко заданных пикселей) - так окно нормально
        открывается и на HD (1366x768), и на Full HD, и на более крупных
        мониторах (1920x1200 и выше), используя доступное пространство,
        но не разрастаясь до неразумных размеров на 4K/ultrawide."""
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None

        # Разумные пределы на случай, если доступную область экрана
        # почему-то не удалось определить, а также "потолок" для очень
        # больших экранов (иначе на 4K окно растянулось бы на весь стол)
        MIN_WIDTH, MIN_HEIGHT = 1024, 700
        MAX_WIDTH, MAX_HEIGHT = 1900, 1200
        FALLBACK_WIDTH, FALLBACK_HEIGHT = 1400, 900

        if available:
            width = max(MIN_WIDTH, min(MAX_WIDTH, int(available.width() * 0.85)))
            height = max(MIN_HEIGHT, min(MAX_HEIGHT, int(available.height() * 0.85)))
            x = available.x() + (available.width() - width) // 2
            y = available.y() + (available.height() - height) // 2
            self.setGeometry(x, y, width, height)
        else:
            self.setGeometry(100, 100, FALLBACK_WIDTH, FALLBACK_HEIGHT)

    def _apply_minimal_left_width(self):
        """Сжимает левую панель до минимальной ширины, нужной блоку
        фильтров - вместо фиксированных пропорций 40/60. Используется и
        при запуске, и при разворачивании/восстановлении окна, и при
        возврате из расширенного режима списка в компактный.

        Дополнительно фиксируем эту ширину как МАКСИМАЛЬНУЮ для левой
        панели - пользователь не может вручную растянуть её шире через
        перетаскивание сплиттера (сузить - по-прежнему можно)."""
        # Если панель фильтров только что была пересобрана (переключение
        # компактный/расширенный вид), даём Qt закончить пересчёт layout -
        # иначе sizeHint() ниже может вернуть ещё не обновлённое значение
        QApplication.processEvents()
        left_width = self.left_panel.sizeHint().width()
        self.left_panel.setMaximumWidth(left_width)
        self.splitter.setSizes([left_width, max(200, self.width() - left_width)])

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            # Разворот/восстановление окна - пересчитываем сжатие левой
            # панели ПОСЛЕ того, как окно реально примет новый размер
            # (сразу внутри changeEvent размеры ещё старые)
            QTimer.singleShot(0, self._apply_minimal_left_width)

    def toggle_statistics(self):
        if self.showing_stats:
            self.right_panel.clear_protocol()
            self.showing_stats = False
            self.left_panel.table.clearSelection()
            self.current_selected_pump = None
            self.reset_layout_to_default()
            self.update_status()
        else:
            stats_data = db.get_statistics()
            self.right_panel.display_statistics(stats_data)
            self.showing_stats = True
            self.current_selected_pump = None
            self.reset_layout_to_default()
            self.update_status()

    def on_pump_selected(self, pump_data):
        if not self.left_panel.compact_mode:
            self.left_panel.btn_view_toggle.setChecked(False)
        if self.showing_stats:
            self.showing_stats = False
        self.right_panel.display_protocol(pump_data)
        self.current_selected_pump = pump_data['pump_number']
        self.update_status()  # без параметров

    def on_pump_status_selected(self, pump_data):
        """Выбор строки в расширенном режиме - обновляем только статус-бар,
        не открывая протокол и не переключая вид обратно в компактный."""
        self.current_selected_pump = pump_data['pump_number']
        self.update_status()

    def on_group_selected(self, items):
        """Клик по заголовку группы дублей - показываем сравнение протоколов."""
        if not self.left_panel.compact_mode:
            self.left_panel.btn_view_toggle.setChecked(False)
        if self.showing_stats:
            self.showing_stats = False
        # Подгружаем полные данные (с результатами испытаний) по каждому насосу группы
        full_items = [db.get_pump_by_id(it['id']) for it in items]
        full_items = [it for it in full_items if it]
        self.right_panel.display_comparison(full_items)
        self.current_selected_pump = f"{items[0]['pump_number']} (сравнение {len(items)} шт.)"
        self.update_status()

    def on_print_requested(self):
        dialog = PrintChoiceDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        choice = dialog.choice

        if choice == "protocol":
            if self.right_panel.current_data is None and self.right_panel.current_comparison_items is None:
                GlowMessageDialog.show_error(self, "Печать", "Сначала откройте протокол для просмотра.")
                return
            self.right_panel.print_protocol()
        elif choice == "list_compact":
            self.print_pump_list(compact=True)
        elif choice == "list_expanded":
            self.print_pump_list(compact=False)
        elif choice == "stats":
            self.right_panel.print_statistics()

    def print_pump_list(self, compact=True):
        """Открывает предпросмотр печати списка насосов - сокращённого или
        расширенного (выбирается явно в диалоге печати), с учётом текущих
        применённых фильтров, текущей сортировки колонки и, если включён
        режим "Дубли", группировки по образцам (как на экране).

        Таблица рисуется вручную через QPainter (а не рендером живого
        QTableWidget) - так гарантированно вписывается в размер листа:
        ширина колонок считается напрямую от ширины страницы."""
        filters = dict(self.left_panel.current_filters or {})

        # ===== Учитываем текущую сортировку колонки в таблице списка =====
        on_screen_columns = (
            ['pump_number', 'test_date', 'verdict', 'test_type', 'is_sealed']
            if self.left_panel.compact_mode else
            ['pump_number', 'test_date', 'mod_name', 'is_sealed', 'test_type', 'order_number', 'verdict']
        )
        field_to_sql = {
            'pump_number': 'p.pump_number', 'test_date': 'p.test_date', 'verdict': 'p.verdict',
            'test_type': 'p.test_type', 'is_sealed': 'p.is_sealed',
            'mod_name': 'mod_name', 'order_number': 'order_number',
        }
        order_by = 'p.test_date DESC'
        header_view = self.left_panel.table.horizontalHeader()
        sort_col = header_view.sortIndicatorSection()
        sort_order = header_view.sortIndicatorOrder()
        if 0 <= sort_col < len(on_screen_columns):
            field = on_screen_columns[sort_col]
            direction = 'ASC' if sort_order == Qt.AscendingOrder else 'DESC'
            order_by = f"{field_to_sql.get(field, 'p.test_date')} {direction}"

        pumps = db.get_all_pumps(filters, order_by=order_by)
        if not pumps:
            QMessageBox.information(self, "Печать", "Нет записей для печати с текущими фильтрами.")
            return

        # Текстовое описание применённых фильтров - выводится над таблицей,
        # чтобы на бумаге было видно, по каким условиям отобран список
        filter_parts = []
        if filters.get('pump_number'):
            filter_parts.append(f"поиск: {filters['pump_number']}")
        if filters.get('verdict'):
            filter_parts.append(f"вердикт: {filters['verdict']}")
        if filters.get('test_type'):
            filter_parts.append(f"тип: {filters['test_type']}")
        if filters.get('is_sealed') is not None:
            filter_parts.append(f"герметичность: {'Да' if filters['is_sealed'] else 'Нет'}")
        if filters.get('order_id'):
            order_str = self.left_panel.order_map.get(filters['order_id'], str(filters['order_id']))
            filter_parts.append(f"заказ: №{order_str}")
        if filters.get('date_from') or filters.get('date_to'):
            filter_parts.append(f"дата: {filters.get('date_from', '')} - {filters.get('date_to', '')}")
        if filters.get('only_duplicates'):
            filter_parts.append("только дубли")
        filters_summary = ("Применены фильтры: " + ", ".join(filter_parts)) if filter_parts else "Фильтры не применены (полный список)"

        if compact:
            headers = ["Номер", "Дата", "Вердикт", "Тип", "Герметичность"]
            col_weights = [1, 1, 1, 1, 1]
        else:
            headers = ["Номер", "Дата", "Модификация", "Герметичность", "Тип", "Заказ", "Вердикт"]
            # Номер/Дата/Заказ - уже, Модификация - шире, остальные - стандартно
            col_weights = [0.7, 0.8, 1.6, 1.1, 0.9, 0.7, 0.9]

        def build_row(p):
            date_str = utils.format_date_display(p.get('test_date'))
            sealed_text = 'Герметичен' if p.get('is_sealed') else 'Негерметичен'
            if compact:
                return [
                    str(p.get('pump_number', '')),
                    date_str,
                    p.get('verdict') or '—',
                    p.get('test_type') or '—',
                    sealed_text,
                ]
            order_num = p.get('order_number')
            order_str = str(order_num).replace('.0', '') if order_num else '—'
            return [
                str(p.get('pump_number', '')),
                date_str,
                p.get('mod_name') or '—',
                sealed_text,
                p.get('test_type') or '—',
                order_str,
                p.get('verdict') or '—',
            ]

        # ===== Группировка по дублям (как на экране), если включена =====
        # Внутри каждой группы порядок сохраняется таким, каким пришёл из
        # БД - то есть с учётом уже применённой выше сортировки колонки.
        print_items = []  # ('header', text) или ('row', values)
        if filters.get('only_duplicates'):
            groups = {}
            for p in pumps:
                key = (p.get('pump_number'), p.get('mod_name'))
                groups.setdefault(key, []).append(p)
            sorted_groups = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0][0] or ''))
            for (pump_number, mod_name), items in sorted_groups:
                print_items.append(('header', f"Образец № {pump_number} — {len(items)} шт."))
                for p in items:
                    print_items.append(('row', build_row(p)))
        else:
            for p in pumps:
                print_items.append(('row', build_row(p)))

        printer = QPrinter()
        printer.setPageSize(QPrinter.A4)
        printer.setOrientation(QPrinter.Portrait if compact else QPrinter.Landscape)
        printer.setPageMargins(8, 8, 8, 8, QPrinter.Millimeter)

        def render_list(printer_obj):
            painter = QPainter()
            painter.begin(printer_obj)
            page_rect = printer_obj.pageRect()

            n_cols = len(headers)
            n_items = len(print_items)

            # Небольшой запас по ширине (таблица уже полной печатной
            # области), чтобы гарантированно не выходить за границы листа
            table_width = page_rect.width() * 0.92
            x0 = page_rect.left() + (page_rect.width() - table_width) / 2

            # Ширина колонок - пропорционально весам (не поровну): номер,
            # дата и заказ уже, модификация шире
            total_weight = sum(col_weights)
            col_widths = [table_width * w / total_weight for w in col_weights]

            # Строка с описанием применённых фильтров над таблицей
            summary_height = page_rect.height() * 0.022
            summary_font = painter.font()
            summary_font.setPointSizeF(max(6, summary_height * 0.5))
            summary_font.setItalic(True)
            painter.setFont(summary_font)
            summary_rect = QRectF(x0, page_rect.top(), table_width, summary_height)
            painter.drawText(summary_rect, Qt.AlignVCenter | Qt.AlignLeft, filters_summary)

            header_height = page_rect.height() * 0.03
            top = page_rect.top() + summary_height
            # Высота строки - под все строки/заголовки групп на одном листе,
            # но не крупнее разумного максимума
            row_height = min((page_rect.height() - summary_height - header_height) / max(n_items, 1),
                            page_rect.height() * 0.03)

            font_size = max(5, min(8, row_height * 0.4))
            font = painter.font()
            font.setPointSizeF(font_size)
            font.setItalic(False)
            font.setBold(True)
            painter.setFont(font)

            pad = min(min(col_widths), row_height) * 0.06

            y = top

            # Заголовки колонок
            x = x0
            for label, cw in zip(headers, col_widths):
                rect = QRectF(x, y, cw, header_height)
                painter.drawRect(rect)
                text_rect = rect.adjusted(pad, pad, -pad, -pad)
                painter.drawText(text_rect, Qt.AlignCenter, label)
                x += cw
            y += header_height

            # Строки и заголовки групп дублей
            for kind, value in print_items:
                if y > page_rect.bottom():
                    break  # без постраничной разбивки - лишнее просто не рисуем
                if kind == 'header':
                    rect = QRectF(x0, y, table_width, row_height)
                    painter.fillRect(rect, QColor(220, 230, 240))
                    painter.drawRect(rect)
                    font.setBold(True)
                    painter.setFont(font)
                    text_rect = rect.adjusted(pad, pad, -pad, -pad)
                    painter.drawText(text_rect, Qt.AlignCenter, value)
                else:
                    font.setBold(False)
                    painter.setFont(font)
                    x = x0
                    for val, cw in zip(value, col_widths):
                        rect = QRectF(x, y, cw, row_height)
                        painter.drawRect(rect)
                        text_rect = rect.adjusted(pad, pad, -pad, -pad)
                        painter.drawText(text_rect, Qt.AlignCenter, str(val))
                        x += cw
                y += row_height

            painter.end()

        preview = QPrintPreviewDialog(printer, self)
        preview.setWindowTitle("Предпросмотр печати - список насосов")
        preview.paintRequested.connect(render_list)
        preview.resize(1000, 850)
        _clamp_to_screen(preview, width_fraction=0.92, height_fraction=0.92)
        preview.exec_()

    def on_import_requested(self):
        """Импорт Excel."""
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл Excel", "", "Excel files (*.xlsx *.xls)"
        )
        if file_path:
            count = importer.import_excel_file(file_path, self)
            if count > 0:
                self.left_panel.refresh()
                self.update_status()
        if self.showing_stats: self.toggle_statistics()

    def open_settings(self):
        self.btn_settings.set_active(True)
        dialog = SettingsDialog(self)
        dialog.exec_()
        self.btn_settings.set_active(False)

    def on_add_requested(self):
        """Ручное добавление записи (модификация, номер, дата, результаты испытаний)."""
        pwd_dialog = PasswordDialog(self, message="Для добавления насоса введите пароль:")
        if pwd_dialog.exec_() != QDialog.Accepted:
            return
        # Пароль уже проверен внутри диалога - если дошли сюда, значит верный

        if not db.get_all_modifications():
            QMessageBox.warning(
                self, "Нет модификаций",
                "В базе нет ни одной модификации. Сначала добавьте модификацию через "
                "⚙️ Настройки → Добавить модификацию."
            )
            return

        dialog = AddPumpDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        data = dialog.get_data()
        # Пароль уже проверен внутри диалога (try_accept) - если дошли
        # сюда, значит он верный

        # ===== Проверка на дубликат (совпадение номера насоса и даты) =====
        existing_id = db.get_pump_by_number_and_date(data['pump_number'], data['test_date'])
        if existing_id:
            display_date = utils.format_date_display(data['test_date'])
            reply1 = QMessageBox.warning(
                self, "Возможный дубликат",
                f"Протокол для насоса №{data['pump_number']} от {display_date} "
                "уже есть в базе.\n\nДобавить его ещё раз?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply1 != QMessageBox.Yes:
                return
            reply2 = QMessageBox.warning(
                self, "Подтверждение",
                f"Вы уверены, что хотите добавить ещё одну запись для насоса "
                f"№{data['pump_number']} от {display_date}?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply2 != QMessageBox.Yes:
                return

        # Заказ (необязательно)
        order_id = None
        if data['order_number']:
            order_id = db.get_order_by_number(data['order_number'])
            if not order_id:
                order_id = db.add_order(data['order_number'])

        # Вердикт и герметичность
        mod = db.get_modification_by_id(data['modification_id'])
        verdict, is_sealed = utils.compute_verdict_and_sealed(
            data['results'], data['seal_results'], mod
        )

        db.add_pump(
            pump_number=data['pump_number'],
            test_date=data['test_date'],
            test_type=data['test_type'],
            modification_id=data['modification_id'],
            order_id=order_id,
            results_json=data['results'],
            seal_results_json=data['seal_results'],
            verdict=verdict,
            is_sealed=is_sealed,
            note=data.get('note', '')
        )

        self.left_panel.refresh()
        self.update_status()
        GlowMessageDialog.show_success(
            self, "Успех",
            f"Насос добавлен.\nВердикт: {verdict}."
        )
    
    def on_delete_requested(self, pump_id):
        """Удаление записи с паролем и подтверждением."""
        # Запрос пароля
        dialog = PasswordDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            if not GlowMessageDialog.confirm(
                self, "Подтверждение удаления",
                "Вы уверены, что хотите удалить эту запись? Это действие необратимо."
            ):
                return
            db.delete_pump(pump_id)
            self.left_panel.refresh()
            self.update_status()
            GlowMessageDialog.show_success(self, "Удаление", "Запись удалена.")
        if self.showing_stats: self.toggle_statistics()

    # def update_status(self, filters=None, selected_pump=None):
    #     all_pumps = db.get_all_pumps()
    #     count = len(all_pumps)
    #     filters_text = ""
    #     if filters:
    #         parts = []
    #         if filters.get('pump_number'):
    #             parts.append(f"поиск: {filters['pump_number']}")
    #         if filters.get('verdict'):
    #             parts.append(f"вердикт: {filters['verdict']}")
    #         if filters.get('test_type'):
    #             parts.append(f"тип: {filters['test_type']}")
    #         if filters.get('is_sealed') is not None:
    #             parts.append(f"герметичность: {'Да' if filters['is_sealed'] else 'Нет'}")
    #         if filters.get('date_from') or filters.get('date_to'):
    #             parts.append(f"дата: {filters.get('date_from', '')} - {filters.get('date_to', '')}")
    #         if filters.get('only_duplicates'):
    #             parts.append("только дубли")
    #         filters_text = ", ".join(parts)
    #     last_update = db.get_last_update_date()
    #     self.status_bar.set_status("Готово", count=count, filters=filters_text, selected_pump=selected_pump, last_update=last_update)

    def update_status(self, filters=None, selected_pump=None):
        # Если фильтры не переданы, берём из левой панели
        if filters is None:
            filters = self.left_panel.current_filters
        # Если выбранный насос не передан, берём сохранённый
        if selected_pump is None:
            selected_pump = self.current_selected_pump

        all_pumps = db.get_all_pumps()
        count = len(all_pumps)
        good_count = sum(1 for p in all_pumps if p.get('verdict') == 'годен')
        filters_text = ""
        if filters:
            parts = []
            if filters.get('pump_number'):
                parts.append(f"поиск: {filters['pump_number']}")
            if filters.get('verdict'):
                parts.append(f"вердикт: {filters['verdict']}")
            if filters.get('test_type'):
                parts.append(f"тип: {filters['test_type']}")
            if filters.get('is_sealed') is not None:
                parts.append(f"герметичность: {'Да' if filters['is_sealed'] else 'Нет'}")
            if filters.get('date_from') or filters.get('date_to'):
                parts.append(f"дата: {filters.get('date_from', '')} - {filters.get('date_to', '')}")
            if filters.get('order_id'):
                order_str = self.left_panel.order_map.get(filters['order_id'], str(filters['order_id']))
                parts.append(f"заказ: №{order_str}")
            if filters.get('only_duplicates'):
                parts.append("только дубли")
            if parts:
                # Если фильтров много - переносим на 2 строки (примерно
                # поровну), иначе при выборе всех фильтров сразу текст не
                # помещается в отведённое место по центру статус-бара
                mid = (len(parts) + 1) // 2
                line1 = ", ".join(parts[:mid])
                line2 = ", ".join(parts[mid:])
                filters_text = line1 + ("\n" + line2 if line2 else "")
        last_update = db.get_last_update_date()
        if last_update and last_update != "нет данных":
            last_update = utils.format_date_display(last_update)
        self.status_bar.set_status("Готово", count=count, good_count=good_count, filters=filters_text,
                                   selected_pump=selected_pump, last_update=last_update)

    def on_edit_requested(self, pump_id):
        pump_data = db.get_pump_by_id(pump_id)
        if not pump_data:
            QMessageBox.warning(self, "Ошибка", "Запись не найдена.")
            return

        if not db.get_all_modifications():
            QMessageBox.warning(
                self, "Нет модификаций",
                "В базе нет ни одной модификации. Сначала добавьте модификацию через "
                "⚙️ Настройки → Добавить модификацию."
            )
            return

        dialog = EditPumpDialog(pump_data, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        data = dialog.get_data()
        # Пароль уже проверен внутри диалога (try_accept) - если дошли
        # сюда, значит он верный

        # ===== Определяем, какие поля реально изменились =====
        changed_fields = []

        old_date = (pump_data.get('test_date') or '').split(' ')[0]
        if old_date != data['test_date']:
            changed_fields.append('test_date')

        if pump_data.get('test_type') != data['test_type']:
            changed_fields.append('test_type')

        if pump_data.get('modification_id') != data['modification_id']:
            changed_fields.append('modification')

        old_order = pump_data.get('order_number')
        old_order_str = str(old_order).replace('.0', '') if old_order else ''
        new_order_str = data['order_number'] or ''
        if old_order_str != new_order_str:
            changed_fields.append('order_number')

        old_results = pump_data.get('results_json') or {}
        for key, new_val in data['results'].items():
            if old_results.get(key) != new_val:
                changed_fields.append(key)

        old_seal = pump_data.get('seal_results_json') or {}
        for key, new_val in data['seal_results'].items():
            if (old_seal.get(key) or '') != (new_val or ''):
                changed_fields.append(key)

        # Заказ: находим/создаём запись заказа
        order_id = None
        if data['order_number']:
            order_id = db.get_order_by_number(data['order_number'])
            if not order_id:
                order_id = db.add_order(data['order_number'])

        # Пересчитываем вердикт и герметичность под (возможно новую) модификацию
        mod = db.get_modification_by_id(data['modification_id'])
        verdict, is_sealed = utils.compute_verdict_and_sealed(
            data['results'], data['seal_results'], mod
        )

        # ===== История правок =====
        # Только дата, без времени - как и везде в приложении
        timestamp = datetime.now().strftime('%d-%m-%Y')
        new_note = data['note']
        old_note = pump_data.get('note', '') or ''
        history_parts = []
        if changed_fields:
            description = utils.describe_changed_fields(changed_fields)
            if description:
                history_parts.append(description)
        if new_note.strip() != old_note.strip():
            if new_note.strip() == "" and old_note.strip() != "":
                history_parts.append("примечание удалено")
            elif new_note.strip() != "" and old_note.strip() == "":
                history_parts.append("примечание добавлено")
            else:
                history_parts.append("примечание изменено")

        edit_date_str = datetime.now().strftime('%Y-%m-%d')
        if history_parts:
            edit_entry = f"{timestamp}: " + "; ".join(history_parts)
            old_history = pump_data.get('edit_history', '') or ''
            new_history = edit_entry + "\n" + old_history if old_history else edit_entry
        else:
            new_history = pump_data.get('edit_history', '') or ''

        # Сохраняем только если что-то реально поменялось (поля или примечание)
        if changed_fields or new_note.strip() != old_note.strip():
            db.update_pump(
                pump_id,
                test_date=data['test_date'],
                test_type=data['test_type'],
                modification_id=data['modification_id'],
                order_id=order_id,
                results_json=data['results'],
                seal_results_json=data['seal_results'],
                verdict=verdict,
                is_sealed=is_sealed,
                note=new_note,
                edit_history=new_history,
                edit_date=edit_date_str,
                changed_fields_json=json.dumps(changed_fields),
            )
            self.left_panel.refresh()
            current_selected = self.right_panel.current_data
            updated = db.get_pump_by_id(pump_id)
            if current_selected and current_selected['id'] == pump_id:
                self.right_panel.display_protocol(updated)
            GlowMessageDialog.show_success(self, "Успех", "Протокол обновлён.")
        else:
            QMessageBox.information(self, "Информация", "Изменений не обнаружено.")

            GlowMessageDialog.show_success(self, "Успех", "Примечание обновлено.")
    
    def on_fit_view_clicked(self):
        self.right_panel.toggle_fit_view()

    def on_hide_protocol_clicked(self):
        self.right_panel.clear_protocol()

    def on_export_pdf_clicked(self):
        self.right_panel.export_to_pdf()

    def on_right_panel_mode_changed(self, mode):
        """Показывает нужные кнопки верхней панели в зависимости от того,
        что сейчас отображается в правой панели - протокол/сравнение
        показывают кнопки "скрыть"/"экспорт в PDF"/"уместить по высоте",
        статистика - кнопки масштаба, в остальных случаях (пусто) -
        ничего из этого."""
        self.btn_hide_protocol.setVisible(mode in ('protocol', 'comparison'))
        self.btn_export_pdf.setVisible(mode in ('protocol', 'comparison', 'stats'))
        self.btn_fit_view.setVisible(mode in ('protocol', 'comparison'))
        self.btn_stats_minus.setVisible(mode == 'stats')
        self.btn_stats_plus.setVisible(mode == 'stats')
        self.btn_stats.set_active(mode == 'stats')

    def on_clear_requested(self):
        # 1. Вернуть раскладку к исходному виду (компактный список + пропорции 40/60)
        self.reset_layout_to_default()
        
        # 2. Сбросить фильтры (вызовет apply_filters и обновит таблицу)
        self.left_panel.reset_filters()
        
        # 3. Снять выделение в таблице
        self.left_panel.table.clearSelection()
        
        # 4. Сбросить выбранный насос в статус-баре
        self.current_selected_pump = None
        
        # 5. Обновить статус-бар (без выбранного насоса, фильтры уже сброшены)
        self.update_status(selected_pump=None)
        
        # 6. Если была статистика, закрыть её
        self.showing_stats = False