# from PyQt5.QtWidgets import QStatusBar, QLabel
# from PyQt5.QtCore import Qt

# class StatusBar(QStatusBar):
#     def __init__(self, parent=None):
#         super().__init__(parent)
        
#         # Левая часть: выбранный насос
#         self.selected_label = QLabel()
#         self.selected_label.setMinimumWidth(150)
#         self.selected_label.setVisible(False)
#         self.addWidget(self.selected_label)
        
#         # Центр: фильтры (растягивается)
#         self.filter_label = QLabel()
#         self.filter_label.setAlignment(Qt.AlignCenter)
#         self.addWidget(self.filter_label, stretch=1)
        
#         # Правая часть: счётчик и дата обновления (прижаты к правому краю)
#         self.count_label = QLabel()
#         self.update_label = QLabel()
#         self.update_label.setStyleSheet("padding-right: 10px;")
#         self.addPermanentWidget(self.count_label)
#         self.addPermanentWidget(self.update_label)
        
#         self.set_status("Готово")
    
#     def set_status(self, message, count=None, good_count=None, filters=None, last_update=None, selected_pump=None):
#         # Левая часть
#         if selected_pump:
#             self.selected_label.setText(f"Выбран образец: {selected_pump}")
#             self.selected_label.setVisible(True)
#         else:
#             self.selected_label.setText("")
#             self.selected_label.setVisible(False)
            
#         # Центр
#         if filters:
#             self.filter_label.setText(f"Применены фильтры: {filters}")
#         else:
#             self.filter_label.setText("")
        
#         # Правая часть
#         if count is not None:
#             count_text = f"Всего проверено: {count} шт."
#             if good_count is not None:
#                 count_text += f", из них годных - {good_count} шт."
#             self.count_label.setText(count_text)
#         else:
#             self.count_label.setText("")
#         if last_update is not None:
#             self.update_label.setText(f"Последнее обновление: {last_update}")
#         else:
#             self.update_label.setText("")

from PyQt5.QtWidgets import QStatusBar, QLabel
from PyQt5.QtCore import Qt

class StatusBar(QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Левая часть: выбранный насос
        self.selected_label = QLabel()
        self.selected_label.setMinimumWidth(150)
        self.selected_label.setStyleSheet("padding-left: 10px;")
        self.selected_label.setVisible(False)
        self.addWidget(self.selected_label)
        
        # Центр: фильтры (растягивается)
        self.filter_label = QLabel()
        self.filter_label.setAlignment(Qt.AlignCenter)
        self.addWidget(self.filter_label, stretch=1)
        
        # Правая часть: счётчик и дата обновления (прижаты к правому краю)
        self.count_label = QLabel()
        self.update_label = QLabel()
        self.update_label.setStyleSheet("padding-right: 10px;")
        self.addPermanentWidget(self.count_label)
        self.addPermanentWidget(self.update_label)
        
        self.set_status("Готово")
    
    def set_status(self, message, count=None, good_count=None, filters=None, last_update=None, selected_pump=None):
        # Левая часть
        if selected_pump:
            self.selected_label.setText(f"Выбран образец: {selected_pump}")
            self.selected_label.setVisible(True)
        else:
            self.selected_label.setText("")
            self.selected_label.setVisible(False)
            
        # Центр
        if filters:
            self.filter_label.setText(f"Применены фильтры: {filters}")
        else:
            self.filter_label.setText("")
        
        # Правая часть
        if count is not None:
            count_text = f"Всего проверено: {count} шт."
            if good_count is not None:
                count_text += f", из них годных - {good_count} шт."
            self.count_label.setText(count_text)
        else:
            self.count_label.setText("")
        if last_update is not None:
            self.update_label.setText(f"Последнее обновление: {last_update}")
        else:
            self.update_label.setText("")