from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QDialogButtonBox, QMessageBox, 
    QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt

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

class AddModificationDialog(QDialog):
    # Позже реализуем
    pass

class AddOrderDialog(QDialog):
    # Позже реализуем
    pass

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