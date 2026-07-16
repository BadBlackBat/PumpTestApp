# from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
# from PyQt5.QtCore import Qt
# from PyQt5.QtWidgets import (
#     QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
#     QPushButton, QTextEdit, QDialogButtonBox, QMessageBox, 
#     QListWidget, QListWidgetItem, QComboBox, QDateEdit,
#     QTableWidget, QTableWidgetItem, QScrollArea, QWidget, QSizePolicy,
#     QApplication
# )
# from PyQt5.QtCore import Qt, QDate
# from PyQt5.QtGui import QFont
# import json

# from .. import database as db
# from .. import utils

# def _clamp_to_screen(widget, width_fraction=0.95, height_fraction=0.92):
#     """Если диалог после adjustSize() оказался больше доступной области
#     экрана (актуально для HD и других небольших мониторов) - аккуратно
#     уменьшает его и центрирует. Вызывать после adjustSize()/resize()."""
#     screen = QApplication.primaryScreen()
#     if not screen:
#         return
#     available = screen.availableGeometry()
#     w = min(widget.width(), int(available.width() * width_fraction))
#     h = min(widget.height(), int(available.height() * height_fraction))
#     if w != widget.width() or h != widget.height():
#         widget.resize(w, h)
#     x = available.x() + (available.width() - w) // 2
#     y = available.y() + (available.height() - h) // 2
#     widget.move(x, y)


# class PasswordDialog(QDialog):
#     def __init__(self, parent=None, message="Для удаления записи введите пароль:"):
#         super().__init__(parent)
#         self.setWindowTitle("Введите пароль")
#         self.setModal(True)
#         layout = QVBoxLayout(self)
#         layout.addWidget(QLabel(message))
#         self.password_input = QLineEdit()
#         self.password_input.setEchoMode(QLineEdit.Password)
#         layout.addWidget(self.password_input)
#         btn_layout = QHBoxLayout()
#         ok_btn = QPushButton("OK")
#         ok_btn.clicked.connect(self.accept)
#         cancel_btn = QPushButton("Отмена")
#         cancel_btn.clicked.connect(self.reject)
#         btn_layout.addWidget(ok_btn)
#         btn_layout.addWidget(cancel_btn)
#         layout.addLayout(btn_layout)
#         self.password = ""

#     def accept(self):
#         self.password = self.password_input.text()
#         super().accept()

# class PointsEditorWidget(QWidget):
#     """Таблица для редактирования точек испытания: X-значение, мин., макс.
#     Позволяет добавлять/удалять точки в пределах max_points (ограничение
#     структуры БД - под точки отведено фиксированное число ячеек результатов)."""
#     def __init__(self, x_values, min_values, max_values, max_points, x_label="X", parent=None):
#         super().__init__(parent)
#         self.max_points = max_points

#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(0, 0, 0, 0)

#         self.table = QTableWidget()
#         self.table.setColumnCount(3)
#         self.table.setHorizontalHeaderLabels([x_label, "Мин.", "Макс."])
#         rows = len(x_values) if x_values else 1
#         self.table.setRowCount(rows)
#         for i in range(rows):
#             x_val = x_values[i] if i < len(x_values) else ''
#             min_val = min_values[i] if i < len(min_values) else ''
#             max_val = max_values[i] if i < len(max_values) else ''
#             x_item = QTableWidgetItem(str(x_val))
#             x_item.setTextAlignment(Qt.AlignCenter)
#             min_item = QTableWidgetItem(str(min_val))
#             min_item.setTextAlignment(Qt.AlignCenter)
#             max_item = QTableWidgetItem(str(max_val))
#             max_item.setTextAlignment(Qt.AlignCenter)
#             self.table.setItem(i, 0, x_item)
#             self.table.setItem(i, 1, min_item)
#             self.table.setItem(i, 2, max_item)
#         self.table.resizeColumnsToContents()
#         layout.addWidget(self.table)
#         self._fit_table_height()

#         # Растяжка перед кнопками: если позже виджет получит большую
#         # фиксированную высоту (см. align_bottom), кнопки уедут вниз и
#         # выровняются по одному уровню с другими таблицами
#         layout.addStretch(1)

#         btn_layout = QHBoxLayout()
#         self.btn_add = QPushButton("+ точка")
#         self.btn_add.setMaximumWidth(80)
#         self.btn_add.clicked.connect(self.add_row)
#         self.btn_remove = QPushButton("− точка")
#         self.btn_remove.setMaximumWidth(80)
#         self.btn_remove.clicked.connect(self.remove_row)
#         btn_layout.addWidget(self.btn_add)
#         btn_layout.addWidget(self.btn_remove)
#         btn_layout.addStretch(1)
#         layout.addLayout(btn_layout)
#         self._update_buttons()

#         # Фиксируем ширину ВСЕГО виджета (не только таблицы) точно по
#         # содержимому, чтобы родительский layout не мог растянуть его шире
#         # таблицы - иначе кнопки визуально "гуляют" отдельно от таблицы
#         self.setFixedWidth(self.table.width())
#         self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)

#     def align_bottom(self, target_height):
#         """Растягивает виджет до target_height - кнопки уедут вниз и
#         выровняются по одному уровню с другими (более высокими) таблицами."""
#         self.setFixedHeight(target_height)

#     def _fit_table_height(self):
#         """Подгоняет высоту и ширину таблицы точно под содержимое - без
#         внутренней прокрутки и без пустого пространства справа. Используется,
#         чтобы диалог обходился без QScrollArea."""
#         small_font = QFont()
#         small_font.setPointSize(9)
#         self.table.setFont(small_font)
#         self.table.horizontalHeader().setFont(small_font)
#         self.table.verticalHeader().setVisible(False)
#         self.table.verticalHeader().setDefaultSectionSize(22)
#         self.table.resizeRowsToContents()
#         self.table.resizeColumnsToContents()
#         self.table.horizontalHeader().setMinimumSectionSize(55)
#         self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
#         self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
#         total_height = self.table.horizontalHeader().height() + 4
#         for row in range(self.table.rowCount()):
#             total_height += self.table.rowHeight(row)
#         self.table.setFixedHeight(total_height)

#         total_width = 6
#         for col in range(self.table.columnCount()):
#             total_width += self.table.columnWidth(col)
#         self.table.setFixedWidth(total_width)

#     def _update_buttons(self):
#         self.btn_add.setEnabled(self.table.rowCount() < self.max_points)
#         self.btn_remove.setEnabled(self.table.rowCount() > 1)

#     def add_row(self):
#         if self.table.rowCount() >= self.max_points:
#             QMessageBox.information(self, "Ограничение", f"Максимум точек для этого испытания: {self.max_points}.")
#             return
#         row = self.table.rowCount()
#         self.table.insertRow(row)
#         for col in range(3):
#             item = QTableWidgetItem("")
#             item.setTextAlignment(Qt.AlignCenter)
#             self.table.setItem(row, col, item)
#         self._fit_table_height()
#         self._update_buttons()

#     def remove_row(self):
#         if self.table.rowCount() <= 1:
#             return
#         self.table.removeRow(self.table.rowCount() - 1)
#         self._fit_table_height()
#         self._update_buttons()

#     def validate(self):
#         """Проверяет, что все ячейки заполнены корректными числами."""
#         for row in range(self.table.rowCount()):
#             for col in range(3):
#                 item = self.table.item(row, col)
#                 text = item.text().strip() if item else ""
#                 if text == "":
#                     return False, f"заполните все ячейки (строка {row + 1})."
#                 try:
#                     float(text)
#                 except ValueError:
#                     return False, f"некорректное числовое значение в строке {row + 1}: '{text}'."
#         return True, ""

#     def get_data(self):
#         x_vals, min_vals, max_vals = [], [], []
#         for row in range(self.table.rowCount()):
#             def get_float(col):
#                 item = self.table.item(row, col)
#                 text = item.text().strip() if item else ""
#                 try:
#                     return float(text)
#                 except ValueError:
#                     return None
#             x_vals.append(get_float(0))
#             min_vals.append(get_float(1))
#             max_vals.append(get_float(2))
#         return x_vals, min_vals, max_vals


# class AddModificationDialog(QDialog):
#     """Диалог добавления новой модификации (или редактирования существующей,
#     если передан existing_mod)."""
#     def __init__(self, parent=None, existing_mod=None):
#         super().__init__(parent)
#         self.setWindowTitle("Добавление модификации насоса ГУР")
#         self.setModal(True)

#         layout = QVBoxLayout(self)

#         layout.addWidget(QLabel("Номер (название) модификации насоса ГУР:"))
#         self.name_input = QLineEdit()
#         if existing_mod:
#             self.name_input.setText(existing_mod['name'])
#         layout.addWidget(self.name_input)

#         # Три испытания - в один горизонтальный ряд, чтобы диалог оставался
#         # компактным по высоте и не требовал прокрутки
#         tests_layout = QHBoxLayout()
#         tests_layout.setSpacing(20)

#         test1_col = QVBoxLayout()
#         test1_col.addWidget(self._section_title("Испытание 1:\nПодача от оборотов\nECO выкл."))
#         self.test1 = PointsEditorWidget(
#             x_values=existing_mod['norm_graph1_x'] if existing_mod else list(utils.DEFAULT_GRAPH1_X),
#             min_values=existing_mod['norm_graph1_min'] if existing_mod else [],
#             max_values=existing_mod['norm_graph1_max'] if existing_mod else [],
#             max_points=utils.MAX_GRAPH1_POINTS,
#             x_label="Обороты"
#         )
#         test1_col.addWidget(self.test1)
#         tests_layout.addLayout(test1_col)

#         test2_col = QVBoxLayout()
#         test2_col.addWidget(self._section_title("Испытание 2:\nПодача от оборотов\nECO вкл."))
#         self.test2 = PointsEditorWidget(
#             x_values=existing_mod['norm_graph2_x'] if existing_mod else list(utils.DEFAULT_GRAPH2_X),
#             min_values=existing_mod['norm_graph2_min'] if existing_mod else [],
#             max_values=existing_mod['norm_graph2_max'] if existing_mod else [],
#             max_points=utils.MAX_GRAPH2_POINTS,
#             x_label="Обороты"
#         )
#         test2_col.addWidget(self.test2)
#         tests_layout.addLayout(test2_col)

#         test3_col = QVBoxLayout()
#         test3_col.addWidget(self._section_title("Испытание 3:\nПодача от силы тока ECO"))
#         self.test3 = PointsEditorWidget(
#             x_values=existing_mod['norm_graph3_x'] if existing_mod else list(utils.DEFAULT_GRAPH3_X),
#             min_values=existing_mod['norm_graph3_min'] if existing_mod else [],
#             max_values=existing_mod['norm_graph3_max'] if existing_mod else [],
#             max_points=utils.MAX_GRAPH3_POINTS,
#             x_label="Ток, А"
#         )
#         test3_col.addWidget(self.test3)
#         tests_layout.addLayout(test3_col)

#         # Выравниваем все 3 таблицы по нижнему краю (по самой высокой из них)
#         max_height = max(self.test1.sizeHint().height(),
#                           self.test2.sizeHint().height(),
#                           self.test3.sizeHint().height())
#         self.test1.align_bottom(max_height)
#         self.test2.align_bottom(max_height)
#         self.test3.align_bottom(max_height)

#         # Центрируем группу таблиц по горизонтали относительно диалога
#         centered_tests_row = QHBoxLayout()
#         centered_tests_row.addStretch(1)
#         centered_tests_row.addLayout(tests_layout)
#         centered_tests_row.addStretch(1)
#         layout.addLayout(centered_tests_row)

#         pressure_box = QVBoxLayout()
#         pressure_box.addWidget(self._section_title("Испытание 4: давление предохранительного клапана"))
#         pressure_row = QHBoxLayout()
#         pressure_row.addWidget(QLabel("Мин., бар:"))
#         self.pressure_min_input = QLineEdit(
#             str(existing_mod['pressure_min']) if existing_mod and existing_mod['pressure_min'] is not None else "")
#         pressure_row.addWidget(self.pressure_min_input)
#         pressure_row.addWidget(QLabel("Макс., бар:"))
#         self.pressure_max_input = QLineEdit(
#             str(existing_mod['pressure_max']) if existing_mod and existing_mod['pressure_max'] is not None else "")
#         pressure_row.addWidget(self.pressure_max_input)
#         pressure_row.addStretch()
#         pressure_box.addLayout(pressure_row)
#         layout.addLayout(pressure_box)

#         seal_box = QVBoxLayout()
#         seal_box.addWidget(self._section_title("Проверка на герметичность"))
#         self.seal_inputs = {}
#         seal_rules = existing_mod['seal_rules'] if existing_mod else dict(utils.DEFAULT_SEAL_REQUIREMENTS)
#         for key in utils.SEAL_KEYS:
#             row_layout = QHBoxLayout()
#             lbl = QLabel(utils.SEAL_LABELS[key] + ":")
#             lbl.setWordWrap(True)
#             lbl.setFixedWidth(220)
#             row_layout.addWidget(lbl)
#             edit = QLineEdit(seal_rules.get(key, utils.DEFAULT_SEAL_REQUIREMENTS[key]))
#             row_layout.addWidget(edit)
#             self.seal_inputs[key] = edit
#             seal_box.addLayout(row_layout)
#         layout.addLayout(seal_box)

#         password_row = QHBoxLayout()
#         password_row.addWidget(QLabel("Пароль для сохранения:"))
#         self.password_input = QLineEdit()
#         self.password_input.setEchoMode(QLineEdit.Password)
#         password_row.addWidget(self.password_input)
#         layout.addLayout(password_row)

#         button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
#         button_box.button(QDialogButtonBox.Cancel).setText("Отмена")
#         button_box.accepted.connect(self.try_accept)
#         button_box.rejected.connect(self.reject)
#         layout.addWidget(button_box)

#         # Открываем окно с минимальной шириной, до которой его можно сжать
#         # при текущем содержимом (без лишних пустот по краям)
#         layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
#         self.adjustSize()
#         _clamp_to_screen(self)

#     def _section_title(self, text):
#         lbl = QLabel(text)
#         lbl.setStyleSheet("font-weight: bold; margin-top: 10px;")
#         return lbl

#     def try_accept(self):
#         if not self.name_input.text().strip():
#             QMessageBox.warning(self, "Ошибка", "Введите номер модификации.")
#             return

#         for label, widget in (("Испытание 1", self.test1), ("Испытание 2", self.test2), ("Испытание 3", self.test3)):
#             ok, msg = widget.validate()
#             if not ok:
#                 QMessageBox.warning(self, "Ошибка", f"{label}: {msg}")
#                 return

#         try:
#             float(self.pressure_min_input.text().strip())
#             float(self.pressure_max_input.text().strip())
#         except ValueError:
#             QMessageBox.warning(self, "Ошибка", "Введите корректные числовые значения давления.")
#             return

#         for key, edit in self.seal_inputs.items():
#             if not edit.text().strip():
#                 QMessageBox.warning(self, "Ошибка", "Заполните все требования по герметичности.")
#                 return

#         if not self.password_input.text():
#             QMessageBox.warning(self, "Ошибка", "Введите пароль.")
#             return

#         self.accept()

#     def get_data(self):
#         x1, min1, max1 = self.test1.get_data()
#         x2, min2, max2 = self.test2.get_data()
#         x3, min3, max3 = self.test3.get_data()
#         return {
#             'name': self.name_input.text().strip(),
#             'graph1_x': x1, 'graph1_min': min1, 'graph1_max': max1,
#             'graph2_x': x2, 'graph2_min': min2, 'graph2_max': max2,
#             'graph3_x': x3, 'graph3_min': min3, 'graph3_max': max3,
#             'pressure_min': float(self.pressure_min_input.text().strip()),
#             'pressure_max': float(self.pressure_max_input.text().strip()),
#             'seal_rules': {key: edit.text().strip() for key, edit in self.seal_inputs.items()},
#             'password': self.password_input.text(),
#         }


# class ViewModificationsDialog(QDialog):
#     """Просмотр уже добавленных модификаций с их нормативами (без пароля)."""
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setWindowTitle("Просмотр модификаций")
#         self.setModal(True)
#         self.resize(650, 500)

#         layout = QHBoxLayout(self)

#         self.list_widget = QListWidget()
#         self.list_widget.setFixedWidth(200)
#         for mod_id, name in db.get_all_modifications():
#             item = QListWidgetItem(name)
#             item.setData(Qt.UserRole, mod_id)
#             self.list_widget.addItem(item)
#         self.list_widget.currentItemChanged.connect(self.show_details)
#         layout.addWidget(self.list_widget)

#         self.details_label = QLabel("Выберите модификацию слева, чтобы увидеть нормативы.")
#         self.details_label.setWordWrap(True)
#         self.details_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
#         scroll = QScrollArea()
#         scroll.setWidgetResizable(True)
#         scroll.setWidget(self.details_label)
#         layout.addWidget(scroll)

#         if self.list_widget.count() == 0:
#             self.details_label.setText("В базе пока нет ни одной модификации.")

#     def show_details(self, current, previous=None):
#         if not current:
#             return
#         mod_id = current.data(Qt.UserRole)
#         mod = db.get_modification_by_id(mod_id)
#         if not mod:
#             return

#         html = f"<h3>{mod['name']}</h3>"

#         def points_html(title, x_vals, min_vals, max_vals):
#             h = f"<p><b>{title}</b><br>"
#             for x, mn, mx in zip(x_vals, min_vals, max_vals):
#                 h += f"{x}: {mn} – {mx}<br>"
#             return h + "</p>"

#         html += points_html("Испытание 1 (ECO выкл.), обороты:",
#                              mod['norm_graph1_x'], mod['norm_graph1_min'], mod['norm_graph1_max'])
#         html += points_html("Испытание 2 (ECO вкл.), обороты:",
#                              mod['norm_graph2_x'], mod['norm_graph2_min'], mod['norm_graph2_max'])
#         html += points_html("Испытание 3, сила тока ECO:",
#                              mod['norm_graph3_x'], mod['norm_graph3_min'], mod['norm_graph3_max'])
#         html += f"<p><b>Давление настройки клапана:</b> {mod['pressure_min']} – {mod['pressure_max']} бар</p>"

#         html += "<p><b>Требования по герметичности:</b><br>"
#         for key in utils.SEAL_KEYS:
#             html += f"{utils.SEAL_LABELS[key]}: {mod['seal_rules'].get(key, '—')}<br>"
#         html += "</p>"

#         self.details_label.setText(html)


# class SettingsDialog(QDialog):
#     """Меню настроек: управление модификациями насосов."""
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setWindowTitle("Настройки")
#         self.setModal(True)
#         self.resize(320, 180)

#         layout = QVBoxLayout(self)
#         layout.addWidget(QLabel("Модификации насосов ГУР:"))

#         btn_add_mod = QPushButton("Добавить модификацию")
#         btn_add_mod.clicked.connect(self.open_add_modification)
#         layout.addWidget(btn_add_mod)

#         btn_view_mod = QPushButton("Просмотреть модификации")
#         btn_view_mod.clicked.connect(self.open_view_modifications)
#         layout.addWidget(btn_view_mod)

#         layout.addStretch()

#         btn_instructions = QPushButton("Инструкция")
#         btn_instructions.clicked.connect(self.open_instructions)
#         layout.addWidget(btn_instructions)

#         btn_close = QPushButton("Закрыть")
#         btn_close.clicked.connect(self.accept)
#         layout.addWidget(btn_close)

#     def open_instructions(self):
#         dialog = QDialog(self)
#         dialog.setWindowTitle("Инструкция")
#         dialog.resize(400, 250)
#         dlg_layout = QVBoxLayout(dialog)
#         dlg_layout.addWidget(QLabel("Инструкция по применению будет размещена позже"))
#         btn_ok = QPushButton("Закрыть")
#         btn_ok.clicked.connect(dialog.accept)
#         dlg_layout.addWidget(btn_ok)
#         dialog.exec_()

#     def open_add_modification(self):
#         dialog = AddModificationDialog(self)
#         if dialog.exec_() != QDialog.Accepted:
#             return
#         data = dialog.get_data()
#         if data['password'] != "admin":
#             QMessageBox.warning(self, "Ошибка", "Неверный пароль. Модификация не сохранена.")
#             return
#         db.add_modification(
#             name=data['name'],
#             norm_graph1_min=json.dumps(data['graph1_min']),
#             norm_graph1_max=json.dumps(data['graph1_max']),
#             norm_graph1_x=json.dumps(data['graph1_x']),
#             norm_graph2_min=json.dumps(data['graph2_min']),
#             norm_graph2_max=json.dumps(data['graph2_max']),
#             norm_graph2_x=json.dumps(data['graph2_x']),
#             norm_graph3_min=json.dumps(data['graph3_min']),
#             norm_graph3_max=json.dumps(data['graph3_max']),
#             norm_graph3_x=json.dumps(data['graph3_x']),
#             pressure_min=data['pressure_min'],
#             pressure_max=data['pressure_max'],
#             seal_rules=json.dumps(data['seal_rules']),
#         )
#         QMessageBox.information(self, "Успех", f"Модификация «{data['name']}» сохранена.")

#     def open_view_modifications(self):
#         dialog = ViewModificationsDialog(self)
#         dialog.exec_()


# class AddOrderDialog(QDialog):
#     # Отдельный диалог не требуется: номер заказа при ручном добавлении
#     # насоса вводится прямо в AddPumpDialog и создаётся автоматически
#     # (как и при импорте из Excel), поэтому здесь оставлена заглушка
#     # для обратной совместимости импортов.
#     pass


# class AddPumpDialog(QDialog):
#     """Диалог ручного добавления протокола проверки насоса."""
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setWindowTitle("Добавление насоса вручную")
#         self.setModal(True)
#         self.selected_mod = None
#         self.value_tables = {}
#         self.seal_inputs = {}

#         outer_layout = QVBoxLayout(self)

#         self.mods = db.get_all_modifications()  # список (id, name)

#         # Один столбец: модификация, номер насоса, дата, тип, номер заказа -
#         # каждое поле на своей строке (уже вместе с и без того узкими
#         # таблицами это даёт минимально возможную ширину окна)
#         def field_row(label_text, widget):
#             row = QHBoxLayout()
#             lbl = QLabel(label_text)
#             lbl.setFixedWidth(110)
#             row.addWidget(lbl)
#             row.addWidget(widget)
#             outer_layout.addLayout(row)

#         self.mod_combo = QComboBox()
#         for mod_id, name in self.mods:
#             self.mod_combo.addItem(name, mod_id)
#         self.mod_combo.currentIndexChanged.connect(self.on_modification_changed)
#         field_row("Модификация:", self.mod_combo)

#         self.pump_number_input = QLineEdit()
#         field_row("№ насоса:", self.pump_number_input)

#         self.date_input = QDateEdit()
#         self.date_input.setCalendarPopup(True)
#         self.date_input.setDate(QDate.currentDate())
#         field_row("Дата:", self.date_input)

#         self.type_combo = QComboBox()
#         self.type_combo.addItems(["первичная", "повторная"])
#         field_row("Тип:", self.type_combo)

#         self.order_input = QLineEdit()
#         field_row("№ заказа:", self.order_input)

#         # Динамическая область: горизонтальные колонки испытаний -
#         # перестраивается при выборе модификации
#         self.values_widget = QWidget()
#         self.values_main_layout = QVBoxLayout(self.values_widget)
#         self.tests_row = QHBoxLayout()      # Испытания 1-3, в ряд
#         self.tests_row.setSpacing(20)
#         self.extra_column = QVBoxLayout()   # Испытание 4, затем герметичность - друг под другом
#         self.extra_column.setSpacing(4)
#         centered_tests_row = QHBoxLayout()
#         centered_tests_row.addStretch(1)
#         centered_tests_row.addLayout(self.tests_row)
#         centered_tests_row.addStretch(1)
#         self.values_main_layout.addLayout(centered_tests_row)
#         self.values_main_layout.addLayout(self.extra_column)
#         outer_layout.addWidget(self.values_widget)

#         note_row = QHBoxLayout()
#         note_row.addWidget(QLabel("Примечание:"))
#         self.note_input = QLineEdit()
#         note_row.addWidget(self.note_input)
#         outer_layout.addLayout(note_row)

#         password_row = QHBoxLayout()
#         password_row.addWidget(QLabel("Пароль для сохранения:"))
#         self.password_input = QLineEdit()
#         self.password_input.setEchoMode(QLineEdit.Password)
#         password_row.addWidget(self.password_input)
#         outer_layout.addLayout(password_row)

#         button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
#         button_box.button(QDialogButtonBox.Cancel).setText("Отмена")
#         button_box.accepted.connect(self.try_accept)
#         button_box.rejected.connect(self.reject)
#         outer_layout.addWidget(button_box)

#         if self.mods:
#             self.on_modification_changed(0)
#         else:
#             QMessageBox.warning(
#                 self, "Нет модификаций",
#                 "В базе нет ни одной модификации. Сначала добавьте модификацию через Настройки → Добавить модификацию."
#             )

#         # Открываем окно с минимальной шириной, до которой его можно сжать
#         # при текущем содержимом (без лишних пустот по краям) - вызываем
#         # ПОСЛЕ построения таблиц испытаний, иначе размер посчитается по
#         # ещё пустой динамической области
#         outer_layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
#         self.adjustSize()
#         _clamp_to_screen(self)

#     def on_modification_changed(self, index):
#         # Очищаем предыдущее содержимое
#         self._clear_sub_layout(self.tests_row)
#         self._clear_sub_layout(self.extra_column)
#         self.value_tables = {}
#         self.seal_inputs = {}

#         mod_id = self.mod_combo.currentData()
#         if mod_id is None:
#             return
#         self.selected_mod = db.get_modification_by_id(mod_id)
#         if not self.selected_mod:
#             return

#         c1, self.value_tables['test1'] = self._build_value_table(
#             "Испытание 1\nРасход от оборотов\nECO выкл, I=0 A",
#             self.selected_mod['norm_graph1_x'], "Обороты"
#         )
#         c2, self.value_tables['test2'] = self._build_value_table(
#             "Испытание 2\nРасход от оборотов\nECO вкл, I=1 A",
#             self.selected_mod['norm_graph2_x'], "Обороты"
#         )
#         c3, self.value_tables['test3'] = self._build_value_table(
#             "Испытание 3\nРасход от силы тока\nна клапане ECO",
#             self.selected_mod['norm_graph3_x'], "Ток, А"
#         )
#         # Выравниваем все 3 таблицы по нижнему краю (по самой высокой из них)
#         max_height = max(c1.sizeHint().height(), c2.sizeHint().height(), c3.sizeHint().height())
#         c1.setFixedHeight(max_height)
#         c2.setFixedHeight(max_height)
#         c3.setFixedHeight(max_height)

#         # Испытание 4 (давление) - полноширинная строка
#         pressure_row = QHBoxLayout()
#         pressure_label = QLabel(
#             f"Испытание 4: давление (норма: {self.selected_mod['pressure_min']} – "
#             f"{self.selected_mod['pressure_max']} бар):"
#         )
#         pressure_label.setStyleSheet("font-weight: bold;")
#         pressure_row.addWidget(pressure_label)
#         self.pressure_input = QLineEdit()
#         self.pressure_input.setFixedWidth(120)
#         pressure_row.addWidget(self.pressure_input)
#         pressure_row.addStretch()
#         self.extra_column.addLayout(pressure_row)

#         # Герметичность - отдельная полноширинная строка ПОД испытанием 4,
#         # каждый пункт на своей строке
#         seal_label = QLabel("Герметичность:")
#         seal_label.setStyleSheet("font-weight: bold;")
#         self.extra_column.addWidget(seal_label)
#         for key in utils.SEAL_KEYS:
#             row = QHBoxLayout()
#             row.setSpacing(6)
#             lbl = QLabel(utils.SEAL_LABELS[key] + ":")
#             lbl.setWordWrap(True)
#             lbl.setFixedWidth(140)
#             row.addWidget(lbl)
#             edit = QLineEdit(self.selected_mod['seal_rules'].get(key, ''))
#             row.addWidget(edit)
#             self.seal_inputs[key] = edit
#             self.extra_column.addLayout(row)

#     def _clear_sub_layout(self, layout):
#         while layout.count():
#             child = layout.takeAt(0)
#             if child.widget():
#                 child.widget().deleteLater()
#             elif child.layout():
#                 self._clear_sub_layout(child.layout())

#     def _build_value_table(self, title, x_values, x_label):
#         container = QWidget()
#         col = QVBoxLayout(container)
#         col.setContentsMargins(0, 0, 0, 0)
#         title_label = QLabel(title)
#         title_label.setStyleSheet("font-weight: bold;")
#         title_label.setWordWrap(True)
#         col.addWidget(title_label)

#         table = QTableWidget()
#         table.setColumnCount(2)
#         table.setHorizontalHeaderLabels([x_label, "Результат"])
#         table.setRowCount(len(x_values))
#         for i, x in enumerate(x_values):
#             x_item = QTableWidgetItem(str(x))
#             x_item.setFlags(Qt.ItemIsEnabled)
#             x_item.setTextAlignment(Qt.AlignCenter)
#             table.setItem(i, 0, x_item)
#             res_item = QTableWidgetItem("")
#             res_item.setTextAlignment(Qt.AlignCenter)
#             table.setItem(i, 1, res_item)
#         table.setEditTriggers(QTableWidget.AllEditTriggers)

#         # Подгоняем высоту и ширину точно под содержимое - без внутренней прокрутки
#         small_font = QFont()
#         small_font.setPointSize(9)
#         table.setFont(small_font)
#         table.horizontalHeader().setFont(small_font)
#         table.verticalHeader().setVisible(False)
#         table.verticalHeader().setDefaultSectionSize(22)
#         table.resizeRowsToContents()
#         table.resizeColumnsToContents()
#         table.horizontalHeader().setMinimumSectionSize(65)
#         table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
#         table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
#         total_height = table.horizontalHeader().height() + 4
#         for row in range(table.rowCount()):
#             total_height += table.rowHeight(row)
#         table.setFixedHeight(total_height)
#         total_width = 6
#         for c in range(table.columnCount()):
#             total_width += table.columnWidth(c)
#         table.setFixedWidth(total_width)

#         col.addWidget(table)
#         col.addStretch(1)
#         # Фиксируем ширину контейнера точно по таблице - чтобы соседняя
#         # растяжка (при выравнивании по низу) не смещала таблицу вбок
#         container.setFixedWidth(table.width())
#         container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
#         self.tests_row.addWidget(container)
#         return container, table

#     def try_accept(self):
#         if not self.mods or not self.selected_mod:
#             QMessageBox.warning(self, "Ошибка", "Сначала добавьте модификацию через Настройки.")
#             return

#         if not self.pump_number_input.text().strip():
#             QMessageBox.warning(self, "Ошибка", "Введите идентификационный номер насоса.")
#             return

#         for key, table in self.value_tables.items():
#             for row in range(table.rowCount()):
#                 item = table.item(row, 1)
#                 text = item.text().strip() if item else ""
#                 if not text:
#                     QMessageBox.warning(self, "Ошибка", "Заполните все значения результатов испытаний.")
#                     return
#                 try:
#                     float(text)
#                 except ValueError:
#                     QMessageBox.warning(self, "Ошибка", f"Некорректное числовое значение: '{text}'.")
#                     return

#         pressure_text = self.pressure_input.text().strip()
#         if not pressure_text:
#             QMessageBox.warning(self, "Ошибка", "Введите значение давления.")
#             return
#         try:
#             float(pressure_text)
#         except ValueError:
#             QMessageBox.warning(self, "Ошибка", "Некорректное значение давления.")
#             return

#         for key, edit in self.seal_inputs.items():
#             if not edit.text().strip():
#                 QMessageBox.warning(self, "Ошибка", "Заполните все поля проверки на герметичность.")
#                 return

#         if not self.password_input.text():
#             QMessageBox.warning(self, "Ошибка", "Введите пароль.")
#             return

#         self.accept()

#     def get_data(self):
#         results = {}

#         def fill(table, start_key):
#             for i in range(table.rowCount()):
#                 key = f'g{start_key + i}'
#                 text = table.item(i, 1).text().strip()
#                 try:
#                     results[key] = float(text)
#                 except ValueError:
#                     results[key] = None

#         fill(self.value_tables['test1'], 5)
#         fill(self.value_tables['test2'], 13)
#         fill(self.value_tables['test3'], 21)
#         results['g32'] = float(self.pressure_input.text().strip())

#         seal_results = {key: edit.text().strip() for key, edit in self.seal_inputs.items()}

#         return {
#             'modification_id': self.selected_mod['id'],
#             'modification_name': self.selected_mod['name'],
#             'pump_number': self.pump_number_input.text().strip(),
#             'test_date': self.date_input.date().toString('yyyy-MM-dd'),
#             'test_type': self.type_combo.currentText(),
#             'order_number': self.order_input.text().strip() or None,
#             'results': results,
#             'seal_results': seal_results,
#             'note': self.note_input.text().strip(),
#             'password': self.password_input.text(),
#         }


# class EditPumpDialog(QDialog):
#     """Комплексное редактирование существующего протокола: номер заказа,
#     дата проверки, модификация, тип проверки, герметичность, значения
#     испытаний и примечание. Идентификационный номер насоса не меняется -
#     показывается как справочная информация."""
#     def __init__(self, pump_data, parent=None):
#         super().__init__(parent)
#         self.pump_data = pump_data
#         self.setWindowTitle(f"Редактирование протокола - насос № {pump_data.get('pump_number')}")
#         self.setModal(True)
#         self.selected_mod = None
#         self.value_tables = {}
#         self.seal_inputs = {}
#         # Исходные значения - используются при перестроении таблиц (смена
#         # модификации), чтобы не терять уже введённые результаты испытаний
#         self.original_results = dict(pump_data.get('results_json') or {})
#         self.original_seal = dict(pump_data.get('seal_results_json') or {})

#         outer_layout = QVBoxLayout(self)

#         self.mods = db.get_all_modifications()

#         info_row = QHBoxLayout()
#         info_row.addWidget(QLabel(f"Идентификационный № насоса: {pump_data.get('pump_number')}"))
#         outer_layout.addLayout(info_row)

#         def field_row(label_text, widget):
#             row = QHBoxLayout()
#             lbl = QLabel(label_text)
#             lbl.setFixedWidth(110)
#             row.addWidget(lbl)
#             row.addWidget(widget)
#             outer_layout.addLayout(row)

#         self.mod_combo = QComboBox()
#         current_index = 0
#         for i, (mod_id, name) in enumerate(self.mods):
#             self.mod_combo.addItem(name, mod_id)
#             if mod_id == pump_data.get('modification_id'):
#                 current_index = i
#         field_row("Модификация:", self.mod_combo)

#         self.date_input = QDateEdit()
#         self.date_input.setCalendarPopup(True)
#         existing_date = pump_data.get('test_date') or ''
#         if existing_date and ' ' in existing_date:
#             existing_date = existing_date.split(' ')[0]
#         qdate = QDate.fromString(existing_date, 'yyyy-MM-dd')
#         self.date_input.setDate(qdate if qdate.isValid() else QDate.currentDate())
#         field_row("Дата:", self.date_input)

#         self.type_combo = QComboBox()
#         self.type_combo.addItems(["первичная", "повторная"])
#         idx = self.type_combo.findText(pump_data.get('test_type') or 'первичная')
#         if idx >= 0:
#             self.type_combo.setCurrentIndex(idx)
#         field_row("Тип:", self.type_combo)

#         self.order_input = QLineEdit()
#         order_num = pump_data.get('order_number')
#         if order_num:
#             self.order_input.setText(str(order_num).replace('.0', ''))
#         field_row("№ заказа:", self.order_input)

#         self.values_widget = QWidget()
#         self.values_main_layout = QVBoxLayout(self.values_widget)
#         self.tests_row = QHBoxLayout()
#         self.tests_row.setSpacing(20)
#         self.extra_column = QVBoxLayout()
#         centered_tests_row = QHBoxLayout()
#         centered_tests_row.addStretch(1)
#         centered_tests_row.addLayout(self.tests_row)
#         centered_tests_row.addStretch(1)
#         self.values_main_layout.addLayout(centered_tests_row)
#         self.values_main_layout.addLayout(self.extra_column)
#         outer_layout.addWidget(self.values_widget)

#         note_row = QHBoxLayout()
#         note_row.addWidget(QLabel("Примечание:"))
#         self.note_input = QLineEdit()
#         self.note_input.setText(pump_data.get('note', '') or '')
#         note_row.addWidget(self.note_input)
#         outer_layout.addLayout(note_row)

#         password_row = QHBoxLayout()
#         password_row.addWidget(QLabel("Пароль для сохранения:"))
#         self.password_input = QLineEdit()
#         self.password_input.setEchoMode(QLineEdit.Password)
#         password_row.addWidget(self.password_input)
#         outer_layout.addLayout(password_row)

#         button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
#         button_box.button(QDialogButtonBox.Cancel).setText("Отмена")
#         button_box.accepted.connect(self.try_accept)
#         button_box.rejected.connect(self.reject)
#         outer_layout.addWidget(button_box)

#         self.mod_combo.setCurrentIndex(current_index)
#         self.mod_combo.currentIndexChanged.connect(self.on_modification_changed)
#         if self.mods:
#             self.on_modification_changed(current_index)
#         else:
#             QMessageBox.warning(
#                 self, "Нет модификаций",
#                 "В базе нет ни одной модификации. Сначала добавьте модификацию через Настройки → Добавить модификацию."
#             )

#         outer_layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
#         self.adjustSize()
#         _clamp_to_screen(self)

#     def on_modification_changed(self, index):
#         self._clear_sub_layout(self.tests_row)
#         self._clear_sub_layout(self.extra_column)
#         self.value_tables = {}
#         self.seal_inputs = {}

#         mod_id = self.mod_combo.currentData()
#         if mod_id is None:
#             return
#         self.selected_mod = db.get_modification_by_id(mod_id)
#         if not self.selected_mod:
#             return

#         self.value_tables['test1'] = self._build_value_table(
#             "Испытание 1\nРасход от оборотов\nECO выкл, I=0 A",
#             self.selected_mod['norm_graph1_x'], "Обороты", 5
#         )
#         self.value_tables['test2'] = self._build_value_table(
#             "Испытание 2\nРасход от оборотов\nECO вкл, I=1 A",
#             self.selected_mod['norm_graph2_x'], "Обороты", 13
#         )
#         self.value_tables['test3'] = self._build_value_table(
#             "Испытание 3\nРасход от силы тока\nна клапане ECO",
#             self.selected_mod['norm_graph3_x'], "Ток, А", 21
#         )

#         pressure_row = QHBoxLayout()
#         pressure_label = QLabel(
#             f"Испытание 4: давление (норма: {self.selected_mod['pressure_min']} – "
#             f"{self.selected_mod['pressure_max']} бар):"
#         )
#         pressure_label.setStyleSheet("font-weight: bold;")
#         pressure_row.addWidget(pressure_label)
#         self.pressure_input = QLineEdit()
#         self.pressure_input.setFixedWidth(120)
#         existing_pressure = self.original_results.get('g32')
#         if existing_pressure is not None:
#             self.pressure_input.setText(str(existing_pressure))
#         pressure_row.addWidget(self.pressure_input)
#         pressure_row.addStretch()
#         self.extra_column.addLayout(pressure_row)

#         seal_label = QLabel("Герметичность:")
#         seal_label.setStyleSheet("font-weight: bold;")
#         self.extra_column.addWidget(seal_label)
#         seal_grid = QHBoxLayout()
#         for key in utils.SEAL_KEYS:
#             one_col = QVBoxLayout()
#             lbl = QLabel(utils.SEAL_LABELS[key] + ":")
#             lbl.setWordWrap(True)
#             lbl.setFixedWidth(140)
#             one_col.addWidget(lbl)
#             edit = QLineEdit(self.original_seal.get(key, self.selected_mod['seal_rules'].get(key, '')))
#             one_col.addWidget(edit)
#             self.seal_inputs[key] = edit
#             seal_grid.addLayout(one_col)
#         seal_grid.addStretch()
#         self.extra_column.addLayout(seal_grid)

#     def _clear_sub_layout(self, layout):
#         while layout.count():
#             child = layout.takeAt(0)
#             if child.widget():
#                 child.widget().deleteLater()
#             elif child.layout():
#                 self._clear_sub_layout(child.layout())

#     def _build_value_table(self, title, x_values, x_label, start_key):
#         col = QVBoxLayout()
#         title_label = QLabel(title)
#         title_label.setStyleSheet("font-weight: bold;")
#         title_label.setWordWrap(True)
#         col.addWidget(title_label)

#         table = QTableWidget()
#         table.setColumnCount(2)
#         table.setHorizontalHeaderLabels([x_label, "Результат"])
#         table.setRowCount(len(x_values))
#         for i, x in enumerate(x_values):
#             x_item = QTableWidgetItem(str(x))
#             x_item.setFlags(Qt.ItemIsEnabled)
#             x_item.setTextAlignment(Qt.AlignCenter)
#             table.setItem(i, 0, x_item)
#             existing_val = self.original_results.get(f'g{start_key + i}')
#             res_item = QTableWidgetItem(str(existing_val) if existing_val is not None else '')
#             res_item.setTextAlignment(Qt.AlignCenter)
#             table.setItem(i, 1, res_item)
#         table.setEditTriggers(QTableWidget.AllEditTriggers)

#         small_font = QFont()
#         small_font.setPointSize(9)
#         table.setFont(small_font)
#         table.horizontalHeader().setFont(small_font)
#         table.verticalHeader().setVisible(False)
#         table.verticalHeader().setDefaultSectionSize(22)
#         table.resizeRowsToContents()
#         table.resizeColumnsToContents()
#         table.horizontalHeader().setMinimumSectionSize(65)
#         table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
#         table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
#         total_height = table.horizontalHeader().height() + 4
#         for row in range(table.rowCount()):
#             total_height += table.rowHeight(row)
#         table.setFixedHeight(total_height)
#         total_width = 6
#         for c in range(table.columnCount()):
#             total_width += table.columnWidth(c)
#         table.setFixedWidth(total_width)

#         col.addWidget(table)
#         col.addStretch(1)
#         container = QWidget()
#         container.setLayout(col)
#         container.setFixedWidth(table.width())
#         container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
#         self.tests_row.addWidget(container)
#         return table

#     def try_accept(self):
#         if not self.mods or not self.selected_mod:
#             QMessageBox.warning(self, "Ошибка", "Сначала добавьте модификацию через Настройки.")
#             return

#         for key, table in self.value_tables.items():
#             for row in range(table.rowCount()):
#                 item = table.item(row, 1)
#                 text = item.text().strip() if item else ""
#                 if not text:
#                     QMessageBox.warning(self, "Ошибка", "Заполните все значения результатов испытаний.")
#                     return
#                 try:
#                     float(text)
#                 except ValueError:
#                     QMessageBox.warning(self, "Ошибка", f"Некорректное числовое значение: '{text}'.")
#                     return

#         pressure_text = self.pressure_input.text().strip()
#         if not pressure_text:
#             QMessageBox.warning(self, "Ошибка", "Введите значение давления.")
#             return
#         try:
#             float(pressure_text)
#         except ValueError:
#             QMessageBox.warning(self, "Ошибка", "Некорректное значение давления.")
#             return

#         for key, edit in self.seal_inputs.items():
#             if not edit.text().strip():
#                 QMessageBox.warning(self, "Ошибка", "Заполните все поля проверки на герметичность.")
#                 return

#         if not self.password_input.text():
#             QMessageBox.warning(self, "Ошибка", "Введите пароль.")
#             return

#         self.accept()

#     def get_data(self):
#         results = {}

#         def fill(table, start_key):
#             for i in range(table.rowCount()):
#                 key = f'g{start_key + i}'
#                 text = table.item(i, 1).text().strip()
#                 try:
#                     results[key] = float(text)
#                 except ValueError:
#                     results[key] = None

#         fill(self.value_tables['test1'], 5)
#         fill(self.value_tables['test2'], 13)
#         fill(self.value_tables['test3'], 21)
#         results['g32'] = float(self.pressure_input.text().strip())

#         seal_results = {key: edit.text().strip() for key, edit in self.seal_inputs.items()}

#         return {
#             'modification_id': self.selected_mod['id'],
#             'modification_name': self.selected_mod['name'],
#             'test_date': self.date_input.date().toString('yyyy-MM-dd'),
#             'test_type': self.type_combo.currentText(),
#             'order_number': self.order_input.text().strip() or None,
#             'results': results,
#             'seal_results': seal_results,
#             'note': self.note_input.text().strip(),
#             'password': self.password_input.text(),
#         }


# class EditProtocolDialog(QDialog):
#     def __init__(self, pump_data, parent=None):
#         super().__init__(parent)
#         self.pump_data = pump_data
#         self.setWindowTitle("Редактирование примечания")
#         self.setModal(True)
#         self.resize(500, 300)

#         layout = QVBoxLayout(self)

#         # Информация о насосе
#         info = QLabel(
#             f"Насос: {pump_data.get('pump_number')}\n"
#             f"Дата: {pump_data.get('test_date')}\n"
#             f"Вердикт: {pump_data.get('verdict')}"
#         )
#         layout.addWidget(info)

#         # Поле для примечания
#         layout.addWidget(QLabel("Примечание:"))
#         self.note_edit = QTextEdit()
#         self.note_edit.setPlainText(pump_data.get('note', ''))
#         layout.addWidget(self.note_edit)

#         # Пароль
#         layout.addWidget(QLabel("Введите пароль для подтверждения:"))
#         self.password_input = QLineEdit()
#         self.password_input.setEchoMode(QLineEdit.Password)
#         layout.addWidget(self.password_input)

#         # Кнопки
#         button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
#         button_box.button(QDialogButtonBox.Cancel).setText("Отмена")
#         button_box.accepted.connect(self.accept)
#         button_box.rejected.connect(self.reject)
#         layout.addWidget(button_box)

#     def get_data(self):
#         return {
#             'note': self.note_edit.toPlainText(),
#             'password': self.password_input.text()
#         }

# class EditHistoryDialog(QDialog):
#     def __init__(self, edit_history, pump_id, parent=None):
#         super().__init__(parent)
#         self.setWindowTitle("Управление историей редактирования")
#         self.setModal(True)
#         self.resize(600, 400)
#         self.pump_id = pump_id
#         self.clear_note = False  # по умолчанию не очищать примечание

#         layout = QVBoxLayout(self)
#         layout.addWidget(QLabel("Выберите записи для удаления (отметьте галочками):"))

#         self.list_widget = QListWidget()
#         self.list_widget.setSelectionMode(QListWidget.MultiSelection)
#         layout.addWidget(self.list_widget)

#         self.entries = []
#         if edit_history:
#             for line in edit_history.strip().split('\n'):
#                 if line.strip():
#                     self.entries.append(line.strip())

#         for entry in self.entries:
#             item = QListWidgetItem(entry)
#             item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
#             item.setCheckState(Qt.Unchecked)
#             self.list_widget.addItem(item)

#         btn_layout = QHBoxLayout()
#         btn_delete_selected = QPushButton("Удалить выбранные")
#         btn_delete_all = QPushButton("Удалить все")
#         btn_cancel = QPushButton("Отмена")

#         btn_delete_selected.clicked.connect(self.delete_selected)
#         btn_delete_all.clicked.connect(self.delete_all)
#         btn_cancel.clicked.connect(self.reject)

#         btn_layout.addWidget(btn_delete_selected)
#         btn_layout.addWidget(btn_delete_all)
#         btn_layout.addWidget(btn_cancel)
#         layout.addLayout(btn_layout)

#         self.result_history = edit_history

#     def delete_selected(self):
#         indices = []
#         for i in range(self.list_widget.count()):
#             item = self.list_widget.item(i)
#             if item.checkState() == Qt.Checked:
#                 indices.append(i)
#         if not indices:
#             QMessageBox.information(self, "Информация", "Не выбрано ни одной записи.")
#             return
#         for i in reversed(indices):
#             self.list_widget.takeItem(i)
#         self.clear_note = False
#         self.save_result()

#     def delete_all(self):
#         reply = QMessageBox.question(self, "Подтверждение",
#                                      "Удалить все записи истории?\nПримечание также будет очищено.",
#                                      QMessageBox.Yes | QMessageBox.No)
#         if reply == QMessageBox.Yes:
#             self.list_widget.clear()
#             self.clear_note = True
#             self.save_result()

#     def save_result(self):
#         new_entries = []
#         for i in range(self.list_widget.count()):
#             item = self.list_widget.item(i)
#             if item.text().strip():
#                 new_entries.append(item.text().strip())
#         self.result_history = "\n".join(new_entries)
#         self.accept()

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QDialogButtonBox, QMessageBox, 
    QListWidget, QListWidgetItem, QComboBox, QDateEdit,
    QTableWidget, QTableWidgetItem, QScrollArea, QWidget, QSizePolicy,
    QApplication
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont
import json

from .. import database as db
from .. import utils
from .. import styles

def _clamp_to_screen(widget, width_fraction=0.95, height_fraction=0.92):
    """Если диалог после adjustSize() оказался больше доступной области
    экрана (актуально для HD и других небольших мониторов) - аккуратно
    уменьшает его и центрирует. Вызывать после adjustSize()/resize()."""
    screen = QApplication.primaryScreen()
    if not screen:
        return
    available = screen.availableGeometry()
    w = min(widget.width(), int(available.width() * width_fraction))
    h = min(widget.height(), int(available.height() * height_fraction))
    if w != widget.width() or h != widget.height():
        widget.resize(w, h)
    x = available.x() + (available.width() - w) // 2
    y = available.y() + (available.height() - h) // 2
    widget.move(x, y)


class PasswordDialog(QDialog):
    def __init__(self, parent=None, message="Для удаления записи введите пароль:"):
        super().__init__(parent)
        self.setWindowTitle("Введите пароль")
        self.setModal(True)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(message))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        self.password = ""

    def accept(self):
        self.password = self.password_input.text()
        super().accept()

class PointsEditorWidget(QWidget):
    """Таблица для редактирования точек испытания: X-значение, мин., макс.
    Позволяет добавлять/удалять точки в пределах max_points (ограничение
    структуры БД - под точки отведено фиксированное число ячеек результатов)."""
    def __init__(self, x_values, min_values, max_values, max_points, x_label="X", parent=None):
        super().__init__(parent)
        self.max_points = max_points

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([x_label, "Мин.", "Макс."])
        rows = len(x_values) if x_values else 1
        self.table.setRowCount(rows)
        for i in range(rows):
            x_val = x_values[i] if i < len(x_values) else ''
            min_val = min_values[i] if i < len(min_values) else ''
            max_val = max_values[i] if i < len(max_values) else ''
            x_item = QTableWidgetItem(str(x_val))
            x_item.setTextAlignment(Qt.AlignCenter)
            min_item = QTableWidgetItem(str(min_val))
            min_item.setTextAlignment(Qt.AlignCenter)
            max_item = QTableWidgetItem(str(max_val))
            max_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 0, x_item)
            self.table.setItem(i, 1, min_item)
            self.table.setItem(i, 2, max_item)
        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)
        self._fit_table_height()

        # Растяжка перед кнопками: если позже виджет получит большую
        # фиксированную высоту (см. align_bottom), кнопки уедут вниз и
        # выровняются по одному уровню с другими таблицами
        layout.addStretch(1)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("+ точка")
        self.btn_add.setMaximumWidth(80)
        self.btn_add.clicked.connect(self.add_row)
        self.btn_remove = QPushButton("− точка")
        self.btn_remove.setMaximumWidth(80)
        self.btn_remove.clicked.connect(self.remove_row)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_remove)
        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)
        self._update_buttons()

        # Фиксируем ширину ВСЕГО виджета (не только таблицы) точно по
        # содержимому, чтобы родительский layout не мог растянуть его шире
        # таблицы - иначе кнопки визуально "гуляют" отдельно от таблицы
        self.setFixedWidth(self.table.width())
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)

    def align_bottom(self, target_height):
        """Растягивает виджет до target_height - кнопки уедут вниз и
        выровняются по одному уровню с другими (более высокими) таблицами."""
        self.setFixedHeight(target_height)

    def _fit_table_height(self):
        """Подгоняет высоту и ширину таблицы точно под содержимое - без
        внутренней прокрутки и без пустого пространства справа. Используется,
        чтобы диалог обходился без QScrollArea."""
        small_font = QFont()
        small_font.setPointSize(9)
        self.table.setFont(small_font)
        self.table.horizontalHeader().setFont(small_font)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(22)
        self.table.resizeRowsToContents()
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setMinimumSectionSize(55)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        total_height = self.table.horizontalHeader().height() + 4
        for row in range(self.table.rowCount()):
            total_height += self.table.rowHeight(row)
        self.table.setFixedHeight(total_height)

        total_width = 6
        for col in range(self.table.columnCount()):
            total_width += self.table.columnWidth(col)
        self.table.setFixedWidth(total_width)

    def _update_buttons(self):
        self.btn_add.setEnabled(self.table.rowCount() < self.max_points)
        self.btn_remove.setEnabled(self.table.rowCount() > 1)

    def add_row(self):
        if self.table.rowCount() >= self.max_points:
            QMessageBox.information(self, "Ограничение", f"Максимум точек для этого испытания: {self.max_points}.")
            return
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col in range(3):
            item = QTableWidgetItem("")
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, col, item)
        self._fit_table_height()
        self._update_buttons()

    def remove_row(self):
        if self.table.rowCount() <= 1:
            return
        self.table.removeRow(self.table.rowCount() - 1)
        self._fit_table_height()
        self._update_buttons()

    def validate(self):
        """Проверяет, что все ячейки заполнены корректными числами."""
        for row in range(self.table.rowCount()):
            for col in range(3):
                item = self.table.item(row, col)
                text = item.text().strip() if item else ""
                if text == "":
                    return False, f"заполните все ячейки (строка {row + 1})."
                try:
                    float(text)
                except ValueError:
                    return False, f"некорректное числовое значение в строке {row + 1}: '{text}'."
        return True, ""

    def get_data(self):
        x_vals, min_vals, max_vals = [], [], []
        for row in range(self.table.rowCount()):
            def get_float(col):
                item = self.table.item(row, col)
                text = item.text().strip() if item else ""
                try:
                    return float(text)
                except ValueError:
                    return None
            x_vals.append(get_float(0))
            min_vals.append(get_float(1))
            max_vals.append(get_float(2))
        return x_vals, min_vals, max_vals


class AddModificationDialog(QDialog):
    """Диалог добавления новой модификации (или редактирования существующей,
    если передан existing_mod)."""
    def __init__(self, parent=None, existing_mod=None):
        super().__init__(parent)
        self.setWindowTitle("Добавление модификации насоса ГУР")
        self.setModal(True)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Номер (название) модификации насоса ГУР:"))
        self.name_input = QLineEdit()
        if existing_mod:
            self.name_input.setText(existing_mod['name'])
        layout.addWidget(self.name_input)

        # Три испытания - в один горизонтальный ряд, чтобы диалог оставался
        # компактным по высоте и не требовал прокрутки
        tests_layout = QHBoxLayout()
        tests_layout.setSpacing(20)

        test1_col = QVBoxLayout()
        test1_col.addWidget(self._section_title("Испытание 1:\nПодача от оборотов\nECO выкл."))
        self.test1 = PointsEditorWidget(
            x_values=existing_mod['norm_graph1_x'] if existing_mod else list(utils.DEFAULT_GRAPH1_X),
            min_values=existing_mod['norm_graph1_min'] if existing_mod else [],
            max_values=existing_mod['norm_graph1_max'] if existing_mod else [],
            max_points=utils.MAX_GRAPH1_POINTS,
            x_label="Обороты"
        )
        test1_col.addWidget(self.test1)
        tests_layout.addLayout(test1_col)

        test2_col = QVBoxLayout()
        test2_col.addWidget(self._section_title("Испытание 2:\nПодача от оборотов\nECO вкл."))
        self.test2 = PointsEditorWidget(
            x_values=existing_mod['norm_graph2_x'] if existing_mod else list(utils.DEFAULT_GRAPH2_X),
            min_values=existing_mod['norm_graph2_min'] if existing_mod else [],
            max_values=existing_mod['norm_graph2_max'] if existing_mod else [],
            max_points=utils.MAX_GRAPH2_POINTS,
            x_label="Обороты"
        )
        test2_col.addWidget(self.test2)
        tests_layout.addLayout(test2_col)

        test3_col = QVBoxLayout()
        test3_col.addWidget(self._section_title("Испытание 3:\nПодача от силы тока ECO"))
        self.test3 = PointsEditorWidget(
            x_values=existing_mod['norm_graph3_x'] if existing_mod else list(utils.DEFAULT_GRAPH3_X),
            min_values=existing_mod['norm_graph3_min'] if existing_mod else [],
            max_values=existing_mod['norm_graph3_max'] if existing_mod else [],
            max_points=utils.MAX_GRAPH3_POINTS,
            x_label="Ток, А"
        )
        test3_col.addWidget(self.test3)
        tests_layout.addLayout(test3_col)

        # Выравниваем все 3 таблицы по нижнему краю (по самой высокой из них)
        max_height = max(self.test1.sizeHint().height(),
                          self.test2.sizeHint().height(),
                          self.test3.sizeHint().height())
        self.test1.align_bottom(max_height)
        self.test2.align_bottom(max_height)
        self.test3.align_bottom(max_height)

        # Центрируем группу таблиц по горизонтали относительно диалога
        centered_tests_row = QHBoxLayout()
        centered_tests_row.addStretch(1)
        centered_tests_row.addLayout(tests_layout)
        centered_tests_row.addStretch(1)
        layout.addLayout(centered_tests_row)

        pressure_box = QVBoxLayout()
        pressure_box.addWidget(self._section_title("Испытание 4: давление предохранительного клапана"))
        pressure_row = QHBoxLayout()
        pressure_row.addWidget(QLabel("Мин., бар:"))
        self.pressure_min_input = QLineEdit(
            str(existing_mod['pressure_min']) if existing_mod and existing_mod['pressure_min'] is not None else "")
        pressure_row.addWidget(self.pressure_min_input)
        pressure_row.addWidget(QLabel("Макс., бар:"))
        self.pressure_max_input = QLineEdit(
            str(existing_mod['pressure_max']) if existing_mod and existing_mod['pressure_max'] is not None else "")
        pressure_row.addWidget(self.pressure_max_input)
        pressure_row.addStretch()
        pressure_box.addLayout(pressure_row)
        layout.addLayout(pressure_box)

        seal_box = QVBoxLayout()
        seal_box.addWidget(self._section_title("Проверка на герметичность"))
        self.seal_inputs = {}
        seal_rules = existing_mod['seal_rules'] if existing_mod else dict(utils.DEFAULT_SEAL_REQUIREMENTS)
        for key in utils.SEAL_KEYS:
            row_layout = QHBoxLayout()
            lbl = QLabel(utils.SEAL_LABELS[key] + ":")
            lbl.setWordWrap(True)
            lbl.setFixedWidth(220)
            row_layout.addWidget(lbl)
            edit = QLineEdit(seal_rules.get(key, utils.DEFAULT_SEAL_REQUIREMENTS[key]))
            row_layout.addWidget(edit)
            self.seal_inputs[key] = edit
            seal_box.addLayout(row_layout)
        layout.addLayout(seal_box)

        password_row = QHBoxLayout()
        password_row.addWidget(QLabel("Пароль для сохранения:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        password_row.addWidget(self.password_input)
        layout.addLayout(password_row)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Cancel).setText("Отмена")
        button_box.accepted.connect(self.try_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Открываем окно с минимальной шириной, до которой его можно сжать
        # при текущем содержимом (без лишних пустот по краям)
        layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
        self.adjustSize()
        _clamp_to_screen(self)

    def _section_title(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(styles.DIALOG_SECTION_TITLE_STYLE)
        return lbl

    def try_accept(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите номер модификации.")
            return

        for label, widget in (("Испытание 1", self.test1), ("Испытание 2", self.test2), ("Испытание 3", self.test3)):
            ok, msg = widget.validate()
            if not ok:
                QMessageBox.warning(self, "Ошибка", f"{label}: {msg}")
                return

        try:
            float(self.pressure_min_input.text().strip())
            float(self.pressure_max_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Введите корректные числовые значения давления.")
            return

        for key, edit in self.seal_inputs.items():
            if not edit.text().strip():
                QMessageBox.warning(self, "Ошибка", "Заполните все требования по герметичности.")
                return

        if not self.password_input.text():
            QMessageBox.warning(self, "Ошибка", "Введите пароль.")
            return

        self.accept()

    def get_data(self):
        x1, min1, max1 = self.test1.get_data()
        x2, min2, max2 = self.test2.get_data()
        x3, min3, max3 = self.test3.get_data()
        return {
            'name': self.name_input.text().strip(),
            'graph1_x': x1, 'graph1_min': min1, 'graph1_max': max1,
            'graph2_x': x2, 'graph2_min': min2, 'graph2_max': max2,
            'graph3_x': x3, 'graph3_min': min3, 'graph3_max': max3,
            'pressure_min': float(self.pressure_min_input.text().strip()),
            'pressure_max': float(self.pressure_max_input.text().strip()),
            'seal_rules': {key: edit.text().strip() for key, edit in self.seal_inputs.items()},
            'password': self.password_input.text(),
        }


class ViewModificationsDialog(QDialog):
    """Просмотр уже добавленных модификаций с их нормативами (без пароля)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Просмотр модификаций")
        self.setModal(True)
        self.resize(650, 500)

        layout = QHBoxLayout(self)

        self.list_widget = QListWidget()
        self.list_widget.setFixedWidth(200)
        for mod_id, name in db.get_all_modifications():
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, mod_id)
            self.list_widget.addItem(item)
        self.list_widget.currentItemChanged.connect(self.show_details)
        layout.addWidget(self.list_widget)

        self.details_label = QLabel("Выберите модификацию слева, чтобы увидеть нормативы.")
        self.details_label.setWordWrap(True)
        self.details_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.details_label)
        layout.addWidget(scroll)

        if self.list_widget.count() == 0:
            self.details_label.setText("В базе пока нет ни одной модификации.")

    def show_details(self, current, previous=None):
        if not current:
            return
        mod_id = current.data(Qt.UserRole)
        mod = db.get_modification_by_id(mod_id)
        if not mod:
            return

        html = f"<h3>{mod['name']}</h3>"

        def points_html(title, x_vals, min_vals, max_vals):
            h = f"<p><b>{title}</b><br>"
            for x, mn, mx in zip(x_vals, min_vals, max_vals):
                h += f"{x}: {mn} – {mx}<br>"
            return h + "</p>"

        html += points_html("Испытание 1 (ECO выкл.), обороты:",
                             mod['norm_graph1_x'], mod['norm_graph1_min'], mod['norm_graph1_max'])
        html += points_html("Испытание 2 (ECO вкл.), обороты:",
                             mod['norm_graph2_x'], mod['norm_graph2_min'], mod['norm_graph2_max'])
        html += points_html("Испытание 3, сила тока ECO:",
                             mod['norm_graph3_x'], mod['norm_graph3_min'], mod['norm_graph3_max'])
        html += f"<p><b>Давление настройки клапана:</b> {mod['pressure_min']} – {mod['pressure_max']} бар</p>"

        html += "<p><b>Требования по герметичности:</b><br>"
        for key in utils.SEAL_KEYS:
            html += f"{utils.SEAL_LABELS[key]}: {mod['seal_rules'].get(key, '—')}<br>"
        html += "</p>"

        self.details_label.setText(html)


class SettingsDialog(QDialog):
    """Меню настроек: управление модификациями насосов."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setModal(True)
        self.resize(320, 180)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Модификации насосов ГУР:"))

        btn_add_mod = QPushButton("Добавить модификацию")
        btn_add_mod.clicked.connect(self.open_add_modification)
        layout.addWidget(btn_add_mod)

        btn_view_mod = QPushButton("Просмотреть модификации")
        btn_view_mod.clicked.connect(self.open_view_modifications)
        layout.addWidget(btn_view_mod)

        layout.addStretch()

        btn_instructions = QPushButton("Инструкция")
        btn_instructions.clicked.connect(self.open_instructions)
        layout.addWidget(btn_instructions)

        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def open_instructions(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Инструкция")
        dialog.resize(400, 250)
        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.addWidget(QLabel("Инструкция по применению будет размещена позже"))
        btn_ok = QPushButton("Закрыть")
        btn_ok.clicked.connect(dialog.accept)
        dlg_layout.addWidget(btn_ok)
        dialog.exec_()

    def open_add_modification(self):
        dialog = AddModificationDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        data = dialog.get_data()
        if data['password'] != "admin":
            QMessageBox.warning(self, "Ошибка", "Неверный пароль. Модификация не сохранена.")
            return
        db.add_modification(
            name=data['name'],
            norm_graph1_min=json.dumps(data['graph1_min']),
            norm_graph1_max=json.dumps(data['graph1_max']),
            norm_graph1_x=json.dumps(data['graph1_x']),
            norm_graph2_min=json.dumps(data['graph2_min']),
            norm_graph2_max=json.dumps(data['graph2_max']),
            norm_graph2_x=json.dumps(data['graph2_x']),
            norm_graph3_min=json.dumps(data['graph3_min']),
            norm_graph3_max=json.dumps(data['graph3_max']),
            norm_graph3_x=json.dumps(data['graph3_x']),
            pressure_min=data['pressure_min'],
            pressure_max=data['pressure_max'],
            seal_rules=json.dumps(data['seal_rules']),
        )
        QMessageBox.information(self, "Успех", f"Модификация «{data['name']}» сохранена.")

    def open_view_modifications(self):
        dialog = ViewModificationsDialog(self)
        dialog.exec_()


class AddOrderDialog(QDialog):
    # Отдельный диалог не требуется: номер заказа при ручном добавлении
    # насоса вводится прямо в AddPumpDialog и создаётся автоматически
    # (как и при импорте из Excel), поэтому здесь оставлена заглушка
    # для обратной совместимости импортов.
    pass


class AddPumpDialog(QDialog):
    """Диалог ручного добавления протокола проверки насоса."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавление насоса вручную")
        self.setModal(True)
        self.selected_mod = None
        self.value_tables = {}
        self.seal_inputs = {}

        outer_layout = QVBoxLayout(self)

        self.mods = db.get_all_modifications()  # список (id, name)

        # Один столбец: модификация, номер насоса, дата, тип, номер заказа -
        # каждое поле на своей строке (уже вместе с и без того узкими
        # таблицами это даёт минимально возможную ширину окна)
        def field_row(label_text, widget):
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFixedWidth(110)
            row.addWidget(lbl)
            row.addWidget(widget)
            outer_layout.addLayout(row)

        self.mod_combo = QComboBox()
        for mod_id, name in self.mods:
            self.mod_combo.addItem(name, mod_id)
        self.mod_combo.currentIndexChanged.connect(self.on_modification_changed)
        field_row("Модификация:", self.mod_combo)

        self.pump_number_input = QLineEdit()
        field_row("№ насоса:", self.pump_number_input)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        field_row("Дата:", self.date_input)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["первичная", "повторная"])
        field_row("Тип:", self.type_combo)

        self.order_input = QLineEdit()
        field_row("№ заказа:", self.order_input)

        # Динамическая область: горизонтальные колонки испытаний -
        # перестраивается при выборе модификации
        self.values_widget = QWidget()
        self.values_main_layout = QVBoxLayout(self.values_widget)
        self.tests_row = QHBoxLayout()      # Испытания 1-3, в ряд
        self.tests_row.setSpacing(20)
        self.extra_column = QVBoxLayout()   # Испытание 4, затем герметичность - друг под другом
        self.extra_column.setSpacing(4)
        centered_tests_row = QHBoxLayout()
        centered_tests_row.addStretch(1)
        centered_tests_row.addLayout(self.tests_row)
        centered_tests_row.addStretch(1)
        self.values_main_layout.addLayout(centered_tests_row)
        self.values_main_layout.addLayout(self.extra_column)
        outer_layout.addWidget(self.values_widget)

        note_row = QHBoxLayout()
        note_row.addWidget(QLabel("Примечание:"))
        self.note_input = QLineEdit()
        note_row.addWidget(self.note_input)
        outer_layout.addLayout(note_row)

        password_row = QHBoxLayout()
        password_row.addWidget(QLabel("Пароль для сохранения:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        password_row.addWidget(self.password_input)
        outer_layout.addLayout(password_row)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Cancel).setText("Отмена")
        button_box.accepted.connect(self.try_accept)
        button_box.rejected.connect(self.reject)
        outer_layout.addWidget(button_box)

        if self.mods:
            self.on_modification_changed(0)
        else:
            QMessageBox.warning(
                self, "Нет модификаций",
                "В базе нет ни одной модификации. Сначала добавьте модификацию через Настройки → Добавить модификацию."
            )

        # Открываем окно с минимальной шириной, до которой его можно сжать
        # при текущем содержимом (без лишних пустот по краям) - вызываем
        # ПОСЛЕ построения таблиц испытаний, иначе размер посчитается по
        # ещё пустой динамической области
        outer_layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
        self.adjustSize()
        _clamp_to_screen(self)

    def on_modification_changed(self, index):
        # Очищаем предыдущее содержимое
        self._clear_sub_layout(self.tests_row)
        self._clear_sub_layout(self.extra_column)
        self.value_tables = {}
        self.seal_inputs = {}

        mod_id = self.mod_combo.currentData()
        if mod_id is None:
            return
        self.selected_mod = db.get_modification_by_id(mod_id)
        if not self.selected_mod:
            return

        c1, self.value_tables['test1'] = self._build_value_table(
            "Испытание 1\nРасход от оборотов\nECO выкл, I=0 A",
            self.selected_mod['norm_graph1_x'], "Обороты"
        )
        c2, self.value_tables['test2'] = self._build_value_table(
            "Испытание 2\nРасход от оборотов\nECO вкл, I=1 A",
            self.selected_mod['norm_graph2_x'], "Обороты"
        )
        c3, self.value_tables['test3'] = self._build_value_table(
            "Испытание 3\nРасход от силы тока\nна клапане ECO",
            self.selected_mod['norm_graph3_x'], "Ток, А"
        )
        # Выравниваем все 3 таблицы по нижнему краю (по самой высокой из них)
        max_height = max(c1.sizeHint().height(), c2.sizeHint().height(), c3.sizeHint().height())
        c1.setFixedHeight(max_height)
        c2.setFixedHeight(max_height)
        c3.setFixedHeight(max_height)

        # Испытание 4 (давление) - полноширинная строка
        pressure_row = QHBoxLayout()
        pressure_label = QLabel(
            f"Испытание 4: давление (норма: {self.selected_mod['pressure_min']} – "
            f"{self.selected_mod['pressure_max']} бар):"
        )
        pressure_label.setStyleSheet(styles.DIALOG_SECTION_TITLE_STYLE_COMPACT)
        pressure_row.addWidget(pressure_label)
        self.pressure_input = QLineEdit()
        self.pressure_input.setFixedWidth(120)
        pressure_row.addWidget(self.pressure_input)
        pressure_row.addStretch()
        self.extra_column.addLayout(pressure_row)

        # Герметичность - отдельная полноширинная строка ПОД испытанием 4,
        # каждый пункт на своей строке
        seal_label = QLabel("Герметичность:")
        seal_label.setStyleSheet(styles.DIALOG_SECTION_TITLE_STYLE_COMPACT)
        self.extra_column.addWidget(seal_label)
        for key in utils.SEAL_KEYS:
            row = QHBoxLayout()
            row.setSpacing(6)
            lbl = QLabel(utils.SEAL_LABELS[key] + ":")
            lbl.setWordWrap(True)
            lbl.setFixedWidth(140)
            row.addWidget(lbl)
            edit = QLineEdit(self.selected_mod['seal_rules'].get(key, ''))
            row.addWidget(edit)
            self.seal_inputs[key] = edit
            self.extra_column.addLayout(row)

    def _clear_sub_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_sub_layout(child.layout())

    def _build_value_table(self, title, x_values, x_label):
        container = QWidget()
        col = QVBoxLayout(container)
        col.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel(title)
        title_label.setStyleSheet(styles.DIALOG_SECTION_TITLE_STYLE_COMPACT)
        title_label.setWordWrap(True)
        col.addWidget(title_label)

        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels([x_label, "Результат"])
        table.setRowCount(len(x_values))
        for i, x in enumerate(x_values):
            x_item = QTableWidgetItem(str(x))
            x_item.setFlags(Qt.ItemIsEnabled)
            x_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 0, x_item)
            res_item = QTableWidgetItem("")
            res_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 1, res_item)
        table.setEditTriggers(QTableWidget.AllEditTriggers)

        # Подгоняем высоту и ширину точно под содержимое - без внутренней прокрутки
        small_font = QFont()
        small_font.setPointSize(9)
        table.setFont(small_font)
        table.horizontalHeader().setFont(small_font)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(22)
        table.resizeRowsToContents()
        table.resizeColumnsToContents()
        table.horizontalHeader().setMinimumSectionSize(65)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        total_height = table.horizontalHeader().height() + 4
        for row in range(table.rowCount()):
            total_height += table.rowHeight(row)
        table.setFixedHeight(total_height)
        total_width = 6
        for c in range(table.columnCount()):
            total_width += table.columnWidth(c)
        table.setFixedWidth(total_width)

        col.addWidget(table)
        col.addStretch(1)
        # Фиксируем ширину контейнера точно по таблице - чтобы соседняя
        # растяжка (при выравнивании по низу) не смещала таблицу вбок
        container.setFixedWidth(table.width())
        container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
        self.tests_row.addWidget(container)
        return container, table

    def try_accept(self):
        if not self.mods or not self.selected_mod:
            QMessageBox.warning(self, "Ошибка", "Сначала добавьте модификацию через Настройки.")
            return

        if not self.pump_number_input.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите идентификационный номер насоса.")
            return

        for key, table in self.value_tables.items():
            for row in range(table.rowCount()):
                item = table.item(row, 1)
                text = item.text().strip() if item else ""
                if not text:
                    QMessageBox.warning(self, "Ошибка", "Заполните все значения результатов испытаний.")
                    return
                try:
                    float(text)
                except ValueError:
                    QMessageBox.warning(self, "Ошибка", f"Некорректное числовое значение: '{text}'.")
                    return

        pressure_text = self.pressure_input.text().strip()
        if not pressure_text:
            QMessageBox.warning(self, "Ошибка", "Введите значение давления.")
            return
        try:
            float(pressure_text)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Некорректное значение давления.")
            return

        for key, edit in self.seal_inputs.items():
            if not edit.text().strip():
                QMessageBox.warning(self, "Ошибка", "Заполните все поля проверки на герметичность.")
                return

        if not self.password_input.text():
            QMessageBox.warning(self, "Ошибка", "Введите пароль.")
            return

        self.accept()

    def get_data(self):
        results = {}

        def fill(table, start_key):
            for i in range(table.rowCount()):
                key = f'g{start_key + i}'
                text = table.item(i, 1).text().strip()
                try:
                    results[key] = float(text)
                except ValueError:
                    results[key] = None

        fill(self.value_tables['test1'], 5)
        fill(self.value_tables['test2'], 13)
        fill(self.value_tables['test3'], 21)
        results['g32'] = float(self.pressure_input.text().strip())

        seal_results = {key: edit.text().strip() for key, edit in self.seal_inputs.items()}

        return {
            'modification_id': self.selected_mod['id'],
            'modification_name': self.selected_mod['name'],
            'pump_number': self.pump_number_input.text().strip(),
            'test_date': self.date_input.date().toString('yyyy-MM-dd'),
            'test_type': self.type_combo.currentText(),
            'order_number': self.order_input.text().strip() or None,
            'results': results,
            'seal_results': seal_results,
            'note': self.note_input.text().strip(),
            'password': self.password_input.text(),
        }


class EditPumpDialog(QDialog):
    """Комплексное редактирование существующего протокола: номер заказа,
    дата проверки, модификация, тип проверки, герметичность, значения
    испытаний и примечание. Идентификационный номер насоса не меняется -
    показывается как справочная информация."""
    def __init__(self, pump_data, parent=None):
        super().__init__(parent)
        self.pump_data = pump_data
        self.setWindowTitle(f"Редактирование протокола - насос № {pump_data.get('pump_number')}")
        self.setModal(True)
        self.selected_mod = None
        self.value_tables = {}
        self.seal_inputs = {}
        # Исходные значения - используются при перестроении таблиц (смена
        # модификации), чтобы не терять уже введённые результаты испытаний
        self.original_results = dict(pump_data.get('results_json') or {})
        self.original_seal = dict(pump_data.get('seal_results_json') or {})

        outer_layout = QVBoxLayout(self)

        self.mods = db.get_all_modifications()

        info_row = QHBoxLayout()
        info_row.addWidget(QLabel(f"Идентификационный № насоса: {pump_data.get('pump_number')}"))
        outer_layout.addLayout(info_row)

        def field_row(label_text, widget):
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFixedWidth(110)
            row.addWidget(lbl)
            row.addWidget(widget)
            outer_layout.addLayout(row)

        self.mod_combo = QComboBox()
        current_index = 0
        for i, (mod_id, name) in enumerate(self.mods):
            self.mod_combo.addItem(name, mod_id)
            if mod_id == pump_data.get('modification_id'):
                current_index = i
        field_row("Модификация:", self.mod_combo)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        existing_date = pump_data.get('test_date') or ''
        if existing_date and ' ' in existing_date:
            existing_date = existing_date.split(' ')[0]
        qdate = QDate.fromString(existing_date, 'yyyy-MM-dd')
        self.date_input.setDate(qdate if qdate.isValid() else QDate.currentDate())
        field_row("Дата:", self.date_input)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["первичная", "повторная"])
        idx = self.type_combo.findText(pump_data.get('test_type') or 'первичная')
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        field_row("Тип:", self.type_combo)

        self.order_input = QLineEdit()
        order_num = pump_data.get('order_number')
        if order_num:
            self.order_input.setText(str(order_num).replace('.0', ''))
        field_row("№ заказа:", self.order_input)

        self.values_widget = QWidget()
        self.values_main_layout = QVBoxLayout(self.values_widget)
        self.tests_row = QHBoxLayout()
        self.tests_row.setSpacing(20)
        self.extra_column = QVBoxLayout()
        centered_tests_row = QHBoxLayout()
        centered_tests_row.addStretch(1)
        centered_tests_row.addLayout(self.tests_row)
        centered_tests_row.addStretch(1)
        self.values_main_layout.addLayout(centered_tests_row)
        self.values_main_layout.addLayout(self.extra_column)
        outer_layout.addWidget(self.values_widget)

        note_row = QHBoxLayout()
        note_row.addWidget(QLabel("Примечание:"))
        self.note_input = QLineEdit()
        self.note_input.setText(pump_data.get('note', '') or '')
        note_row.addWidget(self.note_input)
        outer_layout.addLayout(note_row)

        password_row = QHBoxLayout()
        password_row.addWidget(QLabel("Пароль для сохранения:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        password_row.addWidget(self.password_input)
        outer_layout.addLayout(password_row)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Cancel).setText("Отмена")
        button_box.accepted.connect(self.try_accept)
        button_box.rejected.connect(self.reject)
        outer_layout.addWidget(button_box)

        self.mod_combo.setCurrentIndex(current_index)
        self.mod_combo.currentIndexChanged.connect(self.on_modification_changed)
        if self.mods:
            self.on_modification_changed(current_index)
        else:
            QMessageBox.warning(
                self, "Нет модификаций",
                "В базе нет ни одной модификации. Сначала добавьте модификацию через Настройки → Добавить модификацию."
            )

        outer_layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
        self.adjustSize()
        _clamp_to_screen(self)

    def on_modification_changed(self, index):
        self._clear_sub_layout(self.tests_row)
        self._clear_sub_layout(self.extra_column)
        self.value_tables = {}
        self.seal_inputs = {}

        mod_id = self.mod_combo.currentData()
        if mod_id is None:
            return
        self.selected_mod = db.get_modification_by_id(mod_id)
        if not self.selected_mod:
            return

        self.value_tables['test1'] = self._build_value_table(
            "Испытание 1\nРасход от оборотов\nECO выкл, I=0 A",
            self.selected_mod['norm_graph1_x'], "Обороты", 5
        )
        self.value_tables['test2'] = self._build_value_table(
            "Испытание 2\nРасход от оборотов\nECO вкл, I=1 A",
            self.selected_mod['norm_graph2_x'], "Обороты", 13
        )
        self.value_tables['test3'] = self._build_value_table(
            "Испытание 3\nРасход от силы тока\nна клапане ECO",
            self.selected_mod['norm_graph3_x'], "Ток, А", 21
        )

        pressure_row = QHBoxLayout()
        pressure_label = QLabel(
            f"Испытание 4: давление (норма: {self.selected_mod['pressure_min']} – "
            f"{self.selected_mod['pressure_max']} бар):"
        )
        pressure_label.setStyleSheet(styles.DIALOG_SECTION_TITLE_STYLE_COMPACT)
        pressure_row.addWidget(pressure_label)
        self.pressure_input = QLineEdit()
        self.pressure_input.setFixedWidth(120)
        existing_pressure = self.original_results.get('g32')
        if existing_pressure is not None:
            self.pressure_input.setText(str(existing_pressure))
        pressure_row.addWidget(self.pressure_input)
        pressure_row.addStretch()
        self.extra_column.addLayout(pressure_row)

        seal_label = QLabel("Герметичность:")
        seal_label.setStyleSheet(styles.DIALOG_SECTION_TITLE_STYLE_COMPACT)
        self.extra_column.addWidget(seal_label)
        seal_grid = QHBoxLayout()
        for key in utils.SEAL_KEYS:
            one_col = QVBoxLayout()
            lbl = QLabel(utils.SEAL_LABELS[key] + ":")
            lbl.setWordWrap(True)
            lbl.setFixedWidth(140)
            one_col.addWidget(lbl)
            edit = QLineEdit(self.original_seal.get(key, self.selected_mod['seal_rules'].get(key, '')))
            one_col.addWidget(edit)
            self.seal_inputs[key] = edit
            seal_grid.addLayout(one_col)
        seal_grid.addStretch()
        self.extra_column.addLayout(seal_grid)

    def _clear_sub_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_sub_layout(child.layout())

    def _build_value_table(self, title, x_values, x_label, start_key):
        col = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet(styles.DIALOG_SECTION_TITLE_STYLE_COMPACT)
        title_label.setWordWrap(True)
        col.addWidget(title_label)

        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels([x_label, "Результат"])
        table.setRowCount(len(x_values))
        for i, x in enumerate(x_values):
            x_item = QTableWidgetItem(str(x))
            x_item.setFlags(Qt.ItemIsEnabled)
            x_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 0, x_item)
            existing_val = self.original_results.get(f'g{start_key + i}')
            res_item = QTableWidgetItem(str(existing_val) if existing_val is not None else '')
            res_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 1, res_item)
        table.setEditTriggers(QTableWidget.AllEditTriggers)

        small_font = QFont()
        small_font.setPointSize(9)
        table.setFont(small_font)
        table.horizontalHeader().setFont(small_font)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(22)
        table.resizeRowsToContents()
        table.resizeColumnsToContents()
        table.horizontalHeader().setMinimumSectionSize(65)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        total_height = table.horizontalHeader().height() + 4
        for row in range(table.rowCount()):
            total_height += table.rowHeight(row)
        table.setFixedHeight(total_height)
        total_width = 6
        for c in range(table.columnCount()):
            total_width += table.columnWidth(c)
        table.setFixedWidth(total_width)

        col.addWidget(table)
        col.addStretch(1)
        container = QWidget()
        container.setLayout(col)
        container.setFixedWidth(table.width())
        container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
        self.tests_row.addWidget(container)
        return table

    def try_accept(self):
        if not self.mods or not self.selected_mod:
            QMessageBox.warning(self, "Ошибка", "Сначала добавьте модификацию через Настройки.")
            return

        for key, table in self.value_tables.items():
            for row in range(table.rowCount()):
                item = table.item(row, 1)
                text = item.text().strip() if item else ""
                if not text:
                    QMessageBox.warning(self, "Ошибка", "Заполните все значения результатов испытаний.")
                    return
                try:
                    float(text)
                except ValueError:
                    QMessageBox.warning(self, "Ошибка", f"Некорректное числовое значение: '{text}'.")
                    return

        pressure_text = self.pressure_input.text().strip()
        if not pressure_text:
            QMessageBox.warning(self, "Ошибка", "Введите значение давления.")
            return
        try:
            float(pressure_text)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Некорректное значение давления.")
            return

        for key, edit in self.seal_inputs.items():
            if not edit.text().strip():
                QMessageBox.warning(self, "Ошибка", "Заполните все поля проверки на герметичность.")
                return

        if not self.password_input.text():
            QMessageBox.warning(self, "Ошибка", "Введите пароль.")
            return

        self.accept()

    def get_data(self):
        results = {}

        def fill(table, start_key):
            for i in range(table.rowCount()):
                key = f'g{start_key + i}'
                text = table.item(i, 1).text().strip()
                try:
                    results[key] = float(text)
                except ValueError:
                    results[key] = None

        fill(self.value_tables['test1'], 5)
        fill(self.value_tables['test2'], 13)
        fill(self.value_tables['test3'], 21)
        results['g32'] = float(self.pressure_input.text().strip())

        seal_results = {key: edit.text().strip() for key, edit in self.seal_inputs.items()}

        return {
            'modification_id': self.selected_mod['id'],
            'modification_name': self.selected_mod['name'],
            'test_date': self.date_input.date().toString('yyyy-MM-dd'),
            'test_type': self.type_combo.currentText(),
            'order_number': self.order_input.text().strip() or None,
            'results': results,
            'seal_results': seal_results,
            'note': self.note_input.text().strip(),
            'password': self.password_input.text(),
        }


class EditProtocolDialog(QDialog):
    def __init__(self, pump_data, parent=None):
        super().__init__(parent)
        self.pump_data = pump_data
        self.setWindowTitle("Редактирование примечания")
        self.setModal(True)
        self.resize(500, 300)

        layout = QVBoxLayout(self)

        # Информация о насосе
        info = QLabel(
            f"Насос: {pump_data.get('pump_number')}\n"
            f"Дата: {pump_data.get('test_date')}\n"
            f"Вердикт: {pump_data.get('verdict')}"
        )
        layout.addWidget(info)

        # Поле для примечания
        layout.addWidget(QLabel("Примечание:"))
        self.note_edit = QTextEdit()
        self.note_edit.setPlainText(pump_data.get('note', ''))
        layout.addWidget(self.note_edit)

        # Пароль
        layout.addWidget(QLabel("Введите пароль для подтверждения:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        # Кнопки
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Cancel).setText("Отмена")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_data(self):
        return {
            'note': self.note_edit.toPlainText(),
            'password': self.password_input.text()
        }

class EditHistoryDialog(QDialog):
    def __init__(self, edit_history, pump_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление историей редактирования")
        self.setModal(True)
        self.resize(600, 400)
        self.pump_id = pump_id
        self.clear_note = False  # по умолчанию не очищать примечание

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Выберите записи для удаления (отметьте галочками):"))

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self.list_widget)

        self.entries = []
        if edit_history:
            for line in edit_history.strip().split('\n'):
                if line.strip():
                    self.entries.append(line.strip())

        for entry in self.entries:
            item = QListWidgetItem(entry)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.list_widget.addItem(item)

        btn_layout = QHBoxLayout()
        btn_delete_selected = QPushButton("Удалить выбранные")
        btn_delete_all = QPushButton("Удалить все")
        btn_cancel = QPushButton("Отмена")

        btn_delete_selected.clicked.connect(self.delete_selected)
        btn_delete_all.clicked.connect(self.delete_all)
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_delete_selected)
        btn_layout.addWidget(btn_delete_all)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        self.result_history = edit_history

    def delete_selected(self):
        indices = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                indices.append(i)
        if not indices:
            QMessageBox.information(self, "Информация", "Не выбрано ни одной записи.")
            return
        for i in reversed(indices):
            self.list_widget.takeItem(i)
        self.clear_note = False
        self.save_result()

    def delete_all(self):
        reply = QMessageBox.question(self, "Подтверждение",
                                     "Удалить все записи истории?\nПримечание также будет очищено.",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.list_widget.clear()
            self.clear_note = True
            self.save_result()

    def save_result(self):
        new_entries = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.text().strip():
                new_entries.append(item.text().strip())
        self.result_history = "\n".join(new_entries)
        self.accept()