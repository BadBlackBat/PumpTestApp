import os

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QScrollArea, QSizePolicy,
    QFileDialog, QMessageBox, QFrame, QApplication, QHeaderView,
    QScrollBar, QStyle, QStyleOptionSlider
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtProperty, QSize, QTimer, QPropertyAnimation, QRectF
from PyQt5.QtGui import QColor, QFont, QPainter, QPixmap, QTransform, QLinearGradient, QBrush
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog, QPrintPreviewWidget

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator
import numpy as np

from .. import database as db
from .. import utils
from ..utils import is_value_in_range
from ..utils import format_order_number
from .dialogs import _clamp_to_screen
from .left_panel import _GlowFrame
from .. import styles
from .. import icon_utils

ICONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resources', 'icons'
)
from datetime import datetime


class _CtrlWheelZoomWidget(QWidget):
    """Обычный QWidget, который перехватывает Ctrl+колесо мыши и вызывает
    переданный обработчик - используется для масштабирования обзорного
    снимка протокола и текста статистики колёсиком мыши (без Ctrl колесо
    работает как обычно - прокрутка, если она вообще где-то есть)."""
    def __init__(self, on_ctrl_wheel, parent=None):
        super().__init__(parent)
        self._on_ctrl_wheel = on_ctrl_wheel
        # Обычный QWidget (в отличие от QFrame) не рисует фон, заданный
        # через QSS, без этого атрибута - без него весь наш тёмно-синий
        # градиент просто не отрисовывался
        self.setAttribute(Qt.WA_StyledBackground, True)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            self._on_ctrl_wheel(event)
            event.accept()
        else:
            super().wheelEvent(event)


class _GlowScrollBar(QScrollBar):
    """Полоса прокрутки в фирменном стиле - собственная отрисовка (QSS не
    умеет ни плавную анимацию ширины, ни "бегущую" динамическую подсветку).

    Желоб не рисуется вовсе (полностью прозрачный) - виден только сам
    бегунок. В состоянии покоя - тонкая бирюзовая линия. При наведении
    мыши плавно расширяется СИММЕТРИЧНО в обе стороны от центра (не
    только в одну) до полного вида со скруглёнными краями (35% от
    ширины) и настоящим свечением (ярче по центру бегунка, гаснет к его
    краям - тот же приём, что и у _GlowFrame/_GlowLine). Такое же
    временное раскрытие происходит и просто при прокрутке колесом мыши,
    даже если курсор не касается самой полосы - и плавно гаснет обратно
    через небольшую паузу после того, как прокрутка прекратилась."""

    THIN_WIDTH = 3
    FULL_WIDTH = 8
    MARGIN_TOP = 4
    MARGIN_BOTTOM = 4
    MARGIN_RIGHT = 5          # отступ справа - ощущение "парящей" полосы
    SCROLL_ACTIVITY_LEVEL = 0.65  # насколько раскрывается при прокрутке колесом (без наведения)
    SCROLL_ACTIVITY_HOLD_MS = 700  # сколько ждать после остановки прокрутки перед затуханием

    def __init__(self, parent=None):
        super().__init__(Qt.Vertical, parent)
        self._hover_progress = 0.0  # 0 - состояние покоя, 1 - полностью раскрыта
        self._is_hovering = False
        self.setStyleSheet("QScrollBar { background: transparent; border: none; }")
        # Без этого атрибута Qt рисует собственный фон виджета (из
        # палитры/стиля) ДО нашего paintEvent
        self.setAttribute(Qt.WA_NoSystemBackground, True)

        self._anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._anim.setDuration(160)

        self._activity_timer = QTimer(self)
        self._activity_timer.setSingleShot(True)
        self._activity_timer.timeout.connect(self._on_activity_timeout)

        self.valueChanged.connect(self._on_value_changed)

    def getHoverProgress(self):
        return self._hover_progress

    def setHoverProgress(self, value):
        self._hover_progress = value
        self.update()

    hoverProgress = pyqtProperty(float, getHoverProgress, setHoverProgress)

    def enterEvent(self, event):
        self._is_hovering = True
        self._animate_to(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovering = False
        if not self._activity_timer.isActive():
            self._animate_to(0.0)
        super().leaveEvent(event)

    def _on_value_changed(self, _value):
        """Прокрутка колесом мыши - временно раскрывает полосу, даже если
        курсор её не касается, и держит раскрытой, пока прокрутка активна."""
        if not self._is_hovering:
            self._animate_to(self.SCROLL_ACTIVITY_LEVEL)
        self._activity_timer.start(self.SCROLL_ACTIVITY_HOLD_MS)

    def _on_activity_timeout(self):
        if not self._is_hovering:
            self._animate_to(0.0)

    def _animate_to(self, target):
        self._anim.stop()
        self._anim.setStartValue(self._hover_progress)
        self._anim.setEndValue(target)
        self._anim.start()

    def sizeHint(self):
        base = super().sizeHint()
        return QSize(self.FULL_WIDTH + self.MARGIN_RIGHT, base.height())

    def _handle_rect(self):
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        return self.style().subControlRect(QStyle.CC_ScrollBar, opt, QStyle.SC_ScrollBarSlider, self)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        current_width = self.THIN_WIDTH + (self.FULL_WIDTH - self.THIN_WIDTH) * self._hover_progress
        radius = current_width * 0.35

        # Центр полосы фиксирован (по максимальной ширине) - при
        # раскрытии она растёт СИММЕТРИЧНО в обе стороны от этого центра,
        # а не только влево
        center_x = self.width() - self.MARGIN_RIGHT - self.FULL_WIDTH / 2
        track_x = center_x - current_width / 2

        handle_qrect = self._handle_rect()
        handle_top = handle_qrect.top()
        handle_h = max(1, handle_qrect.height())
        handle_rect = QRectF(track_x, handle_top, current_width, handle_h)

        # Лёгкая тень - слегка смещённый затемнённый дубликат формы прямо
        # под самой полосой (для контраста на светлом фоне)
        shadow_rect = handle_rect.translated(0.6, 1.2)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 60))
        painter.drawRoundedRect(shadow_rect, radius, radius)

        r, g, b = 79, 209, 255
        if self._hover_progress < 0.05:
            # Состояние покоя - просто тонкая бирюзовая линия, без свечения
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(r, g, b, 220))
            painter.drawRoundedRect(handle_rect, radius, radius)
        else:
            # При раскрытии - настоящее свечение: ярче по центру бегунка,
            # гаснет к его собственным краям (тот же приём, что и у рамок)
            handle_gradient = QLinearGradient(0, handle_top, 0, handle_top + handle_h)
            handle_gradient.setColorAt(0.0, QColor(r, g, b, 50))
            handle_gradient.setColorAt(0.5, QColor(r, g, b, 235))
            handle_gradient.setColorAt(1.0, QColor(r, g, b, 50))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(handle_gradient))
            painter.drawRoundedRect(handle_rect, radius, radius)


class RightPanel(QWidget):
    clear_requested = pyqtSignal()   # сигнал для запроса сброса
    mode_changed = pyqtSignal(str)   # 'protocol' / 'comparison' / 'stats' / 'empty'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_data = None
        self.current_comparison_items = None
        self._graph_toolbars = []
        # Ссылки на оси/canvas графиков 1 и 2 - нужны, чтобы при клике на
        # ячейку в таблице теста 1/2/3 отметить точкой соответствующее
        # значение на графике (см. _highlight_graph_point). Заполняются в
        # create_graphs(), сбрасываются при каждой перерисовке протокола.
        self._graph1_ax = None
        self._graph1_canvas = None
        self._graph1_marker = None
        self._graph2_ax = None
        self._graph2_canvas = None
        self._graph2_marker = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(styles.RIGHT_PANEL_SCROLL_STYLE)
        scroll.setVerticalScrollBar(_GlowScrollBar())
        self.scroll_area = scroll  # нужна для временной фиксации ширины при печати

        content = QWidget()
        self.content_widget = content  # нужен целиком для экспорта в PDF
        self.content_layout = QVBoxLayout(content)

        # Кнопки "Скрыть протокол"/"Экспорт в PDF" физически переехали в
        # верхнюю панель приложения (gui.py, значки рядом с "уместить в
        # высоту") - но сами объекты кнопок оставляем здесь и НИКУДА не
        # добавляем в layout: так все show()/hide() ниже по файлу (их
        # много, в разных методах) продолжают работать без переписывания -
        # просто теперь они не на что визуально не влияют, а видимость
        # реальных значков в верхней панели управляется через сигнал
        # mode_changed (см. gui.py, on_right_panel_mode_changed)
        self.clear_btn = QPushButton("Скрыть протокол", self)
        self.clear_btn.setObjectName("chromeButton")
        self.clear_btn.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
        self.clear_btn.clicked.connect(self.clear_protocol)
        self.clear_btn.hide()

        self.export_pdf_btn = QPushButton("Экспорт в PDF", self)
        self.export_pdf_btn.setObjectName("chromeButton")
        self.export_pdf_btn.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
        self.export_pdf_btn.clicked.connect(self.export_to_pdf)
        self.export_pdf_btn.hide()
        self._fit_mode = False

        # Жирный заголовок "Характеристики образца насоса ГУР" - во всю
        # ширину, отдельно от остальных деталей протокола
        self.header_title_label = QLabel("")
        self.header_title_label.setAlignment(Qt.AlignCenter)
        self.header_title_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.content_layout.addWidget(self.header_title_label)

        self.header_label = QLabel("Выберите насос для просмотра протокола")
        self.header_label.setAlignment(Qt.AlignLeft)
        self.header_label.setWordWrap(True)
        self.header_label.setFont(QFont("Arial", 12))

        # Поле условий испытаний - под заголовком "Характеристики...",
        # занимает правую часть под кнопкой "Экспорт в PDF" (та же ширина).
        # Пока рамка со скруглением и текст-заглушка - содержимое добавим позже.
        self.test_conditions_box = QFrame()
        self.test_conditions_box.setStyleSheet(
            "QFrame { border: 1px solid #9a9ea4; border-radius: 8px; }"
        )
        self.test_conditions_box.setFixedWidth(self.export_pdf_btn.sizeHint().width())
        conditions_layout = QVBoxLayout(self.test_conditions_box)
        conditions_layout.setContentsMargins(8, 6, 8, 6)
        self.test_conditions_label = QLabel("Условия проведения испытаний...")
        self.test_conditions_label.setWordWrap(True)
        self.test_conditions_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        conditions_layout.addWidget(self.test_conditions_label)
        conditions_layout.addStretch()

        header_row = QHBoxLayout()
        header_row.addWidget(self.header_label, 1)
        header_row.addWidget(self.test_conditions_box)
        self.content_layout.addLayout(header_row)


        # Логотип: картинка + текст-подсказка под ней. self.logo_label -
        # контейнер (не сам QLabel с картинкой), чтобы весь остальной код
        # (show()/hide() в разных местах файла) не пришлось переписывать
        self.logo_label = QWidget()
        self.logo_label.setObjectName("logoContainer")
        self.logo_label.setAttribute(Qt.WA_StyledBackground, True)
        logo_layout = QVBoxLayout(self.logo_label)
        logo_layout.setAlignment(Qt.AlignCenter)

        logo_text_label = QLabel("Выберите насос для просмотра протокола")
        logo_text_label.setAlignment(Qt.AlignCenter)
        logo_text_label.setStyleSheet(styles.RIGHT_PANEL_LOGO_TEXT_STYLE)
        logo_layout.addWidget(logo_text_label)

        self.logo_label.setStyleSheet(styles.RIGHT_PANEL_LOGO_STYLE)
        self.content_layout.addWidget(self.logo_label)

        # Индикатор загрузки: иконка песочных часов (переворачивается по
        # ходу загрузки протокола - см. _set_loading_progress) + текст.
        # self.loading_label - КОНТЕЙНЕР (не сам QLabel с текстом), чтобы
        # весь остальной код файла (show()/hide() в разных местах) не
        # пришлось переписывать
        self.loading_label = QWidget()
        self.loading_label.setObjectName("loadingContainer")
        loading_layout = QVBoxLayout(self.loading_label)
        loading_layout.setAlignment(Qt.AlignCenter)

        # Иконка - в лейбле ФИКСИРОВАННОГО размера (с запасом под диагональ
        # при повороте на промежуточные углы) - иначе при повороте
        # bounding-box картинки увеличивается, лейбл/панель меняют размер,
        # и всю правую часть визуально "дёргает"
        _LOADING_ICON_SIZE = 28
        self.loading_icon_label = QLabel()
        self.loading_icon_label.setAlignment(Qt.AlignCenter)
        self.loading_icon_label.setFixedSize(_LOADING_ICON_SIZE * 2, _LOADING_ICON_SIZE * 2)
        self._loading_icon_base = None
        load_svg_path = os.path.join(ICONS_DIR, 'load.svg')
        if os.path.exists(load_svg_path):
            self._loading_icon_base = icon_utils.tinted_pixmap(
                load_svg_path, styles.LOADING_ICON_COLOR, size=_LOADING_ICON_SIZE
            )
            self.loading_icon_label.setPixmap(self._loading_icon_base)
        loading_layout.addWidget(self.loading_icon_label, 0, Qt.AlignHCenter)

        self.loading_text_label = QLabel("")
        self.loading_text_label.setAlignment(Qt.AlignCenter)
        self.loading_text_label.setFont(QFont("Arial", 14))
        self.loading_text_label.setStyleSheet(styles.RIGHT_PANEL_LOADING_TEXT_STYLE)
        loading_layout.addWidget(self.loading_text_label, 0, Qt.AlignHCenter)

        self.loading_label.setStyleSheet(styles.RIGHT_PANEL_LOADING_STYLE)
        self.loading_label.hide()
        self.content_layout.addWidget(self.loading_label)

        # Сводная статистика - тёмно-синий фон на всю ширину/высоту области
        # (тот же градиент, что и у логотипа-заглушки при запуске), по
        # центру - карточка со свечением (переиспользуем _GlowFrame - тот
        # же приём, что и в остальных панелях: мягкие края, тень,
        # бирюзовая полоса по контуру)
        self.stats_widget = _CtrlWheelZoomWidget(self._on_stats_wheel)
        self.stats_widget.setObjectName("statsBackground")
        self.stats_widget.setStyleSheet(styles.RIGHT_PANEL_STATS_BG_STYLE)
        stats_outer_layout = QVBoxLayout(self.stats_widget)
        stats_outer_layout.setContentsMargins(20, 20, 20, 20)

        stats_center_row = QHBoxLayout()
        stats_center_row.addStretch(1)
        self.stats_card = _GlowFrame()
        stats_card_layout = QVBoxLayout(self.stats_card)
        stats_card_layout.setContentsMargins(24, 20, 24, 20)
        self.stats_label = QLabel()
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet(styles.RIGHT_PANEL_STATS_TEXT_STYLE)
        self._stats_base_font_size = self.stats_label.font().pointSize() or 10
        self._stats_zoom = 1.0
        stats_card_layout.addWidget(self.stats_label)
        stats_center_row.addWidget(self.stats_card)
        stats_center_row.addStretch(1)

        stats_outer_layout.addStretch(1)
        stats_outer_layout.addLayout(stats_center_row)
        stats_outer_layout.addStretch(1)

        self.stats_widget.hide()
        self.content_layout.addWidget(self.stats_widget)

        # Легенда (постоянная)
        self.legend_label = QLabel()
        self.legend_label.setWordWrap(True)
        self.legend_label.setStyleSheet(styles.RIGHT_PANEL_LEGEND_STYLE)
        self.content_layout.addWidget(self.legend_label)

        # Динамический контейнер: слева таблицы (на общей панели-подложке),
        # справа графики. Сами колонки создаются один раз и больше не
        # пересоздаются - при перерисовке протокола очищается только их
        # содержимое (см. _clear_dynamic_content).
        self.dynamic_widget = QWidget()
        self.dynamic_layout = QHBoxLayout(self.dynamic_widget)
        self.dynamic_layout.setSpacing(10)

        self.tables_panel = QFrame()
        self.tables_panel.setStyleSheet(styles.RIGHT_PANEL_CARD_STYLE)
        self.tables_column = QVBoxLayout(self.tables_panel)
        self.tables_column.setContentsMargins(8, 8, 8, 8)
        self.tables_column.setSpacing(8)

        self.graphs_column = QVBoxLayout()
        self.graphs_column.setSpacing(8)

        self.dynamic_layout.addWidget(self.tables_panel, 0)
        self.dynamic_layout.addLayout(self.graphs_column, 1)
        self.content_layout.addWidget(self.dynamic_widget)

        # Отдельная полноширинная панель для таблицы герметичности (тот же
        # фон, чтобы визуально выглядело продолжением общей панели)
        self.seal_panel = QFrame()
        self.seal_panel.setStyleSheet(styles.RIGHT_PANEL_CARD_STYLE)
        self.seal_layout = QVBoxLayout(self.seal_panel)
        self.seal_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.addWidget(self.seal_panel)

        # Примечание и история редактирования - в самом конце, после
        # герметичности
        self.notes_widget = QWidget()
        self.notes_layout = QVBoxLayout(self.notes_widget)
        self.content_layout.addWidget(self.notes_widget)

        scroll.setWidget(content)
        # Оборачиваем область прокрутки в такую же панель со свечением,
        # что и в левой панели (графитовый контур, бирюзовые вставки по
        # центру каждой стороны, тень со всех сторон, скруглённые углы)
        scroll_frame = _GlowFrame()
        scroll_frame_layout = QVBoxLayout(scroll_frame)
        scroll_frame_layout.setContentsMargins(6, 6, 6, 6)
        scroll_frame_layout.setSpacing(4)

        scroll_frame_layout.addWidget(scroll)

        # Виджет "обзорного" режима - целиковый уменьшенный снимок
        # протокола, без прокрутки, для быстрого просмотра одним взглядом
        # (см. toggle_fit_view). Живёт в той же рамке, что и обычная
        # область прокрутки - видимость переключается между ними. Фон -
        # тот же тёмно-синий градиент, что и при загрузке/показе
        # статистики (п.1) - виден по краям, если снимок уже панели.
        self.overview_bg = _CtrlWheelZoomWidget(self._on_overview_wheel)
        self.overview_bg.setObjectName("statsBackground")
        self.overview_bg.setStyleSheet(styles.RIGHT_PANEL_STATS_BG_STYLE)
        overview_bg_layout = QVBoxLayout(self.overview_bg)
        overview_bg_layout.setContentsMargins(0, 0, 0, 0)
        self.overview_label = QLabel()
        self.overview_label.setAlignment(Qt.AlignCenter)
        self.overview_label.setStyleSheet("background: transparent;")
        overview_bg_layout.addWidget(self.overview_label)
        self.overview_bg.hide()
        scroll_frame_layout.addWidget(self.overview_bg)
        self._overview_base_pixmap = None
        self._overview_zoom = 1.0

        layout.addWidget(scroll_frame)

        # Начальное состояние: показываем логотип, скрываем остальное
        self.header_label.hide()
        self.header_title_label.hide()
        self.test_conditions_box.hide()
        self.legend_label.hide()
        self.seal_panel.hide()
        self.notes_widget.hide()
        self.dynamic_widget.hide()
        self.stats_widget.hide()
        self.logo_label.show()

    def _zoom_stats(self, factor):
        self._stats_zoom = max(0.5, min(3.0, self._stats_zoom * factor))
        new_size = max(6, int(self._stats_base_font_size * self._stats_zoom))
        font = self.stats_label.font()
        font.setPointSize(new_size)
        self.stats_label.setFont(font)

    def _on_stats_wheel(self, event):
        delta = event.angleDelta().y()
        self._zoom_stats(1.15 if delta > 0 else 1 / 1.15)

    def _build_stats_html(self, stats_data):
        """Строит HTML-отчёт сводной статистики - общий для экранного
        показа (тёмная тема) и печати/PDF (светлый классический фон)."""
        html = "<h2>Сводная статистика по базе данных</h2>"
        html += f"<p><b>Всего проверено насосов:</b> {stats_data['total']} шт — 100%</p>"
        html += f"<p><b>Из них годных:</b> {stats_data['good']} шт — {stats_data['good_percent']:.1f}%</p>"
        html += f"<p><b>Годных с первого предъявления:</b> {stats_data['good_first']} шт — {stats_data['good_first_percent']:.1f}%</p>"
        html += f"<p><b>Не годных:</b> {stats_data['bad']} шт — {stats_data['bad_percent']:.1f}%</p>"
        html += f"<p><b>Из них не герметичны:</b> {stats_data['not_sealed']} шт — {stats_data['not_sealed_percent']:.1f}%</p>"

        if stats_data['orders']:
            html += "<h3>Статистика по заказам:</h3>"
            for order in stats_data['orders']:
                order_num = format_order_number(order['order_number'])
                html += f"<p><b>Заказ №{order_num}:</b>"
                date_min = utils.format_date_display(order.get('date_min'))
                date_max = utils.format_date_display(order.get('date_max'))
                if date_min and date_max:
                    html += f"<br> период проверки с <b>{date_min}</b> по <b>{date_max}</b>"
                html += "</p>"
                html += f"<ul>"
                html += f"<li>Всего проверено: {order['total']} шт</li>"
                html += f"<li>Годных: {order['good']} шт</li>"
                html += f"<li>Годных с первого предъявления: {order['good_first']} шт</li>"
                html += f"<li>Не годных: {order['bad']} шт</li>"
                html += f"<li>Не герметичны: {order['not_sealed']} шт</li>"
                html += "</ul>"
        else:
            html += "<p>Нет данных по заказам.</p>"
        return html

    def display_statistics(self, stats_data):
        """Отображает сводную статистику в правой панели."""
        self._clear_dynamic_content()  # очищаем динамическую область
        self._zoom_stats(1.0 / self._stats_zoom)  # сброс масштаба к исходному
        self.logo_label.hide()
        self.header_label.hide()  # скрываем заголовок протокола
        self.test_conditions_box.hide()

        self.stats_label.setText(self._build_stats_html(stats_data))
        self.stats_widget.show()
        self.current_data = None  # сбрасываем текущий протокол, т.к. показываем статистику
        self.current_comparison_items = None
        self.mode_changed.emit('stats')

    def _make_print_stats_label(self, html):
        """Виджет для печати/PDF статистики - классический светлый фон
        (не тёмная тема, используемая на экране)."""
        label = QLabel(html)
        label.setWordWrap(True)
        label.setStyleSheet("background: white; color: #1c1e21; padding: 20px;")
        label.setFixedWidth(750)
        label.adjustSize()
        return label

    def print_statistics(self):
        """Открывает предпросмотр печати сводной статистики по всем
        заказам - всегда берёт свежие данные из базы (не привязано к
        тому, что сейчас показано на экране)."""
        stats_data = db.get_statistics()
        html = self._build_stats_html(stats_data)
        print_label = self._make_print_stats_label(html)

        printer = QPrinter()
        printer.setPageSize(QPrinter.A4)
        printer.setOrientation(QPrinter.Portrait)
        printer.setPageMargins(10, 10, 10, 10, QPrinter.Millimeter)

        preview = QPrintPreviewDialog(printer, self)
        preview.setWindowTitle("Предпросмотр печати - сводная статистика")
        preview.paintRequested.connect(lambda p: self._render_widget_to_printer(print_label, p))
        preview.resize(850, 950)
        _clamp_to_screen(preview, width_fraction=0.92, height_fraction=0.92)

        preview_widget = preview.findChild(QPrintPreviewWidget)
        if preview_widget:
            def _apply_zoom():
                preview_widget.setZoomMode(QPrintPreviewWidget.CustomZoom)
                preview_widget.setZoomFactor(0.65)
            QTimer.singleShot(0, _apply_zoom)

        preview.exec_()

    def _render_widget_to_printer(self, widget, printer):
        try:
            w = max(widget.width(), 1)
            h = max(widget.height(), 1)
            page_rect = printer.pageRect()
            scale_x = (page_rect.width() / w) * 0.98
            scale_y = scale_x * 1.12
            painter = QPainter()
            painter.begin(printer)
            painter.scale(scale_x, scale_y)
            widget.render(painter)
            painter.end()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка печати", f"Не удалось напечатать:\n{e}")

    def display_protocol(self, data):
        self._show_loading()

        self.current_data = data
        self.current_comparison_items = None
        self._clear_dynamic_content()  # очищаем dynamic_layout

        # _clear_dynamic_content() прячет всё, включая индикатор загрузки -
        # возвращаем его обратно и держим видимым, пока строим содержимое
        self.logo_label.hide()
        self.loading_label.show()

        # Заголовок
        date_str = utils.format_date_display(data['test_date'])
            
        order_num = data.get('order_number', '—')
        if order_num != '—' and order_num is not None:
            order_num = str(order_num).replace('.0', '')

        changed_fields = data.get('changed_fields') or []
        ORANGE = "#B35C00"  # тёмно-оранжевый - для отметки изменённых при редактировании значений

        def mark(text, field_key):
            if field_key in changed_fields:
                return f"<span style='color:{ORANGE};'>{text}</span>"
            return text

        verdict_ok = (data['verdict'] == 'годен')
        verdict_text = "Соответствует" if verdict_ok else "Не соответствует"
        verdict_color = "#1a7a1a" if verdict_ok else "#8b0000"

        self.header_title_label.setText("Характеристики образца насоса ГУР")

        header_html = (
            "<div align='left'>"
            f"Протокол проверки насоса ГУР от: <b>{mark(date_str, 'test_date')}</b><br>"
            f"Идентификационный №: <b>{data['pump_number']}</b><br>"
            f"Заказ №: <b>{mark(order_num, 'order_number')}</b><br>"
            f"Проверка: <b>{mark(data['test_type'], 'test_type')}</b><br>"
            f"Модификация: <b>{mark(data.get('mod_name', '—'), 'modification')}</b><br>"
            f"Герметичен: <b>{'Да' if data['is_sealed'] else 'Нет'}</b><br>"
            f"Соответствие нормативным требованиям: "
            f"<b><span style='color:{verdict_color};'>{verdict_text}</span></b>"
        )
        edit_date = data.get('edit_date')
        if edit_date:
            edit_date_display = utils.format_date_display(edit_date)
            header_html += (
                f"<br><span style='font-size:8pt; color:{ORANGE};'>"
                f"Редакция протокола от: {edit_date_display}</span>"
            )
        header_html += "</div>"
        self.header_label.setText(header_html)

        # Динамическое содержимое
        changed_fields = data.get('changed_fields') or []
        t1_title, t1_table = self.create_test_table("Тест 1: Зависимость расхода от оборотов (ECO выкл.)",
                               list(range(5, 13)), data['results_json'], data.get('mod_name'), changed_fields)
        t2_title, t2_table = self.create_test_table("Тест 2: Зависимость расхода от оборотов (ECO вкл.)",
                               list(range(13, 21)), data['results_json'], data.get('mod_name'), changed_fields)
        t3_title, t3_table = self.create_test_table("Тест 3: Зависимость расхода от силы тока ECO",
                               list(range(21, 32)), data['results_json'], data.get('mod_name'), changed_fields)
        p_title, p_table = self.create_pressure_table(data)
        self._set_loading_progress(35)

        # Координируем ширину столбцов между тестами 1-3: каждая колонка
        # (Х, Расход, Мин.треб, Макс.треб) получает одинаковую ширину во
        # всех трёх таблицах - по максимальному содержимому среди них
        # (п.5-6 требований: столбцы "жёстко закреплены", пользователь не
        # может менять их ширину).
        test_tables = [t1_table, t2_table, t3_table]
        col_widths = [
            max(t.columnWidth(col) for t in test_tables)
            for col in range(4)
        ]
        for t in test_tables:
            for col, w in enumerate(col_widths):
                t.setColumnWidth(col, w)
            t.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
            t.setFixedWidth(4 + sum(col_widths))

        # Таблица давления (тест 4): "Допустимый диапазон" по ширине равен
        # сумме столбцов "Мин.треб" + "Макс.треб" остальных таблиц.
        # "Параметр"/"Значение" делят оставшуюся ширину (Х + Расход)
        # пропорционально их собственному естественному размеру - без
        # лишних пустых мест, но и без утраты общей одинаковой ширины
        # всех четырёх таблиц.
        range_width = col_widths[2] + col_widths[3]
        remaining_width = col_widths[0] + col_widths[1]
        natural_param = p_table.columnWidth(0)
        natural_value = p_table.columnWidth(1)
        natural_sum = max(1, natural_param + natural_value)
        param_width = max(40, int(remaining_width * natural_param / natural_sum))
        value_width = remaining_width - param_width
        p_table.setColumnWidth(0, param_width)
        p_table.setColumnWidth(1, value_width)
        p_table.setColumnWidth(2, range_width)
        p_table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        p_table.setFixedWidth(4 + param_width + value_width + range_width)

        # Все четыре таблицы теперь одной и той же общей ширины - растягиваем
        # заголовки на неё же (нужно для точного расчёта их высоты ниже,
        # с учётом возможного переноса текста на 2 строки)
        main_titles = [t1_title, t2_title, t3_title, p_title]
        uniform_width = t1_table.width()
        for lbl in main_titles:
            lbl.setFixedWidth(uniform_width)

        self.create_seal_table(data)
        self._set_loading_progress(55)

        # Высоты групп "заголовок + таблица" - чтобы графики визуально
        # вписывались по размеру в соответствующие таблицы слева. Считаем
        # точно: реальная высота заголовка (с учётом возможного переноса на
        # 2 строки) + все отступы между элементами внутри tables_column.
        spacing = self.tables_column.spacing()
        t1_h = t1_title.heightForWidth(uniform_width)
        t2_h = t2_title.heightForWidth(uniform_width)
        t3_h = t3_title.heightForWidth(uniform_width)
        p_h = p_title.heightForWidth(uniform_width)

        # В диапазоне "тест1+тест2" - 4 элемента (загол1,табл1,загол2,табл2) = 3 отступа
        graph1_height = t1_h + spacing + t1_table.height() + spacing + t2_h + spacing + t2_table.height()
        graph2_height = t3_h + spacing + t3_table.height() + spacing + p_h + spacing + p_table.height()

        # Синхронизируем верхний отступ колонки графиков с панелью таблиц
        # (граница рамки 1px + внутренний отступ 8px), чтобы иконки тулбара
        # графика 1 были на уровне заголовка "Тест 1"
        self.graphs_column.setContentsMargins(0, 9, 0, 0)

        self.create_graphs(data, graph1_height, graph2_height)
        self._set_loading_progress(90)
        show_notes = self.create_notes_section(data)
        self._set_loading_progress(100)

        self.legend_label.setText(
            "<span style='background-color:#ffc8c8; border:1px solid #999;'>"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>"
            "&nbsp;&nbsp;<span style='font-style:italic; font-size:11pt;'>"
            "— значение не соответствует техническим требованиям.</span>"
        )

        # Всё построено - теперь показываем готовый протокол разом и
        # прячем индикатор загрузки
        self.loading_label.hide()
        self.dynamic_widget.show()
        self.seal_panel.show()
        self.header_label.show()
        self.header_title_label.show()
        self.test_conditions_box.show()
        self.legend_label.show()
        if show_notes:
            self.notes_widget.show()
        self.mode_changed.emit('protocol')

    def _compact_table(self, table, fix_width=True):
        """Уменьшает шрифт таблицы и подгоняет высоту (и, если fix_width=True,
        ширину) точно под содержимое, чтобы таблица показывалась полностью,
        без собственной прокрутки и без пустого пространства справа -
        прокручиваться может только вся правая панель целиком."""
        small_font = QFont("Arial", 8)
        table.setFont(small_font)
        table.horizontalHeader().setFont(small_font)
        table.verticalHeader().setDefaultSectionSize(18)
        table.resizeRowsToContents()
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.horizontalHeader().setMinimumSectionSize(40)

        total_height = table.horizontalHeader().height() + 4
        for row in range(table.rowCount()):
            total_height += table.rowHeight(row)
        table.setFixedHeight(total_height)

        if fix_width:
            total_width = 4  # небольшой запас на рамки/скролл-полосы
            for col in range(table.columnCount()):
                total_width += table.columnWidth(col)
            table.setFixedWidth(total_width)
            table.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        else:
            table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def create_test_table(self, title, indices, results, mod_name, changed_fields=None):
        changed_fields = changed_fields or []
        mod = None
        if mod_name:
            mod = db.get_modification_by_name(mod_name)

        if indices[0] == 5:
            norm_min = mod['norm_graph1_min'] if mod else []
            norm_max = mod['norm_graph1_max'] if mod else []
            x_label = "Обороты, об/мин"
            x_vals = mod['norm_graph1_x'] if mod else list(utils.DEFAULT_GRAPH1_X)
        elif indices[0] == 13:
            norm_min = mod['norm_graph2_min'] if mod else []
            norm_max = mod['norm_graph2_max'] if mod else []
            x_label = "Обороты, об/мин"
            x_vals = mod['norm_graph2_x'] if mod else list(utils.DEFAULT_GRAPH2_X)
        elif indices[0] == 21:
            norm_min = mod['norm_graph3_min'] if mod else []
            norm_max = mod['norm_graph3_max'] if mod else []
            x_label = "Сила тока, А"
            x_vals = mod['norm_graph3_x'] if mod else list(utils.DEFAULT_GRAPH3_X)
        else:
            norm_min = []
            norm_max = []
            x_label = ""
            x_vals = []

        # Вспомогательная функция для форматирования чисел
        def format_number(value):
            if value is None or value == '':
                return ''
            try:
                return f"{float(value):.2f}"
            except:
                return str(value)

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels([x_label, "Расход, л/мин", "Мин. треб.", "Макс. треб."])
        table.setRowCount(len(indices))

        # Шрифты ячеек: нормативные столбцы (Х, мин/макс требования) -
        # тем же моноширинным шрифтом, что и цифры в статус-баре; столбец
        # Все ячейки - одним (стандартным) шрифтом; измеренное значение
        # расхода - жирным, чтобы выделялось на фоне нормативных требований
        value_font = QFont("Arial", 8, QFont.Bold)

        for i, idx in enumerate(indices):
            key = f'g{idx}'
            val = results.get(key)
            x_val = x_vals[i] if i < len(x_vals) else ''
            x_item = QTableWidgetItem(str(x_val))
            x_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 0, x_item)

            # Значение расхода с форматированием
            val_text = format_number(val)
            val_item = QTableWidgetItem(val_text)
            val_item.setTextAlignment(Qt.AlignCenter)
            val_item.setFont(value_font)
            if key in changed_fields:
                val_item.setForeground(QColor(179, 92, 0))  # тёмно-оранжевый - значение изменено при редактировании
            # Проверка диапазона (используем исходное значение val, не строку)
            if val is not None and i < len(norm_min) and i < len(norm_max):
                if not is_value_in_range(val, norm_min[i], norm_max[i]):
                    val_item.setBackground(QColor(255, 200, 200))
            elif val is None:
                val_item.setBackground(QColor(255, 200, 200))
            table.setItem(i, 1, val_item)

            # Минimальное и максимальное требования с форматированием
            min_val = norm_min[i] if i < len(norm_min) else None
            max_val = norm_max[i] if i < len(norm_max) else None
            min_text = format_number(min_val)
            max_text = format_number(max_val)
            min_item = QTableWidgetItem(min_text)
            min_item.setTextAlignment(Qt.AlignCenter)
            max_item = QTableWidgetItem(max_text)
            max_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 2, min_item)
            table.setItem(i, 3, max_item)

        table.verticalHeader().setVisible(False)
        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._compact_table(table)

        # Клик по значению расхода или мин./макс. требования - отмечает
        # точкой соответствующее значение на графике (п.7 требований).
        # Тесты 1 и 2 рисуются на одном графике (self._graph1_ax), тест 3 -
        # на втором (self._graph2_ax).
        which_graph = 1 if indices[0] in (5, 13) else 2
        table.cellClicked.connect(
            lambda row, col, xs=list(x_vals), wg=which_graph: self._on_test_cell_clicked(row, col, xs, wg)
        )

        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 9, QFont.Bold))
        title_label.setWordWrap(True)
        self.tables_column.addWidget(title_label)
        self.tables_column.addWidget(table)
        return title_label, table

    def create_pressure_table(self, data):
        mod = None
        if data.get('mod_name'):
            mod = db.get_modification_by_name(data['mod_name'])
        pressure_val = data['results_json'].get('g32')
        min_p = mod['pressure_min'] if mod else None
        max_p = mod['pressure_max'] if mod else None

        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Параметр", "Значение", "Допустимый диапазон"])
        table.setRowCount(1)
        param_item = QTableWidgetItem("Макс. давление, бар")
        param_item.setTextAlignment(Qt.AlignCenter)
        table.setItem(0, 0, param_item)
        val_item = QTableWidgetItem(str(pressure_val) if pressure_val is not None else '')
        val_item.setTextAlignment(Qt.AlignCenter)
        val_item.setFont(QFont("Arial", 8, QFont.Bold))
        if 'g32' in (data.get('changed_fields') or []):
            val_item.setForeground(QColor(179, 92, 0))  # тёмно-оранжевый - значение изменено при редактировании
        if pressure_val is not None and min_p is not None and max_p is not None:
            if not is_value_in_range(pressure_val, min_p, max_p):
                val_item.setBackground(QColor(255, 200, 200))
        elif pressure_val is None:
            val_item.setBackground(QColor(255, 200, 200))
        table.setItem(0, 1, val_item)
        range_item = QTableWidgetItem(f"{min_p} – {max_p}" if min_p is not None and max_p is not None else '')
        range_item.setTextAlignment(Qt.AlignCenter)
        table.setItem(0, 2, range_item)
        table.verticalHeader().setVisible(False)
        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._compact_table(table)

        title_label = QLabel("Тест 4: Давление настройки предохранительного клапана")
        title_label.setFont(QFont("Arial", 9, QFont.Bold))
        title_label.setWordWrap(True)
        self.tables_column.addWidget(title_label)
        self.tables_column.addWidget(table)
        return title_label, table

    def create_seal_table(self, data):
        seal = data['seal_results_json']
        labels = {
            'g33': 'Соединение с седлом клапана ECO',
            'g34': 'Внешняя поверхность катушки ECO',
            'g35': 'Внешняя поверхность с торца катушки ECO',
            'g36': 'Соединение крышки корпуса',
            'g37': 'Масляные образования на уплотнении'
        }
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Место проверки", "Результат"])
        table.setRowCount(len(labels))
        for i, (key, label) in enumerate(labels.items()):
            place_item = QTableWidgetItem(label)
            place_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 0, place_item)
            val = seal.get(key)
            display_text = str(val) if val is not None else ''
            val_item = QTableWidgetItem(display_text)
            val_item.setTextAlignment(Qt.AlignCenter)
            if key in (data.get('changed_fields') or []):
                val_item.setForeground(QColor(179, 92, 0))  # тёмно-оранжевый - значение изменено при редактировании
            if key in ['g33', 'g34', 'g35', 'g36']:
                if val is not None and str(val).strip().lower() != 'отсутствуют':
                    val_item.setBackground(QColor(255, 200, 200))
            elif key == 'g37':
                if val is not None:
                    text = str(val).strip().lower()
                    if text == 'присутствуют в допускаемой степени':
                        val_item.setBackground(QColor(255, 255, 150))
                    elif text != 'отсутствуют':
                        val_item.setBackground(QColor(255, 200, 200))
            table.setItem(i, 1, val_item)
        
        table.verticalHeader().setVisible(False)
        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        self._compact_table(table, fix_width=False)

        title_label = QLabel("Герметичность")
        title_label.setFont(QFont("Arial", 9, QFont.Bold))
        title_label.setWordWrap(True)
        self.seal_layout.addWidget(title_label)
        self.seal_layout.addWidget(table)

    def _plot_series(self, ax, x_vals, y_vals, norm_min, norm_max, color, linestyle, label):
        """Рисует линию БЕЗ маркеров на промежуточных точках; точки, не
        соответствующие нормативам, отмечает красным кружком поверх линии."""
        ax.plot(x_vals, y_vals, linestyle=linestyle, color=color, linewidth=2, label=label)
        out_of_range_x, out_of_range_y = [], []
        for i, v in enumerate(y_vals):
            if v is None or (isinstance(v, float) and np.isnan(v)):
                continue
            if i < len(norm_min) and i < len(norm_max) and norm_min[i] is not None and norm_max[i] is not None:
                if not is_value_in_range(v, norm_min[i], norm_max[i]):
                    out_of_range_x.append(x_vals[i])
                    out_of_range_y.append(v)
        if out_of_range_x:
            ax.plot(out_of_range_x, out_of_range_y, 'o', color='red', markersize=7, zorder=5)

    def _on_test_cell_clicked(self, row, col, x_vals, which_graph):
        """Клик по значению расхода ("Расход") или норматива ("Мин.треб"/
        "Макс.треб") в таблице теста 1/2/3 - отмечает лёгкой точкой это
        значение на соответствующем графике."""
        if col not in (1, 2, 3):  # только столбцы со значениями, не Х
            return
        if row >= len(x_vals):
            return
        table = self.sender()
        if table is None:
            return
        item = table.item(row, col)
        if item is None or not item.text().strip():
            return
        try:
            y = float(item.text())
        except ValueError:
            return
        x = x_vals[row]
        self._highlight_graph_point(which_graph, x, y)

    def _on_comparison_cell_clicked(self, row, col, x_vals, which_graph):
        """То же самое, что _on_test_cell_clicked, но для таблиц сравнения
        дублей - там количество столбцов переменное (по одному на каждый
        найденный дубль, плюс Мин./Макс. треб.), поэтому пропускаем только
        сам столбец Х (col 0), а не проверяем конкретные номера столбцов."""
        if col == 0:
            return
        if row >= len(x_vals):
            return
        table = self.sender()
        if table is None:
            return
        item = table.item(row, col)
        if item is None or not item.text().strip():
            return
        try:
            y = float(item.text())
        except ValueError:
            return
        x = x_vals[row]
        self._highlight_graph_point(which_graph, x, y)

    def _highlight_graph_point(self, which_graph, x, y):
        """Рисует (или переставляет, если уже была) лёгкую точку-маркер
        на графике 1 или 2 в указанных координатах."""
        if which_graph == 1:
            ax, canvas, marker_attr = self._graph1_ax, self._graph1_canvas, '_graph1_marker'
        else:
            ax, canvas, marker_attr = self._graph2_ax, self._graph2_canvas, '_graph2_marker'
        if ax is None or canvas is None:
            return

        old_marker = getattr(self, marker_attr, None)
        if old_marker is not None:
            try:
                old_marker.remove()
            except (ValueError, NotImplementedError):
                pass

        marker, = ax.plot(
            [x], [y], marker='o', markersize=10,
            markerfacecolor='#ff8c00', markeredgecolor='#663300',
            markeredgewidth=1.2, alpha=0.6, zorder=10, linestyle='None'
        )
        setattr(self, marker_attr, marker)
        canvas.draw_idle()

    def _make_graph_widget(self, fig, height=None):
        """Оборачивает Figure в canvas + тулбар matplotlib (зум/панорама/
        сброс масштаба кнопкой 'Home') и возвращает готовый контейнер-виджет
        и сам canvas (нужен отдельно, чтобы перерисовать график после клика
        по ячейке таблицы - см. _highlight_graph_point)."""
        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        toolbar = NavigationToolbar(canvas, self)
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setStyleSheet(styles.RIGHT_PANEL_GRAPH_TOOLBAR_STYLE)
        self._graph_toolbars.append(toolbar)  # понадобится скрыть при экспорте в PDF
        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(0)
        c_layout.addWidget(toolbar)
        c_layout.addWidget(canvas)
        if height:
            container.setFixedHeight(height)
        return container, canvas

    def create_graphs(self, data, graph1_height=None, graph2_height=None):
        mod = None
        if data.get('mod_name'):
            mod = db.get_modification_by_name(data['mod_name'])
        if not mod:
            label = QLabel("Нормативы не найдены для этой модификации")
            self.graphs_column.addWidget(label)
            return

        results = data['results_json']

        # График 1: расход от оборотов (ECO выкл. / ECO вкл.)
        fig1 = Figure(figsize=(4, 3), dpi=100)
        ax1 = fig1.add_subplot(111)
        x_vals = mod.get('norm_graph1_x') or list(utils.DEFAULT_GRAPH1_X)
        y1 = [results.get(f'g{i}') for i in range(5, 13)]
        y2 = [results.get(f'g{i}') for i in range(13, 21)]
        min1 = mod['norm_graph1_min']
        max1 = mod['norm_graph1_max']
        min2 = mod['norm_graph2_min']
        max2 = mod['norm_graph2_max']

        # На случай, если у модификации задано меньше точек, чем стандартные 8 -
        # выравниваем длины, чтобы matplotlib не упал на несовпадении размеров
        n1 = min(len(x_vals), len(y1))
        x_vals_plot = x_vals[:n1]
        y1_plot = [v if v is not None else np.nan for v in y1[:n1]]
        y2_plot = [v if v is not None else np.nan for v in y2[:n1]]

        self._plot_series(ax1, x_vals_plot, y1_plot, min1, max1, 'tab:blue', '-', 'Расход при клапане ECO выкл.')
        self._plot_series(ax1, x_vals_plot, y2_plot, min2, max2, 'tab:red', '-', 'Расход при клапане ECO вкл.')
        if len(min1) == len(x_vals_plot):
            ax1.plot(x_vals_plot, min1, '--', color='tab:blue', label='Мин./макс. треб. ECO выкл.', alpha=0.5)
            ax1.plot(x_vals_plot, max1, '--', color='tab:blue', alpha=0.5)
        if len(min2) == len(x_vals_plot):
            ax1.plot(x_vals_plot, min2, ':', color='tab:red', label='Мин./макс. треб. ECO вкл.', alpha=0.5)
            ax1.plot(x_vals_plot, max2, ':', color='tab:red', alpha=0.5)
        ax1.set_xlabel('Обороты, об/мин')
        ax1.set_ylabel('Расход, л/мин')
        ax1.tick_params(axis='both', labelsize=7)
        ax1.yaxis.set_major_locator(MultipleLocator(2))
        ax1.grid(True, alpha=0.3)
        # Легенда в 2 строки: сверху - мин./макс. требования, снизу -
        # расход. Порядок записей переставлен так, чтобы при заполнении
        # "по столбцам" (поведение matplotlib по умолчанию для ncol=2)
        # получилась именно такая раскладка по строкам.
        handles1, labels1 = ax1.get_legend_handles_labels()
        order1 = [2, 0, 3, 1]
        ax1.legend([handles1[i] for i in order1], [labels1[i] for i in order1],
                  loc='upper center', bbox_to_anchor=(0.5, -0.16), ncol=2,
                  fontsize=7, frameon=False, handlelength=1.4, columnspacing=1.2)
        ax1.set_title('Зависимость расхода от оборотов', fontsize=10)
        ax1.format_coord = lambda x, y: f"RPM={x:.1f}   Q={y:.2f}"
        # rect резервирует место под легенду СНИЗУ за один проход, не
        # трогая остальные поля отдельным subplots_adjust() - именно он
        # раньше сбивал правое поле, делая его непредсказуемо большим
        # Явные фиксированные поля вместо tight_layout(): у tight_layout()
        # есть известная особенность плохо учитывать легенду, вынесенную
        # НАРУЖУ осей через bbox_to_anchor - результат непредсказуемый
        # (то огромные отступы снизу, то справа). Ручные значения дают
        # стабильный, предсказуемый результат.
        fig1.subplots_adjust(left=0.14, right=0.97, top=0.90, bottom=0.24)

        graph1_widget, graph1_canvas = self._make_graph_widget(fig1, graph1_height)
        self.graphs_column.addWidget(graph1_widget)
        self._graph1_ax = ax1
        self._graph1_canvas = graph1_canvas
        self._graph1_marker = None

        # График 2: расход от силы тока ECO
        fig2 = Figure(figsize=(4, 3), dpi=100)
        ax2 = fig2.add_subplot(111)
        x_tok = mod.get('norm_graph3_x') or list(utils.DEFAULT_GRAPH3_X)
        y3 = [results.get(f'g{i}') for i in range(21, 32)]
        n3 = min(len(x_tok), len(y3))
        x_tok_plot = x_tok[:n3]
        y3_plot = [v if v is not None else np.nan for v in y3[:n3]]

        min3 = mod['norm_graph3_min']
        max3 = mod['norm_graph3_max']
        self._plot_series(ax2, x_tok_plot, y3_plot, min3, max3, 'tab:green', '-', 'Расход')
        if len(min3) == len(x_tok_plot):
            ax2.plot(x_tok_plot, min3, '--', color='tab:green', label='Мин./макс. треб.', alpha=0.5)
            ax2.plot(x_tok_plot, max3, '--', color='tab:green', alpha=0.5)
        ax2.set_xlabel('Сила тока, А')
        ax2.set_ylabel('Расход, л/мин')
        ax2.tick_params(axis='both', labelsize=7)
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper center', bbox_to_anchor=(0.5, -0.16), ncol=2,
                  fontsize=8, frameon=False, handlelength=1.4, columnspacing=1.2)
        ax2.set_title('Зависимость расхода от силы тока ECO', fontsize=10)
        ax2.format_coord = lambda x, y: f"I={x:.2f}   Q={y:.2f}"
        # Оси по умолчанию (масштаб по-прежнему можно менять зумом тулбара)
        ax2.set_xlim(0, 1)
        ax2.set_xticks(np.arange(0, 1.01, 0.1))
        ax2.set_ylim(4, 17)
        ax2.set_yticks(np.arange(4, 18, 1))
        fig2.subplots_adjust(left=0.14, right=0.97, top=0.90, bottom=0.20)

        graph2_widget, graph2_canvas = self._make_graph_widget(fig2, graph2_height)
        self.graphs_column.addWidget(graph2_widget)
        self._graph2_ax = ax2
        self._graph2_canvas = graph2_canvas
        self._graph2_marker = None

    def display_comparison(self, items):
        """items - список полных данных (с results_json) насосов-дублей:
        одинаковый номер + модификация. Показывает сравнительные таблицы
        и 2 графика, на каждом - линии всех найденных дублей вместе."""
        self._show_loading("Загрузка сравнения протоколов...")

        self.current_data = None  # это не единичный протокол
        self.current_comparison_items = items  # для экспорта/печати сравнения
        self._clear_dynamic_content()

        self.logo_label.hide()
        self.loading_label.show()

        first = items[0]
        mod_name = first.get('mod_name')
        mod = db.get_modification_by_name(mod_name) if mod_name else None
        dates = [(utils.format_date_display(it['test_date']) if it.get('test_date') else '—') for it in items]

        self.header_title_label.setText("Характеристики образцов насоса ГУР")
        header_html = (
            "<div align='left'>"
            "Сравнение всех найденных дублей выбранного образца<br>"
            f"Идентификационный №: <b>{first['pump_number']}</b><br>"
            f"Модификация: <b>{mod_name or '—'}</b><br>"
            f"Найдено протоколов: <b>{len(items)}</b><br>"
            f"Проверки от: <b>{', '.join(dates)}</b>"
            "</div>"
        )
        self.header_label.setText(header_html)

        norm1_min = mod['norm_graph1_min'] if mod else []
        norm1_max = mod['norm_graph1_max'] if mod else []
        norm1_x = mod['norm_graph1_x'] if mod else list(utils.DEFAULT_GRAPH1_X)
        norm2_min = mod['norm_graph2_min'] if mod else []
        norm2_max = mod['norm_graph2_max'] if mod else []
        norm2_x = mod['norm_graph2_x'] if mod else list(utils.DEFAULT_GRAPH2_X)
        norm3_min = mod['norm_graph3_min'] if mod else []
        norm3_max = mod['norm_graph3_max'] if mod else []
        norm3_x = mod['norm_graph3_x'] if mod else list(utils.DEFAULT_GRAPH3_X)

        t1_title, t1_table = self._create_comparison_table(
            "Тест 1: расход от оборотов (ECO выкл.)",
            list(range(5, 13)), items, norm1_min, norm1_max, norm1_x, "Обороты, об/мин")
        t2_title, t2_table = self._create_comparison_table(
            "Тест 2: расход от оборотов (ECO вкл.)",
            list(range(13, 21)), items, norm2_min, norm2_max, norm2_x, "Обороты, об/мин")
        t3_title, t3_table = self._create_comparison_table(
            "Тест 3: расход от силы тока ECO",
            list(range(21, 32)), items, norm3_min, norm3_max, norm3_x, "Сила тока, А")
        p_title, p_table = self._create_comparison_pressure_table(items, mod)
        self._set_loading_progress(50)

        # Координируем ширину столбцов между тестами 1-3 - тот же приём,
        # что и в одиночном протоколе: одинаковые столбцы (Х, по одному на
        # каждый найденный дубль, Мин.треб, Макс.треб) получают одинаковую
        # ширину во всех трёх таблицах, столбцы жёстко зафиксированы
        test_tables = [t1_table, t2_table, t3_table]
        n_cols = test_tables[0].columnCount()
        col_widths = [
            max(t.columnWidth(col) for t in test_tables)
            for col in range(n_cols)
        ]
        for t in test_tables:
            for col, w in enumerate(col_widths):
                t.setColumnWidth(col, w)
            t.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
            t.setFixedWidth(4 + sum(col_widths))

        # Таблица давления (тест 4): "Допустимый диапазон" по ширине
        # соответствует "Мин.треб" + "Макс.треб" остальных таблиц, "Дата"/
        # "Давление" делят оставшуюся ширину пропорционально своему
        # естественному размеру - без лишних пустых мест
        range_width = col_widths[-2] + col_widths[-1]
        remaining_width = sum(col_widths[:-2])
        natural_date = p_table.columnWidth(0)
        natural_value = p_table.columnWidth(1)
        natural_sum = max(1, natural_date + natural_value)
        date_width = max(40, int(remaining_width * natural_date / natural_sum))
        value_width = remaining_width - date_width
        p_table.setColumnWidth(0, date_width)
        p_table.setColumnWidth(1, value_width)
        p_table.setColumnWidth(2, range_width)
        p_table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        p_table.setFixedWidth(4 + date_width + value_width + range_width)

        uniform_width = t1_table.width()
        for lbl in (t1_title, t2_title, t3_title, p_title):
            lbl.setFixedWidth(uniform_width)

        self._create_comparison_seal_table(items)
        self._create_comparison_graphs(items, mod)
        self._set_loading_progress(100)

        self.legend_label.setText(
            "<span style='background-color:#ffc8c8; border:1px solid #999;'>"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>"
            "&nbsp;&nbsp;<span style='font-style:italic; font-size:11pt;'>"
            "— значение не соответствует техническим требованиям.</span>"
        )

        # Всё построено - теперь показываем готовое сравнение разом и
        # прячем индикатор загрузки
        self.loading_label.hide()
        self.dynamic_widget.show()
        self.seal_panel.show()
        self.header_label.show()
        self.header_title_label.show()
        self.legend_label.show()
        self.mode_changed.emit('comparison')

    def _create_comparison_table(self, title, indices, items, norm_min, norm_max, x_vals, x_label):
        def format_number(value):
            if value is None or value == '':
                return ''
            try:
                return f"{float(value):.2f}"
            except (TypeError, ValueError):
                return str(value)

        dates = [(utils.format_date_display(it['test_date']) if it.get('test_date') else f'#{i+1}') for i, it in enumerate(items)]
        col_labels = [x_label] + dates + ["Мин. треб.", "Макс. треб."]

        table = QTableWidget()
        table.setColumnCount(len(col_labels))
        table.setHorizontalHeaderLabels(col_labels)
        table.setRowCount(len(indices))
        value_font = QFont("Arial", 8, QFont.Bold)

        for row, idx in enumerate(indices):
            key = f'g{idx}'
            x_val = x_vals[row] if row < len(x_vals) else ''
            x_item = QTableWidgetItem(str(x_val))
            x_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 0, x_item)

            for col, it in enumerate(items):
                val = it['results_json'].get(key)
                val_item = QTableWidgetItem(format_number(val))
                val_item.setTextAlignment(Qt.AlignCenter)
                val_item.setFont(value_font)
                if val is not None and row < len(norm_min) and row < len(norm_max):
                    if not is_value_in_range(val, norm_min[row], norm_max[row]):
                        val_item.setBackground(QColor(255, 200, 200))
                elif val is None:
                    val_item.setBackground(QColor(255, 200, 200))
                table.setItem(row, 1 + col, val_item)

            min_val = norm_min[row] if row < len(norm_min) else None
            max_val = norm_max[row] if row < len(norm_max) else None
            min_item = QTableWidgetItem(format_number(min_val))
            min_item.setTextAlignment(Qt.AlignCenter)
            max_item = QTableWidgetItem(format_number(max_val))
            max_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 1 + len(items), min_item)
            table.setItem(row, 2 + len(items), max_item)

        table.verticalHeader().setVisible(False)
        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._compact_table(table)

        # Клик по любому значению (кроме самого Х) - отмечает точкой
        # соответствующее значение на графике, как и в одиночном протоколе
        which_graph = 1 if indices[0] in (5, 13) else 2
        table.cellClicked.connect(
            lambda row, col, xs=list(x_vals), wg=which_graph: self._on_comparison_cell_clicked(row, col, xs, wg)
        )

        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 9, QFont.Bold))
        title_label.setWordWrap(True)
        self.tables_column.addWidget(title_label)
        self.tables_column.addWidget(table)
        return title_label, table

    def _create_comparison_pressure_table(self, items, mod):
        min_p = mod['pressure_min'] if mod else None
        max_p = mod['pressure_max'] if mod else None

        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Дата", "Давление, бар", "Допустимый диапазон"])
        table.setRowCount(len(items))
        for row, it in enumerate(items):
            date_str = utils.format_date_display(it['test_date']) if it.get('test_date') else f'#{row+1}'
            date_item = QTableWidgetItem(date_str)
            date_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 0, date_item)
            pressure_val = it['results_json'].get('g32')
            val_item = QTableWidgetItem(str(pressure_val) if pressure_val is not None else '')
            val_item.setTextAlignment(Qt.AlignCenter)
            val_item.setFont(QFont("Arial", 8, QFont.Bold))
            if pressure_val is not None and min_p is not None and max_p is not None:
                if not is_value_in_range(pressure_val, min_p, max_p):
                    val_item.setBackground(QColor(255, 200, 200))
            elif pressure_val is None:
                val_item.setBackground(QColor(255, 200, 200))
            table.setItem(row, 1, val_item)
            range_item = QTableWidgetItem(
                f"{min_p} – {max_p}" if min_p is not None and max_p is not None else '')
            range_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 2, range_item)

        table.verticalHeader().setVisible(False)
        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._compact_table(table)

        title_label = QLabel("Тест 4: Давление настройки предохранительного клапана")
        title_label.setFont(QFont("Arial", 9, QFont.Bold))
        self.tables_column.addWidget(title_label)
        self.tables_column.addWidget(table)
        return title_label, table

    def _create_comparison_seal_table(self, items):
        labels = {
            'g33': 'Соединение с седлом клапана ECO',
            'g34': 'Внешняя поверхность катушки ECO',
            'g35': 'Внешняя поверхность с торца катушки ECO',
            'g36': 'Соединение крышки корпуса',
            'g37': 'Масляные образования на уплотнении',
        }
        dates = [(utils.format_date_display(it['test_date']) if it.get('test_date') else f'#{i+1}') for i, it in enumerate(items)]
        col_labels = ["Место проверки"] + dates + ["Требование"]

        table = QTableWidget()
        table.setColumnCount(len(col_labels))
        table.setHorizontalHeaderLabels(col_labels)
        table.setRowCount(len(labels))

        for row, (key, label) in enumerate(labels.items()):
            place_item = QTableWidgetItem(label)
            place_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 0, place_item)

            requirement_text = ''
            for col, it in enumerate(items):
                seal = it['seal_results_json']
                val = seal.get(key)
                display_text = str(val) if val is not None else ''
                val_item = QTableWidgetItem(display_text)
                val_item.setTextAlignment(Qt.AlignCenter)
                if key in ('g33', 'g34', 'g35', 'g36'):
                    if val is not None and str(val).strip().lower() != 'отсутствуют':
                        val_item.setBackground(QColor(255, 200, 200))
                    requirement_text = 'отсутствуют'
                else:
                    if val is not None:
                        text = str(val).strip().lower()
                        if text == 'присутствуют в допускаемой степени':
                            val_item.setBackground(QColor(255, 255, 150))
                        elif text != 'отсутствуют':
                            val_item.setBackground(QColor(255, 200, 200))
                    requirement_text = 'отсутствуют или присутствуют в допускаемой степени'
                table.setItem(row, 1 + col, val_item)

            req_item = QTableWidgetItem(requirement_text)
            req_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 1 + len(items), req_item)

        table.verticalHeader().setVisible(False)
        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        self._compact_table(table, fix_width=False)

        title_label = QLabel("Герметичность")
        title_label.setFont(QFont("Arial", 9, QFont.Bold))
        self.seal_layout.addWidget(title_label)
        self.seal_layout.addWidget(table)

    def _create_comparison_graphs(self, items, mod):
        if not mod:
            label = QLabel("Нормативы не найдены для этой модификации")
            self.graphs_column.addWidget(label)
            return

        colors = ['tab:blue', 'tab:red', 'tab:green', 'tab:orange', 'tab:purple', 'tab:brown', 'tab:pink']

        # График 1: расход от оборотов - линии всех дублей вместе
        # (сплошная - ECO выкл., пунктир - ECO вкл.)
        fig1 = Figure(figsize=(4, 3), dpi=100)
        ax1 = fig1.add_subplot(111)
        x_vals = mod.get('norm_graph1_x') or list(utils.DEFAULT_GRAPH1_X)
        min1 = mod['norm_graph1_min']
        max1 = mod['norm_graph1_max']
        min2 = mod['norm_graph2_min']
        max2 = mod['norm_graph2_max']

        for idx, it in enumerate(items):
            color = colors[idx % len(colors)]
            date_str = utils.format_date_display(it['test_date']) if it.get('test_date') else f'#{idx + 1}'
            results = it['results_json']
            y1 = [results.get(f'g{i}') for i in range(5, 13)]
            y2 = [results.get(f'g{i}') for i in range(13, 21)]
            n1 = min(len(x_vals), len(y1))
            x_plot = x_vals[:n1]
            y1_plot = [v if v is not None else np.nan for v in y1[:n1]]
            y2_plot = [v if v is not None else np.nan for v in y2[:n1]]
            self._plot_series(ax1, x_plot, y1_plot, min1, max1, color, '-', f'{date_str}, ECO выкл.')
            self._plot_series(ax1, x_plot, y2_plot, min2, max2, color, '--', f'{date_str}, ECO вкл.')

        if len(min1) == len(x_vals):
            ax1.plot(x_vals, min1, ':', color='dimgray', label='Треб. ECO выкл.', alpha=0.7)
            ax1.plot(x_vals, max1, ':', color='dimgray', alpha=0.7)
        if len(min2) == len(x_vals):
            ax1.plot(x_vals, min2, '-.', color='gray', label='Треб. ECO вкл.', alpha=0.7)
            ax1.plot(x_vals, max2, '-.', color='gray', alpha=0.7)
        ax1.set_xlabel('Обороты, об/мин')
        ax1.set_ylabel('Расход, л/мин')
        ax1.tick_params(axis='both', labelsize=7)
        ax1.yaxis.set_major_locator(MultipleLocator(2))
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper center', bbox_to_anchor=(0.5, -0.16), ncol=3,
                  fontsize=8, frameon=False, handlelength=1.4, columnspacing=1.2)
        ax1.set_title('Сравнение дублей: расход от оборотов', fontsize=10)
        ax1.format_coord = lambda x, y: f"RPM={x:.1f}   Q={y:.2f}"
        fig1.subplots_adjust(left=0.14, right=0.97, top=0.90, bottom=0.26)
        graph1_widget, graph1_canvas = self._make_graph_widget(fig1)
        self._graph1_ax = ax1
        self._graph1_canvas = graph1_canvas
        self._graph1_marker = None
        self.graphs_column.addWidget(graph1_widget)

        # График 2: расход от силы тока ECO - линии всех дублей вместе
        fig2 = Figure(figsize=(4, 3), dpi=100)
        ax2 = fig2.add_subplot(111)
        x_tok = mod.get('norm_graph3_x') or list(utils.DEFAULT_GRAPH3_X)
        min3 = mod['norm_graph3_min']
        max3 = mod['norm_graph3_max']

        for idx, it in enumerate(items):
            color = colors[idx % len(colors)]
            date_str = utils.format_date_display(it['test_date']) if it.get('test_date') else f'#{idx + 1}'
            results = it['results_json']
            y3 = [results.get(f'g{i}') for i in range(21, 32)]
            n3 = min(len(x_tok), len(y3))
            x_plot = x_tok[:n3]
            y3_plot = [v if v is not None else np.nan for v in y3[:n3]]
            self._plot_series(ax2, x_plot, y3_plot, min3, max3, color, '-', date_str)

        if len(min3) == len(x_tok):
            ax2.plot(x_tok, min3, ':', color='gray', label='Мин./макс. треб.', alpha=0.6)
            ax2.plot(x_tok, max3, ':', color='gray', alpha=0.6)
        ax2.set_xlabel('Сила тока, А')
        ax2.set_ylabel('Расход, л/мин')
        ax2.tick_params(axis='both', labelsize=7)
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper center', bbox_to_anchor=(0.5, -0.16), ncol=3,
                  fontsize=8, frameon=False, handlelength=1.4, columnspacing=1.2)
        ax2.set_title('Сравнение дублей: расход от силы тока ECO', fontsize=10)
        ax2.format_coord = lambda x, y: f"I={x:.2f}   Q={y:.2f}"
        ax2.set_xlim(0, 1)
        ax2.set_xticks(np.arange(0, 1.01, 0.1))
        ax2.set_ylim(4, 17)
        ax2.set_yticks(np.arange(4, 18, 1))
        fig2.subplots_adjust(left=0.14, right=0.97, top=0.90, bottom=0.22)
        graph2_widget, graph2_canvas = self._make_graph_widget(fig2)
        self._graph2_ax = ax2
        self._graph2_canvas = graph2_canvas
        self._graph2_marker = None
        self.graphs_column.addWidget(graph2_widget)

    def print_protocol(self):
        """Открывает предпросмотр печати текущего протокола (или сравнения дублей)."""
        if not self.current_data and not self.current_comparison_items:
            QMessageBox.warning(self, "Печать", "Сначала выберите протокол для печати.")
            return

        # Без QPrinter.HighResolution - в паре с render() виджета этот режим
        # на некоторых системах даёт неверный масштаб/пропорции страницы
        printer = QPrinter()
        printer.setPageSize(QPrinter.A4)
        printer.setOrientation(QPrinter.Portrait)
        printer.setPageMargins(10, 10, 10, 10, QPrinter.Millimeter)

        preview = QPrintPreviewDialog(printer, self)
        preview.setWindowTitle("Предпросмотр печати - протокол")
        preview.paintRequested.connect(self._render_protocol_to_printer)

        # Окно должно быть достаточно большим, чтобы лист А4 целиком
        # помещался при масштабе 65% (без обрезки и без прокрутки)
        preview.resize(850, 950)
        _clamp_to_screen(preview, width_fraction=0.92, height_fraction=0.92)

        preview_widget = preview.findChild(QPrintPreviewWidget)
        if preview_widget:
            def _apply_zoom():
                preview_widget.setZoomMode(QPrintPreviewWidget.CustomZoom)
                preview_widget.setZoomFactor(0.65)
            # Устанавливаем масштаб ПОСЛЕ того, как диалог сам завершит
            # начальную раскладку - иначе Qt сбрасывает его на свой расчёт
            QTimer.singleShot(0, _apply_zoom)

        preview.exec_()

    def _render_protocol_to_printer(self, printer):
        """Рендерит текущий протокол на переданный QPrinter (вызывается
        предпросмотром печати, может дергаться несколько раз при смене
        масштаба/страницы в окне предпросмотра).

        Важно: ширина content_widget обычно диктуется текущим размером
        окна программы (QScrollArea с widgetResizable=True растягивает
        его под видимую область) - из-за этого пропорции таблиц/графиков
        на печати менялись бы в зависимости от того, насколько широко
        сейчас развёрнута правая панель. Чтобы печать всегда выглядела
        одинаково (как при полном развороте на всю ширину), на время
        рендера временно фиксируем эталонную ширину."""
        for toolbar in self._graph_toolbars:
            toolbar.hide()

        widget_to_print = self.content_widget
        REFERENCE_WIDTH = 1400  # эталонная ширина "как при полном развороте"

        # Временно отключаем авто-растяжение scroll area и фиксируем ширину
        self.scroll_area.setWidgetResizable(False)
        original_min_w = widget_to_print.minimumWidth()
        original_max_w = widget_to_print.maximumWidth()
        widget_to_print.setFixedWidth(REFERENCE_WIDTH)
        widget_to_print.adjustSize()
        QApplication.processEvents()

        try:
            w = max(widget_to_print.width(), 1)
            h = max(widget_to_print.height(), 1)
            page_rect = printer.pageRect()
            # Масштабируем по ширине - протокол должен заполнять всю ширину
            # листа; высота при необходимости просто продолжается за
            # пределы одной "видимой" страницы (постраничная разбивка не
            # реализована)
            scale_x = (page_rect.width() / w) * 0.98
            # Небольшое вертикальное растяжение (визуально привлекательнее,
            # заполняет лист по высоте лучше, чем строго пропорциональный
            # масштаб от ширины)
            scale_y = scale_x * 1.12

            painter = QPainter()
            painter.begin(printer)
            painter.scale(scale_x, scale_y)
            widget_to_print.render(painter)
            painter.end()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка печати", f"Не удалось напечатать протокол:\n{e}")
        finally:
            # Возвращаем ширину под управление scroll area (обычное поведение на экране)
            widget_to_print.setMinimumWidth(original_min_w)
            widget_to_print.setMaximumWidth(original_max_w)
            self.scroll_area.setWidgetResizable(True)

            for toolbar in self._graph_toolbars:
                toolbar.show()

    def toggle_fit_view(self):
        """Переключает между обычным (прокручиваемым) видом протокола и
        "обзорным" - целиковым снимком, смасштабированным по высоте видимой
        области, без полос прокрутки, для быстрого просмотра одним взглядом.

        Технически это НЕ живые виджеты, уменьшенные "на лету" (Qt не умеет
        аккуратно масштабировать таблицы/графики matplotlib целиком), а
        обычный снимок (QPixmap) текущего отображения - для быстрого
        визуального обзора этого достаточно, но кликать по ячейкам/
        графикам в этом режиме нельзя (только смотреть). Снимок можно
        дополнительно масштабировать колёсиком мыши с зажатым Ctrl."""
        if self.current_data is None and self.current_comparison_items is None:
            return

        if not self._fit_mode:
            self._overview_base_pixmap = self.content_widget.grab()
            self._overview_zoom = 1.0
            self._render_overview()
            self.scroll_area.hide()
            self.overview_bg.show()
            self._fit_mode = True
        else:
            self.overview_bg.hide()
            self.scroll_area.show()
            self._fit_mode = False

    def _render_overview(self):
        """Перестраивает картинку обзорного снимка под текущий зум
        (self._overview_zoom, 1.0 = точно по высоте панели)."""
        base = self._overview_base_pixmap
        if base is None or base.height() == 0:
            return
        viewport_height = self.scroll_area.viewport().height()
        if viewport_height <= 0:
            return
        fit_scale = viewport_height / base.height()
        total_scale = fit_scale * self._overview_zoom
        scaled = base.scaled(
            max(1, int(base.width() * total_scale)), max(1, int(base.height() * total_scale)),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.overview_label.setPixmap(scaled)

    def _on_overview_wheel(self, event):
        """Ctrl+колесо мыши на обзорном снимке - масштабирование. Снимок
        сохранён в исходном (не уменьшенном) разрешении, поэтому умеренное
        увеличение остаётся чётким; очень сильное - как и с любой
        картинкой, растровое увеличение всё же начнёт "мылить"."""
        if not self._fit_mode:
            return
        delta = event.angleDelta().y()
        factor = 1.1 if delta > 0 else (1 / 1.1)
        self._overview_zoom = max(0.3, min(3.0, self._overview_zoom * factor))
        self._render_overview()

    def _export_stats_to_pdf(self):
        """Экспортирует сводную статистику в PDF - светлый классический
        фон (не тёмная тема, используемая на экране)."""
        stats_data = db.get_statistics()
        html = self._build_stats_html(stats_data)
        print_label = self._make_print_stats_label(html)

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить статистику в PDF", "Сводная_статистика.pdf", "PDF файлы (*.pdf)"
        )
        if not file_path:
            return
        if not file_path.lower().endswith('.pdf'):
            file_path += '.pdf'

        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            printer.setPageSize(QPrinter.A4)
            printer.setOrientation(QPrinter.Portrait)
            printer.setPageMargins(10, 10, 10, 10, QPrinter.Millimeter)

            w = max(print_label.width(), 1)
            h = max(print_label.height(), 1)
            page_rect = printer.pageRect()
            scale = min(page_rect.width() / w, page_rect.height() / h) * 0.98

            painter = QPainter()
            painter.begin(printer)
            painter.scale(scale, scale)
            print_label.render(painter)
            painter.end()

            QMessageBox.information(self, "Экспорт в PDF", f"Статистика сохранена:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", f"Не удалось сохранить PDF:\n{e}")

    def export_to_pdf(self):
        """Экспортирует текущий протокол (или сравнение дублей, или -
        если сейчас открыт этот режим - сводную статистику) в PDF-файл."""
        if self.stats_widget.isVisible():
            self._export_stats_to_pdf()
            return

        if self.current_data:
            pump_number = self.current_data.get('pump_number', 'protocol')
            safe_number = str(pump_number).replace('/', '_').replace('\\', '_')
            default_name = f"Протокол_{safe_number}.pdf"
        elif self.current_comparison_items:
            pump_number = self.current_comparison_items[0].get('pump_number', 'comparison')
            safe_number = str(pump_number).replace('/', '_').replace('\\', '_')
            default_name = f"Сравнение_{safe_number}.pdf"
        else:
            QMessageBox.warning(self, "Экспорт в PDF", "Сначала выберите протокол для экспорта.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить протокол в PDF", default_name, "PDF файлы (*.pdf)"
        )
        if not file_path:
            return
        if not file_path.lower().endswith('.pdf'):
            file_path += '.pdf'

        # Скрываем кнопки и тулбары графиков на время рендера - в бумажном
        # документе элементы управления зумом неуместны
        for toolbar in self._graph_toolbars:
            toolbar.hide()

        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            printer.setPageSize(QPrinter.A4)
            printer.setOrientation(QPrinter.Portrait)
            # Обычные поля страницы (не setFullPage) - чтобы контент не
            # обрезался краевой непечатаемой зоной реального принтера
            printer.setPageMargins(10, 10, 10, 10, QPrinter.Millimeter)

            widget_to_print = self.content_widget
            w = max(widget_to_print.width(), 1)
            h = max(widget_to_print.height(), 1)
            page_rect = printer.pageRect()
            # Небольшой запас (0.98), чтобы точно не выйти за границы печати
            scale = min(page_rect.width() / w, page_rect.height() / h) * 0.98

            painter = QPainter()
            painter.begin(printer)
            painter.scale(scale, scale)
            widget_to_print.render(painter)
            painter.end()

            QMessageBox.information(self, "Экспорт в PDF", f"Протокол сохранён:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", f"Не удалось сохранить PDF:\n{e}")
        finally:
            for toolbar in self._graph_toolbars:
                toolbar.show()

    def create_notes_section(self, data):
        note = data.get('note', '')
        if note:
            note_label = QLabel(f"<b>Примечание:</b> {note}")
            note_label.setWordWrap(True)
            self.notes_layout.addWidget(note_label)

        edit_history = data.get('edit_history', '')
        if edit_history:
            history_label = QLabel("<b>История редактирования:</b>")
            history_label.setWordWrap(True)
            self.notes_layout.addWidget(history_label)

            btn_manage = QPushButton("Управлять историей")
            btn_manage.clicked.connect(lambda: self.manage_history(data))
            self.notes_layout.addWidget(btn_manage)

            for line in edit_history.strip().split('\n'):
                if line.strip():
                    line_label = QLabel(f"  {line.strip()}")
                    line_label.setWordWrap(True)
                    self.notes_layout.addWidget(line_label)

        # Не показываем панель прямо здесь - её видимость выставляется в
        # финальном блоке display_protocol()/display_comparison(), вместе
        # со всем остальным содержимым, а не сразу же во время загрузки
        return bool(note or edit_history)

    def manage_history(self, data):
        from ..widgets.dialogs import EditHistoryDialog
        from .. import database as db
        from PyQt5.QtWidgets import QDialog

        dialog = EditHistoryDialog(data.get('edit_history', ''), data['id'], self)
        if dialog.exec_() == QDialog.Accepted:
            new_history = dialog.result_history
            # Обновляем историю
            db.update_pump(data['id'], edit_history=new_history)
            # Если нужно очистить примечание
            if dialog.clear_note:
                db.update_pump(data['id'], note='')
            # Обновляем отображение протокола
            updated = db.get_pump_by_id(data['id'])
            if updated:
                self.display_protocol(updated)

    def clear_protocol(self):
        """Вызывается по кнопке 'Скрыть протокол' - явный сброс просмотра,
        уведомляет наружу (MainWindow), чтобы сбросить фильтры/выделение."""
        self.current_comparison_items = None
        self._clear_dynamic_content()
        self.mode_changed.emit('empty')
        self.clear_requested.emit()

    def _clear_dynamic_content(self):
        """Внутренняя очистка динамической области перед перерисовкой нового
        протокола/статистики. НЕ эмитит сигнал наружу, чтобы не сбрасывать
        фильтры при обычном выборе насоса из списка. Очищаются только
        СОДЕРЖИМОЕ колонок tables_column/graphs_column - сама двухколоночная
        структура (dynamic_layout) не пересоздаётся."""
        self._graph_toolbars = []
        self._graph1_ax = None
        self._graph1_canvas = None
        self._graph1_marker = None
        self._graph2_ax = None
        self._graph2_canvas = None
        self._graph2_marker = None
        for column in (self.tables_column, self.graphs_column, self.seal_layout, self.notes_layout):
            while column.count():
                child = column.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
                elif child.layout():
                    self._clear_layout(child.layout())
        # Скрываем постоянные виджеты, показываем логотип
        if self._fit_mode:
            self._fit_mode = False
            self.overview_bg.hide()
            self.scroll_area.show()
        self.header_label.hide()
        self.header_title_label.hide()
        self.test_conditions_box.hide()
        self.legend_label.hide()
        self.seal_panel.hide()
        self.notes_widget.hide()
        self.dynamic_widget.hide()  # иначе видна пустая панель-подложка без содержимого
        self.stats_widget.hide()
        self.loading_label.hide()
        self.logo_label.show()

    def _show_loading(self, message="Загрузка протокола..."):
        """Показывает индикатор загрузки и СРАЗУ ЖЕ принудительно
        отрисовывает его на экране (иначе Qt отложил бы отрисовку до
        конца текущего обработчика, а он ещё построит все таблицы и
        графики matplotlib - это заметно небыстро). Без этого пользователь
        мог решить, что программа зависла, а не просто загружает данные."""
        self.header_label.hide()
        self.header_title_label.hide()
        self.test_conditions_box.hide()
        self.legend_label.hide()
        self.seal_panel.hide()
        self.notes_widget.hide()
        self.dynamic_widget.hide()
        self.stats_widget.hide()
        self.logo_label.hide()
        self.loading_text_label.setText(message)
        self._set_loading_progress(0)
        self.loading_label.show()
        QApplication.processEvents()

    def _set_loading_progress(self, percent):
        """Поворачивает иконку песочных часов на угол, соответствующий
        проценту загрузки (0% - обычное положение, 100% - перевёрнута на
        180°, как будто часы перевернули). Загрузка протокола - операция
        синхронная (построение таблиц/графиков блокирует событийный
        цикл), поэтому НАСТОЯЩЕЙ плавной анимации здесь не получить - это
        несколько дискретных "щелчков" на контрольных точках прогресса, а
        не непрерывное вращение."""
        if self._loading_icon_base is None:
            return
        angle = (max(0, min(100, percent)) / 100.0) * 180.0
        transform = QTransform().rotate(angle)
        rotated = self._loading_icon_base.transformed(transform, Qt.SmoothTransformation)
        self.loading_icon_label.setPixmap(rotated)
        QApplication.processEvents()

    def _clear_layout(self, layout):
        """Рекурсивно очищает вложенный layout (используется для контейнеров
        график+тулбар внутри graphs_column)."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())