from PyQt5.QtWidgets import QStatusBar, QWidget, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt

class StatusBar(QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Левая часть (растягивается)
        self.left_widget = QWidget()
        self.left_layout = QHBoxLayout(self.left_widget)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.selected_label = QLabel()
        self.filter_label = QLabel()
        self.left_layout.addWidget(self.selected_label)
        self.left_layout.addWidget(self.filter_label)
        self.addWidget(self.left_widget, stretch=1)
        
        # Правая часть (прижата к правому краю)
        self.right_widget = QWidget()
        self.right_layout = QHBoxLayout(self.right_widget)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.count_label = QLabel()
        self.update_label = QLabel()
        self.right_layout.addWidget(self.count_label)
        self.right_layout.addWidget(self.update_label)
        self.addPermanentWidget(self.right_widget)
        
        self.set_status("Готово")
    
    def set_status(self, message, count=None, filters=None, last_update=None, selected_pump=None):
        # Левая часть
        if selected_pump:
            self.selected_label.setText(f"Выбран: {selected_pump}  |  ")
        else:
            self.selected_label.setText("")
        if filters:
            self.filter_label.setText(f"Фильтры: {filters}")
        else:
            self.filter_label.setText("")
        
        # Правая часть
        self.count_label.setText(f"Всего записей: {count}" if count is not None else "")
        # self.update_label.setText(f"  |  Последнее обновление: {last_update}" if last_update else "")
        if last_update is not None:
            self.update_label.setText(f"Последнее обновление: {last_update}")