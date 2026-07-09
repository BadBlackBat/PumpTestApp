from PyQt5.QtWidgets import QStatusBar, QLabel
from PyQt5.QtCore import Qt

class StatusBar(QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.count_label = QLabel()
        self.filter_label = QLabel()
        self.update_label = QLabel()
        
        self.addPermanentWidget(self.count_label)
        self.addPermanentWidget(self.filter_label)
        self.addPermanentWidget(self.update_label)
        
        self.set_status("Готово")
    
    def set_status(self, message, count=None, filters=None, last_update=None):
        """Обновляет строку состояния."""
        self.count_label.setText(f"Всего записей: {count}" if count is not None else "")
        self.filter_label.setText(f"Фильтры: {filters}" if filters else "")
        self.update_label.setText(f"Последнее обновление: {last_update}" if last_update else "")
        # Можно также использовать showMessage для временных сообщений