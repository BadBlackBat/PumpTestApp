import sys
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QLabel, QSplitter, QPushButton, QStatusBar, QHeaderView
)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPolygon

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("База данных проверок насосов ГУР")
        self.setGeometry(100, 100, 1400, 900)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(5, 5, 5, 5)

        self.splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter)

        # ---- Левая панель ----
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Строка поиска
        search_layout = QHBoxLayout()
        search_label = QLabel("Поиск:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите номер насоса...")
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        left_layout.addLayout(search_layout)

        # Фильтры
        filter_layout = QHBoxLayout()
        self.filter_verdict = QComboBox()
        self.filter_verdict.addItems(["Все", "Годен", "Не годен"])
        self.filter_test_type = QComboBox()
        self.filter_test_type.addItems(["Все", "Первичная", "Повторная"])
        self.filter_sealed = QComboBox()
        self.filter_sealed.addItems(["Все", "Герметичен", "Не герметичен"])
        filter_layout.addWidget(QLabel("Вердикт:"))
        filter_layout.addWidget(self.filter_verdict)
        filter_layout.addWidget(QLabel("Тип:"))
        filter_layout.addWidget(self.filter_test_type)
        filter_layout.addWidget(QLabel("Герметичность:"))
        filter_layout.addWidget(self.filter_sealed)
        left_layout.addLayout(filter_layout)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Номер насоса", "Дата", "Вердикт", "Тип проверки", "Герметичность"
        ])
        self.hidden_columns = ["Заказ", "Модификация", "Примечание"]
        for col_name in self.hidden_columns:
            col = self.table.columnCount()
            self.table.insertColumn(col)
            self.table.setHorizontalHeaderItem(col, QTableWidgetItem(col_name))
            self.table.setColumnHidden(col, True)

        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        left_layout.addWidget(self.table)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Добавить")
        self.btn_delete = QPushButton("Удалить")
        self.btn_import = QPushButton("Импорт из Excel")
        self.btn_expand = QPushButton("Расширить список")
        self.btn_expand.setCheckable(True)
        self.btn_expand.toggled.connect(self.toggle_expand)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_import)
        btn_layout.addWidget(self.btn_expand)
        left_layout.addLayout(btn_layout)

        self.splitter.addWidget(left_panel)

        # ---- Правая панель ----
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.detail_label = QLabel("Выберите насос из списка слева для просмотра полного протокола.")
        self.detail_label.setAlignment(Qt.AlignCenter)
        self.detail_label.setWordWrap(True)
        self.detail_label.setFont(QFont("Arial", 12))
        right_layout.addWidget(self.detail_label)
        self.splitter.addWidget(right_panel)

        self.splitter.setSizes([int(self.width() * 0.4), int(self.width() * 0.6)])
        self.is_expanded = False

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Всего насосов: 0 | Фильтры: не применены")

        # Тестовые данные
        self.test_data = [
            {"number": "001", "date": "2026-07-01", "verdict": "Годен", "type": "Первичная", "sealed": True,
             "order": "ЗАЗ-101", "mod": "A1", "note": "Без замечаний"},
            {"number": "002", "date": "2026-07-02", "verdict": "Не годен", "type": "Повторная", "sealed": False,
             "order": "ГАЗ-202", "mod": "B2", "note": "Подтекание"},
            {"number": "003", "date": "2026-07-03", "verdict": "Годен", "type": "Первичная", "sealed": True,
             "order": "УАЗ-303", "mod": "C3", "note": ""},
        ]
        self.populate_table()
        self.table.itemSelectionChanged.connect(self.on_row_selected)

    def populate_table(self):
        self.table.setRowCount(len(self.test_data))
        for row, item in enumerate(self.test_data):
            self.table.setItem(row, 0, QTableWidgetItem(item["number"]))
            self.table.setItem(row, 1, QTableWidgetItem(item["date"]))

            icon = self.create_verdict_icon(item["verdict"] == "Годен")
            self.table.setItem(row, 2, QTableWidgetItem())
            self.table.item(row, 2).setIcon(icon)
            self.table.item(row, 2).setTextAlignment(Qt.AlignCenter)

            icon_type = self.create_type_icon(item["type"])
            self.table.setItem(row, 3, QTableWidgetItem())
            self.table.item(row, 3).setIcon(icon_type)
            self.table.item(row, 3).setTextAlignment(Qt.AlignCenter)

            icon_sealed = self.create_sealed_icon(item["sealed"])
            self.table.setItem(row, 4, QTableWidgetItem())
            self.table.item(row, 4).setIcon(icon_sealed)
            self.table.item(row, 4).setTextAlignment(Qt.AlignCenter)

            extra_col = 5
            self.table.setItem(row, extra_col, QTableWidgetItem(item.get("order", "")))
            self.table.setItem(row, extra_col+1, QTableWidgetItem(item.get("mod", "")))
            self.table.setItem(row, extra_col+2, QTableWidgetItem(item.get("note", "")))

        self.statusBar.showMessage(f"Всего насосов: {len(self.test_data)} | Фильтры: не применены")

    def create_verdict_icon(self, is_good):
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QColor(0, 200, 0) if is_good else QColor(200, 0, 0))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        return QIcon(pixmap)

    def create_type_icon(self, type_str):
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setPen(QColor(0, 0, 200))
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "I" if "Первичная" in type_str else "II")
        painter.end()
        return QIcon(pixmap)

    def create_sealed_icon(self, is_sealed):
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QColor(0, 100, 255) if is_sealed else QColor(180, 180, 180))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, 8, 8, 6)
        # Используем QPolygon, создаём из списка QPoint
        points = [QPoint(4, 8), QPoint(8, 2), QPoint(12, 8)]
        polygon = QPolygon(points)
        painter.drawPolygon(polygon)
        painter.end()
        return QIcon(pixmap)

    def toggle_expand(self, checked):
        self.is_expanded = checked
        if checked:
            self.splitter.setSizes([int(self.width() * 0.7), int(self.width() * 0.3)])
            self.btn_expand.setText("Свернуть список")
            for i in range(5, self.table.columnCount()):
                self.table.setColumnHidden(i, False)
        else:
            self.splitter.setSizes([int(self.width() * 0.4), int(self.width() * 0.6)])
            self.btn_expand.setText("Расширить список")
            for i in range(5, self.table.columnCount()):
                self.table.setColumnHidden(i, True)
        self.splitter.updateGeometry()

    def on_row_selected(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        pump_number = self.table.item(row, 0).text()
        pump_info = next((p for p in self.test_data if p["number"] == pump_number), None)
        if pump_info:
            if self.is_expanded:
                self.btn_expand.setChecked(False)
            self.show_protocol(pump_info)

    def show_protocol(self, data):
        text = (f"Протокол насоса {data['number']}\n"
                f"Дата: {data['date']}\n"
                f"Вердикт: {data['verdict']}\n"
                f"Тип: {data['type']}\n"
                f"Герметичность: {'Да' if data['sealed'] else 'Нет'}\n"
                f"Заказ: {data.get('order', '—')}\n"
                f"Модификация: {data.get('mod', '—')}\n"
                f"Примечание: {data.get('note', '—')}\n\n"
                "Здесь будут таблицы и графики.")
        self.detail_label.setText(text)