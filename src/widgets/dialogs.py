from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QDialogButtonBox, QMessageBox
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
        self.setWindowTitle("Редактирование протокола")
        self.setModal(True)
        layout = QVBoxLayout(self)
        
        # Поле для примечания
        layout.addWidget(QLabel("Примечание:"))
        self.note_edit = QTextEdit()
        self.note_edit.setText(pump_data.get('note', ''))
        layout.addWidget(self.note_edit)
        
        # Поле для причины редактирования
        layout.addWidget(QLabel("Причина редактирования:"))
        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText("Введите причину изменения")
        layout.addWidget(self.reason_edit)
        
        # Пароль
        layout.addWidget(QLabel("Подтвердите пароль:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)
        
        # Кнопки
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
    
    def get_data(self):
        return {
            'note': self.note_edit.toPlainText(),
            'reason': self.reason_edit.text(),
            'password': self.password_input.text()
        }