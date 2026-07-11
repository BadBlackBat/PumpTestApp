from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QCheckBox,
    QDateEdit, QHeaderView, QAbstractItemView, QMenu
)
from PyQt5.QtCore import Qt, pyqtSignal, QDate, QPoint
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPolygon

from .. import database as db
from .. import utils

class LeftPanel(QWidget):
    pump_selected = pyqtSignal(dict)
    request_import = pyqtSignal()
    request_add = pyqtSignal()
    request_delete = pyqtSignal(int)
    request_edit = pyqtSignal(int)
    filters_applied = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.compact_mode = True
        self.current_page = 0
        self.page_size = 20
        self.total_records = 0
        self.current_filters = {}
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
      filter_layout.setSpacing(5)
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
      filter_layout.addWidget(QLabel("Тип:"))
      filter_layout.addWidget(self.filter_test_type)
      filter_layout.addWidget(QLabel("Герметичность:"))
      filter_layout.addWidget(self.filter_sealed)
      filter_layout.addWidget(QLabel("Заказ №:"))
      filter_layout.addWidget(self.filter_order)
      layout.addLayout(filter_layout)

      # Ряд 3: Дата и дубли
      extra_layout = QHBoxLayout()
      extra_layout.setSpacing(5)
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
      extra_layout.addWidget(QLabel("По:"))
      extra_layout.addWidget(self.date_to)
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
          QTableWidget::item:selected {
              background-color: #3d8ec9;
              color: white;
          }
          QHeaderView::section {
              font-weight: bold;
          }
      """)
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

    def populate_table(self, pumps, compact=True):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(pumps))

        # Устанавливаем жирные заголовки (делаем один раз, но можно и тут)
        font = self.table.horizontalHeader().font()
        font.setBold(True)
        self.table.horizontalHeader().setFont(font)

        if compact:
            self.table.setColumnCount(5)
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
            self.table.setColumnCount(7)
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

        for row, p in enumerate(pumps):
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
            if bg_color:
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(bg_color)

        self.table.setSortingEnabled(True)
        if compact:
            self.table.sortByColumn(1, Qt.DescendingOrder)
        else:
            self.table.sortByColumn(0, Qt.AscendingOrder)

    def display_pumps(self, pumps, group_by_number=False):
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

    def on_selection_changed(self):
        """Обработка выбора строки (только в компактном режиме)."""
        if not self.compact_mode:
            return
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        item = self.table.item(row, 0)
        if item is None:
            return
        pump_id = item.data(Qt.UserRole)
        if pump_id is None:
            return
        pump_data = db.get_pump_by_id(pump_id)
        if pump_data:
            self.pump_selected.emit(pump_data)

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

        # Пагинация
        offset = self.current_page * self.page_size
        filtered = db.get_all_pumps(filters, limit=self.page_size, offset=offset)

        # Определяем группировку по номеру (только если включён фильтр дублей)
        group_by_number = self.only_duplicates.isChecked()

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
        total_pages = max(1, (self.total_records + self.page_size - 1) // self.page_size)
        self.page_label.setText(f"Страница {self.current_page + 1} из {total_pages}")
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled((self.current_page + 1) * self.page_size < self.total_records)
        self.count_label.setText(f"Всего записей: {self.total_records}")