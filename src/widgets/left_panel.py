from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QCheckBox,
    QDateEdit, QHeaderView, QAbstractItemView
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_filters = {}
        self.all_pumps = []
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)

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
        layout.addLayout(filter_layout)

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
        layout.addWidget(self.table)

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
        self.apply_filters()

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

        # date_from = self.date_from.date().toString('yyyy-MM-dd')
        # date_to = self.date_to.date().toString('yyyy-MM-dd')
        # filters['date_from'] = date_from
        # filters['date_to'] = date_to

        date_from = self.date_from.date().toString('yyyy-MM-dd')
        date_to = self.date_to.date().toString('yyyy-MM-dd')
        # Применяем фильтр по дате только если даты не являются "все" (можно установить флаг)
        # Для простоты: если date_from == '2000-01-01' и date_to == сегодня, то не добавляем
        if date_from != '2000-01-01' or date_to != QDate.currentDate().toString('yyyy-MM-dd'):
                filters['date_from'] = date_from
                filters['date_to'] = date_to

        if self.only_duplicates.isChecked():
            filters['only_duplicates'] = True

        filtered = db.get_all_pumps(filters)
        self.display_pumps(filtered)

        self.filters_applied.emit(filters)
    

    def display_pumps(self, pumps):
        self.table.setSortingEnabled(False)  # отключаем сортировку
        self.table.setRowCount(len(pumps))
        for row, p in enumerate(pumps):
            # Создаём элементы
            item_num = QTableWidgetItem(p['pump_number'])
            item_num.setData(Qt.UserRole, p['id'])  # устанавливаем ID
            self.table.setItem(row, 0, item_num)
            
            # дата (обрезаем время)
            date_str = p['test_date']
            if date_str and ' ' in date_str:
                date_str = date_str.split(' ')[0]
            self.table.setItem(row, 1, QTableWidgetItem(date_str))
            
            # вердикт
            verdict_item = QTableWidgetItem(p['verdict'] or '')
            if p['verdict'] == 'годен':
                verdict_item.setBackground(QColor(200, 255, 200))
            elif p['verdict'] == 'не годен':
                verdict_item.setBackground(QColor(255, 200, 200))
            self.table.setItem(row, 2, verdict_item)
            
            # тип
            self.table.setItem(row, 3, QTableWidgetItem(p['test_type'] or ''))
            
            # герметичность
            sealed_text = 'Да' if p['is_sealed'] else 'Нет'
            sealed_item = QTableWidgetItem(sealed_text)
            if p['is_sealed']:
                sealed_item.setBackground(QColor(200, 255, 200))
            else:
                sealed_item.setBackground(QColor(255, 200, 200))
            self.table.setItem(row, 4, sealed_item)
            
            # количество проверок
            count = p.get('check_count', 0)
            self.table.setItem(row, 5, QTableWidgetItem(str(count)))
            
            print(f"display_pumps: row={row}, id={p['id']}, number={p['pump_number']}")
        self.table.setSortingEnabled(True)  # включаем сортировку обратно
        
        # Принудительно сортируем по дате (по умолчанию)
        self.table.sortByColumn(1, Qt.DescendingOrder)

    def on_selection_changed(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        # Берём первую колонку (0) текущей строки
        row = selected[0].row()
        item = self.table.item(row, 0)
        if item is None:
            return
        pump_id = item.data(Qt.UserRole)
        print(f"on_selection_changed: row={row}, pump_id={pump_id}")
        if pump_id is None:
            print("pump_id is None, пропускаем")
            return
        pump_data = db.get_pump_by_id(pump_id)
        if pump_data:
            print(f"DEBUG: Отображение протокола для {pump_data['pump_number']}, дата {pump_data['test_date']}")
            self.pump_selected.emit(pump_data)

    def on_delete_clicked(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        pump_id = self.table.item(row, 0).data(Qt.UserRole)
        if pump_id:
            self.request_delete.emit(pump_id)

    def refresh(self):
        self.load_data()
    
    def reset_filters(self):
        self.search_input.clear()
        self.filter_verdict.setCurrentIndex(0)
        self.filter_test_type.setCurrentIndex(0)
        self.filter_sealed.setCurrentIndex(0)
        self.date_from.setDate(QDate(2000, 1, 1))
        self.date_to.setDate(QDate.currentDate())
        self.only_duplicates.setChecked(False)
        self.apply_filters()
    
    filters_applied = pyqtSignal(dict)