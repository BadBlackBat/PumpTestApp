import sys
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QMessageBox, QInputDialog, QLineEdit,
    QDialog, QPushButton, QLabel
)
from PyQt5.QtCore import Qt

from PyQt5.QtGui import QFont

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

        self.current_selected_pump = None
        self.current_filters = None
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Верхняя панель с логотипом и кнопками
        top_layout = QHBoxLayout()

        # Добавляем растяжение слева, чтобы центрировать логотип
        top_layout.addStretch()

        # Логотип (текст)
        logo_label = QLabel("Лаборатория Рулевого Управления")
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setFont(QFont("Arial", 14, QFont.Bold))
        logo_label.setStyleSheet("color: #2c3e50;")
        top_layout.addWidget(logo_label)

        # Растяжение между логотипом и кнопками
        top_layout.addStretch()

        # Кнопки-заглушки
        btn_stats = QPushButton("📊")
        btn_stats.setToolTip("Статистика")
        btn_stats.clicked.connect(self.toggle_statistics)
        top_layout.addWidget(btn_stats)

        btn_theme = QPushButton("🌙")
        btn_settings = QPushButton("⚙️")
        btn_print = QPushButton("🖨️")
        btn_theme.setToolTip("Смена темы")
        btn_settings.setToolTip("Настройки")
        btn_print.setToolTip("Печать")

        # Подключаем заглушки
        btn_theme.clicked.connect(lambda: QMessageBox.information(self, "Тема", "Функция будет реализована позже"))
        btn_settings.clicked.connect(lambda: QMessageBox.information(self, "Настройки", "Функция будет реализована позже"))
        btn_print.clicked.connect(lambda: QMessageBox.information(self, "Печать", "Функция будет реализована позже"))

        top_layout.addWidget(btn_theme)
        top_layout.addWidget(btn_settings)
        top_layout.addWidget(btn_print)

        main_layout.insertLayout(0, top_layout)
        
        # Сплиттер
        self.splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter)
        self.splitter.setHandleWidth(0)
        
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
        self.showing_stats = False

        self.right_panel.clear_requested.connect(self.on_clear_requested)
        
        # Пропорции
        self.splitter.setSizes([int(self.width() * 0.4), int(self.width() * 0.6)])
        
        # Статусная строка
        self.status_bar = StatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status()
        
        # Загрузка данных
        self.left_panel.load_data()
    
    def toggle_statistics(self):
        if not self.left_panel.compact_mode:
            self.left_panel.btn_view_toggle.setChecked(False)
            
        if self.showing_stats:
            self.right_panel.clear_protocol()
            self.showing_stats = False
            self.left_panel.table.clearSelection()
            self.current_selected_pump = None
            self.update_status()
        else:
            stats_data = db.get_statistics()
            self.right_panel.display_statistics(stats_data)
            self.showing_stats = True
            self.current_selected_pump = None
            self.update_status()

    def on_pump_selected(self, pump_data):
        if not self.left_panel.compact_mode:
            self.left_panel.btn_view_toggle.setChecked(False)
        if self.showing_stats:
            self.showing_stats = False
        self.right_panel.display_protocol(pump_data)
        self.current_selected_pump = pump_data['pump_number']
        self.update_status()  # без параметров

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
        if self.showing_stats: self.toggle_statistics()

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
        if self.showing_stats: self.toggle_statistics()

    # def update_status(self, filters=None, selected_pump=None):
    #     all_pumps = db.get_all_pumps()
    #     count = len(all_pumps)
    #     filters_text = ""
    #     if filters:
    #         parts = []
    #         if filters.get('pump_number'):
    #             parts.append(f"поиск: {filters['pump_number']}")
    #         if filters.get('verdict'):
    #             parts.append(f"вердикт: {filters['verdict']}")
    #         if filters.get('test_type'):
    #             parts.append(f"тип: {filters['test_type']}")
    #         if filters.get('is_sealed') is not None:
    #             parts.append(f"герметичность: {'Да' if filters['is_sealed'] else 'Нет'}")
    #         if filters.get('date_from') or filters.get('date_to'):
    #             parts.append(f"дата: {filters.get('date_from', '')} - {filters.get('date_to', '')}")
    #         if filters.get('only_duplicates'):
    #             parts.append("только дубли")
    #         filters_text = ", ".join(parts)
    #     last_update = db.get_last_update_date()
    #     self.status_bar.set_status("Готово", count=count, filters=filters_text, selected_pump=selected_pump, last_update=last_update)

    def update_status(self, filters=None, selected_pump=None):
        # Если фильтры не переданы, берём из левой панели
        if filters is None:
            filters = self.left_panel.current_filters
        # Если выбранный насос не передан, берём сохранённый
        if selected_pump is None:
            selected_pump = self.current_selected_pump

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
        last_update = db.get_last_update_date()
        self.status_bar.set_status("Готово", count=count, filters=filters_text, selected_pump=selected_pump, last_update=last_update)

    def on_edit_requested(self, pump_id):
        pump_data = db.get_pump_by_id(pump_id)
        if not pump_data:
            QMessageBox.warning(self, "Ошибка", "Запись не найдена.")
            return

        dialog = EditProtocolDialog(pump_data, self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if data['password'] != "admin":
                QMessageBox.warning(self, "Ошибка", "Неверный пароль.")
                return

            new_note = data['note']
            old_note = pump_data.get('note', '')

            # Формируем запись для истории
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if new_note.strip() == "" and old_note.strip() != "":
                edit_entry = f"{timestamp}: Примечание удалено"
            elif new_note.strip() != "" and old_note.strip() == "":
                edit_entry = f"{timestamp}: Примечание добавлено"
            elif new_note.strip() != "" and old_note.strip() != "":
                edit_entry = f"{timestamp}: Примечание изменено"
            else:
                edit_entry = f"{timestamp}: Примечание не изменено"  # на всякий случай

            old_history = pump_data.get('edit_history', '')
            new_history = edit_entry + "\n" + old_history if old_history else edit_entry

            # Сохраняем
            db.update_pump(pump_id, note=new_note, edit_history=new_history)

            # Обновляем интерфейс
            self.left_panel.refresh()
            current_selected = self.right_panel.current_data
            if current_selected and current_selected['id'] == pump_id:
                updated = db.get_pump_by_id(pump_id)
                self.right_panel.display_protocol(updated)

            QMessageBox.information(self, "Успех", "Примечание обновлено.")
    
    def on_clear_requested(self):
        # 1. Свернуть расширенный вид
        if not self.left_panel.compact_mode:
            self.left_panel.btn_view_toggle.setChecked(False)
        
        # 2. Сбросить фильтры (вызовет apply_filters и обновит таблицу)
        self.left_panel.reset_filters()
        
        # 3. Снять выделение в таблице
        self.left_panel.table.clearSelection()
        
        # 4. Сбросить выбранный насос в статус-баре
        self.current_selected_pump = None
        
        # 5. Обновить статус-бар (без выбранного насоса, фильтры уже сброшены)
        self.update_status(selected_pump=None)
        
        # 6. Если была статистика, закрыть её
        self.showing_stats = False