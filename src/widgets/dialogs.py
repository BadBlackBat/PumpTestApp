# from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
# from PyQt5.QtCore import Qt
# from PyQt5.QtWidgets import (
#     QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
#     QPushButton, QTextEdit, QDialogButtonBox, QMessageBox, 
#     QListWidget, QListWidgetItem, QComboBox, QDateEdit,
#     QTableWidget, QTableWidgetItem, QScrollArea, QWidget
# )
# from PyQt5.QtCore import Qt, QDate
# import json

# from .. import database as db
# from .. import utils

# class PasswordDialog(QDialog):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setWindowTitle("Введите пароль")
#         self.setModal(True)
#         layout = QVBoxLayout(self)
#         layout.addWidget(QLabel("Для удаления записи введите пароль:"))
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
#             self.table.setItem(i, 0, QTableWidgetItem(str(x_val)))
#             self.table.setItem(i, 1, QTableWidgetItem(str(min_val)))
#             self.table.setItem(i, 2, QTableWidgetItem(str(max_val)))
#         self.table.resizeColumnsToContents()
#         layout.addWidget(self.table)

#         btn_layout = QHBoxLayout()
#         self.btn_add = QPushButton("Добавить точку")
#         self.btn_add.clicked.connect(self.add_row)
#         self.btn_remove = QPushButton("Удалить последнюю точку")
#         self.btn_remove.clicked.connect(self.remove_row)
#         btn_layout.addWidget(self.btn_add)
#         btn_layout.addWidget(self.btn_remove)
#         layout.addLayout(btn_layout)
#         self._update_buttons()

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
#             self.table.setItem(row, col, QTableWidgetItem(""))
#         self._update_buttons()

#     def remove_row(self):
#         if self.table.rowCount() <= 1:
#             return
#         self.table.removeRow(self.table.rowCount() - 1)
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
#         self.resize(680, 720)

#         outer_layout = QVBoxLayout(self)

#         scroll = QScrollArea()
#         scroll.setWidgetResizable(True)
#         content = QWidget()
#         layout = QVBoxLayout(content)

#         layout.addWidget(QLabel("Номер (название) модификации насоса ГУР:"))
#         self.name_input = QLineEdit()
#         if existing_mod:
#             self.name_input.setText(existing_mod['name'])
#         layout.addWidget(self.name_input)

#         layout.addWidget(self._section_title(
#             "Испытание 1: объёмная подача от оборотов (клапан ECO выкл.)"))
#         self.test1 = PointsEditorWidget(
#             x_values=existing_mod['norm_graph1_x'] if existing_mod else list(utils.DEFAULT_GRAPH1_X),
#             min_values=existing_mod['norm_graph1_min'] if existing_mod else [],
#             max_values=existing_mod['norm_graph1_max'] if existing_mod else [],
#             max_points=utils.MAX_GRAPH1_POINTS,
#             x_label="Обороты, об/мин"
#         )
#         layout.addWidget(self.test1)

#         layout.addWidget(self._section_title(
#             "Испытание 2: объёмная подача от оборотов (клапан ECO вкл.)"))
#         self.test2 = PointsEditorWidget(
#             x_values=existing_mod['norm_graph2_x'] if existing_mod else list(utils.DEFAULT_GRAPH2_X),
#             min_values=existing_mod['norm_graph2_min'] if existing_mod else [],
#             max_values=existing_mod['norm_graph2_max'] if existing_mod else [],
#             max_points=utils.MAX_GRAPH2_POINTS,
#             x_label="Обороты, об/мин"
#         )
#         layout.addWidget(self.test2)

#         layout.addWidget(self._section_title(
#             "Испытание 3: объёмная подача от силы тока на клапане ECO"))
#         self.test3 = PointsEditorWidget(
#             x_values=existing_mod['norm_graph3_x'] if existing_mod else list(utils.DEFAULT_GRAPH3_X),
#             min_values=existing_mod['norm_graph3_min'] if existing_mod else [],
#             max_values=existing_mod['norm_graph3_max'] if existing_mod else [],
#             max_points=utils.MAX_GRAPH3_POINTS,
#             x_label="Сила тока, А"
#         )
#         layout.addWidget(self.test3)

#         layout.addWidget(self._section_title(
#             "Испытание 4: давление срабатывания предохранительного клапана"))
#         pressure_layout = QHBoxLayout()
#         pressure_layout.addWidget(QLabel("Мин., бар:"))
#         self.pressure_min_input = QLineEdit(
#             str(existing_mod['pressure_min']) if existing_mod and existing_mod['pressure_min'] is not None else "")
#         pressure_layout.addWidget(self.pressure_min_input)
#         pressure_layout.addWidget(QLabel("Макс., бар:"))
#         self.pressure_max_input = QLineEdit(
#             str(existing_mod['pressure_max']) if existing_mod and existing_mod['pressure_max'] is not None else "")
#         pressure_layout.addWidget(self.pressure_max_input)
#         layout.addLayout(pressure_layout)

#         layout.addWidget(self._section_title("Проверка на герметичность"))
#         self.seal_inputs = {}
#         seal_rules = existing_mod['seal_rules'] if existing_mod else dict(utils.DEFAULT_SEAL_REQUIREMENTS)
#         for key in utils.SEAL_KEYS:
#             row_layout = QHBoxLayout()
#             row_layout.addWidget(QLabel(utils.SEAL_LABELS[key] + ":"))
#             edit = QLineEdit(seal_rules.get(key, utils.DEFAULT_SEAL_REQUIREMENTS[key]))
#             row_layout.addWidget(edit)
#             self.seal_inputs[key] = edit
#             layout.addLayout(row_layout)

#         layout.addWidget(QLabel("Пароль для сохранения:"))
#         self.password_input = QLineEdit()
#         self.password_input.setEchoMode(QLineEdit.Password)
#         layout.addWidget(self.password_input)

#         scroll.setWidget(content)
#         outer_layout.addWidget(scroll)

#         button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
#         button_box.accepted.connect(self.try_accept)
#         button_box.rejected.connect(self.reject)
#         outer_layout.addWidget(button_box)

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
#         btn_close = QPushButton("Закрыть")
#         btn_close.clicked.connect(self.accept)
#         layout.addWidget(btn_close)

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
#         self.resize(680, 780)
#         self.selected_mod = None
#         self.value_tables = {}
#         self.seal_inputs = {}

#         outer_layout = QVBoxLayout(self)
#         scroll = QScrollArea()
#         scroll.setWidgetResizable(True)
#         content = QWidget()
#         self.content_layout = QVBoxLayout(content)

#         self.mods = db.get_all_modifications()  # список (id, name)

#         self.content_layout.addWidget(QLabel("Модификация:"))
#         self.mod_combo = QComboBox()
#         for mod_id, name in self.mods:
#             self.mod_combo.addItem(name, mod_id)
#         self.mod_combo.currentIndexChanged.connect(self.on_modification_changed)
#         self.content_layout.addWidget(self.mod_combo)

#         num_layout = QHBoxLayout()
#         num_layout.addWidget(QLabel("Идентификационный № насоса:"))
#         self.pump_number_input = QLineEdit()
#         num_layout.addWidget(self.pump_number_input)
#         self.content_layout.addLayout(num_layout)

#         date_layout = QHBoxLayout()
#         date_layout.addWidget(QLabel("Дата проверки:"))
#         self.date_input = QDateEdit()
#         self.date_input.setCalendarPopup(True)
#         self.date_input.setDate(QDate.currentDate())
#         date_layout.addWidget(self.date_input)
#         self.content_layout.addLayout(date_layout)

#         type_layout = QHBoxLayout()
#         type_layout.addWidget(QLabel("Тип проверки:"))
#         self.type_combo = QComboBox()
#         self.type_combo.addItems(["первичная", "повторная"])
#         type_layout.addWidget(self.type_combo)
#         self.content_layout.addLayout(type_layout)

#         order_layout = QHBoxLayout()
#         order_layout.addWidget(QLabel("№ заказа (необязательно):"))
#         self.order_input = QLineEdit()
#         order_layout.addWidget(self.order_input)
#         self.content_layout.addLayout(order_layout)

#         # Динамическая область: перестраивается при выборе модификации
#         self.values_widget = QWidget()
#         self.values_layout = QVBoxLayout(self.values_widget)
#         self.content_layout.addWidget(self.values_widget)

#         self.content_layout.addWidget(QLabel("Пароль для сохранения:"))
#         self.password_input = QLineEdit()
#         self.password_input.setEchoMode(QLineEdit.Password)
#         self.content_layout.addWidget(self.password_input)

#         scroll.setWidget(content)
#         outer_layout.addWidget(scroll)

#         button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
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

#     def on_modification_changed(self, index):
#         # Очищаем предыдущее содержимое динамической области
#         while self.values_layout.count():
#             child = self.values_layout.takeAt(0)
#             if child.widget():
#                 child.widget().deleteLater()
#         self.value_tables = {}
#         self.seal_inputs = {}

#         mod_id = self.mod_combo.currentData()
#         if mod_id is None:
#             return
#         self.selected_mod = db.get_modification_by_id(mod_id)
#         if not self.selected_mod:
#             return

#         self.value_tables['test1'] = self._build_value_table(
#             "Испытание 1: подача от оборотов (ECO выкл.)",
#             self.selected_mod['norm_graph1_x'], "Обороты, об/мин"
#         )
#         self.value_tables['test2'] = self._build_value_table(
#             "Испытание 2: подача от оборотов (ECO вкл.)",
#             self.selected_mod['norm_graph2_x'], "Обороты, об/мин"
#         )
#         self.value_tables['test3'] = self._build_value_table(
#             "Испытание 3: подача от силы тока ECO",
#             self.selected_mod['norm_graph3_x'], "Сила тока, А"
#         )

#         pressure_label = QLabel(
#             f"Испытание 4: давление настройки клапана "
#             f"(норма: {self.selected_mod['pressure_min']} – {self.selected_mod['pressure_max']} бар)"
#         )
#         pressure_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
#         self.values_layout.addWidget(pressure_label)
#         self.pressure_input = QLineEdit()
#         self.values_layout.addWidget(self.pressure_input)

#         seal_label = QLabel("Проверка на герметичность")
#         seal_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
#         self.values_layout.addWidget(seal_label)
#         for key in utils.SEAL_KEYS:
#             row_layout = QHBoxLayout()
#             row_layout.addWidget(QLabel(utils.SEAL_LABELS[key] + ":"))
#             edit = QLineEdit(self.selected_mod['seal_rules'].get(key, ''))
#             row_layout.addWidget(edit)
#             self.seal_inputs[key] = edit
#             self.values_layout.addLayout(row_layout)

#     def _build_value_table(self, title, x_values, x_label):
#         title_label = QLabel(title)
#         title_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
#         self.values_layout.addWidget(title_label)

#         table = QTableWidget()
#         table.setColumnCount(2)
#         table.setHorizontalHeaderLabels([x_label, "Результат, л/мин"])
#         table.setRowCount(len(x_values))
#         for i, x in enumerate(x_values):
#             x_item = QTableWidgetItem(str(x))
#             x_item.setFlags(Qt.ItemIsEnabled)
#             table.setItem(i, 0, x_item)
#             table.setItem(i, 1, QTableWidgetItem(""))
#         table.resizeColumnsToContents()
#         table.setEditTriggers(QTableWidget.AllEditTriggers)
#         self.values_layout.addWidget(table)
#         return table

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
    QTableWidget, QTableWidgetItem, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont
import json

from .. import database as db
from .. import utils

class PasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Введите пароль")
        self.setModal(True)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Для удаления записи введите пароль:"))
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
            self.table.setItem(i, 0, QTableWidgetItem(str(x_val)))
            self.table.setItem(i, 1, QTableWidgetItem(str(min_val)))
            self.table.setItem(i, 2, QTableWidgetItem(str(max_val)))
        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)
        self._fit_table_height()

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Добавить точку")
        self.btn_add.clicked.connect(self.add_row)
        self.btn_remove = QPushButton("Удалить последнюю точку")
        self.btn_remove.clicked.connect(self.remove_row)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_remove)
        layout.addLayout(btn_layout)
        self._update_buttons()

    def _fit_table_height(self):
        """Подгоняет высоту таблицы точно под содержимое - без внутренней
        прокрутки. Используется, чтобы диалог обходился без QScrollArea."""
        small_font = QFont()
        small_font.setPointSize(8)
        self.table.setFont(small_font)
        self.table.horizontalHeader().setFont(small_font)
        self.table.verticalHeader().setDefaultSectionSize(20)
        self.table.resizeRowsToContents()
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        total_height = self.table.horizontalHeader().height() + 4
        for row in range(self.table.rowCount()):
            total_height += self.table.rowHeight(row)
        self.table.setFixedHeight(total_height)

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
            self.table.setItem(row, col, QTableWidgetItem(""))
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
        self.resize(1050, 620)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Номер (название) модификации насоса ГУР:"))
        self.name_input = QLineEdit()
        if existing_mod:
            self.name_input.setText(existing_mod['name'])
        layout.addWidget(self.name_input)

        # Три испытания - в один горизонтальный ряд, чтобы диалог оставался
        # компактным по высоте и не требовал прокрутки
        tests_layout = QHBoxLayout()

        test1_col = QVBoxLayout()
        test1_col.addWidget(self._section_title("Испытание 1: подача от оборотов (ECO выкл.)"))
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
        test2_col.addWidget(self._section_title("Испытание 2: подача от оборотов (ECO вкл.)"))
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
        test3_col.addWidget(self._section_title("Испытание 3: подача от силы тока ECO"))
        self.test3 = PointsEditorWidget(
            x_values=existing_mod['norm_graph3_x'] if existing_mod else list(utils.DEFAULT_GRAPH3_X),
            min_values=existing_mod['norm_graph3_min'] if existing_mod else [],
            max_values=existing_mod['norm_graph3_max'] if existing_mod else [],
            max_points=utils.MAX_GRAPH3_POINTS,
            x_label="Ток, А"
        )
        test3_col.addWidget(self.test3)
        tests_layout.addLayout(test3_col)

        layout.addLayout(tests_layout)

        bottom_layout = QHBoxLayout()

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
        pressure_box.addLayout(pressure_row)
        pressure_box.addStretch()
        bottom_layout.addLayout(pressure_box, 1)

        seal_box = QVBoxLayout()
        seal_box.addWidget(self._section_title("Проверка на герметичность"))
        self.seal_inputs = {}
        seal_rules = existing_mod['seal_rules'] if existing_mod else dict(utils.DEFAULT_SEAL_REQUIREMENTS)
        for key in utils.SEAL_KEYS:
            row_layout = QHBoxLayout()
            lbl = QLabel(utils.SEAL_LABELS[key] + ":")
            lbl.setWordWrap(True)
            lbl.setFixedWidth(200)
            row_layout.addWidget(lbl)
            edit = QLineEdit(seal_rules.get(key, utils.DEFAULT_SEAL_REQUIREMENTS[key]))
            row_layout.addWidget(edit)
            self.seal_inputs[key] = edit
            seal_box.addLayout(row_layout)
        bottom_layout.addLayout(seal_box, 2)

        layout.addLayout(bottom_layout)

        password_row = QHBoxLayout()
        password_row.addWidget(QLabel("Пароль для сохранения:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        password_row.addWidget(self.password_input)
        layout.addLayout(password_row)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.try_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _section_title(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("font-weight: bold; margin-top: 10px;")
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
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

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
        self.resize(1100, 650)
        self.selected_mod = None
        self.value_tables = {}
        self.seal_inputs = {}

        outer_layout = QVBoxLayout(self)

        self.mods = db.get_all_modifications()  # список (id, name)

        # Компактная строка с основными полями
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Модификация:"))
        self.mod_combo = QComboBox()
        for mod_id, name in self.mods:
            self.mod_combo.addItem(name, mod_id)
        self.mod_combo.currentIndexChanged.connect(self.on_modification_changed)
        top_row.addWidget(self.mod_combo, 2)

        top_row.addWidget(QLabel("№ насоса:"))
        self.pump_number_input = QLineEdit()
        top_row.addWidget(self.pump_number_input, 1)

        top_row.addWidget(QLabel("Дата:"))
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        top_row.addWidget(self.date_input, 1)

        top_row.addWidget(QLabel("Тип:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["первичная", "повторная"])
        top_row.addWidget(self.type_combo, 1)

        top_row.addWidget(QLabel("№ заказа:"))
        self.order_input = QLineEdit()
        top_row.addWidget(self.order_input, 1)
        outer_layout.addLayout(top_row)

        # Динамическая область: горизонтальные колонки испытаний -
        # перестраивается при выборе модификации
        self.values_widget = QWidget()
        self.values_layout = QHBoxLayout(self.values_widget)
        outer_layout.addWidget(self.values_widget)

        password_row = QHBoxLayout()
        password_row.addWidget(QLabel("Пароль для сохранения:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        password_row.addWidget(self.password_input)
        outer_layout.addLayout(password_row)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
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

    def on_modification_changed(self, index):
        # Очищаем предыдущее содержимое динамической области
        while self.values_layout.count():
            child = self.values_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_sub_layout(child.layout())
        self.value_tables = {}
        self.seal_inputs = {}

        mod_id = self.mod_combo.currentData()
        if mod_id is None:
            return
        self.selected_mod = db.get_modification_by_id(mod_id)
        if not self.selected_mod:
            return

        self.value_tables['test1'] = self._build_value_table(
            "Испытание 1: подача от оборотов (ECO выкл.)",
            self.selected_mod['norm_graph1_x'], "Обороты"
        )
        self.value_tables['test2'] = self._build_value_table(
            "Испытание 2: подача от оборотов (ECO вкл.)",
            self.selected_mod['norm_graph2_x'], "Обороты"
        )
        self.value_tables['test3'] = self._build_value_table(
            "Испытание 3: подача от силы тока ECO",
            self.selected_mod['norm_graph3_x'], "Ток, А"
        )

        # Четвёртая колонка: давление + герметичность
        extra_col = QVBoxLayout()
        pressure_label = QLabel(
            f"Испытание 4: давление\n(норма: {self.selected_mod['pressure_min']} – "
            f"{self.selected_mod['pressure_max']} бар)"
        )
        pressure_label.setStyleSheet("font-weight: bold;")
        pressure_label.setWordWrap(True)
        extra_col.addWidget(pressure_label)
        self.pressure_input = QLineEdit()
        extra_col.addWidget(self.pressure_input)

        seal_label = QLabel("Герметичность")
        seal_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        extra_col.addWidget(seal_label)
        for key in utils.SEAL_KEYS:
            lbl = QLabel(utils.SEAL_LABELS[key] + ":")
            lbl.setWordWrap(True)
            extra_col.addWidget(lbl)
            edit = QLineEdit(self.selected_mod['seal_rules'].get(key, ''))
            extra_col.addWidget(edit)
            self.seal_inputs[key] = edit
        extra_col.addStretch()
        self.values_layout.addLayout(extra_col, 1)

    def _clear_sub_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_sub_layout(child.layout())

    def _build_value_table(self, title, x_values, x_label):
        col = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold;")
        title_label.setWordWrap(True)
        col.addWidget(title_label)

        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels([x_label, "Результат"])
        table.setRowCount(len(x_values))
        for i, x in enumerate(x_values):
            x_item = QTableWidgetItem(str(x))
            x_item.setFlags(Qt.ItemIsEnabled)
            table.setItem(i, 0, x_item)
            table.setItem(i, 1, QTableWidgetItem(""))
        table.setEditTriggers(QTableWidget.AllEditTriggers)

        # Подгоняем высоту точно под содержимое - без внутренней прокрутки
        small_font = QFont()
        small_font.setPointSize(8)
        table.setFont(small_font)
        table.horizontalHeader().setFont(small_font)
        table.verticalHeader().setDefaultSectionSize(20)
        table.resizeRowsToContents()
        table.resizeColumnsToContents()
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        total_height = table.horizontalHeader().height() + 4
        for row in range(table.rowCount()):
            total_height += table.rowHeight(row)
        table.setFixedHeight(total_height)

        col.addWidget(table)
        col.addStretch()
        self.values_layout.addLayout(col, 1)
        return table

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