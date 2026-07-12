from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

from .. import database as db
from .. import utils
from ..utils import is_value_in_range
from ..utils import format_order_number

class RightPanel(QWidget):
    clear_requested = pyqtSignal()   # сигнал для запроса сброса

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

        # Постоянные виджеты
        self.clear_btn = QPushButton("Скрыть протокол")
        self.clear_btn.clicked.connect(self.clear_protocol)
        self.content_layout.addWidget(self.clear_btn)

        self.header_label = QLabel("Выберите насос для просмотра протокола")
        self.header_label.setAlignment(Qt.AlignCenter)
        self.header_label.setWordWrap(True)
        self.header_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.content_layout.addWidget(self.header_label)


        self.logo_label = QLabel("Здесь будет логотип\nВыберите насос для просмотра протокола")
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setFont(QFont("Arial", 14))
        self.logo_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; padding: 20px;")
        self.content_layout.addWidget(self.logo_label)

        # Легенда (постоянная)
        self.legend_label = QLabel()
        self.legend_label.setWordWrap(True)
        self.legend_label.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        self.content_layout.addWidget(self.legend_label)

        # Динамический контейнер
        self.dynamic_widget = QWidget()
        self.dynamic_layout = QVBoxLayout(self.dynamic_widget)
        self.content_layout.addWidget(self.dynamic_widget)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Начальное состояние: показываем логотип, скрываем остальное
        self.header_label.hide()
        self.clear_btn.hide()
        self.legend_label.hide()
        self.logo_label.show()

    def display_statistics(self, stats_data):
        """Отображает сводную статистику в правой панели."""
        self._clear_dynamic_content()  # очищаем динамическую область
        self.logo_label.hide()
        self.header_label.hide()  # скрываем заголовок протокола
        self.clear_btn.hide()

        # Строим HTML-отчёт
        html = "<h2>Сводная статистика по базе данных</h2>"
        html += f"<p><b>Всего проверено насосов:</b> {stats_data['total']} шт — 100%</p>"
        html += f"<p><b>Из них годных:</b> {stats_data['good']} шт — {stats_data['good_percent']:.1f}%</p>"
        html += f"<p><b>Годных с первого предъявления:</b> {stats_data['good_first']} шт — {stats_data['good_first_percent']:.1f}%</p>"
        html += f"<p><b>Не годных:</b> {stats_data['bad']} шт — {stats_data['bad_percent']:.1f}%</p>"
        html += f"<p><b>Из них не герметичны:</b> {stats_data['not_sealed']} шт — {stats_data['not_sealed_percent']:.1f}%</p>"

        # Статистика по заказам
        if stats_data['orders']:
            html += "<h3>Статистика по заказам:</h3>"
            for order in stats_data['orders']:
                order_num = format_order_number(order['order_number'])
                html += f"<p><b>Заказ №{order_num}:</b></p>"
                # html += f"<p><b>Заказ №{order['order_number']}:</b></p>"
                html += f"<ul>"
                html += f"<li>Всего проверено: {order['total']} шт</li>"
                html += f"<li>Годных: {order['good']} шт</li>"
                html += f"<li>Годных с первого предъявления: {order['good_first']} шт</li>"
                html += f"<li>Не годных: {order['bad']} шт</li>"
                html += f"<li>Не герметичны: {order['not_sealed']} шт</li>"
                html += "</ul>"
        else:
            html += "<p>Нет данных по заказам.</p>"

        # Создаём QLabel с HTML и добавляем в dynamic_layout
        label = QLabel(html)
        label.setWordWrap(True)
        label.setStyleSheet("background-color: white; padding: 10px;")
        self.dynamic_layout.addWidget(label)
        self.current_data = None  # сбрасываем текущий протокол, т.к. показываем статистику

    def display_protocol(self, data):
        self.current_data = data
        self._clear_dynamic_content()  # очищаем dynamic_layout

        # Показываем постоянные виджеты
        self.logo_label.hide()
        self.header_label.show()
        self.clear_btn.show()
        self.legend_label.show()

        # Заголовок
        date_str = data['test_date']
        if date_str and ' ' in date_str:
            date_str = date_str.split(' ')[0]
            
        order_num = data.get('order_number', '—')
        if order_num != '—' and order_num is not None:
            order_num = str(order_num).replace('.0', '')
            
        header_text = (f"Характеристики образца насоса ГУР\n"
                       f"Протокол проверки насоса ГУР от: {date_str}\n"
                       f"Идентификационный №: {data['pump_number']}  Заказ: {order_num}\n"
                       f"Проверка: {data['test_type']}\n"
                       f"Модификация: {data.get('mod_name', '—')}\n"
                       f"Герметичен: {'Да' if data['is_sealed'] else 'Нет'}\n"
                       f"Вердикт: {data['verdict']}")
        self.header_label.setText(header_text)

        # Динамическое содержимое
        self.create_test_table("Тест 1: Зависимость расхода от оборотов (ECO выкл.)",
                               list(range(5, 13)), data['results_json'], data.get('mod_name'))
        self.create_test_table("Тест 2: Зависимость расхода от оборотов (ECO вкл.)",
                               list(range(13, 21)), data['results_json'], data.get('mod_name'))
        self.create_test_table("Тест 3: Зависимость расхода от силы тока ECO",
                               list(range(21, 32)), data['results_json'], data.get('mod_name'))
        self.create_pressure_table(data)
        self.create_seal_table(data)
        self.create_graphs(data)
        self.create_notes_section(data)

        self.legend_label.setText("Красная подсветка – значение не соответствует техническим требованиям.")

    def create_test_table(self, title, indices, results, mod_name):
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

        for i, idx in enumerate(indices):
            key = f'g{idx}'
            val = results.get(key)
            x_val = x_vals[i] if i < len(x_vals) else ''
            table.setItem(i, 0, QTableWidgetItem(str(x_val)))

            # Значение расхода с форматированием
            val_text = format_number(val)
            val_item = QTableWidgetItem(val_text)
            # Проверка диапазона (используем исходное значение val, не строку)
            if val is not None and i < len(norm_min) and i < len(norm_max):
                if not is_value_in_range(val, norm_min[i], norm_max[i]):
                    val_item.setBackground(QColor(255, 200, 200))
            elif val is None:
                val_item.setBackground(QColor(255, 200, 200))
            table.setItem(i, 1, val_item)

            # Минимальное и максимальное требования с форматированием
            min_val = norm_min[i] if i < len(norm_min) else None
            max_val = norm_max[i] if i < len(norm_max) else None
            min_text = format_number(min_val)
            max_text = format_number(max_val)
            table.setItem(i, 2, QTableWidgetItem(min_text))
            table.setItem(i, 3, QTableWidgetItem(max_text))

        table.verticalHeader().setVisible(False)
        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.NoEditTriggers)

        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.dynamic_layout.addWidget(title_label)
        self.dynamic_layout.addWidget(table)

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
        table.verticalHeader().setVisible(False)
        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.NoEditTriggers)

        title_label = QLabel("Тест 4: Давление настройки предохранительного клапана")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.dynamic_layout.addWidget(title_label)
        self.dynamic_layout.addWidget(table)

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
        
        table.verticalHeader().setVisible(False)
        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.NoEditTriggers)

        title_label = QLabel("Герметичность")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.dynamic_layout.addWidget(title_label)
        self.dynamic_layout.addWidget(table)

    def create_graphs(self, data):
        mod = None
        if data.get('mod_name'):
            mod = db.get_modification_by_name(data['mod_name'])
        if not mod:
            label = QLabel("Нормативы не найдены для этой модификации")
            self.dynamic_layout.addWidget(label)
            return

        results = data['results_json']

        # График 1
        fig1 = Figure(figsize=(6, 4), dpi=100)
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

        ax1.plot(x_vals_plot, y1_plot, 'b-o', label='ECO выкл.', linewidth=2)
        ax1.plot(x_vals_plot, y2_plot, 'r-o', label='ECO вкл.', linewidth=2)
        if len(min1) == len(x_vals_plot):
            ax1.plot(x_vals_plot, min1, 'b--', label='Мин. треб. ECO выкл.', alpha=0.7)
            ax1.plot(x_vals_plot, max1, 'b:', label='Макс. треб. ECO выкл.', alpha=0.7)
        if len(min2) == len(x_vals_plot):
            ax1.plot(x_vals_plot, min2, 'r--', label='Мин. треб. ECO вкл.', alpha=0.7)
            ax1.plot(x_vals_plot, max2, 'r:', label='Макс. треб. ECO вкл.', alpha=0.7)
        ax1.set_xlabel('Обороты, об/мин')
        ax1.set_ylabel('Расход, л/мин')
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='best', fontsize=8)
        ax1.set_title('Зависимость расхода от оборотов')

        canvas1 = FigureCanvas(fig1)
        canvas1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.dynamic_layout.addWidget(canvas1)

        # График 2
        fig2 = Figure(figsize=(6, 4), dpi=100)
        ax2 = fig2.add_subplot(111)
        x_tok = mod.get('norm_graph3_x') or list(utils.DEFAULT_GRAPH3_X)
        y3 = [results.get(f'g{i}') for i in range(21, 32)]
        n3 = min(len(x_tok), len(y3))
        x_tok_plot = x_tok[:n3]
        y3_plot = [v if v is not None else np.nan for v in y3[:n3]]

        ax2.plot(x_tok_plot, y3_plot, 'g-o', label='Расход', linewidth=2)
        min3 = mod['norm_graph3_min']
        max3 = mod['norm_graph3_max']
        if len(min3) == len(x_tok_plot):
            ax2.plot(x_tok_plot, min3, 'g--', label='Мин. треб.', alpha=0.7)
            ax2.plot(x_tok_plot, max3, 'g:', label='Макс. треб.', alpha=0.7)
        ax2.set_xlabel('Сила тока, А')
        ax2.set_ylabel('Расход, л/мин')
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='best', fontsize=8)
        ax2.set_title('Зависимость расхода от силы тока ECO')

        canvas2 = FigureCanvas(fig2)
        canvas2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.dynamic_layout.addWidget(canvas2)

    def create_notes_section(self, data):
        note = data.get('note', '')
        if note:
            note_label = QLabel(f"<b>Примечание:</b> {note}")
            note_label.setWordWrap(True)
            self.dynamic_layout.addWidget(note_label)

        edit_history = data.get('edit_history', '')
        if edit_history:
            history_label = QLabel("<b>История редактирования:</b>")
            history_label.setWordWrap(True)
            self.dynamic_layout.addWidget(history_label)

            btn_manage = QPushButton("Управлять историей")
            btn_manage.clicked.connect(lambda: self.manage_history(data))
            self.dynamic_layout.addWidget(btn_manage)

            for line in edit_history.strip().split('\n'):
                if line.strip():
                    line_label = QLabel(f"  {line.strip()}")
                    line_label.setWordWrap(True)
                    self.dynamic_layout.addWidget(line_label)

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
        self._clear_dynamic_content()
        self.clear_requested.emit()

    def _clear_dynamic_content(self):
        """Внутренняя очистка динамической области перед перерисовкой нового
        протокола/статистики. НЕ эмитит сигнал наружу, чтобы не сбрасывать
        фильтры при обычном выборе насоса из списка."""
        while self.dynamic_layout.count():
            child = self.dynamic_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        # Скрываем постоянные виджеты, показываем логотип
        self.header_label.hide()
        self.clear_btn.hide()
        self.legend_label.hide()
        self.logo_label.show()