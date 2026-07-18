from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QCheckBox,
    QDateEdit, QHeaderView, QAbstractItemView, QMenu,
    QStyledItemDelegate, QStyle, QStyleOptionViewItem, QApplication,
    QFrame, QGraphicsDropShadowEffect, QGridLayout
)
from PyQt5.QtCore import (
    Qt, pyqtSignal, QDate, QPoint, QTimer, QEvent, QEasingCurve,
    QRect, QRectF, pyqtProperty, QPropertyAnimation
)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPolygon, QLinearGradient

from .. import database as db
from .. import utils
from .. import styles

class _ArrowHoverLineEdit(QLineEdit):
    """Обычный QLineEdit показывает I-образный курсор уже при простом
    наведении мыши, даже если поле неактивно. Здесь курсор остаётся
    стрелкой при наведении и меняется на I-образный только при реальном
    клике/вводе (фокусе)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.ArrowCursor)

    def enterEvent(self, event):
        if not self.hasFocus():
            self.setCursor(Qt.ArrowCursor)
        super().enterEvent(event)

    def mousePressEvent(self, event):
        self.setCursor(Qt.IBeamCursor)
        super().mousePressEvent(event)

    def focusInEvent(self, event):
        self.setCursor(Qt.IBeamCursor)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.setCursor(Qt.ArrowCursor)
        super().focusOutEvent(event)


class _GlowFrame(QFrame):
    """Графитовая панель с фирменным бирюзовым свечением по всем четырём
    сторонам - яркое по центру каждой стороны, гаснущее к углам. Основа
    (градиентный фон, скругление) рисуется через обычный QSS (QFrame
    поддерживает это нативно), свечение - поверх, вручную через
    QPainter (в QSS такого эффекта нет). Тень добавляется отдельным
    QGraphicsDropShadowEffect с нулевым смещением - равномерно со всех
    сторон, а не в одну сторону."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("filtersPanel")
        self.setStyleSheet(styles.LEFT_PANEL_FILTER_PANEL_STYLE)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(styles.LEFT_PANEL_GLOW_SHADOW_BLUR)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r, g, b = styles.LEFT_PANEL_GLOW_COLOR
        t = styles.LEFT_PANEL_GLOW_THICKNESS

        grad_h = QLinearGradient(0, 0, w, 0)
        grad_h.setColorAt(0.0, QColor(r, g, b, 0))
        grad_h.setColorAt(0.5, QColor(r, g, b, 230))
        grad_h.setColorAt(1.0, QColor(r, g, b, 0))
        painter.fillRect(QRectF(0, 0, w, t), grad_h)
        painter.fillRect(QRectF(0, h - t, w, t), grad_h)

        grad_v = QLinearGradient(0, 0, 0, h)
        grad_v.setColorAt(0.0, QColor(r, g, b, 0))
        grad_v.setColorAt(0.5, QColor(r, g, b, 230))
        grad_v.setColorAt(1.0, QColor(r, g, b, 0))
        painter.fillRect(QRectF(0, 0, t, h), grad_v)
        painter.fillRect(QRectF(w - t, 0, t, h), grad_v)


class _NoSelectionPaintDelegate(QStyledItemDelegate):
    """Обычно Qt при отрисовке выделенной ячейки полностью игнорирует её
    собственный фон (Qt::BackgroundRole) и вместо этого рисует заливку
    состояния ":selected" (даже если в QSS она задана как transparent -
    это всё равно перекрывает то, что мы красим через setBackground()).
    Этот делегат перед отрисовкой снимает флаг "выделено" у копии опций -
    ячейка визуально рисуется как обычная, со своим настоящим фоном,
    а выделение как таковое (сигналы, модель) продолжает работать штатно."""
    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.state &= ~QStyle.State_Selected
        opt.state &= ~QStyle.State_HasFocus
        super().paint(painter, opt, index)


class _RowHighlightOverlay(QWidget):
    """Полупрозрачная подсветка поверх строки таблицы. В отличие от ячеек
    QTableWidget, это настоящий QWidget с настоящим Qt-свойством - поэтому
    его цвет можно по-настоящему плавно анимировать через
    QPropertyAnimation (аппаратно поддерживаемая Qt анимация), без ручной
    покадровой интерполяции и без конфликтов с отрисовкой выделения."""
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._color = QColor(0, 0, 0, 0)
        self.hide()

    def _get_color(self):
        return self._color

    def _set_color(self, color):
        self._color = color
        self.update()

    color = pyqtProperty(QColor, _get_color, _set_color)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self._color)


class LeftPanel(QWidget):
    pump_selected = pyqtSignal(dict)
    pump_status_selected = pyqtSignal(dict)
    group_selected = pyqtSignal(list)
    request_import = pyqtSignal()
    request_add = pyqtSignal()
    request_delete = pyqtSignal(int)
    request_edit = pyqtSignal(int)
    filters_applied = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.compact_mode = True
        self.current_page = 0
        self.page_size = 20  # начальное значение, пересчитывается под размер окна
        self.total_records = 0
        self.current_filters = {}
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._on_resize_settled)
        self.setup_ui()
        self.load_data()

    def _make_filter_chip(self, label_text, control_widget):
        """Небольшая полупрозрачная "плашка", объединяющая подпись
        фильтра и её виджет в одну визуальную группу - вместо разбросанных
        по всей панели label+widget с большим отступом между ними."""
        chip = QFrame()
        chip.setStyleSheet(styles.LEFT_PANEL_CHIP_STYLE)
        chip_layout = QHBoxLayout(chip)
        chip_layout.setContentsMargins(8, 0, 8, 0)
        chip_layout.setSpacing(6)
        label = QLabel(label_text)
        label.setStyleSheet(styles.LEFT_PANEL_FILTER_LABEL_STYLE)
        chip_layout.addWidget(label)
        chip_layout.addWidget(control_widget)
        return chip

    def _build_filters_body(self, expanded):
        """Строит тело фильтров (без строки поиска) - в компактном режиме
        грид в 2 строки, в расширенном - всё в одну строку (больше места
        по ширине). Сами контролы (комбобоксы, чекбокс, кнопка) не
        создаются заново - переиспользуются, только перекладываются в
        новые чипы-обёртки."""
        if expanded:
            body = QHBoxLayout()
            body.setSpacing(14)
            body.addWidget(self._make_filter_chip("Вердикт:", self.filter_verdict))
            body.addWidget(self._make_filter_chip("Тип проверки:", self.filter_test_type))
            body.addWidget(self._make_filter_chip("Герметичность:", self.filter_sealed))
            body.addWidget(self._make_filter_chip("Заказ №:", self.filter_order))
            body.addWidget(self._make_filter_chip("С:", self.date_from))
            body.addWidget(self._make_filter_chip("По:", self.date_to))
            body.addWidget(self.only_duplicates)
            body.addWidget(self.btn_reset_filters)
            body.addStretch()
        else:
            body = QGridLayout()
            body.setHorizontalSpacing(14)
            body.setVerticalSpacing(8)
            body.addWidget(self._make_filter_chip("Вердикт:", self.filter_verdict), 0, 0)
            body.addWidget(self._make_filter_chip("Тип проверки:", self.filter_test_type), 0, 1)
            body.addWidget(self._make_filter_chip("Герметичность:", self.filter_sealed), 0, 2)
            body.addWidget(self.only_duplicates, 0, 3)
            body.addWidget(self._make_filter_chip("С:", self.date_from), 1, 0)
            body.addWidget(self._make_filter_chip("По:", self.date_to), 1, 1)
            body.addWidget(self._make_filter_chip("Заказ №:", self.filter_order), 1, 2)
            body.addWidget(self.btn_reset_filters, 1, 3)
            body.setColumnStretch(4, 1)
        return body

    def _detach_filter_controls(self):
        """Отсоединяет контролы фильтров от их текущих чипов-обёрток, НЕ
        уничтожая сами контролы - перед удалением старых чипов, чтобы
        контролы (self.filter_verdict и т.д.) пережили перестроение."""
        for w in (self.filter_verdict, self.filter_test_type, self.filter_sealed,
                  self.filter_order, self.date_from, self.date_to,
                  self.only_duplicates, self.btn_reset_filters):
            w.setParent(None)

    def _clear_layout_and_delete(self, layout):
        """Рекурсивно удаляет все элементы layout (виджеты и вложенные
        layout) - используется для сноса старых чипов при перестроении.
        Вызывать ПОСЛЕ _detach_filter_controls(), иначе вместе с чипами
        удалятся и сами контролы фильтров."""
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                self._clear_layout_and_delete(item.layout())
                item.layout().deleteLater()

    def _reflow_filters(self, expanded):
        """Перестраивает раскладку фильтров под текущий режим просмотра -
        грид в 2 строки (компактный) или всё в одну строку (расширенный,
        больше места по ширине). Вызывается из toggle_view()."""
        self._detach_filter_controls()
        self._clear_layout_and_delete(self.filters_grid)
        self.filters_layout.removeItem(self.filters_grid)
        self.filters_grid.deleteLater()

        self.filters_grid = self._build_filters_body(expanded)
        self.filters_layout.addLayout(self.filters_grid)

    def setup_ui(self):
      layout = QVBoxLayout(self)
      layout.setSpacing(6)
      layout.setContentsMargins(4, 4, 4, 4)

      # Вся панель фильтров - в одной графитовой "карточке" с бирюзовым
      # свечением по всем четырём сторонам (см. класс _GlowFrame)
      filters_panel = _GlowFrame()
      filters_layout = QVBoxLayout(filters_panel)
      filters_layout.setContentsMargins(14, 12, 14, 12)
      filters_layout.setSpacing(8)

      # Ряд 1: Поиск
      search_layout = QHBoxLayout()
      search_layout.setSpacing(10)
      search_label = QLabel("Поиск:")
      search_label.setStyleSheet(styles.LEFT_PANEL_SEARCH_LABEL_STYLE)
      search_label.setFixedWidth(50)
      self.search_input = _ArrowHoverLineEdit()
      self.search_input.setObjectName("searchInput")
      self.search_input.setPlaceholderText("Введите номер насоса...")
      self.search_input.setFixedHeight(34)
      self.search_input.setStyleSheet(styles.LEFT_PANEL_SEARCH_INPUT_STYLE)
      self.search_input.textChanged.connect(self.apply_filters)
      search_layout.addWidget(search_label)
      search_layout.addWidget(self.search_input)
      filters_layout.addLayout(search_layout)

      # Создаём сами виджеты фильтров (раскладка - ниже, через грид)
      self.filter_verdict = QComboBox()
      self.filter_verdict.addItems(["Все", "Годен", "Не годен"])
      self.filter_verdict.currentTextChanged.connect(self.apply_filters)
      self.filter_verdict.setStyleSheet(styles.LEFT_PANEL_COMBO_STYLE)

      self.filter_test_type = QComboBox()
      self.filter_test_type.addItems(["Все", "Первичная", "Повторная"])
      self.filter_test_type.currentTextChanged.connect(self.apply_filters)
      self.filter_test_type.setStyleSheet(styles.LEFT_PANEL_COMBO_STYLE)

      self.filter_sealed = QComboBox()
      self.filter_sealed.addItems(["Все", "Герметичен", "Не герметичен"])
      self.filter_sealed.currentTextChanged.connect(self.apply_filters)
      self.filter_sealed.setStyleSheet(styles.LEFT_PANEL_COMBO_STYLE)

      self.filter_order = QComboBox()
      self.filter_order.addItem("Все заказы")
      self.filter_order.currentTextChanged.connect(self.apply_filters)
      self.filter_order.setStyleSheet(styles.LEFT_PANEL_COMBO_STYLE)

      self.date_from = QDateEdit()
      self.date_from.setCalendarPopup(True)
      self.date_from.setDate(QDate(2000, 1, 1))
      self.date_from.dateChanged.connect(self.apply_filters)
      self.date_from.setStyleSheet(styles.LEFT_PANEL_COMBO_STYLE)
      self.date_from.setMinimumWidth(115)  # шире, симметрично с Вердикт/Тип проверки сверху
      self.date_from.calendarWidget().setStyleSheet(styles.LEFT_PANEL_CALENDAR_STYLE)

      self.date_to = QDateEdit()
      self.date_to.setCalendarPopup(True)
      self.date_to.setDate(QDate.currentDate())
      self.date_to.dateChanged.connect(self.apply_filters)
      self.date_to.setStyleSheet(styles.LEFT_PANEL_COMBO_STYLE)
      self.date_to.setMinimumWidth(115)
      self.date_to.calendarWidget().setStyleSheet(styles.LEFT_PANEL_CALENDAR_STYLE)

      self.only_duplicates = QCheckBox("Дубли")
      self.only_duplicates.setStyleSheet(styles.LEFT_PANEL_CHECKBOX_STYLE)
      self.only_duplicates.stateChanged.connect(self.apply_filters)

      self.btn_reset_filters = QPushButton("Сбросить фильтры")
      self.btn_reset_filters.setObjectName("chromeButton")
      self.btn_reset_filters.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
      self.btn_reset_filters.clicked.connect(self.reset_filters)

      # Грид: Вердикт/Тип проверки/Герметичность/Дубли сверху, Заказ № - под
      # Герметичностью (тот же столбец, та же ширина), Сброс - под Дубли
      # (тот же столбец). Пустой растянутый столбец справа поглощает
      # лишнюю ширину при увеличении окна - сами фильтры при этом
      # остаются компактно слева, не расползаются
      self.filters_grid = QGridLayout()
      self.filters_grid.setHorizontalSpacing(14)
      self.filters_grid.setVerticalSpacing(8)

      # Одинаковая ширина у Герметичность/Заказ № - чтобы смотрелись
      # симметрично друг под другом
      self.filter_sealed.setMinimumWidth(130)
      self.filter_order.setMinimumWidth(130)

      self.filters_grid.addWidget(self._make_filter_chip("Вердикт:", self.filter_verdict), 0, 0)
      self.filters_grid.addWidget(self._make_filter_chip("Тип проверки:", self.filter_test_type), 0, 1)
      self.filters_grid.addWidget(self._make_filter_chip("Герметичность:", self.filter_sealed), 0, 2)
      self.filters_grid.addWidget(self.only_duplicates, 0, 3)

      self.filters_grid.addWidget(self._make_filter_chip("С:", self.date_from), 1, 0)
      self.filters_grid.addWidget(self._make_filter_chip("По:", self.date_to), 1, 1)
      self.filters_grid.addWidget(self._make_filter_chip("Заказ №:", self.filter_order), 1, 2)
      self.filters_grid.addWidget(self.btn_reset_filters, 1, 3)

      self.filters_grid.setColumnStretch(4, 1)  # пустой "хвостовой" столбец - забирает лишнюю ширину
      filters_layout.addLayout(self.filters_grid)
      self.filters_layout = filters_layout  # нужна для перестроения при переключении вида (см. _reflow_filters)

      layout.addWidget(filters_panel)

      # Статистика по заказу (скрыта по умолчанию)
      self.stats_label = QLabel()
      self.stats_label.setWordWrap(True)
      self.stats_label.setStyleSheet(styles.LEFT_PANEL_STATS_LABEL_STYLE)
      self.stats_label.hide()
      layout.addWidget(self.stats_label)

      # Таблица
      self.table = QTableWidget()
      self.table.setStyleSheet(styles.LEFT_PANEL_TABLE_STYLE)
      # Отключаем штатную заливку выделения Qt - иначе она перекрывает наш
      # собственный (анимированный) цвет ячейки, даже если в QSS задать
      # ":selected { background-color: transparent }"
      self.table.setItemDelegate(_NoSelectionPaintDelegate(self.table))
      # Жирные заголовки
      font = self.table.horizontalHeader().font()
      font.setBold(True)
      self.table.horizontalHeader().setFont(font)

      self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
      self.table.setSelectionMode(QAbstractItemView.SingleSelection)
      self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
      self.table.verticalHeader().setVisible(False)
      self.table.setSortingEnabled(True)
      self.table.itemSelectionChanged.connect(self.on_selection_changed)
      self.table.setContextMenuPolicy(Qt.CustomContextMenu)
      self.table.customContextMenuRequested.connect(self.show_context_menu)
      self.table.cellClicked.connect(self.on_cell_clicked)

      # Эффект наведения/выделения строки - через два независимых
      # полупрозрачных оверлея поверх таблицы (см. _RowHighlightOverlay),
      # с настоящей QPropertyAnimation. Сама таблица и её ячейки при этом
      # не трогаются - оверлеи просто рисуются поверх.
      self._hovered_row = -1
      self._selected_row = -1
      self._base_font_size = float(self.table.font().pointSize() or 9)
      self._hover_overlay = _RowHighlightOverlay(self.table.viewport())
      self._selection_overlay = _RowHighlightOverlay(self.table.viewport())
      self._hover_anim = None
      self._selection_anim = None
      self.table.setMouseTracking(True)
      self.table.entered.connect(self.on_row_hover)
      self.table.viewport().installEventFilter(self)

      layout.addWidget(self.table)

      # Центрирование таблицы в левой панели
      self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

      # Нижний блок (кнопки управления + пагинация) - в такой же
      # графитовой панели со свечением, как и фильтры сверху
      bottom_panel = _GlowFrame()
      bottom_layout = QVBoxLayout(bottom_panel)
      bottom_layout.setContentsMargins(14, 10, 14, 10)
      bottom_layout.setSpacing(8)

      # Кнопки управления
      btn_layout = QHBoxLayout()
      btn_layout.setSpacing(8)
      self.btn_add = QPushButton("Добавить насос")
      self.btn_add.setObjectName("chromeButton")
      self.btn_add.setFixedHeight(26)
      self.btn_add.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
      self.btn_add.clicked.connect(self.request_add.emit)
      self.btn_delete = QPushButton("Удалить запись")
      self.btn_delete.setObjectName("chromeButton")
      self.btn_delete.setFixedHeight(26)
      self.btn_delete.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
      self.btn_delete.clicked.connect(self.on_delete_clicked)
      self.btn_import = QPushButton("Импорт Excel")
      self.btn_import.setObjectName("chromeButton")
      self.btn_import.setFixedHeight(26)
      self.btn_import.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
      self.btn_import.clicked.connect(self.request_import.emit)
      self.btn_view_toggle = QPushButton("Расширить")
      self.btn_view_toggle.setObjectName("chromeButton")
      self.btn_view_toggle.setFixedHeight(26)
      self.btn_view_toggle.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
      self.btn_view_toggle.setCheckable(True)
      self.btn_view_toggle.toggled.connect(self.toggle_view)

      btn_layout.addWidget(self.btn_add)
      btn_layout.addWidget(self.btn_delete)
      btn_layout.addWidget(self.btn_import)
      btn_layout.addWidget(self.btn_view_toggle)
      bottom_layout.addLayout(btn_layout)

      # Легенда
      # self.legend_label = QLabel()
      # self.legend_label.setWordWrap(True)
      # self.legend_label.setStyleSheet("background-color: #f9f9f9; border: 1px solid #ddd; padding: 2px; font-size: 9px;")
      # self.update_legend()
      # layout.addWidget(self.legend_label)

      # Пагинация
      pagination_layout = QHBoxLayout()
      pagination_layout.setSpacing(6)
      self.btn_prev = QPushButton("◀")
      self.btn_prev.setObjectName("chromeButton")
      self.btn_prev.setFixedSize(30, 22)
      self.btn_prev.setStyleSheet(styles.LEFT_PANEL_PAGINATION_BTN_STYLE)
      self.btn_prev.clicked.connect(self.prev_page)
      self.btn_next = QPushButton("▶")
      self.btn_next.setObjectName("chromeButton")
      self.btn_next.setFixedSize(30, 22)
      self.btn_next.setStyleSheet(styles.LEFT_PANEL_PAGINATION_BTN_STYLE)
      self.btn_next.clicked.connect(self.next_page)
      self.page_label = QLabel("1/1")
      self.page_label.setAlignment(Qt.AlignCenter)
      self.page_label.setStyleSheet(styles.LEFT_PANEL_FILTER_LABEL_STYLE)
      # Пояснение "Группировка по дублям" - по центру панели, между
      # пагинацией и счётчиком записей. Пусто и скрыто, пока фильтр
      # "Дубли" не включён (см. update_pagination_label)
      self.duplicates_note_label = QLabel("")
      self.duplicates_note_label.setAlignment(Qt.AlignCenter)
      self.duplicates_note_label.setStyleSheet(styles.LEFT_PANEL_FILTER_LABEL_STYLE)
      self.count_label = QLabel("Показано записей: 0")
      self.count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
      self.count_label.setStyleSheet(styles.LEFT_PANEL_FILTER_LABEL_STYLE)
      pagination_layout.addWidget(self.btn_prev)
      pagination_layout.addWidget(self.page_label)
      pagination_layout.addWidget(self.btn_next)
      pagination_layout.addStretch()
      pagination_layout.addWidget(self.duplicates_note_label)
      pagination_layout.addStretch()
      pagination_layout.addWidget(self.count_label)
      bottom_layout.addLayout(pagination_layout)

      layout.addWidget(bottom_panel)

    # def update_legend(self):
    #     legend_text = (
    #         "Легенда: "
    #         "<span style='color:green;'>●</span> годен  "
    #         "<span style='color:red;'>●</span> не годен  "
    #         "<span style='color:blue;'>●</span> герметичен  "
    #         "<span style='color:gray;'>●</span> не герметичен  "
    #         "I — первичная  II — повторная"
    #     )
    #     self.legend_label.setText(legend_text)

    def toggle_view(self, checked):
        """Переключает компактный/расширенный режим списка."""
        parent = self.parent()
        while parent and not hasattr(parent, 'splitter'):
            parent = parent.parent()
        if not parent or not hasattr(parent, 'splitter'):
            return

        if checked:
            # Расширенный режим
            self.compact_mode = False
            self.btn_view_toggle.setText("Свернуть список")
            self._reflow_filters(expanded=True)
            # # Левая 100%, правая 0 (скрываем)
            parent.splitter.setSizes([parent.width(), 0])
            
            # Левая 85%, правая 15% (почти скрыта)
            # parent.splitter.setSizes([int(parent.width() * 0.85), int(parent.width() * 0.15)])
            # self.legend_label.hide()
        else:
            # Компактный режим (минимальный)
            self.compact_mode = True
            self.btn_view_toggle.setText("Расширенный вид")
            self._reflow_filters(expanded=False)
            # Левая 20%, правая 80%
            parent.splitter.setSizes([int(parent.width() * 0.10), int(parent.width() * 0.9)])
            
            # Левая 15%, правая 85%
            # parent.splitter.setSizes([int(parent.width() * 0.15), int(parent.width() * 0.85)])
            # self.legend_label.show()
        self.apply_filters()
        self.table.clearSelection()

    def _setup_table_columns(self, compact=True):
        """Настраивает количество и заголовки колонок таблицы."""
        font = self.table.horizontalHeader().font()
        font.setBold(True)
        self.table.horizontalHeader().setFont(font)

        if compact:
            col_count = 5
            self.table.setColumnCount(col_count)
            self.table.setHorizontalHeaderLabels(["Номер", "Дата", "Вердикт", "Тип", "Герметичность"])
            for col in range(5, self.table.columnCount()):
                self.table.setColumnHidden(col, True)
            self.table.verticalHeader().setVisible(False)
            self.table.setColumnWidth(0, 80)
            self.table.setColumnWidth(1, 100)
            self.table.setColumnWidth(2, 100)
            self.table.setColumnWidth(3, 100)
            self.table.setColumnWidth(4, 100)
        else:
            col_count = 7
            self.table.setColumnCount(col_count)
            self.table.setHorizontalHeaderLabels(
                ["Номер", "Дата", "Модификация", "Герметичность", "Тип", "Заказ", "Вердикт"]
            )
            for col in range(self.table.columnCount()):
                self.table.setColumnHidden(col, False)
            self.table.verticalHeader().setVisible(False)
            self.table.setColumnWidth(0, 110)
            self.table.setColumnWidth(1, 110)
            self.table.setColumnWidth(2, 150)
            self.table.setColumnWidth(3, 110)
            self.table.setColumnWidth(4, 100)
            self.table.setColumnWidth(5, 100)
            self.table.setColumnWidth(6, 250)
        return col_count

    def _fill_pump_row(self, row, p, compact=True):
        """Заполняет одну строку таблицы данными насоса p."""
        # ---- Номер ----
        item_num = QTableWidgetItem(p['pump_number'])
        item_num.setData(Qt.UserRole, p['id'])
        item_num.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 0, item_num)

        # ---- Дата ----
        date_str = p['test_date']
        if date_str and ' ' in date_str:
            date_str = date_str.split(' ')[0]
        item_date = QTableWidgetItem(date_str)
        item_date.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 1, item_date)

        if compact:
            # ---- Вердикт ----
            verdict_text = p['verdict'] if p['verdict'] else '—'
            item_verdict = QTableWidgetItem(verdict_text)
            item_verdict.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, item_verdict)

            # ---- Тип ----
            type_text = p['test_type'] if p['test_type'] else '—'
            item_type = QTableWidgetItem(type_text)
            item_type.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, item_type)

            # ---- Герметичность ----
            sealed_text = 'Герметичен' if p['is_sealed'] else 'Негерметичен'
            item_sealed = QTableWidgetItem(sealed_text)
            item_sealed.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, item_sealed)

        else:
            # ---- Модификация ----
            mod_name = p.get('mod_name', '—')
            item_mod = QTableWidgetItem(mod_name if mod_name else '—')
            item_mod.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, item_mod)

            # ---- Герметичность (текст) ----
            sealed_text = 'Герметичен' if p['is_sealed'] else 'Негерметичен'
            item_sealed = QTableWidgetItem(sealed_text)
            item_sealed.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, item_sealed)

            # ---- Тип ----
            type_text = p['test_type'] if p['test_type'] else '—'
            item_type = QTableWidgetItem(type_text)
            item_type.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, item_type)

            # ---- Заказ ----
            order_num = p.get('order_number', '—')
            order_str = str(order_num).replace('.0', '') if order_num and order_num != '—' else '—'
            item_order = QTableWidgetItem(order_str)
            item_order.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, item_order)

            # ---- Вердикт ----
            verdict_text = p['verdict'] if p['verdict'] else '—'
            item_verdict = QTableWidgetItem(verdict_text)
            item_verdict.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 6, item_verdict)

        # ---- Подсветка всей строки по вердикту ----
        if p['verdict'] == 'годен':
            bg_color = QColor(232, 253, 232)
        elif p['verdict'] == 'не годен':
            bg_color = QColor(245, 230, 230)
        else:
            bg_color = None
        base_font = QFont()
        base_font.setPointSizeF(self._base_font_size)
        base_font.setWeight(QFont.Normal)
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                if bg_color:
                    item.setBackground(bg_color)
                item.setFont(base_font)

    def populate_table(self, pumps, compact=True):
        self.table.setSortingEnabled(False)
        self.table.clearSpans()  # сбрасываем объединения ячеек, оставшиеся от группового режима (дубли)
        self.table.setRowCount(len(pumps))
        self._hovered_row = -1
        self._selected_row = -1
        self._hover_overlay.hide()
        self._selection_overlay.hide()

        col_count = self._setup_table_columns(compact)

        for row, p in enumerate(pumps):
            self._fill_pump_row(row, p, compact)

        self.table.setSortingEnabled(True)
        if compact:
            self.table.sortByColumn(1, Qt.DescendingOrder)
        else:
            self.table.sortByColumn(0, Qt.AscendingOrder)

    def populate_table_grouped(self, pumps, compact=True):
        """Отображает насосы, сгруппированные по номеру + модификации (для
        фильтра 'Дубли'): строка-заголовок 'Образец № X — N шт.', а под ней
        сами протоколы, отсортированные по дате (сначала новые). Если у
        насоса с одинаковым номером разные модификации - это разные группы,
        а не дубликаты."""
        self.table.setSortingEnabled(False)
        self.table.clearSpans()
        self._hovered_row = -1
        self._selected_row = -1
        self._hover_overlay.hide()
        self._selection_overlay.hide()

        # Группируем по (номер насоса, модификация)
        groups = {}
        for p in pumps:
            key = (p['pump_number'], p.get('mod_name'))
            groups.setdefault(key, []).append(p)

        # Сортируем группы: сначала по убыванию количества найденных протоколов,
        # при равном количестве - по номеру насоса
        sorted_groups = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0][0]))

        # Внутри группы - сортировка протоколов по дате (сначала новые)
        for _, items in sorted_groups:
            items.sort(key=lambda p: p['test_date'] or '', reverse=True)

        col_count = self._setup_table_columns(compact)

        total_rows = sum(1 + len(items) for _, items in sorted_groups)
        self.table.setRowCount(total_rows)

        row = 0
        for (pump_number, mod_name), items in sorted_groups:
            # ---- Строка-заголовок группы ----
            header_text = f"Образец № {pump_number} — {len(items)} шт."
            header_item = QTableWidgetItem(header_text)
            header_item.setTextAlignment(Qt.AlignCenter)
            header_item.setFlags(Qt.ItemIsEnabled)  # не выделяется и не открывается как протокол
            header_font = QFont()
            header_font.setBold(True)
            header_item.setFont(header_font)
            header_item.setBackground(QColor(210, 224, 240))
            # Сохраняем сами дублирующиеся протоколы на заголовке -
            # понадобится, чтобы по клику показать сравнение (пункт 5)
            header_item.setData(Qt.UserRole + 1, items)
            self.table.setItem(row, 0, header_item)
            self.table.setSpan(row, 0, 1, col_count)
            row += 1

            for p in items:
                self._fill_pump_row(row, p, compact)
                row += 1

        # Сортировка кликом по заголовку в режиме дублей отключена,
        # т.к. порядок строк задан группировкой
        self.table.setSortingEnabled(False)


    def display_pumps(self, pumps, group_by_number=False):
        if group_by_number:
            self.populate_table_grouped(pumps, compact=self.compact_mode)
        else:
            self.populate_table(pumps, compact=self.compact_mode)

    # Методы создания иконок
    # def create_verdict_icon(self, is_good):
    #     pixmap = QPixmap(24, 24)
    #     pixmap.fill(Qt.transparent)
    #     painter = QPainter(pixmap)
    #     painter.setBrush(QColor(0, 200, 0) if is_good else QColor(200, 0, 0))
    #     painter.setPen(Qt.NoPen)
    #     painter.drawEllipse(6, 6, 12, 12)
    #     painter.end()
    #     return QIcon(pixmap)

    # def create_type_icon(self, type_str):
    #     pixmap = QPixmap(24, 24)
    #     pixmap.fill(Qt.transparent)
    #     painter = QPainter(pixmap)
    #     painter.setPen(QColor(0, 0, 200))
    #     painter.setFont(QFont("Arial", 10, QFont.Bold))
    #     painter.drawText(pixmap.rect(), Qt.AlignCenter, "I" if "первичная" in str(type_str).lower() else "II")
    #     painter.end()
    #     return QIcon(pixmap)

    # def create_sealed_icon(self, is_sealed):
    #     pixmap = QPixmap(24, 24)
    #     pixmap.fill(Qt.transparent)
    #     painter = QPainter(pixmap)
    #     painter.setBrush(QColor(0, 100, 255) if is_sealed else QColor(180, 180, 180))
    #     painter.setPen(Qt.NoPen)
    #     painter.drawEllipse(6, 9, 12, 9)
    #     points = [QPoint(6, 9), QPoint(12, 3), QPoint(18, 9)]
    #     polygon = QPolygon(points)
    #     painter.drawPolygon(polygon)
    #     painter.end()
    #     return QIcon(pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_timer.start(200)
        # Оверлеи привязаны к ширине viewport - если их сейчас видно,
        # подгоняем геометрию под новый размер
        if self._hovered_row != -1:
            rect = self._row_rect(self._hovered_row)
            if rect:
                self._hover_overlay.setGeometry(rect)
        if self._selected_row != -1:
            rect = self._row_rect(self._selected_row)
            if rect:
                self._selection_overlay.setGeometry(rect)

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, '_initial_size_done', False):
            self._initial_size_done = True
            QTimer.singleShot(0, self._on_resize_settled)

    def _compute_dynamic_page_size(self):
        """Считает, сколько строк реально помещается в видимую область
        таблицы сейчас. viewport().height() уже НЕ включает область
        заголовка колонок - вычитать её ещё раз не нужно (это и было
        причиной заниженного расчёта)."""
        row_height = self.table.verticalHeader().defaultSectionSize() or 24
        available = self.table.viewport().height()
        return max(5, available // row_height)

    def _on_resize_settled(self):
        if self.only_duplicates.isChecked():
            return  # в режиме дублей пагинация отключена - не трогаем
        new_page_size = self._compute_dynamic_page_size()
        if new_page_size != self.page_size:
            self.page_size = new_page_size
            self.current_page = 0
            self.apply_filters()

    def on_cell_clicked(self, row, col):
        """Клик по заголовку группы дублей открывает сравнение в правой панели.
        Для обычных строк отдельного эффекта не нужно - выделение само по
        себе (см. on_selection_changed) уже даёт мгновенную яркую реакцию
        на клик; отдельная "вспышка" здесь только маскировала её и
        создавала впечатление задержки."""
        item = self.table.item(row, 0)
        if item is None:
            return
        group_items = item.data(Qt.UserRole + 1)
        if group_items:
            self.group_selected.emit(group_items)

    def _row_is_group_header(self, row):
        item0 = self.table.item(row, 0)
        return bool(item0 and item0.data(Qt.UserRole + 1))

    def _row_items(self, row):
        if row < 0 or row >= self.table.rowCount() or self._row_is_group_header(row):
            return []
        return [it for it in (self.table.item(row, c) for c in range(self.table.columnCount())) if it]

    def _row_rect(self, row):
        """Прямоугольник строки во viewport-координатах, во всю ширину -
        именно сюда позиционируется оверлей подсветки."""
        if row < 0 or row >= self.table.rowCount():
            return None
        top = self.table.rowViewportPosition(row)
        height = self.table.rowHeight(row)
        width = self.table.viewport().width()
        if height <= 0:
            return None
        return QRect(0, top, width, height)

    def _vivid(self, color):
        """Яркая, насыщенная версия цвета строки (для выделения) - тот же
        оттенок, что и обычная подсветка по вердикту, но гораздо
        насыщеннее, с прозрачностью (это оверлей поверх ячейки, а не
        замена её цвета). Для нейтральных строк - акцентный синий."""
        h, s, v, _ = color.getHsv()
        if h < 0 or s < 12:
            c = QColor(120, 165, 235)
        else:
            c = QColor()
            c.setHsv(h, 200, 230)
        c.setAlpha(150)
        return c

    def _vivid_text(self, color):
        """Цвет текста для выделенной строки - почти чёрный (не зависит
        от оттенка строки), для чёткого контраста поверх яркого оверлея."""
        return QColor(15, 15, 15)

    def _refresh_row_font(self, row):
        """Жирность/размер шрифта и цвет текста строки - мгновенно, по
        текущему состоянию (наведена и/или выделена ли она сейчас)."""
        if row < 0 or self._row_is_group_header(row):
            return
        emphasize = (row == self._hovered_row or row == self._selected_row)
        items = self._row_items(row)
        if row == self._selected_row:
            item0 = self.table.item(row, 0)
            base = item0.background().color() if item0 else QColor(255, 255, 255)
            text_color = self._vivid_text(base)
        else:
            text_color = QColor(0, 0, 0)
        for item in items:
            f = item.font()
            f.setBold(emphasize)
            f.setPointSizeF(self._base_font_size + (1 if emphasize else 0))
            item.setFont(f)
            item.setForeground(text_color)

    def _start_overlay_animation(self, overlay, anim_attr, target_color, duration):
        """Плавно (по-настоящему, через QPropertyAnimation) меняет цвет
        оверлея. Останавливает предыдущую анимацию этого же оверлея, если
        она ещё идёт."""
        old = getattr(self, anim_attr, None)
        if old is not None:
            old.stop()
        anim = QPropertyAnimation(overlay, b"color", self.table)
        anim.setDuration(duration)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.setStartValue(overlay.color)
        anim.setEndValue(target_color)
        setattr(self, anim_attr, anim)
        anim.start()

    def _set_overlay_instant(self, overlay, anim_attr, color):
        """Мгновенно (без анимации) задаёт цвет оверлея - останавливает
        текущую анимацию этого оверлея, если она идёт. Перерисовывает
        СРАЗУ (repaint, а не отложенный update) - иначе Qt откладывает
        реальную отрисовку до конца текущего обработчика события, и цвет
        визуально появится только после (возможно медленной) остальной
        части клика - запроса к БД и перестроения правой панели."""
        old = getattr(self, anim_attr, None)
        if old is not None:
            old.stop()
            setattr(self, anim_attr, None)
        overlay.color = color
        overlay.repaint()

    def on_row_hover(self, index):
        """Наведение мыши на строку - полупрозрачный белый оверлей плавно
        проявляется поверх строки (осветление на ~50% за счёт alpha),
        текст мгновенно становится жирным и чуть крупнее."""
        row = index.row()
        if self._row_is_group_header(row):
            row = -1
        if row == self._hovered_row:
            return
        old_hover = self._hovered_row
        self._hovered_row = row
        if old_hover != -1:
            self._start_overlay_animation(self._hover_overlay, '_hover_anim',
                                          QColor(255, 255, 255, 0), 350)
            self._refresh_row_font(old_hover)
        if row != -1:
            rect = self._row_rect(row)
            if rect:
                self._hover_overlay.setGeometry(rect)
                self._hover_overlay.show()
                self._hover_overlay.raise_()
            self._start_overlay_animation(self._hover_overlay, '_hover_anim',
                                          QColor(255, 255, 255, 128), 350)
            self._refresh_row_font(row)

    def eventFilter(self, obj, event):
        if obj is self.table.viewport():
            if event.type() == QEvent.Leave:
                if self._hovered_row != -1:
                    old_hover = self._hovered_row
                    self._hovered_row = -1
                    self._start_overlay_animation(self._hover_overlay, '_hover_anim',
                                                  QColor(255, 255, 255, 0), 350)
                    self._refresh_row_font(old_hover)
            elif event.type() == QEvent.MouseMove:
                # Курсор мог уйти на пустое пространство под последней
                # строкой - там нет валидного индекса, и сигнал entered()
                # в этом случае не срабатывает вообще
                index = self.table.indexAt(event.pos())
                if not index.isValid() and self._hovered_row != -1:
                    old_hover = self._hovered_row
                    self._hovered_row = -1
                    self._start_overlay_animation(self._hover_overlay, '_hover_anim',
                                                  QColor(255, 255, 255, 0), 350)
                    self._refresh_row_font(old_hover)
        return super().eventFilter(obj, event)

    def on_selection_changed(self):
        """Обработка выбора строки. В компактном режиме открывает протокол
        (как раньше); в расширенном - только обновляет статус-бар, не
        переключая вид и не открывая протокол. Плюс - мгновенная (без
        анимации перехода) смена оверлея выделения на яркий цвет строки
        вместо стандартного синего."""
        selected = self.table.selectedItems()
        new_row = selected[0].row() if selected else -1

        if new_row != self._selected_row:
            old_selected = self._selected_row
            self._selected_row = new_row
            if old_selected != -1:
                self._set_overlay_instant(self._selection_overlay, '_selection_anim',
                                          QColor(0, 0, 0, 0))
                self._refresh_row_font(old_selected)
            if new_row != -1:
                rect = self._row_rect(new_row)
                if rect:
                    self._selection_overlay.setGeometry(rect)
                    self._selection_overlay.show()
                    self._selection_overlay.raise_()
                item0 = self.table.item(new_row, 0)
                base = item0.background().color() if item0 else QColor(255, 255, 255)
                self._set_overlay_instant(self._selection_overlay, '_selection_anim',
                                          self._vivid(base))
                self._refresh_row_font(new_row)

            # Принудительно сбрасываем очередь отрисовки ПРЯМО СЕЙЧАС - иначе
            # Qt отложит реальную покраску экрана до конца этого обработчика,
            # а он ещё пойдёт в БД и перестроит всю правую панель (таблицы,
            # графики matplotlib), из-за чего цвет визуально "запаздывал бы"
            self.table.viewport().repaint()
            QApplication.processEvents()

        if not selected:
            return
        row = new_row
        item = self.table.item(row, 0)
        if item is None:
            return
        pump_id = item.data(Qt.UserRole)
        if pump_id is None:
            return
        pump_data = db.get_pump_by_id(pump_id)
        if not pump_data:
            return
        if self.compact_mode:
            self.pump_selected.emit(pump_data)
        else:
            self.pump_status_selected.emit(pump_data)

    def show_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        item = self.table.item(row, 0)
        if not item:
            return
        pump_id = item.data(Qt.UserRole)
        if not pump_id:
            return

        menu = QMenu(self)
        action_view = menu.addAction("Показать протокол")
        action_edit = menu.addAction("Редактировать")
        action_delete = menu.addAction("Удалить")

        action = menu.exec_(self.table.mapToGlobal(pos))

        if action == action_view:
            # Сворачиваем расширенный вид, если он включён
            if not self.compact_mode:
                self.btn_view_toggle.setChecked(False)
            # Выбираем строку и отправляем сигнал
            self.table.selectRow(row)
            self.on_selection_changed()
        elif action == action_edit:
            self.request_edit.emit(pump_id)
        elif action == action_delete:
            self.request_delete.emit(pump_id)

    def on_delete_clicked(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        pump_id = self.table.item(row, 0).data(Qt.UserRole)
        if pump_id:
            self.request_delete.emit(pump_id)

    def load_data(self):
        self.all_pumps = db.get_all_pumps()
        orders = db.get_all_orders()  # возвращает список (id, order_number)
        self.order_map = {}  # словарь {id: отформатированный_номер}
        self.filter_order.blockSignals(True)
        self.filter_order.clear()
        self.filter_order.addItem("Все заказы")
        for oid, onum in orders:
            # Форматируем номер
            order_str = str(onum)
            if '.' in order_str:
                order_str = order_str.rstrip('0').rstrip('.')
            self.order_map[oid] = order_str
            self.filter_order.addItem(order_str, oid)
        self.filter_order.blockSignals(False)
        self.apply_filters()

    def apply_filters(self):
        filters = {}
        search_text = self.search_input.text().strip()
        if search_text:
            filters['pump_number'] = search_text

        verdict = self.filter_verdict.currentText()
        if verdict != 'Все':
            filters['verdict'] = verdict.lower()

        test_type = self.filter_test_type.currentText()
        if test_type != 'Все':
            filters['test_type'] = test_type.lower()

        sealed = self.filter_sealed.currentText()
        if sealed == 'Герметичен':
            filters['is_sealed'] = 1
        elif sealed == 'Не герметичен':
            filters['is_sealed'] = 0

        order_index = self.filter_order.currentIndex()
        if order_index > 0:  # 0 - "Все заказы"
            order_id = self.filter_order.itemData(order_index)
            filters['order_id'] = order_id

        date_from = self.date_from.date().toString('yyyy-MM-dd')
        date_to = self.date_to.date().toString('yyyy-MM-dd')
        if date_from != '2000-01-01' or date_to != QDate.currentDate().toString('yyyy-MM-dd'):
            filters['date_from'] = date_from
            filters['date_to'] = date_to

        if self.only_duplicates.isChecked():
            filters['only_duplicates'] = True

        self.current_filters = filters

        # Подсчёт общего количества
        self.total_records = db.count_pumps(filters)

        # Определяем группировку по номеру (только если включён фильтр дублей)
        group_by_number = self.only_duplicates.isChecked()

        if group_by_number:
            # В режиме дублей группы не должны разрываться постраничной разбивкой -
            # показываем все найденные записи целиком
            filtered = db.get_all_pumps(filters)
        else:
            # Подстраховка: пересчитываем размер страницы прямо сейчас (а не
            # только по событию resize) - гарантирует актуальное значение,
            # даже если окно ещё не успело прислать событие изменения размера
            fresh_page_size = self._compute_dynamic_page_size()
            if fresh_page_size != self.page_size:
                self.page_size = fresh_page_size
                self.current_page = 0
            offset = self.current_page * self.page_size
            filtered = db.get_all_pumps(filters, limit=self.page_size, offset=offset)

        self.display_pumps(filtered, group_by_number=group_by_number)
        self.update_stats(filtered)

        self.update_pagination_label()

        if hasattr(self, 'filters_applied'):
            self.filters_applied.emit(filters)

    def update_stats(self, filtered_pumps):
        if 'order_id' in self.current_filters and self.current_filters['order_id']:
            order_id = self.current_filters['order_id']
            order_str = self.order_map.get(order_id)
            if not order_str:
                self.stats_label.hide()
                return
            total = len(filtered_pumps)
            if total == 0:
                self.stats_label.setText(f"Для заказа №{order_str} нет данных с учётом текущих фильтров.")
                self.stats_label.show()
                return

            good = sum(1 for p in filtered_pumps if p.get('verdict') == 'годен')
            not_sealed = sum(1 for p in filtered_pumps if p.get('is_sealed') is False)
            good_first = sum(1 for p in filtered_pumps if p.get('verdict') == 'годен' and p.get('test_type') == 'первичная')

            good_percent = round(good / total * 100, 1)
            not_sealed_percent = round(not_sealed / total * 100, 1)
            good_first_percent = round(good_first / total * 100, 1)

            if self.compact_mode:
                # Компактный (узкий) режим - фраза "годных с первого
                # предъявления" явно переносится на отдельную строку,
                # иначе слова разрываются посередине при автопереносе
                text = (f"Для заказа №{order_str} проверено <b>{total}</b> насосов: "
                        f"годных — <b>{good}</b> ({good_percent}%), "
                        f"негерметичных — <b>{not_sealed}</b> ({not_sealed_percent}%)<br>"
                        f"годных с первого предъявления — <b>{good_first}</b> ({good_first_percent}%)")
            else:
                # Расширенный режим - места достаточно, вся статистика в
                # одну строку без принудительного переноса
                text = (f"Для заказа №{order_str} проверено <b>{total}</b> насосов: "
                        f"годных — <b>{good}</b> ({good_percent}%), "
                        f"негерметичных — <b>{not_sealed}</b> ({not_sealed_percent}%), "
                        f"годных с первого предъявления — <b>{good_first}</b> ({good_first_percent}%)")
            self.stats_label.setText(text)
            self.stats_label.show()
        else:
            self.stats_label.hide()

    def reset_filters(self):
        self.search_input.clear()
        self.filter_verdict.setCurrentIndex(0)
        self.filter_test_type.setCurrentIndex(0)
        self.filter_sealed.setCurrentIndex(0)
        self.filter_order.setCurrentIndex(0)
        self.date_from.setDate(QDate(2000, 1, 1))
        self.date_to.setDate(QDate.currentDate())
        self.only_duplicates.setChecked(False)
        self.current_page = 0
        self.apply_filters()

    def refresh(self):
        self.current_page = 0
        self.load_data()

    def next_page(self):
        if (self.current_page + 1) * self.page_size < self.total_records:
            self.current_page += 1
            self.apply_filters()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.apply_filters()

    def update_pagination_label(self):
        if self.only_duplicates.isChecked():
            # В режиме дублей показываются сразу все найденные группы,
            # постраничная разбивка не применяется - саму панель пагинации
            # не трогаем (просто отключаем кнопки), пояснение показываем
            # по центру, между пагинацией и счётчиком записей
            self.page_label.setText("Страница 1 из 1")
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)
            self.duplicates_note_label.setText("Группировка по дублям")
            self.count_label.setText(f"Показано записей: {self.total_records}")
            return

        self.duplicates_note_label.setText("")
        total_pages = max(1, (self.total_records + self.page_size - 1) // self.page_size)
        self.page_label.setText(f"Страница {self.current_page + 1} из {total_pages}")
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled((self.current_page + 1) * self.page_size < self.total_records)
        self.count_label.setText(f"Показано записей: {self.total_records}")