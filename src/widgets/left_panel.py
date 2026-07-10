from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QCheckBox,
    QDateEdit, QHeaderView, QAbstractItemView, QMenu
)
from PyQt5.QtCore import Qt, pyqtSignal, QDate
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont

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
        # Инициализация атрибутов ДО вызова setup_ui и load_data
        self.current_page = 0
        self.page_size = 20
        self.total_records = 0
        self.current_filters = {}
        self.all_pumps = []
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Строка поиска
        search_layout = QHBoxLayout()
        search_label = QLabel("Поиск:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите номер насоса...")
        self.search_input.textChanged.connect(self.apply_filters)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)

        # Кнопка сброса
        self.btn_reset_filters = QPushButton("Сбросить фильтры")
        self.btn_reset_filters.clicked.connect(self.reset_filters)
        search_layout.addWidget(self.btn_reset_filters)

        layout.addLayout(search_layout)

        # Фильтры
        filter_layout = QHBoxLayout()
        self.filter_verdict = QComboBox()
        self.filter_verdict.addItems(["Все", "Годен", "Не годен"])
        self.filter_verdict.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Вердикт:"))
        filter_layout.addWidget(self.filter_verdict)

        self.filter_test_type = QComboBox()
        self.filter_test_type.addItems(["Все", "Первичная", "Повторная"])
        self.filter_test_type.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Тип:"))
        filter_layout.addWidget(self.filter_test_type)

        self.filter_sealed = QComboBox()
        self.filter_sealed.addItems(["Все", "Герметичен", "Не герметичен"])
        self.filter_sealed.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Герметичность:"))
        filter_layout.addWidget(self.filter_sealed)

        # Фильтр по заказам
        self.filter_order = QComboBox()
        self.filter_order.addItem("Все заказы")
        self.filter_order.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Заказ:"))
        filter_layout.addWidget(self.filter_order)

        layout.addLayout(filter_layout)

        # Дополнительные фильтры (дата, дубли)
        extra_layout = QHBoxLayout()
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate(2000, 1, 1))
        self.date_from.dateChanged.connect(self.apply_filters)
        extra_layout.addWidget(QLabel("Дата с:"))
        extra_layout.addWidget(self.date_from)

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.dateChanged.connect(self.apply_filters)
        extra_layout.addWidget(QLabel("по:"))
        extra_layout.addWidget(self.date_to)

        self.only_duplicates = QCheckBox("Только дубли")
        self.only_duplicates.stateChanged.connect(self.apply_filters)
        extra_layout.addWidget(self.only_duplicates)

        layout.addLayout(extra_layout)

        # Статистика по заказу
        self.stats_label = QLabel("")
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("background-color: #e8f4f8; border-radius: 5px; border: 1px solid #b0d4e3; padding: 5px;")
        self.stats_label.hide()  # по умолчанию скрыт
        layout.addWidget(self.stats_label)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Номер насоса", "Дата", "Вердикт", "Тип", "Герметичность", "Кол-во проверок"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(1, Qt.DescendingOrder)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        # Контекстное меню
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table)

        # Пагинация
        pagination_layout = QHBoxLayout()
        self.btn_prev = QPushButton("◀ Назад")
        self.btn_prev.clicked.connect(self.prev_page)
        self.btn_next = QPushButton("Вперед ▶")
        self.btn_next.clicked.connect(self.next_page)
        self.page_label = QLabel("Страница 1 из 1")
        pagination_layout.addWidget(self.btn_prev)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.btn_next)
        pagination_layout.addStretch()
        layout.addLayout(pagination_layout)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Добавить")
        self.btn_add.clicked.connect(self.request_add.emit)
        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.clicked.connect(self.on_delete_clicked)
        self.btn_import = QPushButton("Импорт из Excel")
        self.btn_import.clicked.connect(self.request_import.emit)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_import)
        layout.addLayout(btn_layout)

    def load_data(self):
        self.all_pumps = db.get_all_pumps()
        # Обновляем список заказов
        orders = db.get_all_orders()
        self.filter_order.blockSignals(True)
        self.filter_order.clear()
        self.filter_order.addItem("Все заказы")
        for oid, onum in orders:
            self.filter_order.addItem(onum, oid)
        self.filter_order.blockSignals(False)
        self.apply_filters()

    def update_stats(self, filtered_pumps):
        """Обновляет статистику по заказу, если выбран конкретный заказ."""
        # Проверяем, выбран ли заказ в фильтрах
        if 'order_number' in self.current_filters and self.current_filters['order_number']:
            order_number = self.current_filters['order_number']
            total = len(filtered_pumps)
            if total == 0:
                self.stats_label.setText(f"Для заказа №{order_number} нет данных с учётом текущих фильтров.")
                self.stats_label.show()
                return

            good = sum(1 for p in filtered_pumps if p.get('verdict') == 'годен')
            not_sealed = sum(1 for p in filtered_pumps if p.get('is_sealed') is False)
            good_first = sum(1 for p in filtered_pumps if p.get('verdict') == 'годен' and p.get('test_type') == 'первичная')

            good_percent = round(good / total * 100, 1)
            not_sealed_percent = round(not_sealed / total * 100, 1)
            good_first_percent = round(good_first / total * 100, 1)

            text = (f"Для заказа <b>№{order_number}</b> проверено <b>{total}</b> насосов: <br>"
                    f"годных — <b>{good}</b> ({good_percent}%), <br>"
                    f"годных с первого предъявления — <b>{good_first}</b> ({good_first_percent}%), <br>"
                    f"негерметичных — <b>{not_sealed}</b> ({not_sealed_percent}%), ")
            self.stats_label.setText(text)
            self.stats_label.show()
        else:
            self.stats_label.hide()

    # def apply_filters(self):
    #     filters = {}
    #     search_text = self.search_input.text().strip()
    #     if search_text:
    #         filters['pump_number'] = search_text

    #     verdict = self.filter_verdict.currentText()
    #     if verdict != 'Все':
    #         filters['verdict'] = verdict.lower()

    #     test_type = self.filter_test_type.currentText()
    #     if test_type != 'Все':
    #         filters['test_type'] = test_type.lower()

    #     sealed = self.filter_sealed.currentText()
    #     if sealed == 'Герметичен':
    #         filters['is_sealed'] = 1
    #     elif sealed == 'Не герметичен':
    #         filters['is_sealed'] = 0

    #     self.display_pumps(filtered)
        
    #     # Обновляем статистику по заказу
    #     # order_text = self.filter_order.currentText() if hasattr(self, 'filter_order') else "Все заказы"
    #     # if order_text != "Все заказы":
    #     #     stats = db.get_order_stats(order_text)
    #     #     if stats and stats['total'] > 0:
    #     #         good_percent = (stats['good'] / stats['total']) * 100
    #     #         not_sealed_percent = (stats['not_sealed'] / stats['total']) * 100
    #     #         primary_percent = (stats['primary'] / stats['total']) * 100
    #     #         stats_text = (
    #     #             f"<b>Статистика для заказа № {order_text}:</b><br>"
    #     #             f"Всего насосов: {stats['total']}<br>"
    #     #             f"Годных: {stats['good']} шт. ({good_percent:.1f}%)<br>"
    #     #             f"Негерметичных: {stats['not_sealed']} шт. ({not_sealed_percent:.1f}%)<br>"
    #     #             f"С первого предъявления: {stats['primary']} шт. ({primary_percent:.1f}%)"
    #     #         )
    #     #         self.stats_label.setText(stats_text)
    #     #         self.stats_label.show()
    #     #     else:
    #     #         self.stats_label.hide()
    #     # else:
    #     #     self.stats_label.hide()

    #     # Дата
    #     date_from = self.date_from.date().toString('yyyy-MM-dd')
    #     date_to = self.date_to.date().toString('yyyy-MM-dd')
    #     if date_from != '2000-01-01' or date_to != QDate.currentDate().toString('yyyy-MM-dd'):
    #         filters['date_from'] = date_from
    #         filters['date_to'] = date_to

    #     if self.only_duplicates.isChecked():
    #         filters['only_duplicates'] = True

    #     self.current_filters = filters

    #     # Подсчёт общего количества
    #     self.total_records = db.count_pumps(filters)

    #     # Пагинация
    #     offset = self.current_page * self.page_size
    #     filtered = db.get_all_pumps(filters, limit=self.page_size, offset=offset)
    #     self.display_pumps(filtered)
    #     self.update_pagination_label()

    #     # Сигнал для статус-бара
    #     self.filters_applied.emit(filters)

    #     if hasattr(self, 'filters_applied'):
    #         self.filters_applied.emit(filters)

    #     self.update_stats(filtered)

    def apply_filters(self):
        filters = {}
        search_text = self.search_input.text().strip()
        if search_text:
            filters['pump_number'] = search_text

        verdict = self.filter_verdict.currentText()
        if verdict != 'Все':
            filters['verdict'] = verdict

        test_type = self.filter_test_type.currentText()
        if test_type != 'Все':
            filters['test_type'] = test_type

        sealed = self.filter_sealed.currentText()
        if sealed == 'Герметичен':
            filters['is_sealed'] = 1
        elif sealed == 'Не герметичен':
            filters['is_sealed'] = 0

        if hasattr(self, 'filter_order'):
            order_text = self.filter_order.currentText()
            if order_text != "Все заказы":
                filters['order_number'] = order_text

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
        self.display_pumps(filtered)
        self.update_stats(filtered)   # <-- здесь переменная определена
        self.update_pagination_label()

        if hasattr(self, 'filters_applied'):
            self.filters_applied.emit(filters)


    def display_pumps(self, pumps):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(pumps))
        for row, p in enumerate(pumps):
            item_num = QTableWidgetItem(p['pump_number'])
            item_num.setData(Qt.UserRole, p['id'])
            self.table.setItem(row, 0, item_num)

            date_str = p['test_date']
            if date_str and ' ' in date_str:
                date_str = date_str.split(' ')[0]
            self.table.setItem(row, 1, QTableWidgetItem(date_str))

            verdict_item = QTableWidgetItem(p['verdict'] or '')
            if p['verdict'] == 'годен':
                verdict_item.setBackground(QColor(200, 255, 200))
            elif p['verdict'] == 'не годен':
                verdict_item.setBackground(QColor(255, 200, 200))
            self.table.setItem(row, 2, verdict_item)

            self.table.setItem(row, 3, QTableWidgetItem(p['test_type'] or ''))

            sealed_text = 'Да' if p['is_sealed'] else 'Нет'
            sealed_item = QTableWidgetItem(sealed_text)
            if p['is_sealed']:
                sealed_item.setBackground(QColor(200, 255, 200))
            else:
                sealed_item.setBackground(QColor(255, 200, 200))
            self.table.setItem(row, 4, sealed_item)

            count = p.get('check_count', 0)
            self.table.setItem(row, 5, QTableWidgetItem(str(count)))

            print(f"display_pumps: row={row}, id={p['id']}, number={p['pump_number']}")
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(1, Qt.DescendingOrder)

    def on_selection_changed(self):
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
            print(f"DEBUG: Отображение протокола для {pump_data['pump_number']}, дата {pump_data['test_date']}")
            print(f"DEBUG on_selection_changed: mod_name={pump_data.get('mod_name')}, order={pump_data.get('order_number')}")
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
        action_view = menu.addAction("Показать протокол....")
        action_edit = menu.addAction("Вставить примечание")
        action_delete = menu.addAction("Удалить")

        action = menu.exec_(self.table.mapToGlobal(pos))

        if action == action_view:
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
        item = self.table.item(row, 0)
        if not item:
            return
        pump_id = item.data(Qt.UserRole)
        if pump_id:
            self.request_delete.emit(pump_id)

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