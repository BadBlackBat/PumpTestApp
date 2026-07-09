from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QScrollArea
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

import database as db
from utils import is_value_in_range
# Или можно импортировать конкретную функцию:
# from utils import is_value_in_range

class RightPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_data = None
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        # Область прокрутки для всего содержимого
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        
        # Заголовок протокола (шапка)
        self.header_label = QLabel("Выберите насос для просмотра протокола")
        self.header_label.setAlignment(Qt.AlignCenter)
        self.header_label.setWordWrap(True)
        self.header_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.content_layout.addWidget(self.header_label)
        
        # Таблицы (будем добавлять динамически)
        self.tables_widget = QWidget()
        self.tables_layout = QVBoxLayout(self.tables_widget)
        self.content_layout.addWidget(self.tables_widget)
        
        # Графики (заглушка)
        self.graphs_label = QLabel("Здесь будут графики")
        self.graphs_label.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(self.graphs_label)
        
        # Легенда
        self.legend_label = QLabel()
        self.legend_label.setWordWrap(True)
        self.legend_label.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        self.content_layout.addWidget(self.legend_label)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
    
    def display_protocol(self, data):
        """Отображает протокол для выбранного насоса."""
        self.current_data = data
        self.clear_protocol()
        
        # Шапка
        header_text = (f"Характеристики образца насоса ГУР\n"
                       f"Протокол проверки насоса ГУР от: {data['test_date']}\n"
                       f"Идентификационный №: {data['pump_number']}  Заказ: {data.get('order_number', '—')}\n"
                       f"Проверка: {data['test_type']}\n"
                       f"Модификация: {data.get('mod_name', '—')}\n"
                       f"Герметичен: {'Да' if data['is_sealed'] else 'Нет'}\n"
                       f"Вердикт: {data['verdict']}")
        self.header_label.setText(header_text)
        
        # Создаём таблицы для каждого теста
        # Тест 1: G5-G12 (обороты → расход)
        self.create_test_table("Тест 1: Зависимость расхода от оборотов (ECO выкл.)",
                               list(range(5, 13)), 
                               data['results_json'], 
                               data.get('mod_name'))
        
        # Тест 2: G13-G20
        self.create_test_table("Тест 2: Зависимость расхода от оборотов (ECO вкл.)",
                               list(range(13, 21)), 
                               data['results_json'], 
                               data.get('mod_name'))
        
        # Тест 3: G21-G31 (сила тока)
        self.create_test_table("Тест 3: Зависимость расхода от силы тока ECO (I=0..1A)",
                               list(range(21, 32)), 
                               data['results_json'], 
                               data.get('mod_name'))
        
        # Тест 4: Давление настройки клапана (G32)
        self.create_pressure_table(data)
        
        # Герметичность (G33-G37)
        self.create_seal_table(data)
        
        # Легенда
        self.legend_label.setText("Красная подсветка – значение не соответствует техническим требованиям.")
    
    def create_test_table(self, title, indices, results, mod_name):
        """Создаёт таблицу для теста с индексами G5..G32."""
        # Получаем нормативы для модификации
        mod = None
        if mod_name:
            mod = db.get_modification_by_name(mod_name)
        
        # Определяем, какой это тест
        if indices[0] == 5:   # тест 1
            norm_min = mod['norm_graph1_min'] if mod else []
            norm_max = mod['norm_graph1_max'] if mod else []
            x_label = "Обороты, об/мин"
        elif indices[0] == 13: # тест 2
            norm_min = mod['norm_graph2_min'] if mod else []
            norm_max = mod['norm_graph2_max'] if mod else []
            x_label = "Обороты, об/мин"
        elif indices[0] == 21: # тест 3
            norm_min = mod['norm_graph3_min'] if mod else []
            norm_max = mod['norm_graph3_max'] if mod else []
            x_label = "Сила тока, А"
        else:
            norm_min = []
            norm_max = []
            x_label = ""
        
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels([x_label, "Расход, л/мин", "Мин. треб.", "Макс. треб."])
        table.setRowCount(len(indices))
        
        for i, idx in enumerate(indices):
            key = f'g{idx}'
            val = results.get(key)
            # Значение по оси X (обороты или ток)
            if idx <= 12:
                x_vals = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 7500]
                x_val = x_vals[i] if i < len(x_vals) else ''
            elif 13 <= idx <= 20:
                x_vals = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 7500]
                x_val = x_vals[i] if i < len(x_vals) else ''
            elif 21 <= idx <= 31:
                x_vals = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
                x_val = x_vals[i] if i < len(x_vals) else ''
            else:
                x_val = ''
            
            table.setItem(i, 0, QTableWidgetItem(str(x_val)))
            
            # Значение расхода
            val_item = QTableWidgetItem(str(val) if val is not None else '')
            # Проверяем попадание в диапазон
            if val is not None and i < len(norm_min) and i < len(norm_max):
                if not is_value_in_range(val, norm_min[i], norm_max[i]):
                    val_item.setBackground(QColor(255, 200, 200))
            # Если значение пустое, подсвечиваем красным
            elif val is None:
                val_item.setBackground(QColor(255, 200, 200))
            table.setItem(i, 1, val_item)
            
            # Нормативы
            min_val = norm_min[i] if i < len(norm_min) else ''
            max_val = norm_max[i] if i < len(norm_max) else ''
            table.setItem(i, 2, QTableWidgetItem(str(min_val) if min_val != '' else ''))
            table.setItem(i, 3, QTableWidgetItem(str(max_val) if max_val != '' else ''))
        
        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Добавляем заголовок таблицы
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.tables_layout.addWidget(title_label)
        self.tables_layout.addWidget(table)
    
    def create_pressure_table(self, data):
        """Таблица для максимального давления (G32)."""
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
        table.setItem(0, 0, QTableWidgetItem("Макс. давление, бар"))
        val_item = QTableWidgetItem(str(pressure_val) if pressure_val is not None else '')
        if pressure_val is not None and min_p is not None and max_p is not None:
            if not is_value_in_range(pressure_val, min_p, max_p):
                val_item.setBackground(QColor(255, 200, 200))
        elif pressure_val is None:
            val_item.setBackground(QColor(255, 200, 200))
        table.setItem(0, 1, val_item)
        table.setItem(0, 2, QTableWidgetItem(f"{min_p} – {max_p}" if min_p is not None and max_p is not None else ''))
        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        title_label = QLabel("Тест 4: Давление настройки предохранительного клапана")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.tables_layout.addWidget(title_label)
        self.tables_layout.addWidget(table)
    
    def create_seal_table(self, data):
        """Таблица герметичности (G33-G37)."""
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
            table.setItem(i, 0, QTableWidgetItem(label))
            val = seal.get(key)
            val_item = QTableWidgetItem(str(val) if val is not None else '')
            # Подсветка
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
        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        title_label = QLabel("Герметичность")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.tables_layout.addWidget(title_label)
        self.tables_layout.addWidget(table)
    
    def clear_protocol(self):
        """Очищает содержимое протокола (кроме заголовка)."""
        # Удаляем все виджеты из tables_layout, кроме заголовка
        while self.tables_layout.count():
            child = self.tables_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        # Очищаем легенду
        self.legend_label.setText("")
        # Графики пока не трогаем