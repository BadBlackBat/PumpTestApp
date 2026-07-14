# from PyQt5.QtWidgets import (
#     QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
#     QTableWidgetItem, QPushButton, QScrollArea, QSizePolicy,
#     QFileDialog, QMessageBox
# )
# from PyQt5.QtCore import Qt, pyqtSignal
# from PyQt5.QtGui import QColor, QFont, QPainter
# from PyQt5.QtPrintSupport import QPrinter

# import matplotlib
# matplotlib.use('Qt5Agg')
# from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
# from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
# from matplotlib.figure import Figure
# import numpy as np

# from .. import database as db
# from .. import utils
# from ..utils import is_value_in_range
# from ..utils import format_order_number

# class RightPanel(QWidget):
#     clear_requested = pyqtSignal()   # сигнал для запроса сброса

#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.current_data = None
#         self._graph_toolbars = []
#         self.setup_ui()

#     def setup_ui(self):
#         layout = QVBoxLayout(self)
#         scroll = QScrollArea()
#         scroll.setWidgetResizable(True)
#         scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
#         scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

#         content = QWidget()
#         self.content_widget = content  # нужен целиком для экспорта в PDF
#         self.content_layout = QVBoxLayout(content)

#         # Постоянные виджеты
#         top_btns_layout = QHBoxLayout()
#         self.clear_btn = QPushButton("Скрыть протокол")
#         self.clear_btn.clicked.connect(self.clear_protocol)
#         top_btns_layout.addWidget(self.clear_btn)

#         self.export_pdf_btn = QPushButton("Экспорт в PDF")
#         self.export_pdf_btn.clicked.connect(self.export_to_pdf)
#         top_btns_layout.addWidget(self.export_pdf_btn)
#         self.content_layout.addLayout(top_btns_layout)

#         self.header_label = QLabel("Выберите насос для просмотра протокола")
#         self.header_label.setAlignment(Qt.AlignCenter)
#         self.header_label.setWordWrap(True)
#         self.header_label.setFont(QFont("Arial", 12, QFont.Bold))
#         self.content_layout.addWidget(self.header_label)


#         self.logo_label = QLabel("Здесь будет логотип\nВыберите насос для просмотра протокола")
#         self.logo_label.setAlignment(Qt.AlignCenter)
#         self.logo_label.setFont(QFont("Arial", 14))
#         self.logo_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; padding: 20px;")
#         self.content_layout.addWidget(self.logo_label)

#         # Легенда (постоянная)
#         self.legend_label = QLabel()
#         self.legend_label.setWordWrap(True)
#         self.legend_label.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
#         self.content_layout.addWidget(self.legend_label)

#         # Динамический контейнер: слева таблицы, справа графики.
#         # Сами колонки создаются один раз и больше не пересоздаются -
#         # при перерисовке протокола очищается только их содержимое
#         # (см. _clear_dynamic_content), чтобы двухколоночная структура
#         # не ломалась между показами разных протоколов.
#         self.dynamic_widget = QWidget()
#         self.dynamic_layout = QHBoxLayout(self.dynamic_widget)
#         self.tables_column = QVBoxLayout()
#         self.graphs_column = QVBoxLayout()
#         self.dynamic_layout.addLayout(self.tables_column, 0)
#         self.dynamic_layout.addLayout(self.graphs_column, 1)
#         self.content_layout.addWidget(self.dynamic_widget)

#         scroll.setWidget(content)
#         layout.addWidget(scroll)

#         # Начальное состояние: показываем логотип, скрываем остальное
#         self.header_label.hide()
#         self.clear_btn.hide()
#         self.export_pdf_btn.hide()
#         self.legend_label.hide()
#         self.logo_label.show()

#     def display_statistics(self, stats_data):
#         """Отображает сводную статистику в правой панели."""
#         self._clear_dynamic_content()  # очищаем динамическую область
#         self.logo_label.hide()
#         self.header_label.hide()  # скрываем заголовок протокола
#         self.clear_btn.hide()
#         self.export_pdf_btn.hide()

#         # Строим HTML-отчёт
#         html = "<h2>Сводная статистика по базе данных</h2>"
#         html += f"<p><b>Всего проверено насосов:</b> {stats_data['total']} шт — 100%</p>"
#         html += f"<p><b>Из них годных:</b> {stats_data['good']} шт — {stats_data['good_percent']:.1f}%</p>"
#         html += f"<p><b>Годных с первого предъявления:</b> {stats_data['good_first']} шт — {stats_data['good_first_percent']:.1f}%</p>"
#         html += f"<p><b>Не годных:</b> {stats_data['bad']} шт — {stats_data['bad_percent']:.1f}%</p>"
#         html += f"<p><b>Из них не герметичны:</b> {stats_data['not_sealed']} шт — {stats_data['not_sealed_percent']:.1f}%</p>"

#         # Статистика по заказам
#         if stats_data['orders']:
#             html += "<h3>Статистика по заказам:</h3>"
#             for order in stats_data['orders']:
#                 order_num = format_order_number(order['order_number'])
#                 html += f"<p><b>Заказ №{order_num}:</b></p>"
#                 # html += f"<p><b>Заказ №{order['order_number']}:</b></p>"
#                 html += f"<ul>"
#                 html += f"<li>Всего проверено: {order['total']} шт</li>"
#                 html += f"<li>Годных: {order['good']} шт</li>"
#                 html += f"<li>Годных с первого предъявления: {order['good_first']} шт</li>"
#                 html += f"<li>Не годных: {order['bad']} шт</li>"
#                 html += f"<li>Не герметичны: {order['not_sealed']} шт</li>"
#                 html += "</ul>"
#         else:
#             html += "<p>Нет данных по заказам.</p>"

#         # Создаём QLabel с HTML и добавляем в колонку таблиц
#         label = QLabel(html)
#         label.setWordWrap(True)
#         label.setStyleSheet("background-color: white; padding: 10px;")
#         self.tables_column.addWidget(label)
#         self.current_data = None  # сбрасываем текущий протокол, т.к. показываем статистику

#     def display_protocol(self, data):
#         self.current_data = data
#         self._clear_dynamic_content()  # очищаем dynamic_layout

#         # Показываем постоянные виджеты
#         self.logo_label.hide()
#         self.header_label.show()
#         self.clear_btn.show()
#         self.export_pdf_btn.show()
#         self.legend_label.show()

#         # Заголовок
#         date_str = data['test_date']
#         if date_str and ' ' in date_str:
#             date_str = date_str.split(' ')[0]
            
#         order_num = data.get('order_number', '—')
#         if order_num != '—' and order_num is not None:
#             order_num = str(order_num).replace('.0', '')
            
#         header_text = (f"Характеристики образца насоса ГУР\n"
#                        f"Протокол проверки насоса ГУР от: {date_str}\n"
#                        f"Идентификационный №: {data['pump_number']}  Заказ: {order_num}\n"
#                        f"Проверка: {data['test_type']}\n"
#                        f"Модификация: {data.get('mod_name', '—')}\n"
#                        f"Герметичен: {'Да' if data['is_sealed'] else 'Нет'}\n"
#                        f"Вердикт: {data['verdict']}")
#         self.header_label.setText(header_text)

#         # Динамическое содержимое
#         self.create_test_table("Тест 1: Зависимость расхода от оборотов (ECO выкл.)",
#                                list(range(5, 13)), data['results_json'], data.get('mod_name'))
#         self.create_test_table("Тест 2: Зависимость расхода от оборотов (ECO вкл.)",
#                                list(range(13, 21)), data['results_json'], data.get('mod_name'))
#         self.create_test_table("Тест 3: Зависимость расхода от силы тока ECO",
#                                list(range(21, 32)), data['results_json'], data.get('mod_name'))
#         self.create_pressure_table(data)
#         self.create_seal_table(data)
#         self.create_graphs(data)
#         self.create_notes_section(data)

#         self.legend_label.setText(
#             "<span style='background-color:#ffc8c8; border:1px solid #999;'>"
#             "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>"
#             "&nbsp;&nbsp;— значение не соответствует техническим требованиям."
#         )

#     def _compact_table(self, table):
#         """Уменьшает шрифт таблицы и подгоняет высоту и ширину точно под
#         содержимое, чтобы таблица показывалась полностью, без собственной
#         прокрутки и без пустого пространства справа - прокручиваться может
#         только вся правая панель целиком."""
#         small_font = QFont("Arial", 8)
#         table.setFont(small_font)
#         table.horizontalHeader().setFont(small_font)
#         table.verticalHeader().setDefaultSectionSize(18)
#         table.resizeRowsToContents()
#         table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
#         table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
#         table.horizontalHeader().setMinimumSectionSize(40)

#         total_height = table.horizontalHeader().height() + 4
#         for row in range(table.rowCount()):
#             total_height += table.rowHeight(row)
#         table.setFixedHeight(total_height)

#         total_width = 4  # небольшой запас на рамки/скролл-полосы
#         for col in range(table.columnCount()):
#             total_width += table.columnWidth(col)
#         table.setFixedWidth(total_width)
#         table.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

#     def create_test_table(self, title, indices, results, mod_name):
#         mod = None
#         if mod_name:
#             mod = db.get_modification_by_name(mod_name)

#         if indices[0] == 5:
#             norm_min = mod['norm_graph1_min'] if mod else []
#             norm_max = mod['norm_graph1_max'] if mod else []
#             x_label = "Обороты, об/мин"
#             x_vals = mod['norm_graph1_x'] if mod else list(utils.DEFAULT_GRAPH1_X)
#         elif indices[0] == 13:
#             norm_min = mod['norm_graph2_min'] if mod else []
#             norm_max = mod['norm_graph2_max'] if mod else []
#             x_label = "Обороты, об/мин"
#             x_vals = mod['norm_graph2_x'] if mod else list(utils.DEFAULT_GRAPH2_X)
#         elif indices[0] == 21:
#             norm_min = mod['norm_graph3_min'] if mod else []
#             norm_max = mod['norm_graph3_max'] if mod else []
#             x_label = "Сила тока, А"
#             x_vals = mod['norm_graph3_x'] if mod else list(utils.DEFAULT_GRAPH3_X)
#         else:
#             norm_min = []
#             norm_max = []
#             x_label = ""
#             x_vals = []

#         # Вспомогательная функция для форматирования чисел
#         def format_number(value):
#             if value is None or value == '':
#                 return ''
#             try:
#                 return f"{float(value):.2f}"
#             except:
#                 return str(value)

#         table = QTableWidget()
#         table.setColumnCount(4)
#         table.setHorizontalHeaderLabels([x_label, "Расход, л/мин", "Мин. треб.", "Макс. треб."])
#         table.setRowCount(len(indices))

#         for i, idx in enumerate(indices):
#             key = f'g{idx}'
#             val = results.get(key)
#             x_val = x_vals[i] if i < len(x_vals) else ''
#             table.setItem(i, 0, QTableWidgetItem(str(x_val)))

#             # Значение расхода с форматированием
#             val_text = format_number(val)
#             val_item = QTableWidgetItem(val_text)
#             # Проверка диапазона (используем исходное значение val, не строку)
#             if val is not None and i < len(norm_min) and i < len(norm_max):
#                 if not is_value_in_range(val, norm_min[i], norm_max[i]):
#                     val_item.setBackground(QColor(255, 200, 200))
#             elif val is None:
#                 val_item.setBackground(QColor(255, 200, 200))
#             table.setItem(i, 1, val_item)

#             # Минимальное и максимальное требования с форматированием
#             min_val = norm_min[i] if i < len(norm_min) else None
#             max_val = norm_max[i] if i < len(norm_max) else None
#             min_text = format_number(min_val)
#             max_text = format_number(max_val)
#             table.setItem(i, 2, QTableWidgetItem(min_text))
#             table.setItem(i, 3, QTableWidgetItem(max_text))

#         table.verticalHeader().setVisible(False)
#         table.resizeColumnsToContents()
#         table.setEditTriggers(QTableWidget.NoEditTriggers)
#         self._compact_table(table)

#         title_label = QLabel(title)
#         title_label.setFont(QFont("Arial", 9, QFont.Bold))
#         title_label.setWordWrap(True)
#         self.tables_column.addWidget(title_label)
#         self.tables_column.addWidget(table)

#     def create_pressure_table(self, data):
#         mod = None
#         if data.get('mod_name'):
#             mod = db.get_modification_by_name(data['mod_name'])
#         pressure_val = data['results_json'].get('g32')
#         min_p = mod['pressure_min'] if mod else None
#         max_p = mod['pressure_max'] if mod else None

#         table = QTableWidget()
#         table.setColumnCount(3)
#         table.setHorizontalHeaderLabels(["Параметр", "Значение", "Допустимый диапазон"])
#         table.setRowCount(1)
#         table.setItem(0, 0, QTableWidgetItem("Макс. давление, бар"))
#         val_item = QTableWidgetItem(str(pressure_val) if pressure_val is not None else '')
#         if pressure_val is not None and min_p is not None and max_p is not None:
#             if not is_value_in_range(pressure_val, min_p, max_p):
#                 val_item.setBackground(QColor(255, 200, 200))
#         elif pressure_val is None:
#             val_item.setBackground(QColor(255, 200, 200))
#         table.setItem(0, 1, val_item)
#         table.setItem(0, 2, QTableWidgetItem(f"{min_p} – {max_p}" if min_p is not None and max_p is not None else ''))
#         table.verticalHeader().setVisible(False)
#         table.resizeColumnsToContents()
#         table.setEditTriggers(QTableWidget.NoEditTriggers)
#         self._compact_table(table)

#         title_label = QLabel("Тест 4: Давление настройки предохранительного клапана")
#         title_label.setFont(QFont("Arial", 9, QFont.Bold))
#         title_label.setWordWrap(True)
#         self.tables_column.addWidget(title_label)
#         self.tables_column.addWidget(table)

#     def create_seal_table(self, data):
#         seal = data['seal_results_json']
#         labels = {
#             'g33': 'Соединение с седлом клапана ECO',
#             'g34': 'Внешняя поверхность катушки ECO',
#             'g35': 'Внешняя поверхность с торца катушки ECO',
#             'g36': 'Соединение крышки корпуса',
#             'g37': 'Масляные образования на уплотнении'
#         }
#         table = QTableWidget()
#         table.setColumnCount(2)
#         table.setHorizontalHeaderLabels(["Место проверки", "Результат"])
#         table.setRowCount(len(labels))
#         for i, (key, label) in enumerate(labels.items()):
#             table.setItem(i, 0, QTableWidgetItem(label))
#             val = seal.get(key)
#             display_text = str(val) if val is not None else ''
#             if display_text.strip().lower() == 'присутствуют в допускаемой степени':
#                 display_text = 'присутствуют в\nдопускаемой степени'
#             val_item = QTableWidgetItem(display_text)
#             if key in ['g33', 'g34', 'g35', 'g36']:
#                 if val is not None and str(val).strip().lower() != 'отсутствуют':
#                     val_item.setBackground(QColor(255, 200, 200))
#             elif key == 'g37':
#                 if val is not None:
#                     text = str(val).strip().lower()
#                     if text == 'присутствуют в допускаемой степени':
#                         val_item.setBackground(QColor(255, 255, 150))
#                     elif text != 'отсутствуют':
#                         val_item.setBackground(QColor(255, 200, 200))
#             table.setItem(i, 1, val_item)
        
#         table.verticalHeader().setVisible(False)
#         table.resizeColumnsToContents()
#         table.setEditTriggers(QTableWidget.NoEditTriggers)
#         self._compact_table(table)

#         title_label = QLabel("Герметичность")
#         title_label.setFont(QFont("Arial", 9, QFont.Bold))
#         title_label.setWordWrap(True)
#         self.tables_column.addWidget(title_label)
#         self.tables_column.addWidget(table)

#     def _plot_series(self, ax, x_vals, y_vals, norm_min, norm_max, color, linestyle, label):
#         """Рисует линию БЕЗ маркеров на промежуточных точках; точки, не
#         соответствующие нормативам, отмечает красным кружком поверх линии."""
#         ax.plot(x_vals, y_vals, linestyle=linestyle, color=color, linewidth=2, label=label)
#         out_of_range_x, out_of_range_y = [], []
#         for i, v in enumerate(y_vals):
#             if v is None or (isinstance(v, float) and np.isnan(v)):
#                 continue
#             if i < len(norm_min) and i < len(norm_max) and norm_min[i] is not None and norm_max[i] is not None:
#                 if not is_value_in_range(v, norm_min[i], norm_max[i]):
#                     out_of_range_x.append(x_vals[i])
#                     out_of_range_y.append(v)
#         if out_of_range_x:
#             ax.plot(out_of_range_x, out_of_range_y, 'o', color='red', markersize=7, zorder=5)

#     def _make_graph_widget(self, fig):
#         """Оборачивает Figure в canvas + тулбар matplotlib (зум/панорама/
#         сброс масштаба кнопкой 'Home') и возвращает готовый контейнер-виджет."""
#         canvas = FigureCanvas(fig)
#         canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
#         toolbar = NavigationToolbar(canvas, self)
#         self._graph_toolbars.append(toolbar)  # понадобится скрыть при экспорте в PDF
#         container = QWidget()
#         c_layout = QVBoxLayout(container)
#         c_layout.setContentsMargins(0, 0, 0, 0)
#         c_layout.addWidget(toolbar)
#         c_layout.addWidget(canvas)
#         return container

#     def create_graphs(self, data):
#         mod = None
#         if data.get('mod_name'):
#             mod = db.get_modification_by_name(data['mod_name'])
#         if not mod:
#             label = QLabel("Нормативы не найдены для этой модификации")
#             self.graphs_column.addWidget(label)
#             return

#         results = data['results_json']

#         # График 1: расход от оборотов (ECO выкл. / ECO вкл.)
#         fig1 = Figure(figsize=(5, 4), dpi=100)
#         ax1 = fig1.add_subplot(111)
#         x_vals = mod.get('norm_graph1_x') or list(utils.DEFAULT_GRAPH1_X)
#         y1 = [results.get(f'g{i}') for i in range(5, 13)]
#         y2 = [results.get(f'g{i}') for i in range(13, 21)]
#         min1 = mod['norm_graph1_min']
#         max1 = mod['norm_graph1_max']
#         min2 = mod['norm_graph2_min']
#         max2 = mod['norm_graph2_max']

#         # На случай, если у модификации задано меньше точек, чем стандартные 8 -
#         # выравниваем длины, чтобы matplotlib не упал на несовпадении размеров
#         n1 = min(len(x_vals), len(y1))
#         x_vals_plot = x_vals[:n1]
#         y1_plot = [v if v is not None else np.nan for v in y1[:n1]]
#         y2_plot = [v if v is not None else np.nan for v in y2[:n1]]

#         self._plot_series(ax1, x_vals_plot, y1_plot, min1, max1, 'tab:blue', '-', 'ECO выкл.')
#         self._plot_series(ax1, x_vals_plot, y2_plot, min2, max2, 'tab:red', '-', 'ECO вкл.')
#         if len(min1) == len(x_vals_plot):
#             ax1.plot(x_vals_plot, min1, '--', color='tab:blue', label='Мин./макс. треб. ECO выкл.', alpha=0.5)
#             ax1.plot(x_vals_plot, max1, '--', color='tab:blue', alpha=0.5)
#         if len(min2) == len(x_vals_plot):
#             ax1.plot(x_vals_plot, min2, ':', color='tab:red', label='Мин./макс. треб. ECO вкл.', alpha=0.5)
#             ax1.plot(x_vals_plot, max2, ':', color='tab:red', alpha=0.5)
#         ax1.set_xlabel('Обороты, об/мин')
#         ax1.set_ylabel('Расход, л/мин')
#         ax1.grid(True, alpha=0.3)
#         ax1.legend(loc='best', fontsize=7)
#         ax1.set_title('Зависимость расхода от оборотов', fontsize=10)
#         fig1.tight_layout()

#         self.graphs_column.addWidget(self._make_graph_widget(fig1))

#         # График 2: расход от силы тока ECO
#         fig2 = Figure(figsize=(5, 4), dpi=100)
#         ax2 = fig2.add_subplot(111)
#         x_tok = mod.get('norm_graph3_x') or list(utils.DEFAULT_GRAPH3_X)
#         y3 = [results.get(f'g{i}') for i in range(21, 32)]
#         n3 = min(len(x_tok), len(y3))
#         x_tok_plot = x_tok[:n3]
#         y3_plot = [v if v is not None else np.nan for v in y3[:n3]]

#         min3 = mod['norm_graph3_min']
#         max3 = mod['norm_graph3_max']
#         self._plot_series(ax2, x_tok_plot, y3_plot, min3, max3, 'tab:green', '-', 'Расход')
#         if len(min3) == len(x_tok_plot):
#             ax2.plot(x_tok_plot, min3, '--', color='tab:green', label='Мин./макс. треб.', alpha=0.5)
#             ax2.plot(x_tok_plot, max3, '--', color='tab:green', alpha=0.5)
#         ax2.set_xlabel('Сила тока, А')
#         ax2.set_ylabel('Расход, л/мин')
#         ax2.grid(True, alpha=0.3)
#         ax2.legend(loc='best', fontsize=7)
#         ax2.set_title('Зависимость расхода от силы тока ECO', fontsize=10)
#         # Оси по умолчанию (масштаб по-прежнему можно менять зумом тулбара)
#         ax2.set_xlim(0, 1)
#         ax2.set_xticks(np.arange(0, 1.01, 0.1))
#         ax2.set_ylim(4, 17)
#         ax2.set_yticks(np.arange(4, 18, 1))
#         fig2.tight_layout()

#         self.graphs_column.addWidget(self._make_graph_widget(fig2))

#     def display_comparison(self, items):
#         """items - список полных данных (с results_json) насосов-дублей:
#         одинаковый номер + модификация. Показывает сравнительные таблицы
#         и 2 графика, на каждом - линии всех найденных дублей вместе."""
#         self.current_data = None  # это не единичный протокол, экспорт PDF недоступен
#         self._clear_dynamic_content()

#         self.logo_label.hide()
#         self.header_label.show()
#         self.clear_btn.show()
#         self.legend_label.show()

#         first = items[0]
#         mod_name = first.get('mod_name')
#         mod = db.get_modification_by_name(mod_name) if mod_name else None
#         dates = [(it['test_date'].split(' ')[0] if it.get('test_date') else '—') for it in items]

#         header_text = (f"Сравнение дублей\n"
#                        f"Идентификационный №: {first['pump_number']}\n"
#                        f"Модификация: {mod_name or '—'}\n"
#                        f"Найдено протоколов: {len(items)} (даты: {', '.join(dates)})")
#         self.header_label.setText(header_text)

#         norm1_min = mod['norm_graph1_min'] if mod else []
#         norm1_max = mod['norm_graph1_max'] if mod else []
#         norm1_x = mod['norm_graph1_x'] if mod else list(utils.DEFAULT_GRAPH1_X)
#         norm2_min = mod['norm_graph2_min'] if mod else []
#         norm2_max = mod['norm_graph2_max'] if mod else []
#         norm2_x = mod['norm_graph2_x'] if mod else list(utils.DEFAULT_GRAPH2_X)
#         norm3_min = mod['norm_graph3_min'] if mod else []
#         norm3_max = mod['norm_graph3_max'] if mod else []
#         norm3_x = mod['norm_graph3_x'] if mod else list(utils.DEFAULT_GRAPH3_X)

#         self._create_comparison_table("Тест 1: расход от оборотов (ECO выкл.)",
#                                       list(range(5, 13)), items, norm1_min, norm1_max, norm1_x, "Обороты, об/мин")
#         self._create_comparison_table("Тест 2: расход от оборотов (ECO вкл.)",
#                                       list(range(13, 21)), items, norm2_min, norm2_max, norm2_x, "Обороты, об/мин")
#         self._create_comparison_table("Тест 3: расход от силы тока ECO",
#                                       list(range(21, 32)), items, norm3_min, norm3_max, norm3_x, "Сила тока, А")
#         self._create_comparison_pressure_table(items, mod)
#         self._create_comparison_seal_table(items)
#         self._create_comparison_graphs(items, mod)

#         self.legend_label.setText(
#             "Сравнение всех найденных дублей выбранного образца. "
#             "<span style='background-color:#ffc8c8; border:1px solid #999;'>"
#             "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>"
#             "&nbsp;&nbsp;— значение не соответствует техническим требованиям."
#         )

#     def _create_comparison_table(self, title, indices, items, norm_min, norm_max, x_vals, x_label):
#         def format_number(value):
#             if value is None or value == '':
#                 return ''
#             try:
#                 return f"{float(value):.2f}"
#             except (TypeError, ValueError):
#                 return str(value)

#         dates = [(it['test_date'].split(' ')[0] if it.get('test_date') else f'#{i+1}') for i, it in enumerate(items)]
#         col_labels = [x_label] + dates + ["Мин. треб.", "Макс. треб."]

#         table = QTableWidget()
#         table.setColumnCount(len(col_labels))
#         table.setHorizontalHeaderLabels(col_labels)
#         table.setRowCount(len(indices))

#         for row, idx in enumerate(indices):
#             key = f'g{idx}'
#             x_val = x_vals[row] if row < len(x_vals) else ''
#             table.setItem(row, 0, QTableWidgetItem(str(x_val)))

#             for col, it in enumerate(items):
#                 val = it['results_json'].get(key)
#                 val_item = QTableWidgetItem(format_number(val))
#                 if val is not None and row < len(norm_min) and row < len(norm_max):
#                     if not is_value_in_range(val, norm_min[row], norm_max[row]):
#                         val_item.setBackground(QColor(255, 200, 200))
#                 elif val is None:
#                     val_item.setBackground(QColor(255, 200, 200))
#                 table.setItem(row, 1 + col, val_item)

#             min_val = norm_min[row] if row < len(norm_min) else None
#             max_val = norm_max[row] if row < len(norm_max) else None
#             table.setItem(row, 1 + len(items), QTableWidgetItem(format_number(min_val)))
#             table.setItem(row, 2 + len(items), QTableWidgetItem(format_number(max_val)))

#         table.verticalHeader().setVisible(False)
#         table.resizeColumnsToContents()
#         table.setEditTriggers(QTableWidget.NoEditTriggers)
#         self._compact_table(table)

#         title_label = QLabel(title)
#         title_label.setFont(QFont("Arial", 9, QFont.Bold))
#         title_label.setWordWrap(True)
#         self.tables_column.addWidget(title_label)
#         self.tables_column.addWidget(table)

#     def _create_comparison_pressure_table(self, items, mod):
#         min_p = mod['pressure_min'] if mod else None
#         max_p = mod['pressure_max'] if mod else None

#         table = QTableWidget()
#         table.setColumnCount(3)
#         table.setHorizontalHeaderLabels(["Дата", "Давление, бар", "Допустимый диапазон"])
#         table.setRowCount(len(items))
#         for row, it in enumerate(items):
#             date_str = it['test_date'].split(' ')[0] if it.get('test_date') else f'#{row+1}'
#             table.setItem(row, 0, QTableWidgetItem(date_str))
#             pressure_val = it['results_json'].get('g32')
#             val_item = QTableWidgetItem(str(pressure_val) if pressure_val is not None else '')
#             if pressure_val is not None and min_p is not None and max_p is not None:
#                 if not is_value_in_range(pressure_val, min_p, max_p):
#                     val_item.setBackground(QColor(255, 200, 200))
#             elif pressure_val is None:
#                 val_item.setBackground(QColor(255, 200, 200))
#             table.setItem(row, 1, val_item)
#             table.setItem(row, 2, QTableWidgetItem(
#                 f"{min_p} – {max_p}" if min_p is not None and max_p is not None else ''))

#         table.verticalHeader().setVisible(False)
#         table.resizeColumnsToContents()
#         table.setEditTriggers(QTableWidget.NoEditTriggers)
#         self._compact_table(table)

#         title_label = QLabel("Тест 4: Давление настройки предохранительного клапана")
#         title_label.setFont(QFont("Arial", 9, QFont.Bold))
#         self.tables_column.addWidget(title_label)
#         self.tables_column.addWidget(table)

#     def _create_comparison_seal_table(self, items):
#         labels = {
#             'g33': 'Седло клап. ECO',
#             'g34': 'Пов. катушки ECO',
#             'g35': 'Торец катушки ECO',
#             'g36': 'Крышка корпуса',
#             'g37': 'Масл. образования',
#         }
#         table = QTableWidget()
#         table.setColumnCount(1 + len(labels))
#         table.setHorizontalHeaderLabels(["Дата"] + list(labels.values()))
#         table.setRowCount(len(items))
#         for row, it in enumerate(items):
#             date_str = it['test_date'].split(' ')[0] if it.get('test_date') else f'#{row+1}'
#             table.setItem(row, 0, QTableWidgetItem(date_str))
#             seal = it['seal_results_json']
#             for col, key in enumerate(labels.keys()):
#                 val = seal.get(key)
#                 display_text = str(val) if val is not None else ''
#                 if display_text.strip().lower() == 'присутствуют в допускаемой степени':
#                     display_text = 'присутствуют в\nдопускаемой степени'
#                 val_item = QTableWidgetItem(display_text)
#                 if key in ('g33', 'g34', 'g35', 'g36'):
#                     if val is not None and str(val).strip().lower() != 'отсутствуют':
#                         val_item.setBackground(QColor(255, 200, 200))
#                 else:
#                     if val is not None:
#                         text = str(val).strip().lower()
#                         if text == 'присутствуют в допускаемой степени':
#                             val_item.setBackground(QColor(255, 255, 150))
#                         elif text != 'отсутствуют':
#                             val_item.setBackground(QColor(255, 200, 200))
#                 table.setItem(row, 1 + col, val_item)

#         table.verticalHeader().setVisible(False)
#         table.resizeColumnsToContents()
#         table.setEditTriggers(QTableWidget.NoEditTriggers)
#         self._compact_table(table)

#         title_label = QLabel("Герметичность")
#         title_label.setFont(QFont("Arial", 9, QFont.Bold))
#         self.tables_column.addWidget(title_label)
#         self.tables_column.addWidget(table)

#     def _create_comparison_graphs(self, items, mod):
#         if not mod:
#             label = QLabel("Нормативы не найдены для этой модификации")
#             self.graphs_column.addWidget(label)
#             return

#         colors = ['tab:blue', 'tab:red', 'tab:green', 'tab:orange', 'tab:purple', 'tab:brown', 'tab:pink']

#         # График 1: расход от оборотов - линии всех дублей вместе
#         # (сплошная - ECO выкл., пунктир - ECO вкл.)
#         fig1 = Figure(figsize=(5, 4), dpi=100)
#         ax1 = fig1.add_subplot(111)
#         x_vals = mod.get('norm_graph1_x') or list(utils.DEFAULT_GRAPH1_X)
#         min1 = mod['norm_graph1_min']
#         max1 = mod['norm_graph1_max']

#         for idx, it in enumerate(items):
#             color = colors[idx % len(colors)]
#             date_str = it['test_date'].split(' ')[0] if it.get('test_date') else f'#{idx + 1}'
#             results = it['results_json']
#             y1 = [results.get(f'g{i}') for i in range(5, 13)]
#             y2 = [results.get(f'g{i}') for i in range(13, 21)]
#             n1 = min(len(x_vals), len(y1))
#             x_plot = x_vals[:n1]
#             y1_plot = [v if v is not None else np.nan for v in y1[:n1]]
#             y2_plot = [v if v is not None else np.nan for v in y2[:n1]]
#             self._plot_series(ax1, x_plot, y1_plot, min1, max1, color, '-', f'{date_str}, ECO выкл.')
#             self._plot_series(ax1, x_plot, y2_plot, min1, max1, color, '--', f'{date_str}, ECO вкл.')

#         if len(min1) == len(x_vals):
#             ax1.plot(x_vals, min1, ':', color='gray', label='Мин./макс. треб.', alpha=0.6)
#             ax1.plot(x_vals, max1, ':', color='gray', alpha=0.6)
#         ax1.set_xlabel('Обороты, об/мин')
#         ax1.set_ylabel('Расход, л/мин')
#         ax1.grid(True, alpha=0.3)
#         ax1.legend(loc='best', fontsize=6)
#         ax1.set_title('Сравнение дублей: расход от оборотов', fontsize=10)
#         fig1.tight_layout()
#         self.graphs_column.addWidget(self._make_graph_widget(fig1))

#         # График 2: расход от силы тока ECO - линии всех дублей вместе
#         fig2 = Figure(figsize=(5, 4), dpi=100)
#         ax2 = fig2.add_subplot(111)
#         x_tok = mod.get('norm_graph3_x') or list(utils.DEFAULT_GRAPH3_X)
#         min3 = mod['norm_graph3_min']
#         max3 = mod['norm_graph3_max']

#         for idx, it in enumerate(items):
#             color = colors[idx % len(colors)]
#             date_str = it['test_date'].split(' ')[0] if it.get('test_date') else f'#{idx + 1}'
#             results = it['results_json']
#             y3 = [results.get(f'g{i}') for i in range(21, 32)]
#             n3 = min(len(x_tok), len(y3))
#             x_plot = x_tok[:n3]
#             y3_plot = [v if v is not None else np.nan for v in y3[:n3]]
#             self._plot_series(ax2, x_plot, y3_plot, min3, max3, color, '-', date_str)

#         if len(min3) == len(x_tok):
#             ax2.plot(x_tok, min3, ':', color='gray', label='Мин./макс. треб.', alpha=0.6)
#             ax2.plot(x_tok, max3, ':', color='gray', alpha=0.6)
#         ax2.set_xlabel('Сила тока, А')
#         ax2.set_ylabel('Расход, л/мин')
#         ax2.grid(True, alpha=0.3)
#         ax2.legend(loc='best', fontsize=6)
#         ax2.set_title('Сравнение дублей: расход от силы тока ECO', fontsize=10)
#         ax2.set_xlim(0, 1)
#         ax2.set_xticks(np.arange(0, 1.01, 0.1))
#         ax2.set_ylim(4, 17)
#         ax2.set_yticks(np.arange(4, 18, 1))
#         fig2.tight_layout()
#         self.graphs_column.addWidget(self._make_graph_widget(fig2))

#     def export_to_pdf(self):
#         """Экспортирует текущий (единичный) протокол в PDF-файл."""
#         if not self.current_data:
#             QMessageBox.warning(self, "Экспорт в PDF", "Сначала выберите протокол для экспорта.")
#             return

#         pump_number = self.current_data.get('pump_number', 'protocol')
#         safe_number = str(pump_number).replace('/', '_').replace('\\', '_')
#         default_name = f"Протокол_{safe_number}.pdf"
#         file_path, _ = QFileDialog.getSaveFileName(
#             self, "Сохранить протокол в PDF", default_name, "PDF файлы (*.pdf)"
#         )
#         if not file_path:
#             return
#         if not file_path.lower().endswith('.pdf'):
#             file_path += '.pdf'

#         # Скрываем кнопки и тулбары графиков на время рендера - в бумажном
#         # документе элементы управления зумом неуместны
#         self.clear_btn.hide()
#         self.export_pdf_btn.hide()
#         for toolbar in self._graph_toolbars:
#             toolbar.hide()

#         try:
#             printer = QPrinter(QPrinter.HighResolution)
#             printer.setOutputFormat(QPrinter.PdfFormat)
#             printer.setOutputFileName(file_path)
#             printer.setPageSize(QPrinter.A4)
#             printer.setOrientation(QPrinter.Portrait)
#             printer.setFullPage(True)

#             widget_to_print = self.content_widget
#             w = max(widget_to_print.width(), 1)
#             h = max(widget_to_print.height(), 1)
#             page_rect = printer.pageRect()
#             scale = min(page_rect.width() / w, page_rect.height() / h)

#             painter = QPainter()
#             painter.begin(printer)
#             painter.scale(scale, scale)
#             widget_to_print.render(painter)
#             painter.end()

#             QMessageBox.information(self, "Экспорт в PDF", f"Протокол сохранён:\n{file_path}")
#         except Exception as e:
#             QMessageBox.critical(self, "Ошибка экспорта", f"Не удалось сохранить PDF:\n{e}")
#         finally:
#             self.clear_btn.show()
#             self.export_pdf_btn.show()
#             for toolbar in self._graph_toolbars:
#                 toolbar.show()

#     def create_notes_section(self, data):
#         note = data.get('note', '')
#         if note:
#             note_label = QLabel(f"<b>Примечание:</b> {note}")
#             note_label.setWordWrap(True)
#             self.tables_column.addWidget(note_label)

#         edit_history = data.get('edit_history', '')
#         if edit_history:
#             history_label = QLabel("<b>История редактирования:</b>")
#             history_label.setWordWrap(True)
#             self.tables_column.addWidget(history_label)

#             btn_manage = QPushButton("Управлять историей")
#             btn_manage.clicked.connect(lambda: self.manage_history(data))
#             self.tables_column.addWidget(btn_manage)

#             for line in edit_history.strip().split('\n'):
#                 if line.strip():
#                     line_label = QLabel(f"  {line.strip()}")
#                     line_label.setWordWrap(True)
#                     self.tables_column.addWidget(line_label)

#     def manage_history(self, data):
#         from ..widgets.dialogs import EditHistoryDialog
#         from .. import database as db
#         from PyQt5.QtWidgets import QDialog

#         dialog = EditHistoryDialog(data.get('edit_history', ''), data['id'], self)
#         if dialog.exec_() == QDialog.Accepted:
#             new_history = dialog.result_history
#             # Обновляем историю
#             db.update_pump(data['id'], edit_history=new_history)
#             # Если нужно очистить примечание
#             if dialog.clear_note:
#                 db.update_pump(data['id'], note='')
#             # Обновляем отображение протокола
#             updated = db.get_pump_by_id(data['id'])
#             if updated:
#                 self.display_protocol(updated)

#     def clear_protocol(self):
#         """Вызывается по кнопке 'Скрыть протокол' - явный сброс просмотра,
#         уведомляет наружу (MainWindow), чтобы сбросить фильтры/выделение."""
#         self._clear_dynamic_content()
#         self.clear_requested.emit()

#     def _clear_dynamic_content(self):
#         """Внутренняя очистка динамической области перед перерисовкой нового
#         протокола/статистики. НЕ эмитит сигнал наружу, чтобы не сбрасывать
#         фильтры при обычном выборе насоса из списка. Очищаются только
#         СОДЕРЖИМОЕ колонок tables_column/graphs_column - сама двухколоночная
#         структура (dynamic_layout) не пересоздаётся."""
#         self._graph_toolbars = []
#         for column in (self.tables_column, self.graphs_column):
#             while column.count():
#                 child = column.takeAt(0)
#                 if child.widget():
#                     child.widget().deleteLater()
#                 elif child.layout():
#                     self._clear_layout(child.layout())
#         # Скрываем постоянные виджеты, показываем логотип
#         self.header_label.hide()
#         self.clear_btn.hide()
#         self.export_pdf_btn.hide()
#         self.legend_label.hide()
#         self.logo_label.show()

#     def _clear_layout(self, layout):
#         """Рекурсивно очищает вложенный layout (используется для контейнеров
#         график+тулбар внутри graphs_column)."""
#         while layout.count():
#             child = layout.takeAt(0)
#             if child.widget():
#                 child.widget().deleteLater()
#             elif child.layout():
#                 self._clear_layout(child.layout())

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QScrollArea, QSizePolicy,
    QFileDialog, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QColor, QFont, QPainter
from PyQt5.QtPrintSupport import QPrinter

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
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
        self._graph_toolbars = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        content = QWidget()
        self.content_widget = content  # нужен целиком для экспорта в PDF
        self.content_layout = QVBoxLayout(content)

        # Постоянные виджеты
        top_btns_layout = QHBoxLayout()
        self.clear_btn = QPushButton("Скрыть протокол")
        self.clear_btn.clicked.connect(self.clear_protocol)
        top_btns_layout.addWidget(self.clear_btn)

        self.export_pdf_btn = QPushButton("Экспорт в PDF")
        self.export_pdf_btn.clicked.connect(self.export_to_pdf)
        top_btns_layout.addWidget(self.export_pdf_btn)
        self.content_layout.addLayout(top_btns_layout)

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

        # Динамический контейнер: слева таблицы (на общей панели-подложке),
        # справа графики. Сами колонки создаются один раз и больше не
        # пересоздаются - при перерисовке протокола очищается только их
        # содержимое (см. _clear_dynamic_content).
        self.dynamic_widget = QWidget()
        self.dynamic_layout = QHBoxLayout(self.dynamic_widget)
        self.dynamic_layout.setSpacing(10)

        panel_style = ("QFrame { background-color: #f2f5f7; "
                       "border: 1px solid #d5dbe0; border-radius: 4px; }")

        self.tables_panel = QFrame()
        self.tables_panel.setStyleSheet(panel_style)
        self.tables_column = QVBoxLayout(self.tables_panel)
        self.tables_column.setContentsMargins(8, 8, 8, 8)
        self.tables_column.setSpacing(8)

        self.graphs_column = QVBoxLayout()

        self.dynamic_layout.addWidget(self.tables_panel, 0)
        self.dynamic_layout.addLayout(self.graphs_column, 1)
        self.content_layout.addWidget(self.dynamic_widget)

        # Отдельная полноширинная панель для таблицы герметичности (тот же
        # фон, чтобы визуально выглядело продолжением общей панели)
        self.seal_panel = QFrame()
        self.seal_panel.setStyleSheet(panel_style)
        self.seal_layout = QVBoxLayout(self.seal_panel)
        self.seal_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.addWidget(self.seal_panel)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Начальное состояние: показываем логотип, скрываем остальное
        self.header_label.hide()
        self.clear_btn.hide()
        self.export_pdf_btn.hide()
        self.legend_label.hide()
        self.seal_panel.hide()
        self.logo_label.show()

    def display_statistics(self, stats_data):
        """Отображает сводную статистику в правой панели."""
        self._clear_dynamic_content()  # очищаем динамическую область
        self.logo_label.hide()
        self.header_label.hide()  # скрываем заголовок протокола
        self.clear_btn.hide()
        self.export_pdf_btn.hide()

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

        # Создаём QLabel с HTML и добавляем в колонку таблиц
        label = QLabel(html)
        label.setWordWrap(True)
        label.setStyleSheet("background-color: white; padding: 10px;")
        self.tables_column.addWidget(label)
        self.current_data = None  # сбрасываем текущий протокол, т.к. показываем статистику

    def display_protocol(self, data):
        self.current_data = data
        self._clear_dynamic_content()  # очищаем dynamic_layout

        # Показываем постоянные виджеты
        self.logo_label.hide()
        self.header_label.show()
        self.clear_btn.show()
        self.export_pdf_btn.show()
        self.legend_label.show()

        # Заголовок
        date_str = data['test_date']
        if date_str and ' ' in date_str:
            date_str = date_str.split(' ')[0]
            
        order_num = data.get('order_number', '—')
        if order_num != '—' and order_num is not None:
            order_num = str(order_num).replace('.0', '')
            
        header_html = (
            "<div align='center'>Характеристики образца насоса ГУР</div>"
            "<div align='left'>"
            f"Протокол проверки насоса ГУР от: {date_str}<br>"
            f"Идентификационный №: {data['pump_number']}  Заказ: {order_num}<br>"
            f"Проверка: {data['test_type']}<br>"
            f"Модификация: {data.get('mod_name', '—')}<br>"
            f"Герметичен: {'Да' if data['is_sealed'] else 'Нет'}<br>"
            f"Вердикт: {data['verdict']}"
            "</div>"
        )
        self.header_label.setText(header_html)

        # Динамическое содержимое
        t1_table = self.create_test_table("Тест 1: Зависимость расхода от оборотов (ECO выкл.)",
                               list(range(5, 13)), data['results_json'], data.get('mod_name'))
        t2_table = self.create_test_table("Тест 2: Зависимость расхода от оборотов (ECO вкл.)",
                               list(range(13, 21)), data['results_json'], data.get('mod_name'))
        t3_table = self.create_test_table("Тест 3: Зависимость расхода от силы тока ECO",
                               list(range(21, 32)), data['results_json'], data.get('mod_name'))
        p_table = self.create_pressure_table(data)

        # Выравниваем таблицы тестов 1-3 и давления по максимальной ширине
        # (лишняя ширина уходит в последнюю колонку - без пустых полос)
        main_tables = [t1_table, t2_table, t3_table, p_table]
        uniform_width = max(t.width() for t in main_tables)
        for t in main_tables:
            t.horizontalHeader().setStretchLastSection(True)
            t.setFixedWidth(uniform_width)

        self.create_seal_table(data)
        self.seal_panel.show()

        # Высоты групп "заголовок + таблица" - чтобы графики визуально
        # вписывались по размеру в соответствующие таблицы слева
        title_h = 22  # приблизительная высота строки заголовка + отступ
        spacing = self.tables_column.spacing()
        graph1_height = title_h + t1_table.height() + spacing + title_h + t2_table.height()
        graph2_height = title_h + t3_table.height() + spacing + title_h + p_table.height()

        self.create_graphs(data, graph1_height, graph2_height)
        self.create_notes_section(data)

        self.legend_label.setText(
            "<span style='background-color:#ffc8c8; border:1px solid #999;'>"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>"
            "&nbsp;&nbsp;— значение не соответствует техническим требованиям."
        )

    def _compact_table(self, table, fix_width=True):
        """Уменьшает шрифт таблицы и подгоняет высоту (и, если fix_width=True,
        ширину) точно под содержимое, чтобы таблица показывалась полностью,
        без собственной прокрутки и без пустого пространства справа -
        прокручиваться может только вся правая панель целиком."""
        small_font = QFont("Arial", 8)
        table.setFont(small_font)
        table.horizontalHeader().setFont(small_font)
        table.verticalHeader().setDefaultSectionSize(18)
        table.resizeRowsToContents()
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.horizontalHeader().setMinimumSectionSize(40)

        total_height = table.horizontalHeader().height() + 4
        for row in range(table.rowCount()):
            total_height += table.rowHeight(row)
        table.setFixedHeight(total_height)

        if fix_width:
            total_width = 4  # небольшой запас на рамки/скролл-полосы
            for col in range(table.columnCount()):
                total_width += table.columnWidth(col)
            table.setFixedWidth(total_width)
            table.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        else:
            table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

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
            x_item = QTableWidgetItem(str(x_val))
            x_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 0, x_item)

            # Значение расхода с форматированием
            val_text = format_number(val)
            val_item = QTableWidgetItem(val_text)
            val_item.setTextAlignment(Qt.AlignCenter)
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
            min_item = QTableWidgetItem(min_text)
            min_item.setTextAlignment(Qt.AlignCenter)
            max_item = QTableWidgetItem(max_text)
            max_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 2, min_item)
            table.setItem(i, 3, max_item)

        table.verticalHeader().setVisible(False)
        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._compact_table(table)

        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 9, QFont.Bold))
        title_label.setWordWrap(True)
        self.tables_column.addWidget(title_label)
        self.tables_column.addWidget(table)
        return table

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
        param_item = QTableWidgetItem("Макс. давление, бар")
        param_item.setTextAlignment(Qt.AlignCenter)
        table.setItem(0, 0, param_item)
        val_item = QTableWidgetItem(str(pressure_val) if pressure_val is not None else '')
        val_item.setTextAlignment(Qt.AlignCenter)
        if pressure_val is not None and min_p is not None and max_p is not None:
            if not is_value_in_range(pressure_val, min_p, max_p):
                val_item.setBackground(QColor(255, 200, 200))
        elif pressure_val is None:
            val_item.setBackground(QColor(255, 200, 200))
        table.setItem(0, 1, val_item)
        range_item = QTableWidgetItem(f"{min_p} – {max_p}" if min_p is not None and max_p is not None else '')
        range_item.setTextAlignment(Qt.AlignCenter)
        table.setItem(0, 2, range_item)
        table.verticalHeader().setVisible(False)
        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._compact_table(table)

        title_label = QLabel("Тест 4: Давление настройки предохранительного клапана")
        title_label.setFont(QFont("Arial", 9, QFont.Bold))
        title_label.setWordWrap(True)
        self.tables_column.addWidget(title_label)
        self.tables_column.addWidget(table)
        return table

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
            place_item = QTableWidgetItem(label)
            place_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 0, place_item)
            val = seal.get(key)
            display_text = str(val) if val is not None else ''
            if display_text.strip().lower() == 'присутствуют в допускаемой степени':
                display_text = 'присутствуют в\nдопускаемой степени'
            val_item = QTableWidgetItem(display_text)
            val_item.setTextAlignment(Qt.AlignCenter)
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
        table.horizontalHeader().setStretchLastSection(True)
        self._compact_table(table, fix_width=False)

        title_label = QLabel("Герметичность")
        title_label.setFont(QFont("Arial", 9, QFont.Bold))
        title_label.setWordWrap(True)
        self.seal_layout.addWidget(title_label)
        self.seal_layout.addWidget(table)

    def _plot_series(self, ax, x_vals, y_vals, norm_min, norm_max, color, linestyle, label):
        """Рисует линию БЕЗ маркеров на промежуточных точках; точки, не
        соответствующие нормативам, отмечает красным кружком поверх линии."""
        ax.plot(x_vals, y_vals, linestyle=linestyle, color=color, linewidth=2, label=label)
        out_of_range_x, out_of_range_y = [], []
        for i, v in enumerate(y_vals):
            if v is None or (isinstance(v, float) and np.isnan(v)):
                continue
            if i < len(norm_min) and i < len(norm_max) and norm_min[i] is not None and norm_max[i] is not None:
                if not is_value_in_range(v, norm_min[i], norm_max[i]):
                    out_of_range_x.append(x_vals[i])
                    out_of_range_y.append(v)
        if out_of_range_x:
            ax.plot(out_of_range_x, out_of_range_y, 'o', color='red', markersize=7, zorder=5)

    def _make_graph_widget(self, fig, height=None):
        """Оборачивает Figure в canvas + тулбар matplotlib (зум/панорама/
        сброс масштаба кнопкой 'Home') и возвращает готовый контейнер-виджет.
        Если задана height - контейнер фиксируется по высоте (чтобы график
        визуально вписывался в размер соответствующих таблиц слева)."""
        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        toolbar = NavigationToolbar(canvas, self)
        toolbar.setIconSize(QSize(16, 16))
        self._graph_toolbars.append(toolbar)  # понадобится скрыть при экспорте в PDF
        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(2)
        c_layout.addWidget(toolbar)
        c_layout.addWidget(canvas)
        if height:
            container.setFixedHeight(height)
        return container

    def create_graphs(self, data, graph1_height=None, graph2_height=None):
        mod = None
        if data.get('mod_name'):
            mod = db.get_modification_by_name(data['mod_name'])
        if not mod:
            label = QLabel("Нормативы не найдены для этой модификации")
            self.graphs_column.addWidget(label)
            return

        results = data['results_json']

        # График 1: расход от оборотов (ECO выкл. / ECO вкл.)
        fig1 = Figure(figsize=(4, 3), dpi=100)
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

        self._plot_series(ax1, x_vals_plot, y1_plot, min1, max1, 'tab:blue', '-', 'ECO выкл.')
        self._plot_series(ax1, x_vals_plot, y2_plot, min2, max2, 'tab:red', '-', 'ECO вкл.')
        if len(min1) == len(x_vals_plot):
            ax1.plot(x_vals_plot, min1, '--', color='tab:blue', label='Мин./макс. треб. ECO выкл.', alpha=0.5)
            ax1.plot(x_vals_plot, max1, '--', color='tab:blue', alpha=0.5)
        if len(min2) == len(x_vals_plot):
            ax1.plot(x_vals_plot, min2, ':', color='tab:red', label='Мин./макс. треб. ECO вкл.', alpha=0.5)
            ax1.plot(x_vals_plot, max2, ':', color='tab:red', alpha=0.5)
        ax1.set_xlabel('Обороты, об/мин')
        ax1.set_ylabel('Расход, л/мин')
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='best', fontsize=7)
        ax1.set_title('Зависимость расхода от оборотов', fontsize=10)
        fig1.tight_layout()

        self.graphs_column.addWidget(self._make_graph_widget(fig1, graph1_height))

        # График 2: расход от силы тока ECO
        fig2 = Figure(figsize=(4, 3), dpi=100)
        ax2 = fig2.add_subplot(111)
        x_tok = mod.get('norm_graph3_x') or list(utils.DEFAULT_GRAPH3_X)
        y3 = [results.get(f'g{i}') for i in range(21, 32)]
        n3 = min(len(x_tok), len(y3))
        x_tok_plot = x_tok[:n3]
        y3_plot = [v if v is not None else np.nan for v in y3[:n3]]

        min3 = mod['norm_graph3_min']
        max3 = mod['norm_graph3_max']
        self._plot_series(ax2, x_tok_plot, y3_plot, min3, max3, 'tab:green', '-', 'Расход')
        if len(min3) == len(x_tok_plot):
            ax2.plot(x_tok_plot, min3, '--', color='tab:green', label='Мин./макс. треб.', alpha=0.5)
            ax2.plot(x_tok_plot, max3, '--', color='tab:green', alpha=0.5)
        ax2.set_xlabel('Сила тока, А')
        ax2.set_ylabel('Расход, л/мин')
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='best', fontsize=7)
        ax2.set_title('Зависимость расхода от силы тока ECO', fontsize=10)
        # Оси по умолчанию (масштаб по-прежнему можно менять зумом тулбара)
        ax2.set_xlim(0, 1)
        ax2.set_xticks(np.arange(0, 1.01, 0.1))
        ax2.set_ylim(4, 17)
        ax2.set_yticks(np.arange(4, 18, 1))
        fig2.tight_layout()

        self.graphs_column.addWidget(self._make_graph_widget(fig2, graph2_height))

    def display_comparison(self, items):
        """items - список полных данных (с results_json) насосов-дублей:
        одинаковый номер + модификация. Показывает сравнительные таблицы
        и 2 графика, на каждом - линии всех найденных дублей вместе."""
        self.current_data = None  # это не единичный протокол, экспорт PDF недоступен
        self._clear_dynamic_content()

        self.logo_label.hide()
        self.header_label.show()
        self.clear_btn.show()
        self.legend_label.show()

        first = items[0]
        mod_name = first.get('mod_name')
        mod = db.get_modification_by_name(mod_name) if mod_name else None
        dates = [(it['test_date'].split(' ')[0] if it.get('test_date') else '—') for it in items]

        header_text = (f"Сравнение дублей\n"
                       f"Идентификационный №: {first['pump_number']}\n"
                       f"Модификация: {mod_name or '—'}\n"
                       f"Найдено протоколов: {len(items)} (даты: {', '.join(dates)})")
        self.header_label.setText(header_text)

        norm1_min = mod['norm_graph1_min'] if mod else []
        norm1_max = mod['norm_graph1_max'] if mod else []
        norm1_x = mod['norm_graph1_x'] if mod else list(utils.DEFAULT_GRAPH1_X)
        norm2_min = mod['norm_graph2_min'] if mod else []
        norm2_max = mod['norm_graph2_max'] if mod else []
        norm2_x = mod['norm_graph2_x'] if mod else list(utils.DEFAULT_GRAPH2_X)
        norm3_min = mod['norm_graph3_min'] if mod else []
        norm3_max = mod['norm_graph3_max'] if mod else []
        norm3_x = mod['norm_graph3_x'] if mod else list(utils.DEFAULT_GRAPH3_X)

        self._create_comparison_table("Тест 1: расход от оборотов (ECO выкл.)",
                                      list(range(5, 13)), items, norm1_min, norm1_max, norm1_x, "Обороты, об/мин")
        self._create_comparison_table("Тест 2: расход от оборотов (ECO вкл.)",
                                      list(range(13, 21)), items, norm2_min, norm2_max, norm2_x, "Обороты, об/мин")
        self._create_comparison_table("Тест 3: расход от силы тока ECO",
                                      list(range(21, 32)), items, norm3_min, norm3_max, norm3_x, "Сила тока, А")
        self._create_comparison_pressure_table(items, mod)
        self._create_comparison_seal_table(items)
        self._create_comparison_graphs(items, mod)

        self.legend_label.setText(
            "Сравнение всех найденных дублей выбранного образца. "
            "<span style='background-color:#ffc8c8; border:1px solid #999;'>"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>"
            "&nbsp;&nbsp;— значение не соответствует техническим требованиям."
        )

    def _create_comparison_table(self, title, indices, items, norm_min, norm_max, x_vals, x_label):
        def format_number(value):
            if value is None or value == '':
                return ''
            try:
                return f"{float(value):.2f}"
            except (TypeError, ValueError):
                return str(value)

        dates = [(it['test_date'].split(' ')[0] if it.get('test_date') else f'#{i+1}') for i, it in enumerate(items)]
        col_labels = [x_label] + dates + ["Мин. треб.", "Макс. треб."]

        table = QTableWidget()
        table.setColumnCount(len(col_labels))
        table.setHorizontalHeaderLabels(col_labels)
        table.setRowCount(len(indices))

        for row, idx in enumerate(indices):
            key = f'g{idx}'
            x_val = x_vals[row] if row < len(x_vals) else ''
            table.setItem(row, 0, QTableWidgetItem(str(x_val)))

            for col, it in enumerate(items):
                val = it['results_json'].get(key)
                val_item = QTableWidgetItem(format_number(val))
                if val is not None and row < len(norm_min) and row < len(norm_max):
                    if not is_value_in_range(val, norm_min[row], norm_max[row]):
                        val_item.setBackground(QColor(255, 200, 200))
                elif val is None:
                    val_item.setBackground(QColor(255, 200, 200))
                table.setItem(row, 1 + col, val_item)

            min_val = norm_min[row] if row < len(norm_min) else None
            max_val = norm_max[row] if row < len(norm_max) else None
            table.setItem(row, 1 + len(items), QTableWidgetItem(format_number(min_val)))
            table.setItem(row, 2 + len(items), QTableWidgetItem(format_number(max_val)))

        table.verticalHeader().setVisible(False)
        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._compact_table(table)

        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 9, QFont.Bold))
        title_label.setWordWrap(True)
        self.tables_column.addWidget(title_label)
        self.tables_column.addWidget(table)

    def _create_comparison_pressure_table(self, items, mod):
        min_p = mod['pressure_min'] if mod else None
        max_p = mod['pressure_max'] if mod else None

        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Дата", "Давление, бар", "Допустимый диапазон"])
        table.setRowCount(len(items))
        for row, it in enumerate(items):
            date_str = it['test_date'].split(' ')[0] if it.get('test_date') else f'#{row+1}'
            table.setItem(row, 0, QTableWidgetItem(date_str))
            pressure_val = it['results_json'].get('g32')
            val_item = QTableWidgetItem(str(pressure_val) if pressure_val is not None else '')
            if pressure_val is not None and min_p is not None and max_p is not None:
                if not is_value_in_range(pressure_val, min_p, max_p):
                    val_item.setBackground(QColor(255, 200, 200))
            elif pressure_val is None:
                val_item.setBackground(QColor(255, 200, 200))
            table.setItem(row, 1, val_item)
            table.setItem(row, 2, QTableWidgetItem(
                f"{min_p} – {max_p}" if min_p is not None and max_p is not None else ''))

        table.verticalHeader().setVisible(False)
        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._compact_table(table)

        title_label = QLabel("Тест 4: Давление настройки предохранительного клапана")
        title_label.setFont(QFont("Arial", 9, QFont.Bold))
        self.tables_column.addWidget(title_label)
        self.tables_column.addWidget(table)

    def _create_comparison_seal_table(self, items):
        labels = {
            'g33': 'Седло клап. ECO',
            'g34': 'Пов. катушки ECO',
            'g35': 'Торец катушки ECO',
            'g36': 'Крышка корпуса',
            'g37': 'Масл. образования',
        }
        table = QTableWidget()
        table.setColumnCount(1 + len(labels))
        table.setHorizontalHeaderLabels(["Дата"] + list(labels.values()))
        table.setRowCount(len(items))
        for row, it in enumerate(items):
            date_str = it['test_date'].split(' ')[0] if it.get('test_date') else f'#{row+1}'
            table.setItem(row, 0, QTableWidgetItem(date_str))
            seal = it['seal_results_json']
            for col, key in enumerate(labels.keys()):
                val = seal.get(key)
                display_text = str(val) if val is not None else ''
                if display_text.strip().lower() == 'присутствуют в допускаемой степени':
                    display_text = 'присутствуют в\nдопускаемой степени'
                val_item = QTableWidgetItem(display_text)
                if key in ('g33', 'g34', 'g35', 'g36'):
                    if val is not None and str(val).strip().lower() != 'отсутствуют':
                        val_item.setBackground(QColor(255, 200, 200))
                else:
                    if val is not None:
                        text = str(val).strip().lower()
                        if text == 'присутствуют в допускаемой степени':
                            val_item.setBackground(QColor(255, 255, 150))
                        elif text != 'отсутствуют':
                            val_item.setBackground(QColor(255, 200, 200))
                table.setItem(row, 1 + col, val_item)

        table.verticalHeader().setVisible(False)
        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._compact_table(table)

        title_label = QLabel("Герметичность")
        title_label.setFont(QFont("Arial", 9, QFont.Bold))
        self.tables_column.addWidget(title_label)
        self.tables_column.addWidget(table)

    def _create_comparison_graphs(self, items, mod):
        if not mod:
            label = QLabel("Нормативы не найдены для этой модификации")
            self.graphs_column.addWidget(label)
            return

        colors = ['tab:blue', 'tab:red', 'tab:green', 'tab:orange', 'tab:purple', 'tab:brown', 'tab:pink']

        # График 1: расход от оборотов - линии всех дублей вместе
        # (сплошная - ECO выкл., пунктир - ECO вкл.)
        fig1 = Figure(figsize=(5, 4), dpi=100)
        ax1 = fig1.add_subplot(111)
        x_vals = mod.get('norm_graph1_x') or list(utils.DEFAULT_GRAPH1_X)
        min1 = mod['norm_graph1_min']
        max1 = mod['norm_graph1_max']

        for idx, it in enumerate(items):
            color = colors[idx % len(colors)]
            date_str = it['test_date'].split(' ')[0] if it.get('test_date') else f'#{idx + 1}'
            results = it['results_json']
            y1 = [results.get(f'g{i}') for i in range(5, 13)]
            y2 = [results.get(f'g{i}') for i in range(13, 21)]
            n1 = min(len(x_vals), len(y1))
            x_plot = x_vals[:n1]
            y1_plot = [v if v is not None else np.nan for v in y1[:n1]]
            y2_plot = [v if v is not None else np.nan for v in y2[:n1]]
            self._plot_series(ax1, x_plot, y1_plot, min1, max1, color, '-', f'{date_str}, ECO выкл.')
            self._plot_series(ax1, x_plot, y2_plot, min1, max1, color, '--', f'{date_str}, ECO вкл.')

        if len(min1) == len(x_vals):
            ax1.plot(x_vals, min1, ':', color='gray', label='Мин./макс. треб.', alpha=0.6)
            ax1.plot(x_vals, max1, ':', color='gray', alpha=0.6)
        ax1.set_xlabel('Обороты, об/мин')
        ax1.set_ylabel('Расход, л/мин')
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='best', fontsize=6)
        ax1.set_title('Сравнение дублей: расход от оборотов', fontsize=10)
        fig1.tight_layout()
        self.graphs_column.addWidget(self._make_graph_widget(fig1))

        # График 2: расход от силы тока ECO - линии всех дублей вместе
        fig2 = Figure(figsize=(5, 4), dpi=100)
        ax2 = fig2.add_subplot(111)
        x_tok = mod.get('norm_graph3_x') or list(utils.DEFAULT_GRAPH3_X)
        min3 = mod['norm_graph3_min']
        max3 = mod['norm_graph3_max']

        for idx, it in enumerate(items):
            color = colors[idx % len(colors)]
            date_str = it['test_date'].split(' ')[0] if it.get('test_date') else f'#{idx + 1}'
            results = it['results_json']
            y3 = [results.get(f'g{i}') for i in range(21, 32)]
            n3 = min(len(x_tok), len(y3))
            x_plot = x_tok[:n3]
            y3_plot = [v if v is not None else np.nan for v in y3[:n3]]
            self._plot_series(ax2, x_plot, y3_plot, min3, max3, color, '-', date_str)

        if len(min3) == len(x_tok):
            ax2.plot(x_tok, min3, ':', color='gray', label='Мин./макс. треб.', alpha=0.6)
            ax2.plot(x_tok, max3, ':', color='gray', alpha=0.6)
        ax2.set_xlabel('Сила тока, А')
        ax2.set_ylabel('Расход, л/мин')
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='best', fontsize=6)
        ax2.set_title('Сравнение дублей: расход от силы тока ECO', fontsize=10)
        ax2.set_xlim(0, 1)
        ax2.set_xticks(np.arange(0, 1.01, 0.1))
        ax2.set_ylim(4, 17)
        ax2.set_yticks(np.arange(4, 18, 1))
        fig2.tight_layout()
        self.graphs_column.addWidget(self._make_graph_widget(fig2))

    def export_to_pdf(self):
        """Экспортирует текущий (единичный) протокол в PDF-файл."""
        if not self.current_data:
            QMessageBox.warning(self, "Экспорт в PDF", "Сначала выберите протокол для экспорта.")
            return

        pump_number = self.current_data.get('pump_number', 'protocol')
        safe_number = str(pump_number).replace('/', '_').replace('\\', '_')
        default_name = f"Протокол_{safe_number}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить протокол в PDF", default_name, "PDF файлы (*.pdf)"
        )
        if not file_path:
            return
        if not file_path.lower().endswith('.pdf'):
            file_path += '.pdf'

        # Скрываем кнопки и тулбары графиков на время рендера - в бумажном
        # документе элементы управления зумом неуместны
        self.clear_btn.hide()
        self.export_pdf_btn.hide()
        for toolbar in self._graph_toolbars:
            toolbar.hide()

        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            printer.setPageSize(QPrinter.A4)
            printer.setOrientation(QPrinter.Portrait)
            # Обычные поля страницы (не setFullPage) - чтобы контент не
            # обрезался краевой непечатаемой зоной реального принтера
            printer.setPageMargins(10, 10, 10, 10, QPrinter.Millimeter)

            widget_to_print = self.content_widget
            w = max(widget_to_print.width(), 1)
            h = max(widget_to_print.height(), 1)
            page_rect = printer.pageRect()
            # Небольшой запас (0.98), чтобы точно не выйти за границы печати
            scale = min(page_rect.width() / w, page_rect.height() / h) * 0.98

            painter = QPainter()
            painter.begin(printer)
            painter.scale(scale, scale)
            widget_to_print.render(painter)
            painter.end()

            QMessageBox.information(self, "Экспорт в PDF", f"Протокол сохранён:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", f"Не удалось сохранить PDF:\n{e}")
        finally:
            self.clear_btn.show()
            self.export_pdf_btn.show()
            for toolbar in self._graph_toolbars:
                toolbar.show()

    def create_notes_section(self, data):
        note = data.get('note', '')
        if note:
            note_label = QLabel(f"<b>Примечание:</b> {note}")
            note_label.setWordWrap(True)
            self.tables_column.addWidget(note_label)

        edit_history = data.get('edit_history', '')
        if edit_history:
            history_label = QLabel("<b>История редактирования:</b>")
            history_label.setWordWrap(True)
            self.tables_column.addWidget(history_label)

            btn_manage = QPushButton("Управлять историей")
            btn_manage.clicked.connect(lambda: self.manage_history(data))
            self.tables_column.addWidget(btn_manage)

            for line in edit_history.strip().split('\n'):
                if line.strip():
                    line_label = QLabel(f"  {line.strip()}")
                    line_label.setWordWrap(True)
                    self.tables_column.addWidget(line_label)

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
        фильтры при обычном выборе насоса из списка. Очищаются только
        СОДЕРЖИМОЕ колонок tables_column/graphs_column - сама двухколоночная
        структура (dynamic_layout) не пересоздаётся."""
        self._graph_toolbars = []
        for column in (self.tables_column, self.graphs_column, self.seal_layout):
            while column.count():
                child = column.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
                elif child.layout():
                    self._clear_layout(child.layout())
        # Скрываем постоянные виджеты, показываем логотип
        self.header_label.hide()
        self.clear_btn.hide()
        self.export_pdf_btn.hide()
        self.legend_label.hide()
        self.seal_panel.hide()
        self.logo_label.show()

    def _clear_layout(self, layout):
        """Рекурсивно очищает вложенный layout (используется для контейнеров
        график+тулбар внутри graphs_column)."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())