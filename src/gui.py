import sys
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QMessageBox, QInputDialog, QLineEdit,
    QDialog
)
from PyQt5.QtCore import Qt

from .widgets.left_panel import LeftPanel
from .widgets.right_panel import RightPanel
from .widgets.status_bar import StatusBar
from .widgets.dialogs import PasswordDialog, AddModificationDialog, AddOrderDialog
from . import database as db
from . import excel_importer as importer

from datetime import datetime
from .widgets.dialogs import EditProtocolDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("База данных проверок насосов ГУР")
        self.setGeometry(100, 100, 1400, 900)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Сплиттер
        self.splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter)
        
        # Левая панель
        self.left_panel = LeftPanel()
        self.left_panel.pump_selected.connect(self.on_pump_selected)
        self.left_panel.request_import.connect(self.on_import_requested)
        self.left_panel.request_add.connect(self.on_add_requested)
        self.left_panel.request_delete.connect(self.on_delete_requested)
        self.left_panel.request_edit.connect(self.on_edit_requested)
        self.left_panel.filters_applied.connect(self.update_status)
        self.splitter.addWidget(self.left_panel)
        
        # Правая панель
        self.right_panel = RightPanel()
        self.splitter.addWidget(self.right_panel)
        
        # Пропорции
        self.splitter.setSizes([int(self.width() * 0.4), int(self.width() * 0.6)])
        
        # Статусная строка
        self.status_bar = StatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status()
        
        # Загрузка данных
        self.left_panel.load_data()
    
    def on_pump_selected(self, pump_data):
        """Обработка выбора насоса."""
        self.right_panel.display_protocol(pump_data)
        self.update_status(selected_pump=pump_data['pump_number'])
    
    def on_import_requested(self):
        """Импорт Excel."""
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл Excel", "", "Excel files (*.xlsx *.xls)"
        )
        if file_path:
            count = importer.import_excel_file(file_path, self)
            if count > 0:
                self.left_panel.refresh()
                self.update_status()
    
    def on_add_requested(self):
        """Ручное добавление записи (пока заглушка)."""
        # Позже реализуем диалог добавления
        QMessageBox.information(self, "Добавление", "Функция добавления вручную будет реализована позже.")
    
    def on_delete_requested(self, pump_id):
        """Удаление записи с паролем."""
        # Запрос пароля
        dialog = PasswordDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            if dialog.password == "admin":  # временный пароль
                db.delete_pump(pump_id)
                self.left_panel.refresh()
                self.update_status()
                QMessageBox.information(self, "Удаление", "Запись удалена.")
            else:
                QMessageBox.warning(self, "Ошибка", "Неверный пароль.")
    
    def update_status(self, filters=None, selected_pump=None):
        all_pumps = db.get_all_pumps()
        count = len(all_pumps)
        filters_text = ""
        if filters:
            parts = []
            if filters.get('pump_number'):
                parts.append(f"поиск: {filters['pump_number']}")
            if filters.get('verdict'):
                parts.append(f"вердикт: {filters['verdict']}")
            if filters.get('test_type'):
                parts.append(f"тип: {filters['test_type']}")
            if filters.get('is_sealed') is not None:
                parts.append(f"герметичность: {'Да' if filters['is_sealed'] else 'Нет'}")
            if filters.get('date_from') or filters.get('date_to'):
                parts.append(f"дата: {filters.get('date_from', '')} - {filters.get('date_to', '')}")
            if filters.get('only_duplicates'):
                parts.append("только дубли")
            filters_text = ", ".join(parts)
        # Передаём дату обновления (можно текущую или из БД)
        from datetime import datetime
        last_update = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.status_bar.set_status("Готово", count=count, filters=filters_text,
                                last_update=last_update, selected_pump=selected_pump)
    
    def on_edit_requested(self, pump_id):
        pump_data = db.get_pump_by_id(pump_id)
        if not pump_data:
            return
        dialog = EditProtocolDialog(pump_data, self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if data['password'] != "admin":  # временный пароль
                QMessageBox.warning(self, "Ошибка", "Неверный пароль")
                return
            # Формируем запись истории
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            reason = data['reason']
            if not reason:
                reason = "Без указания причины"
            new_entry = f"{timestamp}: {reason}\n"
            old_history = pump_data.get('edit_history', '')
            if old_history:
                edit_history = new_entry + old_history
            else:
                edit_history = new_entry
            
            # Обновляем запись
            db.update_pump(pump_id, note=data['note'], edit_history=edit_history)
            self.left_panel.refresh()
            # Если текущий открытый протокол относится к этому насосу, обновить правую панель
            if self.right_panel.current_data and self.right_panel.current_data['id'] == pump_id:
                updated = db.get_pump_by_id(pump_id)
                self.right_panel.display_protocol(updated)
            QMessageBox.information(self, "Успех", "Протокол обновлён.")