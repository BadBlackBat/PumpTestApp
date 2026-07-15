# from PyQt5.QtWidgets import (
#     QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
#     QTableWidget, QTableWidgetItem, QPushButton, QLabel, QCheckBox,
#     QDateEdit, QHeaderView, QAbstractItemView, QMenu
# )
# from PyQt5.QtCore import Qt, pyqtSignal, QDate, QPoint, QTimer, QEvent, QVariantAnimation, QEasingCurve
# from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPolygon

# from .. import database as db
# from .. import utils

# class LeftPanel(QWidget):
#     pump_selected = pyqtSignal(dict)
#     pump_status_selected = pyqtSignal(dict)
#     group_selected = pyqtSignal(list)
#     request_import = pyqtSignal()
#     request_add = pyqtSignal()
#     request_delete = pyqtSignal(int)
#     request_edit = pyqtSignal(int)
#     filters_applied = pyqtSignal(dict)

#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.compact_mode = True
#         self.current_page = 0
#         self.page_size = 20  # начальное значение, пересчитывается под размер окна
#         self.total_records = 0
#         self.current_filters = {}
#         self._resize_timer = QTimer(self)
#         self._resize_timer.setSingleShot(True)
#         self._resize_timer.timeout.connect(self._on_resize_settled)
#         self.setup_ui()
#         self.load_data()

#     def setup_ui(self):
#       layout = QVBoxLayout(self)
#       layout.setSpacing(4)  # Уменьшаем отступы
#       layout.setContentsMargins(4, 4, 4, 4)

#       # Ряд 1: Поиск + кнопка сброса
#       search_layout = QHBoxLayout()
#       search_label = QLabel("Поиск:")
#       search_label.setFixedWidth(40)
#       self.search_input = QLineEdit()
#       self.search_input.setPlaceholderText("Введите номер насоса...")
#       self.search_input.textChanged.connect(self.apply_filters)
#       self.btn_reset_filters = QPushButton("Сбросить фильтры")
#       self.btn_reset_filters.setFixedWidth(120)
#       self.btn_reset_filters.clicked.connect(self.reset_filters)
#       search_layout.addWidget(search_label)
#       search_layout.addWidget(self.search_input)
#       search_layout.addWidget(self.btn_reset_filters)
#       layout.addLayout(search_layout)

#       # Ряд 2: Фильтры (вердикт, тип, герметичность, заказ)
#       filter_layout = QHBoxLayout()
#       filter_layout.setSpacing(2)  # минимальный - между подписью и её виджетом
#       self.filter_verdict = QComboBox()
#       self.filter_verdict.addItems(["Все", "Годен", "Не годен"])
#       self.filter_verdict.currentTextChanged.connect(self.apply_filters)
#       self.filter_test_type = QComboBox()
#       self.filter_test_type.addItems(["Все", "Первичная", "Повторная"])
#       self.filter_test_type.currentTextChanged.connect(self.apply_filters)
#       self.filter_sealed = QComboBox()
#       self.filter_sealed.addItems(["Все", "Герметичен", "Не герметичен"])
#       self.filter_sealed.currentTextChanged.connect(self.apply_filters)
#       self.filter_order = QComboBox()
#       self.filter_order.addItem("Все заказы")
#       self.filter_order.currentTextChanged.connect(self.apply_filters)

#       filter_layout.addWidget(QLabel("Вердикт:"))
#       filter_layout.addWidget(self.filter_verdict)
#       filter_layout.addSpacing(20)  # большой - между разными фильтрами
#       filter_layout.addWidget(QLabel("Тип:"))
#       filter_layout.addWidget(self.filter_test_type)
#       filter_layout.addSpacing(20)
#       filter_layout.addWidget(QLabel("Герметичность:"))
#       filter_layout.addWidget(self.filter_sealed)
#       filter_layout.addSpacing(20)
#       filter_layout.addWidget(QLabel("Заказ №:"))
#       filter_layout.addWidget(self.filter_order)
#       layout.addLayout(filter_layout)

#       # Ряд 3: Дата и дубли
#       extra_layout = QHBoxLayout()
#       extra_layout.setSpacing(2)  # минимальный - между подписью и её виджетом
#       self.date_from = QDateEdit()
#       self.date_from.setCalendarPopup(True)
#       self.date_from.setDate(QDate(2000, 1, 1))
#       self.date_from.dateChanged.connect(self.apply_filters)
#       self.date_to = QDateEdit()
#       self.date_to.setCalendarPopup(True)
#       self.date_to.setDate(QDate.currentDate())
#       self.date_to.dateChanged.connect(self.apply_filters)
#       self.only_duplicates = QCheckBox("Дубли")
#       self.only_duplicates.stateChanged.connect(self.apply_filters)

#       extra_layout.addWidget(QLabel("С:"))
#       extra_layout.addWidget(self.date_from)
#       extra_layout.addSpacing(20)  # большой - между разными фильтрами
#       extra_layout.addWidget(QLabel("По:"))
#       extra_layout.addWidget(self.date_to)
#       extra_layout.addSpacing(20)
#       extra_layout.addWidget(self.only_duplicates)
#       layout.addLayout(extra_layout)

#       # Статистика по заказу (скрыта по умолчанию)
#       self.stats_label = QLabel()
#       self.stats_label.setWordWrap(True)
#       self.stats_label.setStyleSheet("""
#           background-color: #e8f4f8;
#           border: 1px solid #b0d4e3;
#           border-radius: 5px;
#           padding: 4px;
#           margin: 5px 0px;
#           font-size: 12px;
#       """)
#       self.stats_label.hide()
#       layout.addWidget(self.stats_label)

#       # Таблица
#       self.table = QTableWidget()
#       self.table.setStyleSheet("""
#           QTableWidget::item {
#               text-align: center;
#           }
#           QTableWidget::item:selected {
#               background-color: #3d8ec9;
#               color: white;
#           }
#           QHeaderView::section {
#               font-weight: bold;
#           }
#       """)
#       # Жирные заголовки
#       font = self.table.horizontalHeader().font()
#       font.setBold(True)
#       self.table.horizontalHeader().setFont(font)

#       self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
#       self.table.setSelectionMode(QAbstractItemView.SingleSelection)
#       self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
#       self.table.verticalHeader().setVisible(False)
#       self.table.setSortingEnabled(True)
#       self.table.itemSelectionChanged.connect(self.on_selection_changed)
#       self.table.setContextMenuPolicy(Qt.CustomContextMenu)
#       self.table.customContextMenuRequested.connect(self.show_context_menu)
#       self.table.cellClicked.connect(self.on_cell_clicked)

#       # Эффект наведения на строку (плавное осветление цвета + жирный
#       # текст) и эффект нажатия (плавное приглушение цвета)
#       self._hovered_row = -1
#       self._row_base_bg = {}     # row -> "родной" цвет строки (по вердикту)
#       self._row_animations = {}  # row -> активная QVariantAnimation
#       self.table.setMouseTracking(True)
#       self.table.entered.connect(self.on_row_hover)
#       self.table.viewport().installEventFilter(self)

#       layout.addWidget(self.table)

#       # Центрирование таблицы в левой панели
#       self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

#       # Кнопки управления
#       btn_layout = QHBoxLayout()
#       btn_layout.setSpacing(5)
#       self.btn_add = QPushButton("Добавить")
#       self.btn_add.clicked.connect(self.request_add.emit)
#       self.btn_delete = QPushButton("Удалить")
#       self.btn_delete.clicked.connect(self.on_delete_clicked)
#       self.btn_import = QPushButton("Импорт")
#       self.btn_import.clicked.connect(self.request_import.emit)
#       self.btn_view_toggle = QPushButton("Расширить")
#       self.btn_view_toggle.setCheckable(True)
#       self.btn_view_toggle.toggled.connect(self.toggle_view)

#       btn_layout.addWidget(self.btn_add)
#       btn_layout.addWidget(self.btn_delete)
#       btn_layout.addWidget(self.btn_import)
#       btn_layout.addWidget(self.btn_view_toggle)
#       layout.addLayout(btn_layout)

#       # Легенда
#       # self.legend_label = QLabel()
#       # self.legend_label.setWordWrap(True)
#       # self.legend_label.setStyleSheet("background-color: #f9f9f9; border: 1px solid #ddd; padding: 2px; font-size: 9px;")
#       # self.update_legend()
#       # layout.addWidget(self.legend_label)

#       # Пагинация
#       pagination_layout = QHBoxLayout()
#       pagination_layout.setSpacing(3)
#       self.btn_prev = QPushButton("◀")
#       self.btn_prev.setFixedWidth(30)
#       self.btn_prev.clicked.connect(self.prev_page)
#       self.btn_next = QPushButton("▶")
#       self.btn_next.setFixedWidth(30)
#       self.btn_next.clicked.connect(self.next_page)
#       self.page_label = QLabel("1/1")
#       self.page_label.setAlignment(Qt.AlignCenter)
#       self.count_label = QLabel("Всего: 0")
#       self.count_label.setAlignment(Qt.AlignRight)
#       pagination_layout.addWidget(self.btn_prev)
#       pagination_layout.addWidget(self.page_label)
#       pagination_layout.addWidget(self.btn_next)
#       pagination_layout.addStretch()
#       pagination_layout.addWidget(self.count_label)
#       layout.addLayout(pagination_layout)

#     # def update_legend(self):
#     #     legend_text = (
#     #         "Легенда: "
#     #         "<span style='color:green;'>●</span> годен  "
#     #         "<span style='color:red;'>●</span> не годен  "
#     #         "<span style='color:blue;'>●</span> герметичен  "
#     #         "<span style='color:gray;'>●</span> не герметичен  "
#     #         "I — первичная  II — повторная"
#     #     )
#     #     self.legend_label.setText(legend_text)

#     def toggle_view(self, checked):
#         """Переключает компактный/расширенный режим списка."""
#         parent = self.parent()
#         while parent and not hasattr(parent, 'splitter'):
#             parent = parent.parent()
#         if not parent or not hasattr(parent, 'splitter'):
#             return

#         if checked:
#             # Расширенный режим
#             self.compact_mode = False
#             self.btn_view_toggle.setText("Свернуть список")
#             # # Левая 100%, правая 0 (скрываем)
#             parent.splitter.setSizes([parent.width(), 0])
            
#             # Левая 85%, правая 15% (почти скрыта)
#             # parent.splitter.setSizes([int(parent.width() * 0.85), int(parent.width() * 0.15)])
#             # self.legend_label.hide()
#         else:
#             # Компактный режим (минимальный)
#             self.compact_mode = True
#             self.btn_view_toggle.setText("Расширенный вид")
#             # Левая 20%, правая 80%
#             parent.splitter.setSizes([int(parent.width() * 0.10), int(parent.width() * 0.9)])
            
#             # Левая 15%, правая 85%
#             # parent.splitter.setSizes([int(parent.width() * 0.15), int(parent.width() * 0.85)])
#             # self.legend_label.show()
#         self.apply_filters()
#         self.table.clearSelection()

#     def _setup_table_columns(self, compact=True):
#         """Настраивает количество и заголовки колонок таблицы."""
#         font = self.table.horizontalHeader().font()
#         font.setBold(True)
#         self.table.horizontalHeader().setFont(font)

#         if compact:
#             col_count = 5
#             self.table.setColumnCount(col_count)
#             self.table.setHorizontalHeaderLabels(["Номер", "Дата", "Вердикт", "Тип", "Герметичность"])
#             for col in range(5, self.table.columnCount()):
#                 self.table.setColumnHidden(col, True)
#             self.table.verticalHeader().setVisible(False)
#             self.table.setColumnWidth(0, 80)
#             self.table.setColumnWidth(1, 100)
#             self.table.setColumnWidth(2, 100)
#             self.table.setColumnWidth(3, 100)
#             self.table.setColumnWidth(4, 100)
#         else:
#             col_count = 7
#             self.table.setColumnCount(col_count)
#             self.table.setHorizontalHeaderLabels(
#                 ["Номер", "Дата", "Модификация", "Герметичность", "Тип", "Заказ", "Вердикт"]
#             )
#             for col in range(self.table.columnCount()):
#                 self.table.setColumnHidden(col, False)
#             self.table.verticalHeader().setVisible(False)
#             self.table.setColumnWidth(0, 110)
#             self.table.setColumnWidth(1, 110)
#             self.table.setColumnWidth(2, 150)
#             self.table.setColumnWidth(3, 110)
#             self.table.setColumnWidth(4, 100)
#             self.table.setColumnWidth(5, 100)
#             self.table.setColumnWidth(6, 250)
#         return col_count

#     def _fill_pump_row(self, row, p, compact=True):
#         """Заполняет одну строку таблицы данными насоса p."""
#         # ---- Номер ----
#         item_num = QTableWidgetItem(p['pump_number'])
#         item_num.setData(Qt.UserRole, p['id'])
#         item_num.setTextAlignment(Qt.AlignCenter)
#         self.table.setItem(row, 0, item_num)

#         # ---- Дата ----
#         date_str = p['test_date']
#         if date_str and ' ' in date_str:
#             date_str = date_str.split(' ')[0]
#         item_date = QTableWidgetItem(date_str)
#         item_date.setTextAlignment(Qt.AlignCenter)
#         self.table.setItem(row, 1, item_date)

#         if compact:
#             # ---- Вердикт ----
#             verdict_text = p['verdict'] if p['verdict'] else '—'
#             item_verdict = QTableWidgetItem(verdict_text)
#             item_verdict.setTextAlignment(Qt.AlignCenter)
#             self.table.setItem(row, 2, item_verdict)

#             # ---- Тип ----
#             type_text = p['test_type'] if p['test_type'] else '—'
#             item_type = QTableWidgetItem(type_text)
#             item_type.setTextAlignment(Qt.AlignCenter)
#             self.table.setItem(row, 3, item_type)

#             # ---- Герметичность ----
#             sealed_text = 'Герметичен' if p['is_sealed'] else 'Негерметичен'
#             item_sealed = QTableWidgetItem(sealed_text)
#             item_sealed.setTextAlignment(Qt.AlignCenter)
#             self.table.setItem(row, 4, item_sealed)

#         else:
#             # ---- Модификация ----
#             mod_name = p.get('mod_name', '—')
#             item_mod = QTableWidgetItem(mod_name if mod_name else '—')
#             item_mod.setTextAlignment(Qt.AlignCenter)
#             self.table.setItem(row, 2, item_mod)

#             # ---- Герметичность (текст) ----
#             sealed_text = 'Герметичен' if p['is_sealed'] else 'Негерметичен'
#             item_sealed = QTableWidgetItem(sealed_text)
#             item_sealed.setTextAlignment(Qt.AlignCenter)
#             self.table.setItem(row, 3, item_sealed)

#             # ---- Тип ----
#             type_text = p['test_type'] if p['test_type'] else '—'
#             item_type = QTableWidgetItem(type_text)
#             item_type.setTextAlignment(Qt.AlignCenter)
#             self.table.setItem(row, 4, item_type)

#             # ---- Заказ ----
#             order_num = p.get('order_number', '—')
#             order_str = str(order_num).replace('.0', '') if order_num and order_num != '—' else '—'
#             item_order = QTableWidgetItem(order_str)
#             item_order.setTextAlignment(Qt.AlignCenter)
#             self.table.setItem(row, 5, item_order)

#             # ---- Вердикт ----
#             verdict_text = p['verdict'] if p['verdict'] else '—'
#             item_verdict = QTableWidgetItem(verdict_text)
#             item_verdict.setTextAlignment(Qt.AlignCenter)
#             self.table.setItem(row, 6, item_verdict)

#         # ---- Подсветка всей строки по вердикту ----
#         if p['verdict'] == 'годен':
#             bg_color = QColor(232, 253, 232)
#         elif p['verdict'] == 'не годен':
#             bg_color = QColor(245, 230, 230)
#         else:
#             bg_color = None
#         if bg_color:
#             for col in range(self.table.columnCount()):
#                 item = self.table.item(row, col)
#                 if item:
#                     item.setBackground(bg_color)
#         # Запоминаем базовый цвет строки - от него анимируются
#         # наведение/нажатие и к нему же возвращаемся
#         self._row_base_bg[row] = bg_color if bg_color else QColor(255, 255, 255)

#     def populate_table(self, pumps, compact=True):
#         self.table.setSortingEnabled(False)
#         self.table.clearSpans()  # сбрасываем объединения ячеек, оставшиеся от группового режима (дубли)
#         self.table.setRowCount(len(pumps))
#         self._hovered_row = -1
#         self._row_base_bg = {}
#         for anim in self._row_animations.values():
#             anim.stop()
#         self._row_animations = {}

#         col_count = self._setup_table_columns(compact)

#         for row, p in enumerate(pumps):
#             self._fill_pump_row(row, p, compact)

#         self.table.setSortingEnabled(True)
#         if compact:
#             self.table.sortByColumn(1, Qt.DescendingOrder)
#         else:
#             self.table.sortByColumn(0, Qt.AscendingOrder)

#     def populate_table_grouped(self, pumps, compact=True):
#         """Отображает насосы, сгруппированные по номеру + модификации (для
#         фильтра 'Дубли'): строка-заголовок 'Образец № X — N шт.', а под ней
#         сами протоколы, отсортированные по дате (сначала новые). Если у
#         насоса с одинаковым номером разные модификации - это разные группы,
#         а не дубликаты."""
#         self.table.setSortingEnabled(False)
#         self.table.clearSpans()
#         self._hovered_row = -1
#         self._row_base_bg = {}
#         for anim in self._row_animations.values():
#             anim.stop()
#         self._row_animations = {}

#         # Группируем по (номер насоса, модификация)
#         groups = {}
#         for p in pumps:
#             key = (p['pump_number'], p.get('mod_name'))
#             groups.setdefault(key, []).append(p)

#         # Сортируем группы: сначала по убыванию количества найденных протоколов,
#         # при равном количестве - по номеру насоса
#         sorted_groups = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0][0]))

#         # Внутри группы - сортировка протоколов по дате (сначала новые)
#         for _, items in sorted_groups:
#             items.sort(key=lambda p: p['test_date'] or '', reverse=True)

#         col_count = self._setup_table_columns(compact)

#         total_rows = sum(1 + len(items) for _, items in sorted_groups)
#         self.table.setRowCount(total_rows)

#         row = 0
#         for (pump_number, mod_name), items in sorted_groups:
#             # ---- Строка-заголовок группы ----
#             header_text = f"Образец № {pump_number} — {len(items)} шт."
#             header_item = QTableWidgetItem(header_text)
#             header_item.setTextAlignment(Qt.AlignCenter)
#             header_item.setFlags(Qt.ItemIsEnabled)  # не выделяется и не открывается как протокол
#             header_font = QFont()
#             header_font.setBold(True)
#             header_item.setFont(header_font)
#             header_item.setBackground(QColor(210, 224, 240))
#             # Сохраняем сами дублирующиеся протоколы на заголовке -
#             # понадобится, чтобы по клику показать сравнение (пункт 5)
#             header_item.setData(Qt.UserRole + 1, items)
#             self.table.setItem(row, 0, header_item)
#             self.table.setSpan(row, 0, 1, col_count)
#             row += 1

#             for p in items:
#                 self._fill_pump_row(row, p, compact)
#                 row += 1

#         # Сортировка кликом по заголовку в режиме дублей отключена,
#         # т.к. порядок строк задан группировкой
#         self.table.setSortingEnabled(False)


#     def display_pumps(self, pumps, group_by_number=False):
#         if group_by_number:
#             self.populate_table_grouped(pumps, compact=self.compact_mode)
#         else:
#             self.populate_table(pumps, compact=self.compact_mode)

#     # Методы создания иконок
#     # def create_verdict_icon(self, is_good):
#     #     pixmap = QPixmap(24, 24)
#     #     pixmap.fill(Qt.transparent)
#     #     painter = QPainter(pixmap)
#     #     painter.setBrush(QColor(0, 200, 0) if is_good else QColor(200, 0, 0))
#     #     painter.setPen(Qt.NoPen)
#     #     painter.drawEllipse(6, 6, 12, 12)
#     #     painter.end()
#     #     return QIcon(pixmap)

#     # def create_type_icon(self, type_str):
#     #     pixmap = QPixmap(24, 24)
#     #     pixmap.fill(Qt.transparent)
#     #     painter = QPainter(pixmap)
#     #     painter.setPen(QColor(0, 0, 200))
#     #     painter.setFont(QFont("Arial", 10, QFont.Bold))
#     #     painter.drawText(pixmap.rect(), Qt.AlignCenter, "I" if "первичная" in str(type_str).lower() else "II")
#     #     painter.end()
#     #     return QIcon(pixmap)

#     # def create_sealed_icon(self, is_sealed):
#     #     pixmap = QPixmap(24, 24)
#     #     pixmap.fill(Qt.transparent)
#     #     painter = QPainter(pixmap)
#     #     painter.setBrush(QColor(0, 100, 255) if is_sealed else QColor(180, 180, 180))
#     #     painter.setPen(Qt.NoPen)
#     #     painter.drawEllipse(6, 9, 12, 9)
#     #     points = [QPoint(6, 9), QPoint(12, 3), QPoint(18, 9)]
#     #     polygon = QPolygon(points)
#     #     painter.drawPolygon(polygon)
#     #     painter.end()
#     #     return QIcon(pixmap)

#     def resizeEvent(self, event):
#         super().resizeEvent(event)
#         self._resize_timer.start(200)

#     def showEvent(self, event):
#         super().showEvent(event)
#         if not getattr(self, '_initial_size_done', False):
#             self._initial_size_done = True
#             QTimer.singleShot(0, self._on_resize_settled)

#     def _compute_dynamic_page_size(self):
#         """Считает, сколько строк реально помещается в видимую область
#         таблицы сейчас. viewport().height() уже НЕ включает область
#         заголовка колонок - вычитать её ещё раз не нужно (это и было
#         причиной заниженного расчёта)."""
#         row_height = self.table.verticalHeader().defaultSectionSize() or 24
#         available = self.table.viewport().height()
#         return max(5, available // row_height)

#     def _on_resize_settled(self):
#         if self.only_duplicates.isChecked():
#             return  # в режиме дублей пагинация отключена - не трогаем
#         new_page_size = self._compute_dynamic_page_size()
#         if new_page_size != self.page_size:
#             self.page_size = new_page_size
#             self.current_page = 0
#             self.apply_filters()

#     def on_cell_clicked(self, row, col):
#         """Клик по заголовку группы дублей открывает сравнение в правой панели.
#         Для обычных строк - плавный эффект нажатия (цвет на мгновение
#         становится менее контрастным и плавно возвращается)."""
#         item = self.table.item(row, 0)
#         if item is None:
#             return
#         group_items = item.data(Qt.UserRole + 1)
#         if group_items:
#             self.group_selected.emit(group_items)
#             return
#         self._press_row(row)

#     def _row_is_group_header(self, row):
#         item0 = self.table.item(row, 0)
#         return bool(item0 and item0.data(Qt.UserRole + 1))

#     def _row_items(self, row):
#         if row < 0 or row >= self.table.rowCount() or self._row_is_group_header(row):
#             return []
#         return [it for it in (self.table.item(row, c) for c in range(self.table.columnCount())) if it]

#     @staticmethod
#     def _blend(color_from, color_to, t):
#         r = color_from.red() + (color_to.red() - color_from.red()) * t
#         g = color_from.green() + (color_to.green() - color_from.green()) * t
#         b = color_from.blue() + (color_to.blue() - color_from.blue()) * t
#         return QColor(int(r), int(g), int(b))

#     def _lighten(self, color, factor=0.35):
#         """Смешивает цвет с белым - делает ярче (для наведения)."""
#         return self._blend(color, QColor(255, 255, 255), factor)

#     def _mute(self, color, factor=0.45):
#         """Смешивает цвет с нейтральным серым - делает менее контрастным
#         (для эффекта нажатия)."""
#         return self._blend(color, QColor(205, 205, 205), factor)

#     def _animate_row(self, row, target_color, duration=350, on_finished=None):
#         """Плавно перекрашивает всю строку в target_color за duration мс.
#         Останавливает предыдущую анимацию этой же строки, если она ещё идёт
#         (чтобы быстрые движения мыши/клики не накладывались друг на друга)."""
#         items = self._row_items(row)
#         if not items:
#             if on_finished:
#                 on_finished()
#             return

#         old_anim = self._row_animations.get(row)
#         if old_anim is not None:
#             old_anim.stop()

#         start_colors = [it.background().color() for it in items]

#         anim = QVariantAnimation(self.table)
#         anim.setDuration(duration)
#         anim.setEasingCurve(QEasingCurve.InOutQuad)
#         anim.setStartValue(0.0)
#         anim.setEndValue(1.0)

#         def update(t):
#             for it, start_c in zip(items, start_colors):
#                 if it:
#                     it.setBackground(self._blend(start_c, target_color, t))

#         anim.valueChanged.connect(update)
#         if on_finished:
#             anim.finished.connect(on_finished)
#         self._row_animations[row] = anim
#         anim.start()

#     def on_row_hover(self, index):
#         """Наведение мыши на строку - цвет плавно становится ярче, текст -
#         жирным и чуть крупнее."""
#         row = index.row()
#         if row == self._hovered_row:
#             return
#         self._leave_row(self._hovered_row)
#         self._enter_row(row)
#         self._hovered_row = row

#     def _enter_row(self, row):
#         items = self._row_items(row)
#         if not items:
#             return
#         base = self._row_base_bg.get(row, QColor(255, 255, 255))
#         self._animate_row(row, self._lighten(base), duration=350)
#         for item in items:
#             font = item.font()
#             font.setBold(True)
#             font.setPointSize(font.pointSize() + 1)
#             item.setFont(font)

#     def _leave_row(self, row):
#         items = self._row_items(row)
#         if not items:
#             return
#         base = self._row_base_bg.get(row, QColor(255, 255, 255))
#         self._animate_row(row, base, duration=350)
#         for item in items:
#             font = item.font()
#             font.setBold(False)
#             font.setPointSize(max(1, font.pointSize() - 1))
#             item.setFont(font)

#     def _press_row(self, row):
#         """Плавный эффект нажатия: цвет строки на мгновение становится
#         менее контрастным и плавно возвращается к тому, что должно быть
#         (наведённый или обычный вид - в зависимости от текущего состояния)."""
#         items = self._row_items(row)
#         if not items:
#             return
#         current = items[0].background().color()
#         muted = self._mute(current)

#         def restore():
#             base = self._row_base_bg.get(row, QColor(255, 255, 255))
#             target = self._lighten(base) if row == self._hovered_row else base
#             self._animate_row(row, target, duration=200)

#         self._animate_row(row, muted, duration=150, on_finished=restore)

#     def eventFilter(self, obj, event):
#         if obj is self.table.viewport():
#             if event.type() == QEvent.Leave:
#                 self._leave_row(self._hovered_row)
#                 self._hovered_row = -1
#             elif event.type() == QEvent.MouseMove:
#                 # Курсор мог уйти на пустое пространство под последней
#                 # строкой - там нет валидного индекса, и сигнал entered()
#                 # в этом случае не срабатывает вообще
#                 index = self.table.indexAt(event.pos())
#                 if not index.isValid() and self._hovered_row != -1:
#                     self._leave_row(self._hovered_row)
#                     self._hovered_row = -1
#         return super().eventFilter(obj, event)

#     def on_selection_changed(self):
#         """Обработка выбора строки. В компактном режиме открывает протокол
#         (как раньше); в расширенном - только обновляет статус-бар, не
#         переключая вид и не открывая протокол."""
#         selected = self.table.selectedItems()
#         if not selected:
#             return
#         row = selected[0].row()
#         item = self.table.item(row, 0)
#         if item is None:
#             return
#         pump_id = item.data(Qt.UserRole)
#         if pump_id is None:
#             return
#         pump_data = db.get_pump_by_id(pump_id)
#         if not pump_data:
#             return
#         if self.compact_mode:
#             self.pump_selected.emit(pump_data)
#         else:
#             self.pump_status_selected.emit(pump_data)

#     def show_context_menu(self, pos):
#         row = self.table.rowAt(pos.y())
#         if row < 0:
#             return
#         item = self.table.item(row, 0)
#         if not item:
#             return
#         pump_id = item.data(Qt.UserRole)
#         if not pump_id:
#             return

#         menu = QMenu(self)
#         action_view = menu.addAction("Показать протокол")
#         action_edit = menu.addAction("Редактировать")
#         action_delete = menu.addAction("Удалить")

#         action = menu.exec_(self.table.mapToGlobal(pos))

#         if action == action_view:
#             # Сворачиваем расширенный вид, если он включён
#             if not self.compact_mode:
#                 self.btn_view_toggle.setChecked(False)
#             # Выбираем строку и отправляем сигнал
#             self.table.selectRow(row)
#             self.on_selection_changed()
#         elif action == action_edit:
#             self.request_edit.emit(pump_id)
#         elif action == action_delete:
#             self.request_delete.emit(pump_id)

#     def on_delete_clicked(self):
#         selected = self.table.selectedItems()
#         if not selected:
#             return
#         row = selected[0].row()
#         pump_id = self.table.item(row, 0).data(Qt.UserRole)
#         if pump_id:
#             self.request_delete.emit(pump_id)

#     def load_data(self):
#         self.all_pumps = db.get_all_pumps()
#         orders = db.get_all_orders()  # возвращает список (id, order_number)
#         self.order_map = {}  # словарь {id: отформатированный_номер}
#         self.filter_order.blockSignals(True)
#         self.filter_order.clear()
#         self.filter_order.addItem("Все заказы")
#         for oid, onum in orders:
#             # Форматируем номер
#             order_str = str(onum)
#             if '.' in order_str:
#                 order_str = order_str.rstrip('0').rstrip('.')
#             self.order_map[oid] = order_str
#             self.filter_order.addItem(order_str, oid)
#         self.filter_order.blockSignals(False)
#         self.apply_filters()

#     def apply_filters(self):
#         filters = {}
#         search_text = self.search_input.text().strip()
#         if search_text:
#             filters['pump_number'] = search_text

#         verdict = self.filter_verdict.currentText()
#         if verdict != 'Все':
#             filters['verdict'] = verdict.lower()

#         test_type = self.filter_test_type.currentText()
#         if test_type != 'Все':
#             filters['test_type'] = test_type.lower()

#         sealed = self.filter_sealed.currentText()
#         if sealed == 'Герметичен':
#             filters['is_sealed'] = 1
#         elif sealed == 'Не герметичен':
#             filters['is_sealed'] = 0

#         order_index = self.filter_order.currentIndex()
#         if order_index > 0:  # 0 - "Все заказы"
#             order_id = self.filter_order.itemData(order_index)
#             filters['order_id'] = order_id

#         date_from = self.date_from.date().toString('yyyy-MM-dd')
#         date_to = self.date_to.date().toString('yyyy-MM-dd')
#         if date_from != '2000-01-01' or date_to != QDate.currentDate().toString('yyyy-MM-dd'):
#             filters['date_from'] = date_from
#             filters['date_to'] = date_to

#         if self.only_duplicates.isChecked():
#             filters['only_duplicates'] = True

#         self.current_filters = filters

#         # Подсчёт общего количества
#         self.total_records = db.count_pumps(filters)

#         # Определяем группировку по номеру (только если включён фильтр дублей)
#         group_by_number = self.only_duplicates.isChecked()

#         if group_by_number:
#             # В режиме дублей группы не должны разрываться постраничной разбивкой -
#             # показываем все найденные записи целиком
#             filtered = db.get_all_pumps(filters)
#         else:
#             # Подстраховка: пересчитываем размер страницы прямо сейчас (а не
#             # только по событию resize) - гарантирует актуальное значение,
#             # даже если окно ещё не успело прислать событие изменения размера
#             fresh_page_size = self._compute_dynamic_page_size()
#             if fresh_page_size != self.page_size:
#                 self.page_size = fresh_page_size
#                 self.current_page = 0
#             offset = self.current_page * self.page_size
#             filtered = db.get_all_pumps(filters, limit=self.page_size, offset=offset)

#         self.display_pumps(filtered, group_by_number=group_by_number)
#         self.update_stats(filtered)

#         self.update_pagination_label()

#         if hasattr(self, 'filters_applied'):
#             self.filters_applied.emit(filters)

#     def update_stats(self, filtered_pumps):
#         if 'order_id' in self.current_filters and self.current_filters['order_id']:
#             order_id = self.current_filters['order_id']
#             order_str = self.order_map.get(order_id)
#             if not order_str:
#                 self.stats_label.hide()
#                 return
#             total = len(filtered_pumps)
#             if total == 0:
#                 self.stats_label.setText(f"Для заказа №{order_str} нет данных с учётом текущих фильтров.")
#                 self.stats_label.show()
#                 return

#             good = sum(1 for p in filtered_pumps if p.get('verdict') == 'годен')
#             not_sealed = sum(1 for p in filtered_pumps if p.get('is_sealed') is False)
#             good_first = sum(1 for p in filtered_pumps if p.get('verdict') == 'годен' and p.get('test_type') == 'первичная')

#             good_percent = round(good / total * 100, 1)
#             not_sealed_percent = round(not_sealed / total * 100, 1)
#             good_first_percent = round(good_first / total * 100, 1)

#             text = (f"Для заказа №{order_str} проверено <b>{total}</b> насосов: "
#                     f"годных — <b>{good}</b> ({good_percent}%), "
#                     f"негерметичных — <b>{not_sealed}</b> ({not_sealed_percent}%), "
#                     f"годных с первого предъявления — <b>{good_first}</b> ({good_first_percent}%)")
#             self.stats_label.setText(text)
#             self.stats_label.show()
#         else:
#             self.stats_label.hide()

#     def reset_filters(self):
#         self.search_input.clear()
#         self.filter_verdict.setCurrentIndex(0)
#         self.filter_test_type.setCurrentIndex(0)
#         self.filter_sealed.setCurrentIndex(0)
#         self.filter_order.setCurrentIndex(0)
#         self.date_from.setDate(QDate(2000, 1, 1))
#         self.date_to.setDate(QDate.currentDate())
#         self.only_duplicates.setChecked(False)
#         self.current_page = 0
#         self.apply_filters()

#     def refresh(self):
#         self.current_page = 0
#         self.load_data()

#     def next_page(self):
#         if (self.current_page + 1) * self.page_size < self.total_records:
#             self.current_page += 1
#             self.apply_filters()

#     def prev_page(self):
#         if self.current_page > 0:
#             self.current_page -= 1
#             self.apply_filters()

#     def update_pagination_label(self):
#         if self.only_duplicates.isChecked():
#             # В режиме дублей показываются сразу все найденные группы,
#             # постраничная разбивка не применяется
#             self.page_label.setText("Группировка по дублям")
#             self.btn_prev.setEnabled(False)
#             self.btn_next.setEnabled(False)
#             self.count_label.setText(f"Всего записей: {self.total_records}")
#             return

#         total_pages = max(1, (self.total_records + self.page_size - 1) // self.page_size)
#         self.page_label.setText(f"Страница {self.current_page + 1} из {total_pages}")
#         self.btn_prev.setEnabled(self.current_page > 0)
#         self.btn_next.setEnabled((self.current_page + 1) * self.page_size < self.total_records)
#         self.count_label.setText(f"Всего записей: {self.total_records}")

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QCheckBox,
    QDateEdit, QHeaderView, QAbstractItemView, QMenu,
    QStyledItemDelegate, QStyle, QStyleOptionViewItem
)
from PyQt5.QtCore import Qt, pyqtSignal, QDate, QPoint, QTimer, QEvent, QVariantAnimation, QEasingCurve
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPolygon

from .. import database as db
from .. import utils

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

    def setup_ui(self):
      layout = QVBoxLayout(self)
      layout.setSpacing(4)  # Уменьшаем отступы
      layout.setContentsMargins(4, 4, 4, 4)

      # Ряд 1: Поиск + кнопка сброса
      search_layout = QHBoxLayout()
      search_label = QLabel("Поиск:")
      search_label.setFixedWidth(40)
      self.search_input = QLineEdit()
      self.search_input.setPlaceholderText("Введите номер насоса...")
      self.search_input.textChanged.connect(self.apply_filters)
      self.btn_reset_filters = QPushButton("Сбросить фильтры")
      self.btn_reset_filters.setFixedWidth(120)
      self.btn_reset_filters.clicked.connect(self.reset_filters)
      search_layout.addWidget(search_label)
      search_layout.addWidget(self.search_input)
      search_layout.addWidget(self.btn_reset_filters)
      layout.addLayout(search_layout)

      # Ряд 2: Фильтры (вердикт, тип, герметичность, заказ)
      filter_layout = QHBoxLayout()
      filter_layout.setSpacing(2)  # минимальный - между подписью и её виджетом
      self.filter_verdict = QComboBox()
      self.filter_verdict.addItems(["Все", "Годен", "Не годен"])
      self.filter_verdict.currentTextChanged.connect(self.apply_filters)
      self.filter_test_type = QComboBox()
      self.filter_test_type.addItems(["Все", "Первичная", "Повторная"])
      self.filter_test_type.currentTextChanged.connect(self.apply_filters)
      self.filter_sealed = QComboBox()
      self.filter_sealed.addItems(["Все", "Герметичен", "Не герметичен"])
      self.filter_sealed.currentTextChanged.connect(self.apply_filters)
      self.filter_order = QComboBox()
      self.filter_order.addItem("Все заказы")
      self.filter_order.currentTextChanged.connect(self.apply_filters)

      filter_layout.addWidget(QLabel("Вердикт:"))
      filter_layout.addWidget(self.filter_verdict)
      filter_layout.addSpacing(20)  # большой - между разными фильтрами
      filter_layout.addWidget(QLabel("Тип:"))
      filter_layout.addWidget(self.filter_test_type)
      filter_layout.addSpacing(20)
      filter_layout.addWidget(QLabel("Герметичность:"))
      filter_layout.addWidget(self.filter_sealed)
      filter_layout.addSpacing(20)
      filter_layout.addWidget(QLabel("Заказ №:"))
      filter_layout.addWidget(self.filter_order)
      layout.addLayout(filter_layout)

      # Ряд 3: Дата и дубли
      extra_layout = QHBoxLayout()
      extra_layout.setSpacing(2)  # минимальный - между подписью и её виджетом
      self.date_from = QDateEdit()
      self.date_from.setCalendarPopup(True)
      self.date_from.setDate(QDate(2000, 1, 1))
      self.date_from.dateChanged.connect(self.apply_filters)
      self.date_to = QDateEdit()
      self.date_to.setCalendarPopup(True)
      self.date_to.setDate(QDate.currentDate())
      self.date_to.dateChanged.connect(self.apply_filters)
      self.only_duplicates = QCheckBox("Дубли")
      self.only_duplicates.stateChanged.connect(self.apply_filters)

      extra_layout.addWidget(QLabel("С:"))
      extra_layout.addWidget(self.date_from)
      extra_layout.addSpacing(20)  # большой - между разными фильтрами
      extra_layout.addWidget(QLabel("По:"))
      extra_layout.addWidget(self.date_to)
      extra_layout.addSpacing(20)
      extra_layout.addWidget(self.only_duplicates)
      layout.addLayout(extra_layout)

      # Статистика по заказу (скрыта по умолчанию)
      self.stats_label = QLabel()
      self.stats_label.setWordWrap(True)
      self.stats_label.setStyleSheet("""
          background-color: #e8f4f8;
          border: 1px solid #b0d4e3;
          border-radius: 5px;
          padding: 4px;
          margin: 5px 0px;
          font-size: 12px;
      """)
      self.stats_label.hide()
      layout.addWidget(self.stats_label)

      # Таблица
      self.table = QTableWidget()
      self.table.setStyleSheet("""
          QTableWidget::item {
              text-align: center;
          }
          QHeaderView::section {
              font-weight: bold;
          }
      """)
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

      # Эффект наведения на строку (плавное осветление цвета + жирный
      # текст) и эффект нажатия (плавное приглушение цвета). Базовый цвет
      # строки хранится как данные ячейки (см. _row_base_color) - не в
      # словаре по индексу, т.к. сортировка таблицы переставляет строки
      self._hovered_row = -1
      self._selected_row = -1
      self._base_font_size = float(self.table.font().pointSize() or 9)
      self._row_animations = {}  # row -> активная QVariantAnimation
      self.table.setMouseTracking(True)
      self.table.entered.connect(self.on_row_hover)
      self.table.viewport().installEventFilter(self)

      layout.addWidget(self.table)

      # Центрирование таблицы в левой панели
      self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

      # Кнопки управления
      btn_layout = QHBoxLayout()
      btn_layout.setSpacing(5)
      self.btn_add = QPushButton("Добавить")
      self.btn_add.clicked.connect(self.request_add.emit)
      self.btn_delete = QPushButton("Удалить")
      self.btn_delete.clicked.connect(self.on_delete_clicked)
      self.btn_import = QPushButton("Импорт")
      self.btn_import.clicked.connect(self.request_import.emit)
      self.btn_view_toggle = QPushButton("Расширить")
      self.btn_view_toggle.setCheckable(True)
      self.btn_view_toggle.toggled.connect(self.toggle_view)

      btn_layout.addWidget(self.btn_add)
      btn_layout.addWidget(self.btn_delete)
      btn_layout.addWidget(self.btn_import)
      btn_layout.addWidget(self.btn_view_toggle)
      layout.addLayout(btn_layout)

      # Легенда
      # self.legend_label = QLabel()
      # self.legend_label.setWordWrap(True)
      # self.legend_label.setStyleSheet("background-color: #f9f9f9; border: 1px solid #ddd; padding: 2px; font-size: 9px;")
      # self.update_legend()
      # layout.addWidget(self.legend_label)

      # Пагинация
      pagination_layout = QHBoxLayout()
      pagination_layout.setSpacing(3)
      self.btn_prev = QPushButton("◀")
      self.btn_prev.setFixedWidth(30)
      self.btn_prev.clicked.connect(self.prev_page)
      self.btn_next = QPushButton("▶")
      self.btn_next.setFixedWidth(30)
      self.btn_next.clicked.connect(self.next_page)
      self.page_label = QLabel("1/1")
      self.page_label.setAlignment(Qt.AlignCenter)
      self.count_label = QLabel("Всего: 0")
      self.count_label.setAlignment(Qt.AlignRight)
      pagination_layout.addWidget(self.btn_prev)
      pagination_layout.addWidget(self.page_label)
      pagination_layout.addWidget(self.btn_next)
      pagination_layout.addStretch()
      pagination_layout.addWidget(self.count_label)
      layout.addLayout(pagination_layout)

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
            # # Левая 100%, правая 0 (скрываем)
            parent.splitter.setSizes([parent.width(), 0])
            
            # Левая 85%, правая 15% (почти скрыта)
            # parent.splitter.setSizes([int(parent.width() * 0.85), int(parent.width() * 0.15)])
            # self.legend_label.hide()
        else:
            # Компактный режим (минимальный)
            self.compact_mode = True
            self.btn_view_toggle.setText("Расширенный вид")
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
        base_color = bg_color if bg_color else QColor(255, 255, 255)
        base_font = QFont()
        base_font.setPointSizeF(self._base_font_size)
        base_font.setWeight(QFont.Normal)
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                if bg_color:
                    item.setBackground(bg_color)
                item.setFont(base_font)
        # Запоминаем базовый цвет строки как данные ПЕРВОЙ ячейки - именно
        # там, а не в словаре по номеру строки, потому что таблица потом
        # сортируется (setSortingEnabled/sortByColumn) и физически
        # переставляет строки; словарь по индексу строки после сортировки
        # указывал бы уже на другой насос
        item0 = self.table.item(row, 0)
        if item0:
            item0.setData(Qt.UserRole + 2, base_color)

    def populate_table(self, pumps, compact=True):
        self.table.setSortingEnabled(False)
        self.table.clearSpans()  # сбрасываем объединения ячеек, оставшиеся от группового режима (дубли)
        self.table.setRowCount(len(pumps))
        self._hovered_row = -1
        self._selected_row = -1
        for anim in self._row_animations.values():
            anim.stop()
        self._row_animations = {}

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
        for anim in self._row_animations.values():
            anim.stop()
        self._row_animations = {}

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
        Для обычных строк - плавный эффект нажатия (цвет на мгновение
        становится менее контрастным и плавно возвращается)."""
        item = self.table.item(row, 0)
        if item is None:
            return
        group_items = item.data(Qt.UserRole + 1)
        if group_items:
            self.group_selected.emit(group_items)
            return
        self._press_row(row)

    def _row_is_group_header(self, row):
        item0 = self.table.item(row, 0)
        return bool(item0 and item0.data(Qt.UserRole + 1))

    def _row_items(self, row):
        if row < 0 or row >= self.table.rowCount() or self._row_is_group_header(row):
            return []
        return [it for it in (self.table.item(row, c) for c in range(self.table.columnCount())) if it]

    @staticmethod
    def _blend(color_from, color_to, t):
        r = color_from.red() + (color_to.red() - color_from.red()) * t
        g = color_from.green() + (color_to.green() - color_from.green()) * t
        b = color_from.blue() + (color_to.blue() - color_from.blue()) * t
        return QColor(int(r), int(g), int(b))

    def _lighten(self, color, factor=0.5):
        """Смешивает цвет с белым - делает ярче (для наведения)."""
        return self._blend(color, QColor(255, 255, 255), factor)

    def _mute(self, color, factor=0.45):
        """Смешивает цвет с нейтральным серым - делает менее контрастным
        (для эффекта нажатия)."""
        return self._blend(color, QColor(205, 205, 205), factor)

    def _vivid(self, color):
        """Яркая, насыщенная версия цвета строки (для выделения) - тот же
        оттенок, что и обычная подсветка по вердикту, но гораздо
        насыщеннее. Для нейтральных строк (без оттенка) - акцентный синий."""
        h, s, v, _ = color.getHsv()
        if h < 0 or s < 12:
            return QColor(140, 185, 235)
        vivid = QColor()
        vivid.setHsv(h, 190, 220)
        return vivid

    def _row_base_color(self, row):
        """Базовый цвет строки (по вердикту), хранится как данные первой
        ячейки - переживает пересортировку таблицы, в отличие от словаря
        по индексу строки."""
        item0 = self.table.item(row, 0)
        color = item0.data(Qt.UserRole + 2) if item0 else None
        return color if color else QColor(255, 255, 255)

    def _state_for_row(self, row):
        """Возвращает (цвет, размер_шрифта, насыщенность_шрифта), которые
        ДОЛЖНЫ сейчас отображаться для строки - в зависимости от того,
        выделена она, наведена, или в обычном состоянии."""
        base = self._row_base_color(row)
        if row == self._selected_row:
            return self._vivid(base), self._base_font_size + 1, QFont.Bold
        if row == self._hovered_row:
            return self._lighten(base, 0.5), self._base_font_size + 1, QFont.Bold
        return base, self._base_font_size, QFont.Normal

    def _animate_row(self, row, target_color, target_size, target_weight, duration, on_finished=None):
        """Плавно и СИНХРОННО меняет цвет фона, размер и насыщенность
        шрифта всей строки за duration мс - всё на одном таймлайне, так
        что цвет и шрифт всегда меняются вместе. Останавливает предыдущую
        анимацию этой же строки, если она ещё идёт."""
        items = self._row_items(row)
        if not items:
            if on_finished:
                on_finished()
            return

        old_anim = self._row_animations.get(row)
        if old_anim is not None:
            old_anim.stop()

        start_colors = [it.background().color() for it in items]
        start_font = items[0].font()
        start_size = start_font.pointSizeF()
        start_weight = start_font.weight()

        anim = QVariantAnimation(self.table)
        anim.setDuration(duration)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)

        def update(t):
            size = start_size + (target_size - start_size) * t
            weight = start_weight + (target_weight - start_weight) * t
            for it, start_c in zip(items, start_colors):
                if it:
                    it.setBackground(self._blend(start_c, target_color, t))
                    f = it.font()
                    f.setPointSizeF(size)
                    f.setWeight(int(weight))
                    it.setFont(f)

        anim.valueChanged.connect(update)
        if on_finished:
            anim.finished.connect(on_finished)
        self._row_animations[row] = anim
        anim.start()

    def _animate_row_to_state(self, row, duration=350, on_finished=None):
        color, size, weight = self._state_for_row(row)
        self._animate_row(row, color, size, weight, duration, on_finished)

    def on_row_hover(self, index):
        """Наведение мыши на строку - цвет, размер и жирность шрифта
        плавно и синхронно переходят в "наведённое" состояние."""
        row = index.row()
        if self._row_is_group_header(row):
            row = -1
        if row == self._hovered_row:
            return
        old_hover = self._hovered_row
        self._hovered_row = row
        if old_hover != -1:
            self._animate_row_to_state(old_hover, duration=350)
        if row != -1:
            self._animate_row_to_state(row, duration=350)

    def _press_row(self, row):
        """Плавный эффект нажатия: цвет строки на мгновение становится
        менее контрастным (шрифт при этом не меняется) и плавно
        возвращается к тому состоянию, которое сейчас должно отображаться
        (выделенному, наведённому или обычному).

        Возврат запускается НЕЗАВИСИМЫМ таймером, а не через сигнал
        finished() у анимации приглушения - Qt не эмитит finished(), если
        анимация была прервана чьим-то ещё вызовом .stop() (например,
        параллельной анимацией выделения), из-за чего возврат мог вообще
        не произойти и строка "зависала" приглушённой."""
        items = self._row_items(row)
        if not items:
            return
        current_font = items[0].font()
        current_color = items[0].background().color()
        muted = self._mute(current_color)

        self._animate_row(row, muted, current_font.pointSizeF(), current_font.weight(), duration=150)

        def restore():
            self._animate_row_to_state(row, duration=200)
        QTimer.singleShot(150, restore)

    def eventFilter(self, obj, event):
        if obj is self.table.viewport():
            if event.type() == QEvent.Leave:
                old_hover = self._hovered_row
                self._hovered_row = -1
                if old_hover != -1:
                    self._animate_row_to_state(old_hover, duration=350)
            elif event.type() == QEvent.MouseMove:
                # Курсор мог уйти на пустое пространство под последней
                # строкой - там нет валидного индекса, и сигнал entered()
                # в этом случае не срабатывает вообще
                index = self.table.indexAt(event.pos())
                if not index.isValid() and self._hovered_row != -1:
                    old_hover = self._hovered_row
                    self._hovered_row = -1
                    self._animate_row_to_state(old_hover, duration=350)
        return super().eventFilter(obj, event)

    def on_selection_changed(self):
        """Обработка выбора строки. В компактном режиме открывает протокол
        (как раньше); в расширенном - только обновляет статус-бар, не
        переключая вид и не открывая протокол. Плюс - синхронизированная
        анимация выделения (яркий цвет строки вместо стандартного синего)."""
        selected = self.table.selectedItems()
        new_row = selected[0].row() if selected else -1

        if new_row != self._selected_row:
            old_selected = self._selected_row
            self._selected_row = new_row
            if old_selected != -1:
                self._animate_row_to_state(old_selected, duration=300)
            if new_row != -1:
                self._animate_row_to_state(new_row, duration=300)

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
            # постраничная разбивка не применяется
            self.page_label.setText("Группировка по дублям")
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)
            self.count_label.setText(f"Всего записей: {self.total_records}")
            return

        total_pages = max(1, (self.total_records + self.page_size - 1) // self.page_size)
        self.page_label.setText(f"Страница {self.current_page + 1} из {total_pages}")
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled((self.current_page + 1) * self.page_size < self.total_records)
        self.count_label.setText(f"Всего записей: {self.total_records}")