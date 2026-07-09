from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

from .. import database as db
from ..utils import is_value_in_range

class RightPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_data = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        content = QWidget()
        self.content_layout = QVBoxLayout(content)

        self.header_label = QLabel("Выберите насос для просмотра протокола")
        self.header_label.setAlignment(Qt.AlignCenter)
        self.header_label.setWordWrap(True)
        self.header_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.content_layout.addWidget(self.header_label)

        self.tables_widget = QWidget()
        self.tables_layout = QVBoxLayout(self.tables_widget)
        self.content_layout.addWidget(self.tables_widget)

        self.graphs_widget = QWidget()
        self.graphs_layout = QVBoxLayout(self.graphs_widget)
        self.content_layout.addWidget(self.graphs_widget)

        self.legend_label = QLabel()
        self.legend_label.setWordWrap(True)
        self.legend_label.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        self.content_layout.addWidget(self.legend_label)

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def display_protocol(self, data):
        self.current_data = data
        self.clear_protocol()  # полностью пересоздаём содержимое

        # Обрезаем время
        date_str = data['test_date']
        if date_str and ' ' in date_str:
            date_str = date_str.split(' ')[0]

        header_text = (f"Характеристики образца насоса ГУР\n"
                    f"Протокол проверки насоса ГУР от: {date_str}\n"
                    f"Идентификационный №: {data['pump_number']}  Заказ №: {data.get('order_number', '—')}\n"
                    f"Проверка: {data['test_type']}\n"
                    f"Модификация: {data.get('mod_name', '—')}\n"
                    f"Герметичен: {'Да' if data['is_sealed'] else 'Нет'}\n"
                    f"Вердикт: {data['verdict']}")
        self.header_label.setText(header_text)

        # Таблицы
        self.create_test_table("Тест 1: Зависимость расхода от оборотов (ECO выкл.)",
                            list(range(5, 13)), data['results_json'], data.get('mod_name'))
        self.create_test_table("Тест 2: Зависимость расхода от оборотов (ECO вкл.)",
                            list(range(13, 21)), data['results_json'], data.get('mod_name'))
        self.create_test_table("Тест 3: Зависимость расхода от силы тока ECO",
                            list(range(21, 32)), data['results_json'], data.get('mod_name'))
        self.create_pressure_table(data)
        self.create_seal_table(data)
        self.create_graphs(data)

        # Легенда
        self.legend_label.setText("Красная подсветка – значение не соответствует техническим требованиям.")

        # Примечание
        note = data.get('note', '').strip()
        if note:
            header_text += f"\nПримечание: {note}"
        # История редактирования
        edit_history = data.get('edit_history')
        if edit_history:
            history_label = QLabel(f"История редактирования:\n{edit_history}")
            history_label.setWordWrap(True)
            history_label.setStyleSheet("background-color: #f0f0f0; padding: 5px; margin-top: 10px;")
            self.content_layout.addWidget(history_label)




    def create_test_table(self, title, indices, results, mod_name):
        mod = None
        if mod_name:
            mod = db.get_modification_by_name(mod_name)

        if indices[0] == 5:
            norm_min = mod['norm_graph1_min'] if mod else []
            norm_max = mod['norm_graph1_max'] if mod else []
            x_label = "Обороты, об/мин"
            x_vals = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 7500]
        elif indices[0] == 13:
            norm_min = mod['norm_graph2_min'] if mod else []
            norm_max = mod['norm_graph2_max'] if mod else []
            x_label = "Обороты, об/мин"
            x_vals = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 7500]
        elif indices[0] == 21:
            norm_min = mod['norm_graph3_min'] if mod else []
            norm_max = mod['norm_graph3_max'] if mod else []
            x_label = "Сила тока, А"
            x_vals = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        else:
            norm_min = []
            norm_max = []
            x_label = ""
            x_vals = []

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels([x_label, "Расход, л/мин", "Мин. треб.", "Макс. треб."])
        table.setRowCount(len(indices))

        for i, idx in enumerate(indices):
            key = f'g{idx}'
            val = results.get(key)
            x_val = x_vals[i] if i < len(x_vals) else ''
            table.setItem(i, 0, QTableWidgetItem(str(x_val)))

            # val_item = QTableWidgetItem(str(val) if val is not None else '')
            if val is not None:
                try:
                    val_text = f"{float(val):.2f}"
                except:
                    val_text = str(val)
            else:
                val_text = ''
            val_item = QTableWidgetItem(val_text)
            
            if val is not None and i < len(norm_min) and i < len(norm_max):
                if not is_value_in_range(val, norm_min[i], norm_max[i]):
                    val_item.setBackground(QColor(255, 200, 200))
            elif val is None:
                val_item.setBackground(QColor(255, 200, 200))
            table.setItem(i, 1, val_item)

            min_val = norm_min[i] if i < len(norm_min) else ''
            max_val = norm_max[i] if i < len(norm_max) else ''
            table.setItem(i, 2, QTableWidgetItem(str(min_val) if min_val != '' else ''))
            table.setItem(i, 3, QTableWidgetItem(str(max_val) if max_val != '' else ''))

        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.NoEditTriggers)

        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.tables_layout.addWidget(title_label)
        self.tables_layout.addWidget(table)

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

    def create_graphs(self, data):
        print(f"DEBUG: Построение графиков для {data['pump_number']}")
        mod = None
        if data.get('mod_name'):
            mod = db.get_modification_by_name(data['mod_name'])
        if not mod:
            label = QLabel("Нормативы не найдены для этой модификации")
            self.graphs_layout.addWidget(label)
            return

        results = data['results_json']

        # График 1
        fig1 = Figure(figsize=(6, 3), dpi=100)
        ax1 = fig1.add_subplot(111)
        x_vals = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 7500]
        y1 = [results.get(f'g{i}') for i in range(5, 13)]
        y2 = [results.get(f'g{i}') for i in range(13, 21)]
        min1 = mod['norm_graph1_min']
        max1 = mod['norm_graph1_max']
        min2 = mod['norm_graph2_min']
        max2 = mod['norm_graph2_max']

        y1_plot = [v if v is not None else np.nan for v in y1]
        y2_plot = [v if v is not None else np.nan for v in y2]

        ax1.plot(x_vals, y1_plot, 'b-o', label='ECO выкл.', linewidth=2)
        ax1.plot(x_vals, y2_plot, 'r-o', label='ECO вкл.', linewidth=2)
        if len(min1) == len(x_vals):
            ax1.plot(x_vals, min1, 'b--', label='Мин. треб. ECO выкл.', alpha=0.7)
            ax1.plot(x_vals, max1, 'b:', label='Макс. треб. ECO выкл.', alpha=0.7)
        if len(min2) == len(x_vals):
            ax1.plot(x_vals, min2, 'r--', label='Мин. треб. ECO вкл.', alpha=0.7)
            ax1.plot(x_vals, max2, 'r:', label='Макс. треб. ECO вкл.', alpha=0.7)
        ax1.set_xlabel('Обороты, об/мин')
        ax1.set_ylabel('Расход, л/мин')
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='best', fontsize=8)
        ax1.set_title('Зависимость расхода от оборотов')

        canvas1 = FigureCanvas(fig1)
        canvas1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.graphs_layout.addWidget(canvas1)

        # График 2
        fig2 = Figure(figsize=(6, 3), dpi=100)
        ax2 = fig2.add_subplot(111)
        x_tok = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        y3 = [results.get(f'g{i}') for i in range(21, 32)]
        y3_plot = [v if v is not None else np.nan for v in y3]

        ax2.plot(x_tok, y3_plot, 'g-o', label='Расход', linewidth=2)
        min3 = mod['norm_graph3_min']
        max3 = mod['norm_graph3_max']
        if len(min3) == len(x_tok):
            ax2.plot(x_tok, min3, 'g--', label='Мин. треб.', alpha=0.7)
            ax2.plot(x_tok, max3, 'g:', label='Макс. треб.', alpha=0.7)
        ax2.set_xlabel('Сила тока, А')
        ax2.set_ylabel('Расход, л/мин')
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='best', fontsize=8)
        ax2.set_title('Зависимость расхода от силы тока ECO')

        canvas2 = FigureCanvas(fig2)
        canvas2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.graphs_layout.addWidget(canvas2)

    def clear_protocol(self):
    # Удаляем все виджеты из content_layout
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        # Заново создаём основные виджеты
        self.header_label = QLabel()
        self.header_label.setAlignment(Qt.AlignCenter)
        self.header_label.setWordWrap(True)
        self.header_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.content_layout.addWidget(self.header_label)
        
        self.tables_widget = QWidget()
        self.tables_layout = QVBoxLayout(self.tables_widget)
        self.content_layout.addWidget(self.tables_widget)
        
        self.graphs_widget = QWidget()
        self.graphs_layout = QVBoxLayout(self.graphs_widget)
        self.content_layout.addWidget(self.graphs_widget)
        
        self.legend_label = QLabel()
        self.legend_label.setWordWrap(True)
        self.legend_label.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        self.content_layout.addWidget(self.legend_label)

    # def clear_protocol(self):
    #     while self.tables_layout.count():
    #         child = self.tables_layout.takeAt(0)
    #         if child.widget():
    #             child.widget().deleteLater()
    #     while self.graphs_layout.count():
    #         child = self.graphs_layout.takeAt(0)
    #         if child.widget():
    #             child.widget().deleteLater()
    #     self.legend_label.setText("")