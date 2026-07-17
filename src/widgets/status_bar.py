# from PyQt5.QtWidgets import QStatusBar, QLabel
# from PyQt5.QtCore import Qt
# from .. import styles

# class StatusBar(QStatusBar):
#     def __init__(self, parent=None):
#         super().__init__(parent)
        
#         # Левая часть: выбранный насос
#         self.selected_label = QLabel()
#         self.selected_label.setMinimumWidth(150)
#         self.selected_label.setStyleSheet(styles.STATUS_BAR_SELECTED_LABEL_STYLE)
#         self.selected_label.setVisible(False)
#         self.addWidget(self.selected_label)
        
#         # Центр: фильтры (растягивается)
#         self.filter_label = QLabel()
#         self.filter_label.setAlignment(Qt.AlignCenter)
#         self.addWidget(self.filter_label, stretch=1)
        
#         # Правая часть: счётчик и дата обновления (прижаты к правому краю)
#         self.count_label = QLabel()
#         self.update_label = QLabel()
#         self.update_label.setStyleSheet(styles.STATUS_BAR_UPDATE_LABEL_STYLE)
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

from PyQt5.QtWidgets import QStatusBar, QLabel, QWidget, QGraphicsDropShadowEffect, QVBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QLinearGradient, QBrush
from .. import styles


class _GlowLine(QWidget):
    """Тонкая светящаяся полоса-акцент на всю ширину статус-бара -
    имитация свечения приборной панели (HUD). Прозрачная по краям,
    ярче к центру - настоящий "blur" QSS не поддерживает, поэтому
    свечение имитируется градиентом с плавным затуханием альфа-канала."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setFixedHeight(styles.STATUS_BAR_GLOW_HEIGHT)

    def paintEvent(self, event):
        painter = QPainter(self)
        r, g, b = styles.STATUS_BAR_GLOW_COLOR
        max_alpha = styles.STATUS_BAR_GLOW_MAX_ALPHA
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0.0, QColor(r, g, b, 0))
        gradient.setColorAt(0.5, QColor(r, g, b, max_alpha))
        gradient.setColorAt(1.0, QColor(r, g, b, 0))
        painter.fillRect(self.rect(), QBrush(gradient))


class StatusBar(QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Тёмная "графитовая" панель со скруглёнными верхними углами и
        # светлым моноширинным HUD-шрифтом
        self.setStyleSheet(styles.STATUS_BAR_STYLE)
        self.setFixedHeight(styles.STATUS_BAR_HEIGHT)

        # Тень, приподнимающая панель над остальным содержимым окна -
        # смещена немного вверх, чтобы подчеркнуть эффект "парения"
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(styles.STATUS_BAR_SHADOW_BLUR_RADIUS)
        shadow.setColor(QColor(*styles.STATUS_BAR_SHADOW_COLOR))
        shadow.setOffset(*styles.STATUS_BAR_SHADOW_OFFSET)
        self.setGraphicsEffect(shadow)

        # Светящаяся полоса по центру - позиционируется вдоль верхнего
        # края в resizeEvent (см. ниже), чтобы всегда покрывать всю
        # текущую ширину панели
        self._glow_line = _GlowLine(self)

        # Левая часть: выбранный насос
        self.selected_label = QLabel()
        self.selected_label.setMinimumWidth(150)
        self.selected_label.setStyleSheet(styles.STATUS_BAR_SELECTED_LABEL_STYLE)
        self.selected_label.setVisible(False)
        self.addWidget(self.selected_label)
        
        # Центр: фильтры (растягивается, может переноситься на 2 строки -
        # при выборе сразу многих фильтров текст не помещается в одну)
        self.filter_label = QLabel()
        self.filter_label.setAlignment(Qt.AlignCenter)
        self.filter_label.setWordWrap(True)
        self.addWidget(self.filter_label, stretch=1)
        
        # Правая часть: счётчик и дата обновления - друг под другом (2
        # строки), а не в одну длинную строку через весь низ окна
        self.count_label = QLabel()
        self.count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.update_label = QLabel()
        self.update_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        right_info_widget = QWidget()
        right_info_layout = QVBoxLayout(right_info_widget)
        # Отступ справа - на контейнере целиком (через margins layout, а
        # не QSS padding), иначе верхняя и нижняя строки заканчивались бы
        # не вровень
        right_info_layout.setContentsMargins(0, 0, styles.STATUS_BAR_RIGHT_MARGIN, 0)
        right_info_layout.setSpacing(0)
        right_info_layout.addWidget(self.count_label)
        right_info_layout.addWidget(self.update_label)
        self.addPermanentWidget(right_info_widget)
        
        self.set_status("Готово")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._glow_line.setGeometry(0, 0, self.width(), styles.STATUS_BAR_GLOW_HEIGHT)
        self._glow_line.raise_()
    
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