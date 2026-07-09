from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QCheckBox,
    QDateEdit, QHeaderView, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal, QDate
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont

import database as db
import utils

class LeftPanel(QWidget):
    # Сигналы для взаимодействия с главным окном
    pump_selected = pyqtSignal(dict)  # при выборе записи
    request_import = pyqtSignal()     # запрос на импорт Excel
    request_add = pyqtSignal()        # запрос на добавление вручную
    request_delete = pyqtSignal(int)  # запрос на удаление записи
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_filters = {}
        self.all_pumps = []
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # ---- Строка поиска ----
        search_layout = QHBoxLayout()
        search_label = QLabel("Поиск:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите номер насоса...")
        self.search_input.textChanged.connect(self.apply_filters)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # ---- Фильтры ----
        filter_layout = QHBoxLayout()
        # Вердикт
        self.filter_verdict = QComboBox()
        self.filter_verdict.addItems(["Все", "Годен", "Не годен"])
        self.filter_verdict.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Вердикт:"))
        filter_layout.addWidget(self.filter_verdict)
        
        # Тип проверки
        self.filter_test_type = QComboBox()
        self.filter_test_type.addItems(["Все", "Первичная", "Повторная"])
        self.filter_test_type.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Тип:"))
        filter_layout.addWidget(self.filter_test_type)
        
        # Герметичность
        self.filter_sealed = QComboBox()
        self.filter_sealed.addItems(["Все", "Герметичен", "Не герметичен"])
        self.filter_sealed.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Герметичность:"))
        filter_layout.addWidget(self.filter_sealed)
        layout.addLayout(filter_layout)
        
        # ---- Дополнительные фильтры (дата, дубли) ----
        extra_layout = QHBoxLayout()
        # Дата с
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.dateChanged.connect(self.apply_filters)
        extra_layout.addWidget(QLabel("Дата с:"))
        extra_layout.addWidget(self.date_from)
        
        # Дата по
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.dateChanged.connect(self.apply_filters)
        extra_layout.addWidget(QLabel("по:"))
        extra_layout.addWidget(self.date_to)
        
        # Только дубли
        self.only_duplicates = QCheckBox("Только дубли")
        self.only_duplicates.stateChanged.connect(self.apply_filters)
        extra_layout.addWidget(self.only_duplicates)
        
        layout.addLayout(extra_layout)
        
        # ---- Таблица списка насосов ----
        self.table = QTableWidget()
        self.table.setColumnCount(6)  # Номер, Дата, Вердикт, Тип, Герметичность, Кол-во проверок
        self.table.setHorizontalHeaderLabels([
            "Номер насоса", "Дата", "Вердикт", "Тип", "Герметичность", "Кол-во проверок"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(1, Qt.DescendingOrder)  # сортировка по дате по убыванию
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        layout.addWidget(self.table)
        
        # ---- Кнопки управления ----
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
        """Загружает данные из БД и обновляет таблицу."""
        self.all_pumps = db.get_all_pumps()
        self.apply_filters()
    
    def apply_filters(self):
        """Применяет текущие фильтры к данным и обновляет таблицу."""
        filters = {}
        # Поиск по номеру
        search_text = self.search_input.text().strip()
        if search_text:
            filters['pump_number'] = search_text
        
        # Вердикт
        verdict = self.filter_verdict.currentText()
        if verdict != 'Все':
            filters['verdict'] = verdict
        
        # Тип проверки
        test_type = self.filter_test_type.currentText()
        if test_type != 'Все':
            filters['test_type'] = test_type
        
        # Герметичность
        sealed = self.filter_sealed.currentText()
        if sealed == 'Герметичен':
            filters['is_sealed'] = 1
        elif sealed == 'Не герметичен':
            filters['is_sealed'] = 0
        
        # Дата
        date_from = self.date_from.date().toString('yyyy-MM-dd')
        date_to = self.date_to.date().toString('yyyy-MM-dd')
        filters['date_from'] = date_from
        filters['date_to'] = date_to
        
        # Дубли
        if self.only_duplicates.isChecked():
            filters['only_duplicates'] = True
        
        # Получаем отфильтрованные данные из БД
        filtered = db.get_all_pumps(filters)
        self.display_pumps(filtered)
    
    def display_pumps(self, pumps):
        """Отображает список насосов в таблице."""
        self.table.setRowCount(len(pumps))
        for row, p in enumerate(pumps):
            # Номер
            self.table.setItem(row, 0, QTableWidgetItem(p['pump_number']))
            # Дата
            self.table.setItem(row, 1, QTableWidgetItem(p['test_date']))
            # Вердикт (текст + цвет фона)
            verdict_item = QTableWidgetItem(p['verdict'] or '')
            if p['verdict'] == 'годен':
                verdict_item.setBackground(QColor(200, 255, 200))
            elif p['verdict'] == 'не годен':
                verdict_item.setBackground(QColor(255, 200, 200))
            self.table.setItem(row, 2, verdict_item)
            # Тип
            self.table.setItem(row, 3, QTableWidgetItem(p['test_type'] or ''))
            # Герметичность
            sealed_text = 'Да' if p['is_sealed'] else 'Нет'
            sealed_item = QTableWidgetItem(sealed_text)
            if p['is_sealed']:
                sealed_item.setBackground(QColor(200, 255, 200))
            else:
                sealed_item.setBackground(QColor(255, 200, 200))
            self.table.setItem(row, 4, sealed_item)
            # Количество проверок
            count = p.get('check_count', 0)
            self.table.setItem(row, 5, QTableWidgetItem(str(count)))
            # Сохраняем id записи в данных строки (для последующего использования)
            self.table.item(row, 0).setData(Qt.UserRole, p['id'])
    
    def on_selection_changed(self):
        """Обработка выбора строки."""
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        pump_id = self.table.item(row, 0).data(Qt.UserRole)
        if pump_id:
            pump_data = db.get_pump_by_id(pump_id)
            if pump_data:
                self.pump_selected.emit(pump_data)
    
    def on_delete_clicked(self):
        """Запрос на удаление выбранной записи."""
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        pump_id = self.table.item(row, 0).data(Qt.UserRole)
        if pump_id:
            self.request_delete.emit(pump_id)
    
    def refresh(self):
        """Обновляет данные (после импорта, добавления, удаления)."""
        self.load_data()