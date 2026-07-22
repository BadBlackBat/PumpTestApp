from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QDialogButtonBox, QMessageBox, 
    QListWidget, QListWidgetItem, QComboBox, QDateEdit,
    QTableWidget, QTableWidgetItem, QScrollArea, QWidget, QSizePolicy,
    QApplication, QGraphicsOpacityEffect, QFrame, QHeaderView
)
from PyQt5.QtCore import Qt, QDate, QPoint, QSize, QPropertyAnimation, QEasingCurve, QTimer
from PyQt5.QtGui import QFont, QColor, QFontMetrics
import json
import os

from .. import database as db
from .. import utils
from .. import styles
from .. import icon_utils
from .left_panel import _GlowFrame
from .status_bar import _GlowLine

ICONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resources', 'icons'
)

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


class _DialogCloseButton(QPushButton):
    """Крестик закрытия - своя кнопка вместо системной (т.к. у безрамочного
    окна нет системного заголовка). Серая по умолчанию, бирюзовая при
    наведении - тот же принцип, что и у иконок верхней панели (см.
    gui.py, _IconButton) - здесь не переиспользуем тот класс напрямую,
    чтобы не тянуть импорт из gui.py в dialogs.py (риск цикличного
    импорта: gui.py и так импортирует диалоги). При наведении иконка не
    только меняет цвет, но и увеличивается - кнопка сразу имеет
    фиксированный размер под БОЛЬШИЙ (hover) вариант, чтобы разрастание
    иконки не сдвигало соседние элементы заголовка."""
    def __init__(self, size=28, hover_size=36, parent=None):
        super().__init__(parent)
        close_path = os.path.join(ICONS_DIR, 'close.svg')
        self._normal_icon = icon_utils.tinted_icon(close_path, styles.TOP_BAR_ICON_COLOR_NORMAL, size)
        self._hover_icon = icon_utils.tinted_icon(close_path, "#ff5c5c", hover_size)
        self._size = size
        self._hover_size = hover_size
        self.setIcon(self._normal_icon)
        self.setIconSize(QSize(size, size))
        self.setFlat(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(hover_size + 6, hover_size + 6)
        self.setStyleSheet("QPushButton { border: none; background: transparent; }")

    def enterEvent(self, event):
        self.setIcon(self._hover_icon)
        self.setIconSize(QSize(self._hover_size, self._hover_size))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setIcon(self._normal_icon)
        self.setIconSize(QSize(self._size, self._size))
        super().leaveEvent(event)


class _GlowDialog(QDialog):
    """Базовое безрамочное окно в фирменном стиле - переиспользует ту же
    графитовую панель со свечением и тенью, что и остальные панели
    приложения (см. _GlowFrame в left_panel.py). Своя строка заголовка
    (т.к. системной рамки нет) с крестиком закрытия, перетаскивание окна
    мышью за заголовок. Наследники добавляют содержимое в self.body_layout,
    и в конце своего __init__ обязаны вызвать self._lock_size(), которая
    фиксирует размер окна (не растягивается, resize-рамки нет по
    определению у безрамочного окна)."""
    def __init__(self, parent=None, title=""):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self._drag_pos = None
        self._closing_started = False

        outer_layout = QVBoxLayout(self)
        # Отступ вокруг рамки - тени (QGraphicsDropShadowEffect у
        # _GlowFrame) нужно место, куда "растекаться" за пределы самой
        # панели. Без этого запаса тень обрезается ровно по границе окна,
        # и этот обрезанный край выглядит как слабый квадратный контур.
        outer_layout.setContentsMargins(18, 18, 18, 18)

        self.glow_frame = _GlowFrame()
        outer_layout.addWidget(self.glow_frame)

        frame_layout = QVBoxLayout(self.glow_frame)
        frame_layout.setContentsMargins(16, 8, 16, 16)
        frame_layout.setSpacing(0)
        self.frame_layout = frame_layout

        title_row = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            "color: #f2f4f6; font-weight: bold; font-size: 11pt; background: transparent;"
        )
        # Резервируем высоту строки заголовка под размер кнопки-крестика
        # (она позиционируется абсолютно, а не через layout заголовка) -
        # иначе для диалогов с коротким заголовком крестик мог "наезжать"
        # на первый ряд содержимого ниже
        self.title_label.setMinimumHeight(42)
        # Оставляем справа пустое место под будущий крестик (сам он не в
        # layout - см. ниже), чтобы длинный заголовок на него не наезжал
        title_row.addWidget(self.title_label)
        title_row.addStretch()
        frame_layout.addLayout(title_row)
        frame_layout.addSpacing(2)  # минимальный зазор - полоса ближе к заголовку

        # Светящаяся полоса-подчёркивание под заголовком - тот же приём,
        # что и в статус-баре/верхней панели (яркая по центру, гаснущая
        # к краям), просто переиспользуем тот же класс
        title_underline = _GlowLine()
        frame_layout.addWidget(title_underline)
        frame_layout.addSpacing(10)  # обычный зазор перед содержимым диалога

        self.body_layout = QVBoxLayout()
        self.body_layout.setSpacing(10)
        frame_layout.addLayout(self.body_layout)

        # Крестик закрытия - НЕ в layout, а поверх правого верхнего угла
        # абсолютным позиционированием (родитель - сама рамка glow_frame).
        # Так при наведении он может увеличиваться, не "раздвигая" соседние
        # элементы заголовка и не тратя зарезервированное под это место.
        self.close_btn = _DialogCloseButton(parent=self.glow_frame)
        self.close_btn.setAutoDefault(False)
        self.close_btn.setDefault(False)
        self.close_btn.clicked.connect(self.reject)

    def _lock_size(self, clamp_to_screen=False):
        """Фиксирует размер окна по текущему содержимому - вызывать в
        конце __init__ наследника, после того как весь контент добавлен.
        clamp_to_screen=True - для больших/динамических диалогов (много
        полей, таблицы) - сначала аккуратно уменьшает окно, если оно не
        помещается на маленьком экране."""
        self.adjustSize()
        if clamp_to_screen:
            _clamp_to_screen(self)
        size = self.size()
        # Небольшой запас по высоте (а не строго min == max) - жёсткая
        # фиксация "тютелька в тютельку" иногда конфликтует с тем, как
        # Windows округляет геометрию окна при масштабировании экрана
        # (DPI) - именно это давало предупреждение
        # "QWindowsWindow::setGeometry: Unable to set geometry..." в
        # консоли. Само окно от этого визуально не "плавает" - у
        # безрамочного окна всё равно нет видимого края, за который можно
        # было бы вручную потянуть и растянуть его.
        self.setMinimumSize(size)
        self.setMaximumSize(size.width(), size.height() + 20)
        self._position_close_button()

    def _position_close_button(self):
        """Ставит крестик в правый верхний угол рамки - вызывается после
        _lock_size(), когда размер окна уже точно известен и больше не
        поменяется."""
        margin = 8
        x = self.glow_frame.width() - self.close_btn.width() - margin
        y = margin
        self.close_btn.move(x, y)
        self.close_btn.raise_()

    # --- Плавное появление/закрытие (fade in/out через прозрачность
    # окна) - т.к. это модальные диалоги на exec_(), событийный цикл во
    # время анимации продолжает работать как обычно ---
    def showEvent(self, event):
        super().showEvent(event)
        self.setWindowOpacity(0.0)
        self._fade_in_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_in_anim.setDuration(180)
        self._fade_in_anim.setStartValue(0.0)
        self._fade_in_anim.setEndValue(1.0)
        self._fade_in_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_in_anim.start()

    def _fade_out_then(self, finish_callback):
        if self._closing_started:
            return
        self._closing_started = True

        self._closing_callback = finish_callback
        self._already_closed = False

        self._fade_out_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_out_anim.setDuration(140)
        self._fade_out_anim.setStartValue(self.windowOpacity())
        self._fade_out_anim.setEndValue(0.0)
        self._fade_out_anim.setEasingCurve(QEasingCurve.InCubic)
        self._fade_out_anim.finished.connect(self._run_closing_callback_once)
        self._fade_out_anim.start()

        # Подстраховка: если по какой-то причине сигнал finished от
        # анимации не придёт (редкий сбой аниматора) - всё равно закрываем
        # окно принудительно через 250мс. Без этой подстраховки диалог
        # мог остаться "подвешенным" модальным окном навсегда - вся
        # программа выглядела бы зависшей, и Windows реагировала бы
        # системным "гонгом" на любой клик по заблокированному окну.
        QTimer.singleShot(250, self._run_closing_callback_once)

    def _run_closing_callback_once(self):
        if self._already_closed:
            return
        self._already_closed = True
        self._closing_callback()

    def accept(self):
        self._fade_out_then(super().accept)

    def reject(self):
        self._fade_out_then(super().reject)

    def keyPressEvent(self, event):
        # ESC больше не закрывает окно мгновенно без предупреждения - это
        # рискованно для диалогов с уже введёнными данными (можно случайно
        # стереть всю заполненную форму одним нажатием). Закрыть окно
        # по-прежнему можно явно - крестиком или кнопкой "Отмена".
        if event.key() == Qt.Key_Escape:
            event.ignore()
            return
        super().keyPressEvent(event)

    # --- Перетаскивание окна мышью за заголовок (нет системной рамки) ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.y() < 58:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)


class GlowMessageDialog(_GlowDialog):
    """Информационное/предупреждающее окно в фирменном стиле - иконка
    слева, текст справа, одна кнопка OK. Используется вместо обычного
    QMessageBox.warning() там, где нужен единый стиль (например,
    сообщение о неверном пароле)."""
    def __init__(self, parent=None, title="Ошибка", message="", icon_name="warning.svg"):
        super().__init__(parent, title=title)

        content_row = QHBoxLayout()
        content_row.setSpacing(12)
        icon_label = QLabel()
        icon_path = os.path.join(ICONS_DIR, icon_name)
        if os.path.exists(icon_path):
            icon_label.setPixmap(icon_utils.plain_pixmap(icon_path, 40))
        icon_label.setStyleSheet("background: transparent;")
        content_row.addWidget(icon_label)

        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("color: #e8eaed; background: transparent;")
        content_row.addWidget(msg_label, 1)
        self.body_layout.addLayout(content_row)

        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("chromeButton")
        ok_btn.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
        ok_btn.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(ok_btn)
        btn_row.addStretch()
        self.body_layout.addLayout(btn_row)

        self.setMinimumWidth(340)
        self._lock_size()

    @staticmethod
    def show_error(parent, title, message):
        """Удобный короткий вызов - GlowMessageDialog.show_error(self, "Ошибка", "текст")
        вместо QMessageBox.warning(...)."""
        dlg = GlowMessageDialog(parent, title=title, message=message, icon_name="warning.svg")
        dlg.exec_()

    @staticmethod
    def show_success(parent, title, message):
        """То же самое, но с зелёной иконкой-галочкой - вместо
        QMessageBox.information(...)."""
        dlg = GlowMessageDialog(parent, title=title, message=message, icon_name="success.svg")
        dlg.exec_()


class PrintChoiceDialog(_GlowDialog):
    """Диалог выбора того, что печатать - иконка принтера сверху, варианты
    печати кнопками в один ряд (вместо прежнего QMessageBox с кнопками)."""
    def __init__(self, parent=None):
        super().__init__(parent, title="Печать")
        self.choice = None

        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        icon_label = QLabel()
        icon_path = os.path.join(ICONS_DIR, 'print.svg')
        if os.path.exists(icon_path):
            icon_label.setPixmap(icon_utils.tinted_pixmap(icon_path, styles.TOP_BAR_ICON_COLOR_NORMAL, 40))
        icon_label.setStyleSheet("background: transparent;")
        top_row.addWidget(icon_label)
        msg_label = QLabel("Что напечатать?")
        msg_label.setStyleSheet("color: #e8eaed; font-size: 11pt; background: transparent;")
        top_row.addWidget(msg_label, 1)
        self.body_layout.addLayout(top_row)

        def make_btn(text, value):
            btn = QPushButton(text)
            btn.setObjectName("chromeButton")
            btn.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
            btn.clicked.connect(lambda: self._choose(value))
            return btn

        btn_col = QVBoxLayout()
        btn_col.setSpacing(8)
        btn_col.addWidget(make_btn("Текущий протокол", "protocol"))
        btn_col.addWidget(make_btn("Список насосов (сокращённый)", "list_compact"))
        btn_col.addWidget(make_btn("Список насосов (расширенный)", "list_expanded"))
        btn_col.addSpacing(14)
        btn_col.addWidget(make_btn("Ничего", "cancel"))
        self.body_layout.addLayout(btn_col)

        self.setMinimumWidth(320)
        self._lock_size()

    def _choose(self, value):
        self.choice = value
        if value == "cancel":
            self.reject()
        else:
            self.accept()


class PasswordDialog(_GlowDialog):
    def __init__(self, parent=None, message="Для удаления записи введите пароль:", correct_password="admin"):
        super().__init__(parent, title="Введите пароль")
        self._correct_password = correct_password

        msg_label = QLabel(message)
        msg_label.setStyleSheet("color: #e8eaed; background: transparent;")
        msg_label.setWordWrap(True)
        self.body_layout.addWidget(msg_label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self.try_accept)
        self.body_layout.addWidget(self.password_input)

        # Строка ошибки - место под неё зарезервировано СРАЗУ (текст
        # пустой, но высота уже заложена в _lock_size() ниже), иначе на
        # фиксированном по размеру окне появление текста после первой
        # неудачной попытки было бы некуда вставить
        self.error_label = QLabel("")
        self.error_label.setStyleSheet(
            "color: #ff8080; background: transparent; font-size: 9pt;"
        )
        self.error_label.setWordWrap(True)
        self.error_label.setMinimumHeight(18)
        self.body_layout.addWidget(self.error_label)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("chromeButton")
        ok_btn.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
        ok_btn.setAutoDefault(False)
        ok_btn.setDefault(False)
        ok_btn.clicked.connect(self.try_accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("chromeButton")
        cancel_btn.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        self.body_layout.addLayout(btn_layout)

        self.password = ""
        self.setMinimumWidth(320)
        self._lock_size()

    def try_accept(self):
        """Проверяет пароль ПЕРЕД закрытием окна - и по Enter, и по кнопке
        OK. Если пароль неверный - окно НЕ закрывается, показывает ошибку
        внутри и даёт попробовать ещё раз (вместо того чтобы закрыться
        независимо от результата, а сообщить об ошибке уже после)."""
        entered = self.password_input.text()
        if entered != self._correct_password:
            self.error_label.setText("Неверный пароль. Попробуйте ещё раз.")
            self.password_input.clear()
            self.password_input.setFocus()
            return
        self.password = entered
        self.accept()

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

        if self.password_input.text() != "admin":
            QMessageBox.warning(self, "Ошибка", "Неверный пароль.")
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


class SettingsDialog(_GlowDialog):
    """Меню настроек: управление модификациями насосов."""
    def __init__(self, parent=None):
        super().__init__(parent, title="Настройки")
        # Боковые отступы шире, чем у остальных диалогов - только здесь
        left, top, right, bottom = self.frame_layout.getContentsMargins()
        self.frame_layout.setContentsMargins(left + 10, top, right + 10, bottom)

        label = QLabel("Модификации насосов ГУР:")
        label.setStyleSheet("color: #e8eaed; background: transparent; font-size: 10.5pt;")
        self.body_layout.addWidget(label)

        # Крупнее шрифт и отступы кнопок, чем стандартный chromeButton -
        # добавляем сверху ту же шапку стиля, но с более крупными числами
        big_button_style = styles.LEFT_PANEL_RESET_BTN_STYLE + """
            QPushButton#chromeButton {
                font-size: 10.5pt;
                padding: 9px 16px;
            }
        """

        def make_btn(text, slot):
            btn = QPushButton(text)
            btn.setObjectName("chromeButton")
            btn.setStyleSheet(big_button_style)
            btn.clicked.connect(slot)
            return btn

        # Блок 1: управление модификациями
        self.body_layout.addWidget(make_btn("Добавить модификацию", self.open_add_modification))
        self.body_layout.addWidget(make_btn("Просмотреть модификации", self.open_view_modifications))

        # Явный разделительный отступ - зрительно отделяет управление
        # модификациями от служебных действий (инструкция/закрытие)
        self.body_layout.addSpacing(22)

        # Блок 2: служебные действия
        self.body_layout.addWidget(make_btn("Инструкция", self.open_instructions))
        self.body_layout.addWidget(make_btn("Закрыть", self.accept))

        self.setMinimumWidth(340)
        self._lock_size()
        self._add_watermark(os.path.join(ICONS_DIR, 'settings_2.svg'))

    def _add_watermark(self, svg_path):
        """Лёгкий силуэт иконки настроек (шестерёнка) на весь фон окна,
        ПОД кнопками - чисто декоративный элемент, мышь через него
        "проваливается" к тому, что под ним."""
        if not os.path.exists(svg_path):
            return
        size = int(min(self.glow_frame.width(), self.glow_frame.height()) * 0.8)
        pixmap = icon_utils.tinted_pixmap(svg_path, "#ffffff", size)
        watermark = QLabel(self.glow_frame)
        watermark.setPixmap(pixmap)
        watermark.setAttribute(Qt.WA_TransparentForMouseEvents)
        watermark.setStyleSheet("background: transparent;")
        opacity_effect = QGraphicsOpacityEffect(watermark)
        opacity_effect.setOpacity(0.06)
        watermark.setGraphicsEffect(opacity_effect)
        watermark.resize(pixmap.size())
        watermark.move(
            (self.glow_frame.width() - pixmap.width()) // 2,
            (self.glow_frame.height() - pixmap.height()) // 2
        )
        watermark.lower()
        watermark.show()

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
        # Пароль уже проверен внутри диалога (try_accept) - если дошли
        # сюда, значит он верный
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


class AddPumpDialog(_GlowDialog):
    """Диалог ручного добавления протокола проверки насоса."""

    # Варианты для полей проверки на герметичность (п.6/7 требований)
    _LEAK_OPTIONS = ["Отсутствуют", "Каплепадение", "Подтекание", "Иное"]
    _OIL_OPTIONS = [
        "Отсутствуют", "Присутствуют в допускаемой степени",
        "Присутствуют в чрезмерном объёме", "Иное"
    ]

    def __init__(self, parent=None):
        super().__init__(parent, title="Добавление насоса вручную")
        self.selected_mod = None
        self.value_tables = {}
        self.seal_inputs = {}

        self.mods = db.get_all_modifications()  # список (id, name)

        # Заголовок в 2 строки, по несколько полей в каждой (п.1):
        # 1я строка - № насоса + Модификация; 2я - № заказа + Дата + Тип.
        # Подпись - по размеру своего текста (без фиксированной ширины -
        # иначе между текстом и полем остаётся пустое место). Ширину полей
        # считаем точно через QFontMetrics (не на глаз), чтобы:
        # - № насоса и Модификация были одной ширины между собой;
        # - № заказа/Дата/Тип были одной ширины между собой;
        # - ОБЩАЯ длина строки 1 совпадала с общей длиной строки 2.
        SPACING = 8
        CHIP_PAD = 8 * 2 + 4  # внутренние отступы чипа (см. compact_field)
        arrow_path = os.path.join(ICONS_DIR, 'dropdown_arrow.svg').replace('\\', '/')
        INPUT_STYLE = (
            "QLineEdit, QComboBox, QDateEdit { "
            "background-color: #f0f0f0; color: #1c1e21; "
            "border: 1px solid #6b6f75; border-radius: 4px; padding: 1px 6px; }"
            "QLineEdit:hover, QComboBox:hover, QDateEdit:hover, "
            "QLineEdit:focus, QComboBox:focus, QDateEdit:focus { "
            "border: 1px solid #4fd1ff; }"
            "QComboBox::drop-down, QDateEdit::drop-down { border: none; }"
            f"QComboBox::down-arrow, QDateEdit::down-arrow {{ "
            f"image: url({arrow_path}); width: 10px; height: 10px; }}"
        )

        def compact_field(label_text, widget, field_width):
            chip = QFrame()
            chip.setStyleSheet(styles.LEFT_PANEL_CHIP_STYLE)
            box = QHBoxLayout(chip)
            box.setContentsMargins(8, 3, 8, 3)
            box.setSpacing(4)
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #e8eaed; background: transparent;")
            widget.setFixedWidth(field_width)
            widget.setStyleSheet(INPUT_STYLE)
            box.addWidget(lbl)
            box.addWidget(widget)
            return chip

        # Строим чипы строки 2 (№ заказа/Дата/Тип) первыми и измеряем их
        # РЕАЛЬНУЮ ширину через sizeHint() - это надёжнее приближённого
        # расчёта на бумаге, т.к. Qt сам точно знает, сколько места нужно
        # с учётом всех внутренних отступов рамки/чипа/шрифта. Дальше
        # считаем ширину поля строки 1 так, чтобы "Модификация" заканчивалась
        # ровно там же, где заканчивается "Тип проверки" (п.4 требований).
        FIELD_W_ROW2 = 90  # № заказа/Дата/Тип - одной ширины между собой

        self.order_input = QLineEdit()
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.calendarWidget().setStyleSheet(styles.LEFT_PANEL_CALENDAR_STYLE)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["первичная", "повторная"])

        chip_order = compact_field("№ заказа:", self.order_input, FIELD_W_ROW2)
        chip_date = compact_field("Дата проверки:", self.date_input, FIELD_W_ROW2)
        chip_type = compact_field("Тип проверки:", self.type_combo, FIELD_W_ROW2)

        row2_total = (
            chip_order.sizeHint().width() + chip_date.sizeHint().width()
            + chip_type.sizeHint().width() + 2 * SPACING
        )

        self.pump_number_input = QLineEdit()
        self.mod_combo = QComboBox()
        for mod_id, name in self.mods:
            self.mod_combo.addItem(name, mod_id)
        self.mod_combo.currentIndexChanged.connect(self.on_modification_changed)

        # Пробная ширина для строки 1 - чип "№ насоса" измеряем при этой
        # ширине, а недостающую разницу до row2_total целиком отдаём чипу
        # "Модификация" - так его правый край гарантированно совпадёт с
        # правым краем "Тип проверки".
        #
        # ВАЖНО: накладные расходы самого чипа (рамка, внутренние отступы,
        # плюс то, что QComboBox может занимать чуть больше места, чем
        # QLineEdit при той же setFixedWidth) - измеряем НАПРЯМУЮ на
        # пробной сборке, а не предполагаем константой (CHIP_PAD) - иначе
        # накапливается небольшая, но заметная погрешность.
        trial_w = 150
        chip_pump = compact_field("№ насоса:", self.pump_number_input, trial_w)
        remaining_for_mod = row2_total - chip_pump.sizeHint().width() - SPACING

        chip_mod = compact_field("Модификация насоса:", self.mod_combo, trial_w)
        mod_overhead = chip_mod.sizeHint().width() - trial_w
        mod_field_w = max(80, remaining_for_mod - mod_overhead)
        self.mod_combo.setFixedWidth(mod_field_w)

        row1 = QHBoxLayout()
        row1.addWidget(chip_pump)
        row1.addSpacing(SPACING)
        row1.addWidget(chip_mod)
        row1.addStretch(1)
        self.body_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(chip_order)
        row2.addSpacing(SPACING)
        row2.addWidget(chip_date)
        row2.addSpacing(SPACING)
        row2.addWidget(chip_type)
        row2.addStretch(1)
        self.body_layout.addLayout(row2)

        # Динамическая область: испытания 1-4 друг под другом (одна
        # колонка, п.1 требований), с заметным отступом между ними
        # (п.5), затем отдельно - проверка на герметичность
        self.values_widget = QWidget()
        self.values_main_layout = QVBoxLayout(self.values_widget)
        self.values_main_layout.setContentsMargins(0, 0, 0, 0)
        self.tests_column = QVBoxLayout()   # испытания 1, 2, 3, 4 - друг под другом
        self.tests_column.setSpacing(22)
        self.extra_column = QVBoxLayout()   # проверка на герметичность
        self.extra_column.setSpacing(4)
        self.values_main_layout.addLayout(self.tests_column)
        self.values_main_layout.addSpacing(18)
        self.values_main_layout.addLayout(self.extra_column)
        self.body_layout.addWidget(self.values_widget)

        note_row = QHBoxLayout()
        self.note_label = QLabel("Примечание:")
        self.note_label.setStyleSheet("color: #e8eaed; background: transparent;")
        note_row.addWidget(self.note_label)
        self.note_input = QLineEdit()
        self.note_input.setStyleSheet(
            "QLineEdit { border: 1px solid #6b6f75; border-radius: 6px; "
            "background-color: #f0f0f0; color: #1c1e21; padding: 2px 6px; }"
            "QLineEdit:hover, QLineEdit:focus { border: 1px solid #4fd1ff; }"
        )
        note_row.addWidget(self.note_input)
        note_row.addStretch(1)
        self.body_layout.addLayout(note_row)

        # Отступ перед паролем, чтобы он визуально не сливался с примечанием
        self.body_layout.addSpacing(16)

        # Поле пароля здесь не нужно - пароль уже запрашивается и
        # проверяется ДО открытия этого диалога (см. gui.py,
        # on_add_requested), повторный ввод был бы избыточен (п.5)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Сохранить")
        ok_btn.setObjectName("chromeButton")
        ok_btn.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
        ok_btn.setAutoDefault(False)
        ok_btn.setDefault(False)
        ok_btn.clicked.connect(self.try_accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("chromeButton")
        cancel_btn.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        self.body_layout.addLayout(btn_layout)

        if self.mods:
            self.on_modification_changed(0)
        else:
            GlowMessageDialog.show_error(
                self, "Нет модификаций",
                "В базе нет ни одной модификации. Сначала добавьте модификацию через Настройки → Добавить модификацию."
            )

        # Диалог большой и динамический (таблицы испытаний) - сжимаем под
        # экран, если не помещается, и только потом фиксируем размер
        self._lock_size(clamp_to_screen=True)

    def on_modification_changed(self, index):
        # Очищаем предыдущее содержимое
        self._clear_sub_layout(self.tests_column)
        self._clear_sub_layout(self.extra_column)
        self.value_tables = {}
        self.seal_inputs = {}

        mod_id = self.mod_combo.currentData()
        if mod_id is None:
            return
        self.selected_mod = db.get_modification_by_id(mod_id)
        if not self.selected_mod:
            return

        _, self.value_tables['test1'] = self._build_value_table(
            "Испытание 1:\nЗависимость объемной подачи от оборотов привода насоса ГУР\n"
            "клапан ECO выключен, I = 0 A",
            self.selected_mod['norm_graph1_x'], "Обороты, об/мин"
        )
        _, self.value_tables['test2'] = self._build_value_table(
            "Испытание 2:\nЗависимость объемной подачи от оборотов привода насоса ГУР\n"
            "клапан ECO включен, I = 1 A",
            self.selected_mod['norm_graph2_x'], "Обороты, об/мин"
        )
        _, self.value_tables['test3'] = self._build_value_table(
            "Испытание 3:\nЗависимость объемной подачи от управляющего сигнала на клапане ECO\n"
            "клапан ECO выключен, I = 0 A",
            self.selected_mod['norm_graph3_x'], "Сила тока, А"
        )

        # У теста 3 обычно больше контрольных точек (столбцов), чем у
        # тестов 1/2 - из-за этого его таблица получается шире их. Сжимаем
        # столбцы теста 3 пропорционально, чтобы общая ширина совпадала с
        # тестами 1/2 (п.2) - это заодно уменьшает и минимальную ширину
        # всего окна (п.4), т.к. она считается по самой широкой таблице.
        self._match_table_width(
            self.value_tables['test3'],
            self.value_tables['test1'].width(),
            self.value_tables['test1'].verticalHeader().width()
        )

        # Испытание 4 (давление) - "Испытание 4:" отдельной строкой сверху,
        # название испытания вместе с полем ввода - строкой ниже
        table_width = self.value_tables['test1'].width()

        pressure_col = QVBoxLayout()
        pressure_col.setSpacing(2)
        test4_prefix = QLabel("Испытание 4:")
        test4_prefix.setStyleSheet("color: #e8eaed; font-weight: bold; background: transparent;")
        pressure_col.addWidget(test4_prefix)

        line2_text = "Определение максимального давления срабатывания"
        line2_label = QLabel(line2_text)
        line2_label.setWordWrap(False)
        line2_label.setStyleSheet("color: #e8eaed; font-weight: bold; background: transparent;")
        pressure_col.addWidget(line2_label)

        line3_text = "предохранительного клапана:"
        line3_label = QLabel(line3_text)
        line3_label.setWordWrap(False)
        line3_label.setStyleSheet("color: #e8eaed; font-weight: bold; background: transparent;")

        # Поле ввода считаем так, чтобы 3я строка (подпись + поле)
        # заканчивалась ровно там же, где заканчивается 2я строка.
        # Меряем через sizeHint() самих QLabel (а не сырые метрики шрифта) -
        # это учитывает собственные внутренние отступы QLabel и точнее
        # совпадает с тем, что реально отрисовывается на экране.
        line2_w = line2_label.sizeHint().width()
        line3_label_w = line3_label.sizeHint().width()
        PRESSURE_SPACING = 8
        input_w = max(60, line2_w - line3_label_w - PRESSURE_SPACING)

        self.pressure_input = QLineEdit()
        self.pressure_input.setFixedWidth(input_w)
        self.pressure_input.setStyleSheet(
            "QLineEdit { border: 1px solid #6b6f75; border-radius: 6px; "
            "background-color: #f0f0f0; color: #1c1e21; padding: 2px 6px; }"
            "QLineEdit:hover, QLineEdit:focus { border: 1px solid #4fd1ff; }"
        )
        pressure_row = QHBoxLayout()
        pressure_row.setSpacing(PRESSURE_SPACING)
        pressure_row.addWidget(line3_label)
        pressure_row.addWidget(self.pressure_input)
        pressure_row.addStretch()
        pressure_col.addLayout(pressure_row)
        self.tests_column.addLayout(pressure_col)

        # Примечание - по ширине точно как таблицы испытаний (п.2 и п.3),
        # а не растянуто на всё окно
        note_label_width = QFontMetrics(self.note_label.font()).horizontalAdvance("Примечание:") + 4
        self.note_input.setFixedWidth(max(80, table_width - note_label_width - 6))

        # Проверка на герметичность - подзаголовок (в одну строку, без
        # переноса, п.4) и 5 пунктов, каждый со своим выпадающим списком.
        # Подписи - без переноса, одной (максимальной среди всех пяти)
        # ширины - выравнивает и сами выпадающие списки в одну колонку.
        seal_label = QLabel("Проверка на герметичность:")
        seal_label.setWordWrap(False)
        seal_label.setStyleSheet("color: #e8eaed; font-weight: bold; background: transparent;")
        self.extra_column.addWidget(seal_label)

        seal_fm = QFontMetrics(QLabel().font())
        seal_label_w = max(
            seal_fm.horizontalAdvance(utils.SEAL_LABELS[k] + ":") for k in utils.SEAL_KEYS
        ) + 6

        for key in utils.SEAL_KEYS:
            row = QHBoxLayout()
            row.setSpacing(6)
            lbl = QLabel(utils.SEAL_LABELS[key] + ":")
            lbl.setWordWrap(False)
            lbl.setFixedWidth(seal_label_w)
            lbl.setStyleSheet("color: #e8eaed; background: transparent;")
            row.addWidget(lbl)
            combo = self._make_seal_combo(key, self.selected_mod['seal_rules'].get(key, ''))
            row.addWidget(combo)
            row.addStretch(1)
            self.seal_inputs[key] = combo
            self.extra_column.addLayout(row)

    def _make_seal_combo(self, key, stored_value):
        """Выпадающий список для одного пункта проверки на герметичность -
        свой набор вариантов и значение по умолчанию для "масляных
        образований на уплотнении" (g37) и для остальных четырёх пунктов.
        Ширина - по самой длинной записи среди ВСЕХ вариантов (+ запас
        под стрелку раскрытия), а не на всю ширину строки (п.4)."""
        if key == 'g37':
            options, default_index = self._OIL_OPTIONS, 1
        else:
            options, default_index = self._LEAK_OPTIONS, 0
        combo = QComboBox()
        combo.addItems(options)
        idx = combo.findText(stored_value, Qt.MatchFixedString)
        combo.setCurrentIndex(idx if idx >= 0 else default_index)

        # Явно задаём непрозрачный фон и самому списку, и его выпадающей
        # части - без этого выпадающий список мог наследовать прозрачность
        # (WA_TranslucentBackground) безрамочного родительского окна, из-за
        # чего при открытии возникало визуальное "задвоение" значения
        arrow_path = os.path.join(ICONS_DIR, 'dropdown_arrow.svg').replace('\\', '/')
        combo.setStyleSheet(f"""
            QComboBox {{
                background-color: #f0f0f0;
                color: #1c1e21;
                border: 1px solid #6b6f75;
                border-radius: 4px;
                padding: 2px 6px;
            }}
            QComboBox:hover, QComboBox:focus {{
                border: 1px solid #4fd1ff;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: url({arrow_path});
                width: 10px;
                height: 10px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #f0f0f0;
                color: #1c1e21;
                selection-background-color: #4fd1ff;
                selection-color: #1c1e21;
                outline: none;
            }}
        """)

        longest = max(self._OIL_OPTIONS + self._LEAK_OPTIONS, key=len)
        text_width = QFontMetrics(combo.font()).horizontalAdvance(longest)
        combo.setFixedWidth(text_width + 45)
        return combo

    def _clear_sub_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_sub_layout(child.layout())

    def _match_table_width(self, table, target_width, target_header_width=None):
        """Пропорционально меняет ширину столбцов таблицы (растягивает
        ИЛИ сжимает - в любую сторону), чтобы её общая ширина точно
        совпала с target_width - используется для теста 3, у которого
        обычно другое количество контрольных точек (столбцов), чем у
        тестов 1/2, из-за чего его таблица иначе была бы то шире, то
        уже их. Запас (+2) должен совпадать с тем, что использует
        _build_value_table - иначе даже "подогнанная" ширина будет чуть
        отличаться от цели.

        target_header_width - если передан, ширина строкового заголовка
        (левого столбца с подписями "Обороты, об/мин"/"Сила тока, А" и
        т.п.) тоже принудительно выравнивается под эталонную таблицу -
        у теста 3 подпись обычно короче ("Сила тока, А"), из-за чего
        заголовок сам по себе уже ýже, и без этого выравнивания общая
        ширина всё равно немного не совпадала бы."""
        if target_header_width is not None:
            table.verticalHeader().setFixedWidth(target_header_width)
        header_w = table.verticalHeader().width()
        col_count = table.columnCount()
        if col_count == 0:
            return
        current_cols_width = sum(table.columnWidth(c) for c in range(col_count))
        if current_cols_width == 0:
            return
        available = max(30 * col_count, target_width - header_w - 2)
        scale = available / current_cols_width
        for c in range(col_count):
            table.setColumnWidth(c, max(30, int(table.columnWidth(c) * scale)))
        new_total = header_w + 2 + sum(table.columnWidth(c) for c in range(col_count))
        table.setFixedWidth(new_total)

    def _build_value_table(self, title, x_values, x_label):
        """Таблица испытания - заголовок сверху, затем ряд контрольных
        точек по горизонтали (X - только для чтения) и под ним ряд полей
        ввода измеренного значения (п.3 требований)."""
        container = QWidget()
        col = QVBoxLayout(container)
        col.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #e8eaed; font-weight: bold; background: transparent;")
        title_label.setWordWrap(True)
        col.addWidget(title_label)

        table = QTableWidget()
        table.setRowCount(2)
        table.setColumnCount(len(x_values))
        table.setVerticalHeaderLabels([x_label, "Расход, л/мин"])
        table.horizontalHeader().setVisible(False)
        table.setStyleSheet("""
            QTableWidget {
                gridline-color: #b0b4b9;
                border: 1px solid #6b6f75;
                border-radius: 4px;
                background-color: #f0f0f0;
            }
            QTableWidget::item {
                padding: 1px;
            }
            QTableWidget::item:hover {
                background-color: #d6f3ff;
            }
            QTableWidget::item:selected {
                background-color: #bdeeff;
                color: #1c1e21;
            }
            QHeaderView::section {
                background-color: #3a3d42;
                color: #e8eaed;
                border: 1px solid #6b6f75;
                padding: 2px 6px;
            }
        """)

        cell_text_color = QColor("#1c1e21")  # тёмный текст - на светлом фоне ячеек читается всегда
        for i, x in enumerate(x_values):
            x_item = QTableWidgetItem(str(x))
            x_item.setFlags(Qt.ItemIsEnabled)
            x_item.setTextAlignment(Qt.AlignCenter)
            x_item.setForeground(cell_text_color)
            table.setItem(0, i, x_item)
            res_item = QTableWidgetItem("")
            res_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)
            res_item.setTextAlignment(Qt.AlignCenter)
            res_item.setForeground(cell_text_color)
            table.setItem(1, i, res_item)
        table.setEditTriggers(QTableWidget.AllEditTriggers)

        # Подгоняем высоту и ширину точно под содержимое - без внутренней
        # прокрутки. Запас (+16px на столбец) - чтобы крайние значения не
        # обрезались: resizeColumnsToContents() иногда немного занижает
        # нужную ширину, особенно у самих крайних столбцов таблицы.
        small_font = QFont()
        small_font.setPointSize(9)
        table.setFont(small_font)
        table.verticalHeader().setFont(small_font)
        table.resizeRowsToContents()
        table.resizeColumnsToContents()
        min_section = 55
        for c in range(table.columnCount()):
            table.setColumnWidth(c, max(min_section, table.columnWidth(c) + 4))
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        total_height = 2
        for row in range(table.rowCount()):
            total_height += table.rowHeight(row)
        table.setFixedHeight(total_height)
        total_width = table.verticalHeader().width() + 2
        for c in range(table.columnCount()):
            total_width += table.columnWidth(c)
        table.setFixedWidth(total_width)

        # Блокируем изменение ширины/высоты столбцов и строк пользователем -
        # ВАЖНО: только теперь, ПОСЛЕ авто-подгонки размеров выше. Если
        # включить Fixed раньше, resizeRowsToContents()/resizeColumnsToContents()
        # частично перестают работать (секции уже "заморожены"), из-за чего
        # строка ввода могла становиться почти нулевой высоты - клик по ней
        # ни к чему не приводил (п.2 бага).
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        col.addWidget(table)
        container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.tests_column.addWidget(container)
        return container, table

    def try_accept(self):
        if not self.mods or not self.selected_mod:
            GlowMessageDialog.show_error(self, "Ошибка", "Сначала добавьте модификацию через Настройки.")
            return

        if not self.pump_number_input.text().strip():
            GlowMessageDialog.show_error(self, "Ошибка", "Введите идентификационный номер насоса.")
            return

        for key, table in self.value_tables.items():
            for col in range(table.columnCount()):
                item = table.item(1, col)
                text = item.text().strip() if item else ""
                if not text:
                    GlowMessageDialog.show_error(self, "Ошибка", "Заполните все значения результатов испытаний.")
                    return
                try:
                    float(text)
                except ValueError:
                    GlowMessageDialog.show_error(self, "Ошибка", f"Некорректное числовое значение: '{text}'.")
                    return

        pressure_text = self.pressure_input.text().strip()
        if not pressure_text:
            GlowMessageDialog.show_error(self, "Ошибка", "Введите значение давления.")
            return
        try:
            float(pressure_text)
        except ValueError:
            GlowMessageDialog.show_error(self, "Ошибка", "Некорректное значение давления.")
            return

        self.accept()

    def get_data(self):
        results = {}

        def fill(table, start_key):
            for col in range(table.columnCount()):
                key = f'g{start_key + col}'
                text = table.item(1, col).text().strip()
                try:
                    results[key] = float(text)
                except ValueError:
                    results[key] = None

        fill(self.value_tables['test1'], 5)
        fill(self.value_tables['test2'], 13)
        fill(self.value_tables['test3'], 21)
        results['g32'] = float(self.pressure_input.text().strip())

        seal_results = {key: combo.currentText() for key, combo in self.seal_inputs.items()}

        return {
            'modification_id': self.selected_mod['id'],
            'modification_name': self.selected_mod['name'],
            'pump_number': self.pump_number_input.text().strip(),
            'test_date': self.date_input.date().toString('yyyy-MM-dd'),
            'test_type': self.type_combo.currentText(),
            'order_number': utils.normalize_order_number(self.order_input.text().strip()) or None,
            'results': results,
            'seal_results': seal_results,
            'note': self.note_input.text().strip(),
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

        if self.password_input.text() != "admin":
            QMessageBox.warning(self, "Ошибка", "Неверный пароль.")
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
            'order_number': utils.normalize_order_number(self.order_input.text().strip()) or None,
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
            f"Дата: {utils.format_date_display(pump_data.get('test_date'))}\n"
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
        button_box.accepted.connect(self.try_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def try_accept(self):
        if self.password_input.text() != "admin":
            QMessageBox.warning(self, "Ошибка", "Неверный пароль.")
            return
        self.accept()

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