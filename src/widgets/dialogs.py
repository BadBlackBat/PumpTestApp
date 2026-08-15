from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QTextBrowser, QDialogButtonBox, QMessageBox, 
    QListWidget, QListWidgetItem, QComboBox, QDateEdit,
    QTableWidget, QTableWidgetItem, QScrollArea, QWidget, QSizePolicy,
    QApplication, QGraphicsOpacityEffect, QFrame, QHeaderView, QGridLayout,
    QGraphicsBlurEffect, QGraphicsColorizeEffect, QGraphicsScene, QGraphicsPixmapItem,
    QCheckBox, QProgressBar, QRadioButton, QButtonGroup, QFileDialog, QAction
)
from PyQt5.QtCore import Qt, QDate, QPoint, QSize, QPropertyAnimation, QEasingCurve, QTimer, QRectF, pyqtProperty, QSettings, QUrl, QUrlQuery
from PyQt5.QtGui import QFont, QColor, QFontMetrics, QPainter, QPixmap, QIcon, QPen, QDesktopServices
import json
import os

from .. import database as db
from .. import app_paths
from .. import utils
from .. import styles
from .. import icon_utils
from .. import db_settings
from .. import db_lock
from .. import auth
from .. import version
from .. import db_sync
from .left_panel import _GlowFrame, _GlowScrollBar
from .status_bar import _GlowLine
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.ticker import MultipleLocator

ICONS_DIR = os.path.join(app_paths.get_resources_dir(), 'icons')

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
    def __init__(self, size=24, hover_size=32, parent=None):
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


class _BlurOverlay(QWidget):
    """Полупрозрачный размытый "снимок" виджета - показывается поверх
    него, пока открыт диалог, создавая эффект размытия/обесцвечивания
    фона. Работает на статичном снимке (grab()), а не на живом виджете
    через QGraphicsEffect - последнее не всегда одинаково затрагивает
    вложенные элементы со сложной отрисовкой (заголовки таблиц,
    графики matplotlib) - снимок гарантированно захватывает вообще всё.
    Появляется и исчезает плавной анимацией прозрачности, а не мгновенно."""
    def __init__(self, target_widget, blur_radius=8, desaturate=False):
        parent_widget = target_widget.parentWidget()
        if parent_widget is not None:
            # Обычный случай - у цели есть родитель (например,
            # content_widget внутри central, или glow_frame внутри
            # диалога) - оверлей становится "соседом" в том же родителе,
            # с той же геометрией
            super().__init__(parent_widget)
            self.setGeometry(target_widget.geometry())
        else:
            # У цели нет родителя - она сама окно верхнего уровня
            # (например, всё главное окно целиком) - оверлей становится
            # её СОБСТВЕННЫМ дочерним виджетом, во всю её площадь
            super().__init__(target_widget)
            self.setGeometry(0, 0, target_widget.width(), target_widget.height())
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._opacity_value = 0.0
        self._pixmap = self._build_snapshot(target_widget, blur_radius, desaturate)
        self.raise_()
        self.show()
        self._anim = QPropertyAnimation(self, b"overlayOpacity", self)

    @staticmethod
    def _apply_scene_effect(pixmap, effect):
        scene = QGraphicsScene()
        item = QGraphicsPixmapItem(pixmap)
        item.setGraphicsEffect(effect)
        scene.addItem(item)
        result = QPixmap(pixmap.size())
        result.fill(Qt.transparent)
        painter = QPainter(result)
        scene.render(painter, QRectF(result.rect()), QRectF(pixmap.rect()))
        painter.end()
        return result

    def _build_snapshot(self, target_widget, blur_radius, desaturate):
        pixmap = target_widget.grab()
        blur_effect = QGraphicsBlurEffect()
        blur_effect.setBlurRadius(blur_radius)
        pixmap = self._apply_scene_effect(pixmap, blur_effect)
        if desaturate:
            colorize_effect = QGraphicsColorizeEffect()
            colorize_effect.setColor(QColor(130, 130, 130))
            colorize_effect.setStrength(0.5)
            pixmap = self._apply_scene_effect(pixmap, colorize_effect)
        return pixmap

    def getOverlayOpacity(self):
        return self._opacity_value

    def setOverlayOpacity(self, value):
        self._opacity_value = value
        self.update()

    overlayOpacity = pyqtProperty(float, getOverlayOpacity, setOverlayOpacity)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setOpacity(self._opacity_value)
        painter.drawPixmap(0, 0, self._pixmap)

    def fade_in(self, duration=220):
        self._anim.stop()
        self._anim.setDuration(duration)
        self._anim.setStartValue(self._opacity_value)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

    def fade_out_and_remove(self, duration=220):
        self._anim.stop()
        self._anim.setDuration(duration)
        self._anim.setStartValue(self._opacity_value)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.InCubic)
        self._anim.finished.connect(self.deleteLater)
        self._anim.start()


class _DialogBackgroundManager:
    """Централизованно размывает/обесцвечивает то, что оказывается "не в
    фокусе", когда открывается один из наших диалогов (_GlowDialog) -
    либо главное окно программы (если это первый открытый диалог), либо
    предыдущий диалог (если этот диалог открылся поверх другого)."""
    _stack = []
    main_window = None
    _main_target = None
    _overlays = {}  # виджет -> текущий активный на нём _BlurOverlay
    BLUR_RADIUS = 8  # чуть слабее прежнего (было 14)
    enabled = True  # можно выключить в настройках - см. load_settings()

    @classmethod
    def load_settings(cls):
        """Загружает сохранённое состояние (вкл/выкл) - вызывать один раз
        при запуске программы, до создания главного окна."""
        settings = QSettings("PumpTestApp", "MainSettings")
        cls.enabled = settings.value("background_blur_enabled", True, type=bool)

    @classmethod
    def set_enabled(cls, value):
        cls.enabled = value
        settings = QSettings("PumpTestApp", "MainSettings")
        settings.setValue("background_blur_enabled", value)
        if not value:
            # Выключили прямо сейчас - убираем уже показанные размытия,
            # если они есть
            for widget in list(cls._overlays.keys()):
                cls._hide_overlay(widget)
        else:
            # Включили прямо сейчас - применяем немедленно к тому, что
            # сейчас находится "не в фокусе" (за текущим верхним диалогом
            # в стеке), а не только при следующем открытии диалога
            if len(cls._stack) >= 2:
                cls._show_overlay(cls._stack[-2].glow_frame, desaturate=False)
            elif cls._stack and cls.main_window is not None:
                cls._show_overlay(cls._main_target, desaturate=True)

    @classmethod
    def register_main_window(cls, window, target_widget):
        cls.main_window = window
        cls._main_target = target_widget

    @classmethod
    def on_dialog_opened(cls, dialog):
        if dialog in cls._stack:
            # Уже был в стеке (например, диалог настроек, который мы
            # просто скрывали, а не закрывали, и сейчас показываем снова
            # после закрытия следующего пункта меню) - ничего размывать
            # не нужно, иначе он "размыл бы сам себя"
            return
        if cls.enabled:
            if cls._stack:
                cls._show_overlay(cls._stack[-1].glow_frame, desaturate=False)
            elif cls.main_window is not None:
                cls._show_overlay(cls._main_target, desaturate=True)
        cls._stack.append(dialog)

    @classmethod
    def on_dialog_closed(cls, dialog):
        if dialog in cls._stack:
            cls._stack.remove(dialog)
        if not cls.enabled:
            return
        if cls._stack:
            cls._hide_overlay(cls._stack[-1].glow_frame)
        elif cls.main_window is not None:
            cls._hide_overlay(cls._main_target)

    @classmethod
    def _show_overlay(cls, widget, desaturate):
        if widget is None:
            return
        old = cls._overlays.pop(widget, None)
        if old is not None:
            old.setParent(None)
            old.deleteLater()
        overlay = _BlurOverlay(widget, blur_radius=cls.BLUR_RADIUS, desaturate=desaturate)
        cls._overlays[widget] = overlay
        overlay.fade_in()

    @classmethod
    def _hide_overlay(cls, widget):
        overlay = cls._overlays.pop(widget, None)
        if overlay is not None:
            overlay.fade_out_and_remove()


class _GlowDialog(QDialog):
    """Базовое безрамочное окно в фирменном стиле - переиспользует ту же
    графитовую панель со свечением и тенью, что и остальные панели
    приложения (см. _GlowFrame в left_panel.py). Своя строка заголовка
    (т.к. системной рамки нет) с крестиком закрытия, перетаскивание окна
    мышью за заголовок. Наследники добавляют содержимое в self.body_layout,
    и в конце своего __init__ обязаны вызвать self._lock_size(), которая
    фиксирует размер окна (не растягивается, resize-рамки нет по
    определению у безрамочного окна)."""
    def __init__(self, parent=None, title="", glow_color=None):
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
        outer_layout.setContentsMargins(styles.scaled(18), styles.scaled(18), styles.scaled(18), styles.scaled(18))

        self.glow_frame = _GlowFrame(glow_color=glow_color)
        outer_layout.addWidget(self.glow_frame)

        frame_layout = QVBoxLayout(self.glow_frame)
        frame_layout.setContentsMargins(styles.scaled(16), styles.scaled(5), styles.scaled(16), styles.scaled(16))
        frame_layout.setSpacing(0)
        self.frame_layout = frame_layout

        title_row = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            f"color: #f2f4f6; font-weight: bold; font-size: {styles.scaled_pt(12)}pt; background: transparent;"
        )
        # Резервируем высоту строки заголовка под размер кнопки-крестика
        # (она позиционируется абсолютно, а не через layout заголовка) -
        # иначе для диалогов с коротким заголовком крестик мог "наезжать"
        # на первый ряд содержимого ниже
        self.title_label.setMinimumHeight(styles.scaled(38))
        # Оставляем справа пустое место под будущий крестик (сам он не в
        # layout - см. ниже), чтобы длинный заголовок на него не наезжал
        title_row.addWidget(self.title_label)
        title_row.addStretch()
        frame_layout.addLayout(title_row)
        frame_layout.addSpacing(2)  # минимальный зазор - полоса ближе к заголовку

        # Светящаяся полоса-подчёркивание под заголовком - тот же приём,
        # что и в статус-баре/верхней панели (яркая по центру, гаснущая
        # к краям), просто переиспользуем тот же класс
        title_underline = _GlowLine(color=glow_color)
        frame_layout.addWidget(title_underline)
        frame_layout.addSpacing(10)  # обычный зазор перед содержимым диалога

        self.body_layout = QVBoxLayout()
        self.body_layout.setSpacing(styles.scaled(10))
        frame_layout.addLayout(self.body_layout)

        # Крестик закрытия - НЕ в layout, а поверх правого верхнего угла
        # абсолютным позиционированием (родитель - сама рамка glow_frame).
        # Так при наведении он может увеличиваться, не "раздвигая" соседние
        # элементы заголовка и не тратя зарезервированное под это место.
        self.close_btn = _DialogCloseButton(parent=self.glow_frame)
        self.close_btn.setAutoDefault(False)
        self.close_btn.setDefault(False)
        self.close_btn.clicked.connect(self.reject)

    def _lock_size(self, clamp_to_screen=False, width_fraction=0.95, height_fraction=0.92):
        """Фиксирует размер окна по текущему содержимому - вызывать в
        конце __init__ наследника, после того как весь контент добавлен.
        clamp_to_screen=True - для больших/динамических диалогов (много
        полей, таблицы) - сначала аккуратно уменьшает окно, если оно не
        помещается на маленьком экране."""
        self.adjustSize()
        # Принудительно "прогоняем" отложенные события layout'а - без
        # этого geometry() дочерних виджетов (в частности, glow_frame)
        # не всегда успевает обновиться синхронно сразу после adjustSize(),
        # особенно для раскладок с переносом текста (расчёт итоговой
        # ширины/высоты у таких меток нередко требует нескольких проходов
        # layout-движка) - из-за этого self.glow_frame.width() ниже, в
        # _position_close_button(), мог отражать не окончательное, а
        # промежуточное значение, и крестик оказывался не у истинного
        # правого края.
        QApplication.processEvents()
        if clamp_to_screen:
            _clamp_to_screen(self, width_fraction=width_fraction, height_fraction=height_fraction)
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
        # Дублируем применение темы здесь же (не только в showEvent) -
        # это вызывается в конце __init__ КАЖДОГО диалога, когда весь
        # его контент уже точно построен
        styles.retheme_widget_tree(self)

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
        _DialogBackgroundManager.on_dialog_opened(self)
        # Подстраховка: центрируем ещё раз прямо перед показом (а не
        # только один раз в конструкторе) - на случай, если геометрия
        # экрана/содержимого успела чуть измениться к этому моменту
        _clamp_to_screen(self)
        # То же самое - переставляем крестик ещё раз прямо перед показом.
        # _lock_size() (вызывается в конце __init__ каждого диалога)
        # иногда даёт неточный результат для содержимого с не до конца
        # определившейся шириной на тот момент (например, список с
        # прокруткой, чья итоговая ширина/наличие самой полосы прокрутки
        # может определиться чуть позже) - сейчас, при показе, геометрия
        # уже точно окончательная.
        self._position_close_button()
        # Перекрашиваем текст/акценты под текущую тему - на светлой теме
        # белый текст (зашитый буквально в коде диалога) иначе был бы не
        # виден на светлом фоне
        styles.retheme_widget_tree(self)
        self.setWindowOpacity(0.0)
        self._fade_in_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_in_anim.setDuration(220)
        self._fade_in_anim.setStartValue(0.0)
        self._fade_in_anim.setEndValue(1.0)
        self._fade_in_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_in_anim.start()

    def _fade_out_then(self, finish_callback):
        if self._closing_started:
            return
        self._closing_started = True
        _DialogBackgroundManager.on_dialog_closed(self)

        self._closing_callback = finish_callback
        self._already_closed = False

        self._fade_out_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_out_anim.setDuration(190)
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
        QTimer.singleShot(320, self._run_closing_callback_once)

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
    def __init__(self, parent=None, title="Ошибка", message="", icon_name="warning.svg", confirm_mode=False,
                 yes_text="Да", no_text="Нет"):
        super().__init__(parent, title=title)

        content_row = QHBoxLayout()
        content_row.setSpacing(styles.scaled(12))
        icon_label = QLabel()
        icon_path = os.path.join(ICONS_DIR, icon_name)
        if os.path.exists(icon_path):
            icon_label.setPixmap(icon_utils.plain_pixmap(icon_path, 40))
        icon_label.setStyleSheet("background: transparent;")
        content_row.addWidget(icon_label)

        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("color: #e8eaed; background: transparent;")

        # QLabel с переносом текста без явной ширины иногда получает
        # "квадратный" естественный размер вместо ширины, нужной для
        # одной строки - из-за этого даже короткие фразы ("Протокол
        # обновлён") переносились на 2 строки с кучей пустого места
        # справа. Меряем по метрикам шрифта реальную ширину самой
        # широкой строки сообщения и используем её напрямую (с запасом,
        # но не больше 380px) - короткие сообщения остаются в одну
        # строку, длинные по-прежнему переносятся.
        fm = QFontMetrics(msg_label.font())
        natural_width = max(fm.horizontalAdvance(line) for line in message.split('\n')) if message else 0
        msg_label.setFixedWidth(min(max(natural_width + 12, 80), 380))

        content_row.addWidget(msg_label)
        content_row.addStretch(1)
        self.body_layout.addLayout(content_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        if confirm_mode:
            yes_btn = QPushButton(yes_text)
            yes_btn.setObjectName("chromeButton")
            yes_btn.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
            yes_btn.setAutoDefault(False)
            yes_btn.clicked.connect(self.accept)
            no_btn = QPushButton(no_text)
            no_btn.setObjectName("chromeButton")
            no_btn.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
            no_btn.setAutoDefault(False)
            no_btn.clicked.connect(self.reject)
            btn_row.addWidget(yes_btn)
            btn_row.addWidget(no_btn)
        else:
            ok_btn = QPushButton("OK")
            ok_btn.setObjectName("chromeButton")
            ok_btn.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
            # Кнопка по умолчанию - Enter срабатывает так же, как клик
            # (единственная кнопка реакции - разумно дать Enter её нажать)
            ok_btn.setAutoDefault(True)
            ok_btn.setDefault(True)
            ok_btn.clicked.connect(self.accept)
            btn_row.addWidget(ok_btn)
        btn_row.addStretch()
        self.body_layout.addLayout(btn_row)

        self.setMinimumWidth(styles.scaled(260))
        self._lock_size()

    @staticmethod
    def show_error(parent, title, message):
        """Удобный короткий вызов - GlowMessageDialog.show_error(self, "Ошибка", "текст")
        вместо QMessageBox.warning(...)."""
        dlg = GlowMessageDialog(parent, title=title, message=message, icon_name="warning.svg")
        dlg.exec_()

    @staticmethod
    def confirm(parent, title, message, icon_name="warning.svg", yes_text="Да", no_text="Нет"):
        """Диалог подтверждения (2 кнопки) в фирменном стиле - возвращает
        True, если пользователь нажал первую кнопку (yes_text)."""
        dlg = GlowMessageDialog(
            parent, title=title, message=message, icon_name=icon_name,
            confirm_mode=True, yes_text=yes_text, no_text=no_text
        )
        return dlg.exec_() == QDialog.Accepted

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
        top_row.setSpacing(styles.scaled(10))
        icon_label = QLabel()
        icon_path = os.path.join(ICONS_DIR, 'print.svg')
        if os.path.exists(icon_path):
            icon_label.setPixmap(icon_utils.tinted_pixmap(icon_path, styles.TOP_BAR_ICON_COLOR_NORMAL, 40))
        icon_label.setStyleSheet("background: transparent;")
        top_row.addWidget(icon_label)
        msg_label = QLabel("Что напечатать?")
        msg_label.setStyleSheet(f"color: #e8eaed; font-size: {styles.scaled_pt(12)}pt; background: transparent;")
        top_row.addWidget(msg_label, 1)
        self.body_layout.addLayout(top_row)

        def make_btn(text, value):
            btn = QPushButton(text)
            btn.setObjectName("chromeButton")
            btn.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
            btn.clicked.connect(lambda: self._choose(value))
            return btn

        btn_col = QVBoxLayout()
        btn_col.setSpacing(styles.scaled(8))
        btn_col.addWidget(make_btn("Текущий протокол", "protocol"))
        btn_col.addWidget(make_btn("Список насосов (сокращённый)", "list_compact"))
        btn_col.addWidget(make_btn("Список насосов (расширенный)", "list_expanded"))
        btn_col.addWidget(make_btn("Сводная статистика по заказам", "stats"))
        btn_col.addSpacing(14)
        btn_col.addWidget(make_btn("Ничего", "cancel"))
        self.body_layout.addLayout(btn_col)

        self.setMinimumWidth(styles.scaled(320))
        self._lock_size()

    def _choose(self, value):
        self.choice = value
        if value == "cancel":
            self.reject()
        else:
            self.accept()


class NetworkAheadChoiceDialog(_GlowDialog):
    """Диалог выбора действия при обнаружении "сеть ушла вперёд" - три
    варианта сразу в одном окне (умное слияние / полная замена сети /
    отмена), а не цепочка из нескольких последовательных диалогов - на
    практике было легко перепутать, какой именно вариант выбираешь при
    отказе от предыдущего в такой цепочке."""
    def __init__(self, parent=None):
        super().__init__(parent, title="Сеть ушла вперёд")
        self.choice = None
        text_color = styles.get_dialog_text_color()

        top_row = QHBoxLayout()
        top_row.setSpacing(styles.scaled(10))
        icon_label = QLabel()
        icon_path = os.path.join(ICONS_DIR, 'warning.svg')
        if os.path.exists(icon_path):
            icon_label.setPixmap(icon_utils.plain_pixmap(icon_path, 40))
        icon_label.setStyleSheet("background: transparent;")
        top_row.addWidget(icon_label)
        msg_label = QLabel(
            "Пока вы работали, сеть уже изменилась - либо кто-то другой "
            "успел выгрузить свои правки, либо ваша локальная копия сейчас "
            "старше сетевой (например, после восстановления из резервной "
            "копии). Выберите, как поступить:"
        )
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(f"color: {text_color}; background: transparent;")
        msg_label.setFixedWidth(styles.scaled(360))
        top_row.addWidget(msg_label, 1)
        self.body_layout.addLayout(top_row)

        def make_btn(text, value):
            btn = QPushButton(text)
            btn.setObjectName("chromeButton")
            btn.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
            btn.clicked.connect(lambda: self._choose(value))
            return btn

        def make_hint(text):
            hint = QLabel(text)
            hint.setWordWrap(True)
            hint.setFixedWidth(styles.scaled(360))
            hint.setStyleSheet(f"color: {text_color}; background: transparent; font-size: {styles.scaled_pt(10)}pt;")
            return hint

        self.body_layout.addSpacing(6)
        self.body_layout.addWidget(make_hint(
            "Умное слияние - подтянет сетевую версию и добавит в неё ваши "
            "локальные добавления (только добавленные записи - не правки "
            "уже существующих; о них будет сообщено отдельно)."
        ))
        self.body_layout.addWidget(make_btn("Умное слияние", "merge"))

        self.body_layout.addSpacing(10)
        self.body_layout.addWidget(make_hint(
            "Полная замена сети - сеть станет точно такой же, как ваша "
            "текущая локальная копия. ВНИМАНИЕ: записи, которых нет в "
            "локальной копии, будут удалены из сети безвозвратно "
            "(резервная копия сетевой версии сохранится автоматически)."
        ))
        self.body_layout.addWidget(make_btn("Полная замена сети", "replace"))

        self.body_layout.addSpacing(14)
        self.body_layout.addWidget(make_btn("Отмена", "cancel"))

        self.setMinimumWidth(styles.scaled(400))
        self._lock_size(clamp_to_screen=True)

    def _choose(self, value):
        self.choice = value
        if value == "cancel":
            self.reject()
        else:
            self.accept()


class ExportProgressDialog(_GlowDialog):
    """Диалог с индикатором прогресса на время экспорта в PDF - блокирует
    основную программу (модально), показывает процент выполнения.

    Размытие/обесцвечивание фона здесь ПРИНУДИТЕЛЬНОЕ - не зависит от
    переключателя в настройках (экспорт и так блокирует всю основную
    программу целиком, пользователь должен видеть это визуально в любом
    случае). Если общий переключатель размытия и так включён - обычный
    механизм (_DialogBackgroundManager, через showEvent родителя) уже
    покажет размытие сам; здесь мы лишь дополнительно подстраховываемся
    на случай, если он выключен."""
    def __init__(self, parent=None):
        super().__init__(parent, title="Экспорт в PDF")
        self.setWindowModality(Qt.ApplicationModal)
        self._forced_overlay = None

        label = QLabel("Подождите, идёт экспорт файла PDF...")
        label.setWordWrap(True)
        label.setStyleSheet("color: #e8eaed; background: transparent;")
        self.body_layout.addWidget(label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #2b2d31;
                border: 1px solid #6b6f75;
                border-radius: 4px;
                color: #e8eaed;
                text-align: center;
                height: 22px;
            }
            QProgressBar::chunk {
                background-color: #4fd1ff;
                border-radius: 4px;
            }
        """)
        self.body_layout.addWidget(self.progress_bar)

        self.setMinimumWidth(styles.scaled(360))
        self.close_btn.hide()  # экспорт нельзя прервать закрытием окна
        self._lock_size()

    def set_progress(self, value):
        self.progress_bar.setValue(value)
        QApplication.processEvents()

    def showEvent(self, event):
        super().showEvent(event)
        if not _DialogBackgroundManager.enabled and self._forced_overlay is None:
            target = _DialogBackgroundManager._main_target
            if target is not None:
                self._forced_overlay = _BlurOverlay(
                    target, blur_radius=_DialogBackgroundManager.BLUR_RADIUS, desaturate=True
                )
                self._forced_overlay.fade_in()

    def _fade_out_then(self, finish_callback):
        if self._forced_overlay is not None:
            self._forced_overlay.fade_out_and_remove()
            self._forced_overlay = None
        super()._fade_out_then(finish_callback)


class InstructionsDialog(_GlowDialog):
    """Окно инструкции - фирменный стиль, но с жёлтой (не бирюзовой)
    подсветкой, чтобы визуально выделяться среди остальных диалогов.
    Текст загружается из внешнего файла resources/instructions.txt
    (обычный текст с HTML-тегами внутри) - чтобы изменить содержимое
    инструкции, достаточно отредактировать этот файл, без изменений в
    коде программы."""
    _YELLOW = (230, 200, 40)
    INSTRUCTIONS_PATH = os.path.join(app_paths.get_resources_dir(), 'instructions.txt')

    def __init__(self, parent=None):
        super().__init__(parent, title="Инструкция", glow_color=self._YELLOW)

        text_browser = QTextBrowser()
        text_browser.setOpenExternalLinks(True)
        text_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: #f0f0f0;
                color: #1c1e21;
                border: 1px solid #6b6f75;
                border-radius: 6px;
                padding: {styles.scaled(10)}px;
            }}
        """)
        text_browser.setHtml(self._load_instructions_html())
        text_browser.setMinimumSize(styles.scaled(520), styles.scaled(420))
        self.body_layout.addWidget(text_browser)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_ok = QPushButton("Закрыть")
        btn_ok.setObjectName("chromeButton")
        btn_ok.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE + """
            QPushButton#chromeButton:hover {
                border: 2px solid #e6c828;
            }
        """)
        btn_ok.setAutoDefault(False)
        btn_ok.setDefault(False)
        btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(btn_ok)
        btn_row.addStretch()
        self.body_layout.addLayout(btn_row)

        self._lock_size(clamp_to_screen=True)

    def _load_instructions_html(self):
        try:
            with open(self.INSTRUCTIONS_PATH, encoding='utf-8') as f:
                return f.read()
        except OSError:
            return (
                "<p>Файл инструкции не найден "
                f"({self.INSTRUCTIONS_PATH}).</p>"
            )


def _make_eye_icon(color="#e8eaed", size=18):
    """Рисует простую иконку "глаз" (кнопка показать/скрыть пароль) -
    программно через QPainter, без отдельного файла ресурса."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidth(max(1, size // 12))
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    eye_rect = QRectF(size * 0.06, size * 0.28, size * 0.88, size * 0.44)
    painter.drawEllipse(eye_rect)
    painter.setBrush(QColor(color))
    r = size * 0.13
    painter.drawEllipse(QRectF(size / 2 - r, size / 2 - r, r * 2, r * 2))
    painter.end()
    return QIcon(pixmap)


def setup_password_field(line_edit, accept_callback=None, icon_color="#e8eaed"):
    """Готовит обычное поле ввода пароля - добавляет кнопку-"глазок"
    прямо внутри поля (через QLineEdit.addAction - встроенный механизм
    Qt, без лишних виджетов в раскладке) для временного показа введённого
    пароля, и подключает Enter к переданному обработчику (если передан) -
    используется во всех диалогах ввода пароля для единообразия."""
    eye_action = QAction(_make_eye_icon(icon_color), "", line_edit)
    eye_action.setCheckable(True)
    eye_action.setToolTip("Показать пароль")

    def _toggle_visibility(checked):
        line_edit.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        eye_action.setToolTip("Скрыть пароль" if checked else "Показать пароль")

    eye_action.toggled.connect(_toggle_visibility)
    line_edit.addAction(eye_action, QLineEdit.TrailingPosition)

    if accept_callback is not None:
        line_edit.returnPressed.connect(accept_callback)

    return eye_action


class PasswordDialog(_GlowDialog):
    def __init__(self, parent=None, message="Для удаления записи введите пароль:"):
        super().__init__(parent, title="Введите пароль")

        msg_label = QLabel(message)
        msg_label.setStyleSheet("color: #e8eaed; background: transparent;")
        msg_label.setWordWrap(True)
        self.body_layout.addWidget(msg_label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(styles.get_password_input_style())
        self.password_input.returnPressed.connect(self.try_accept)
        eye_color = "#2b2d31" if styles.is_light_theme() else "#e8eaed"
        setup_password_field(self.password_input, icon_color=eye_color)
        self.body_layout.addWidget(self.password_input)

        # Строка ошибки - место под неё зарезервировано СРАЗУ (текст
        # пустой, но высота уже заложена в _lock_size() ниже), иначе на
        # фиксированном по размеру окне появление текста после первой
        # неудачной попытки было бы некуда вставить
        self.error_label = QLabel("")
        self.error_label.setStyleSheet(
            f"color: #ff8080; background: transparent; font-size: {styles.scaled_pt(10)}pt;"
        )
        self.error_label.setWordWrap(True)
        self.error_label.setMinimumHeight(styles.scaled(18))
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
        self.setMinimumWidth(styles.scaled(320))
        self._lock_size()

    def try_accept(self):
        """Проверяет пароль ПЕРЕД закрытием окна - и по Enter, и по кнопке
        OK. Если пароль неверный - окно НЕ закрывается, показывает ошибку
        внутри и даёт попробовать ещё раз (вместо того чтобы закрыться
        независимо от результата, а сообщить об ошибке уже после)."""
        entered = self.password_input.text()
        if not auth.check_password(entered):
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
    def __init__(self, x_values, min_values, max_values, max_points, x_label="X", x_is_integer=False, parent=None):
        super().__init__(parent)
        self.max_points = max_points
        self.x_is_integer = x_is_integer

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([x_label, "Мин.", "Макс."])
        self.table.setStyleSheet(f"""
            QTableWidget {{
                gridline-color: #b0b4b9;
                border: 1px solid #6b6f75;
                border-radius: 4px;
                background-color: #f0f0f0;
            }}
            QTableWidget::item {{
                padding: {styles.scaled(1)}px;
            }}
            QTableWidget::item:hover {{
                background-color: #cdf2da;
            }}
            QTableWidget::item:selected {{
                background-color: #a8e8bd;
                color: #1c1e21;
            }}
            QHeaderView::section {{
                background-color: #3a3d42;
                color: #e8eaed;
                border: 1px solid #6b6f75;
                padding: {styles.scaled(2)}px {styles.scaled(6)}px;
            }}
        """)
        rows = len(x_values) if x_values else 1
        self.table.setRowCount(rows)
        cell_text_color = QColor("#1c1e21")
        for i in range(rows):
            x_val = x_values[i] if i < len(x_values) else ''
            min_val = min_values[i] if i < len(min_values) else ''
            max_val = max_values[i] if i < len(max_values) else ''
            if self.x_is_integer and x_val != '':
                try:
                    x_val = int(round(float(x_val)))
                except (ValueError, TypeError):
                    pass
            x_item = QTableWidgetItem(str(x_val))
            x_item.setTextAlignment(Qt.AlignCenter)
            x_item.setForeground(cell_text_color)
            min_item = QTableWidgetItem(str(min_val))
            min_item.setTextAlignment(Qt.AlignCenter)
            min_item.setForeground(cell_text_color)
            max_item = QTableWidgetItem(str(max_val))
            max_item.setTextAlignment(Qt.AlignCenter)
            max_item.setForeground(cell_text_color)
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

        GREEN_BTN_STYLE = styles.LEFT_PANEL_RESET_BTN_STYLE + """
            QPushButton#chromeButton:hover {
                border: 2px solid #2ecc71;
            }
        """
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("+ точка")
        self.btn_add.setObjectName("chromeButton")
        self.btn_add.setStyleSheet(GREEN_BTN_STYLE)
        self.btn_add.setMaximumWidth(80)
        self.btn_add.clicked.connect(self.add_row)
        self.btn_remove = QPushButton("− точка")
        self.btn_remove.setObjectName("chromeButton")
        self.btn_remove.setStyleSheet(GREEN_BTN_STYLE)
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
        внутренней прокрутки и без пустого пространства по краям.
        Используется, чтобы диалог обходился без QScrollArea. Столбцы
        зафиксированы (Fixed) - пользователь не может их растягивать."""
        small_font = QFont()
        small_font.setPointSize(styles.scaled_pt(10))
        self.table.setFont(small_font)
        self.table.horizontalHeader().setFont(small_font)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(styles.scaled(22))
        self.table.resizeRowsToContents()
        self.table.resizeColumnsToContents()
        min_section = styles.scaled(40)
        for col in range(self.table.columnCount()):
            self.table.setColumnWidth(col, max(min_section, self.table.columnWidth(col) + styles.scaled(4)))
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        total_height = self.table.horizontalHeader().height() + 2
        for row in range(self.table.rowCount()):
            total_height += self.table.rowHeight(row)
        self.table.setFixedHeight(total_height)

        total_width = 2
        for col in range(self.table.columnCount()):
            total_width += self.table.columnWidth(col)
        self.table.setFixedWidth(total_width)
        self.setFixedWidth(total_width)

        # Фиксируем столбцы от изменения размера пользователем - ВАЖНО:
        # именно после того, как выше уже посчитана и применена нужная
        # ширина, иначе Fixed-режим мешает самой авто-подгонке
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

    def match_width(self, target_width):
        """Пропорционально растягивает/сжимает столбцы таблицы, чтобы её
        общая ширина совпала с target_width - используется, чтобы все три
        таблицы испытаний (у которых может быть разное число столбцов)
        были одной ширины (п.1 требований)."""
        col_count = self.table.columnCount()
        if col_count == 0:
            return
        current_cols_width = sum(self.table.columnWidth(c) for c in range(col_count))
        if current_cols_width == 0:
            return
        available = max(30 * col_count, target_width - 2)
        scale = available / current_cols_width
        for c in range(col_count):
            self.table.setColumnWidth(c, max(styles.scaled(30), int(self.table.columnWidth(c) * scale)))
        new_total = 2 + sum(self.table.columnWidth(c) for c in range(col_count))
        self.table.setFixedWidth(new_total)
        self.setFixedWidth(new_total)

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
            x_val = get_float(0)
            if self.x_is_integer and x_val is not None:
                x_val = int(round(x_val))
            x_vals.append(x_val)
            min_vals.append(get_float(1))
            max_vals.append(get_float(2))
        return x_vals, min_vals, max_vals


class AddModificationDialog(_GlowDialog):
    """Диалог добавления новой модификации (или редактирования существующей,
    если передан existing_mod). Фирменный стиль как у остальных диалогов,
    но с зелёной (не бирюзовой/оранжевой) подсветкой - контрастно
    смотрится на графитовом фоне и легко отличим от других окон."""

    _GREEN = (46, 204, 113)

    def __init__(self, parent=None, existing_mod=None):
        title = (
            f"Редактирование модификации - {existing_mod['name']}" if existing_mod
            else "Добавление модификации насоса ГУР"
        )
        super().__init__(parent, title=title, glow_color=self._GREEN)

        INPUT_STYLE = (
            "QLineEdit, QComboBox { "
            "background-color: #f0f0f0; color: #1c1e21; "
            f"border: 1px solid #6b6f75; border-radius: 4px; padding: {styles.scaled(1)}px {styles.scaled(6)}px; }}"
            "QLineEdit:hover, QComboBox:hover, QLineEdit:focus, QComboBox:focus { "
            "border: 1px solid #2ecc71; }"
            "QComboBox::drop-down { border: none; }"
        )
        GREEN_BTN_STYLE = styles.LEFT_PANEL_RESET_BTN_STYLE + """
            QPushButton#chromeButton:hover {
                border: 2px solid #2ecc71;
            }
        """

        name_row = QHBoxLayout()
        name_label = QLabel("Номер (название) модификации насоса ГУР:")
        name_label.setStyleSheet("color: #e8eaed; background: transparent;")
        name_row.addWidget(name_label)
        self.name_input = QLineEdit()
        self.name_input.setStyleSheet(INPUT_STYLE)
        if existing_mod:
            self.name_input.setText(existing_mod['name'])
        name_row.addWidget(self.name_input)
        self.body_layout.addLayout(name_row)

        norm_title = self._section_title("Установленные нормативные требования")
        norm_title.setStyleSheet(
            f"color: #e8eaed; font-weight: bold; font-size: {styles.scaled_pt(12)}pt; background: transparent;"
        )
        self.body_layout.addWidget(norm_title)

        # Три испытания - в один горизонтальный ряд, чтобы диалог оставался
        # компактным по высоте и не требовал прокрутки
        tests_layout = QHBoxLayout()
        tests_layout.setSpacing(styles.scaled(20))

        test1_col = QVBoxLayout()
        test1_col.addWidget(self._section_title("Испытание 1:\nПодача от оборотов\nECO выкл."))
        self.test1 = PointsEditorWidget(
            x_values=existing_mod['norm_graph1_x'] if existing_mod else list(utils.DEFAULT_GRAPH1_X),
            min_values=existing_mod['norm_graph1_min'] if existing_mod else [],
            max_values=existing_mod['norm_graph1_max'] if existing_mod else [],
            max_points=utils.MAX_GRAPH1_POINTS,
            x_label="Обороты",
            x_is_integer=True
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
            x_label="Обороты",
            x_is_integer=True
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

        # Выравниваем все 3 таблицы по ширине (по самой широкой из них) -
        # п.1 требований: у испытаний может быть разное число контрольных
        # точек, из-за чего таблицы иначе получались бы разной ширины
        max_width = max(self.test1.width(), self.test2.width(), self.test3.width())
        self.test1.match_width(max_width)
        self.test2.match_width(max_width)
        self.test3.match_width(max_width)

        # Центрируем группу таблиц по горизонтали относительно диалога
        centered_tests_row = QHBoxLayout()
        centered_tests_row.addStretch(1)
        centered_tests_row.addLayout(tests_layout)
        centered_tests_row.addStretch(1)
        self.body_layout.addLayout(centered_tests_row)

        pressure_box = QVBoxLayout()
        pressure_box.addWidget(self._section_title("Испытание 4: давление предохранительного клапана"))
        pressure_row = QHBoxLayout()
        pmin_label = QLabel("Мин., бар:")
        pmin_label.setStyleSheet("color: #e8eaed; background: transparent;")
        pressure_row.addWidget(pmin_label)
        self.pressure_min_input = QLineEdit(
            str(existing_mod['pressure_min']) if existing_mod and existing_mod['pressure_min'] is not None else "")
        self.pressure_min_input.setStyleSheet(INPUT_STYLE)
        self.pressure_min_input.setFixedWidth(styles.scaled(80))
        pressure_row.addWidget(self.pressure_min_input)
        pmax_label = QLabel("Макс., бар:")
        pmax_label.setStyleSheet("color: #e8eaed; background: transparent;")
        pressure_row.addWidget(pmax_label)
        self.pressure_max_input = QLineEdit(
            str(existing_mod['pressure_max']) if existing_mod and existing_mod['pressure_max'] is not None else "")
        self.pressure_max_input.setStyleSheet(INPUT_STYLE)
        self.pressure_max_input.setFixedWidth(styles.scaled(80))
        pressure_row.addWidget(self.pressure_max_input)
        pressure_row.addStretch()
        pressure_box.addLayout(pressure_row)
        self.body_layout.addLayout(pressure_box)

        seal_box = QVBoxLayout()
        seal_box.addWidget(self._section_title("Проверка на герметичность"))
        self.seal_inputs = {}
        seal_rules = existing_mod['seal_rules'] if existing_mod else dict(utils.DEFAULT_SEAL_REQUIREMENTS)

        seal_fm = QFontMetrics(QLabel().font())
        seal_label_w = max(
            seal_fm.horizontalAdvance(utils.SEAL_LABELS[k] + ":") for k in utils.SEAL_KEYS
        ) + 6
        self._seal_label_w = seal_label_w
        self._seal_input_style = INPUT_STYLE
        self._seal_btn_style = GREEN_BTN_STYLE
        self._seal_last_key = utils.SEAL_KEYS[-1]
        self._seal_field_width = 260  # единая ширина ВСЕХ полей герметичности - и первого, и добавленных
        self._seal_extra_layout = QVBoxLayout()
        self._seal_extra_layout.setSpacing(styles.scaled(6))

        def make_seal_edit(text):
            e = QLineEdit(text)
            e.setStyleSheet(self._seal_input_style)
            e.setFixedWidth(self._seal_field_width)
            return e

        for key in utils.SEAL_KEYS:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(styles.scaled(6))
            lbl = QLabel(utils.SEAL_LABELS[key] + ":")
            lbl.setWordWrap(False)
            lbl.setFixedWidth(seal_label_w)
            lbl.setStyleSheet("color: #e8eaed; background: transparent;")
            row_layout.addWidget(lbl)

            if key == self._seal_last_key:
                stored = seal_rules.get(key, "") or ""
                if existing_mod:
                    parts = [p.strip() for p in stored.split(";") if p.strip()] or ["отсутствуют"]
                else:
                    # Новая модификация - не используем старую комбинированную
                    # строку по умолчанию ("отсутствуют или присутствуют...") -
                    # она была рассчитана на одно поле, а не на новый формат
                    # с несколькими отдельными полями
                    parts = ["отсутствуют"]

                first_edit = make_seal_edit(parts[0])
                row_layout.addWidget(first_edit)
                self.seal_inputs[key] = [first_edit]

                self._add_seal_btn = QPushButton("+")
                self._add_seal_btn.setObjectName("chromeButton")
                self._add_seal_btn.setFixedSize(26, 24)
                self._add_seal_btn.setToolTip("Добавить ещё одно поле для этого требования (максимум 3)")
                self._add_seal_btn.setStyleSheet(self._seal_btn_style)
                self._add_seal_btn.clicked.connect(lambda: self._add_seal_field())
                row_layout.addWidget(self._add_seal_btn)
                row_layout.addStretch(1)

                seal_box.addLayout(row_layout)
                seal_box.addLayout(self._seal_extra_layout)

                # По умолчанию сразу показываем второе поле - с готовой
                # формулировкой "присутствуют в допускаемой степени", а не
                # пустым (если модификация уже существует и там правда
                # было сохранено 2-3 формулировки - используем их вместо
                # значения по умолчанию)
                if len(parts) >= 2:
                    for extra_text in parts[1:3]:
                        self._add_seal_field(extra_text, relock=False)
                else:
                    self._add_seal_field("присутствуют в допускаемой степени", relock=False)
            else:
                edit = make_seal_edit(seal_rules.get(key, "отсутствуют") or "отсутствуют")
                row_layout.addWidget(edit)
                row_layout.addStretch(1)
                self.seal_inputs[key] = edit
                seal_box.addLayout(row_layout)
        self.body_layout.addLayout(seal_box)

        self.body_layout.addSpacing(16)

        password_row = QHBoxLayout()
        password_row.addStretch(1)
        password_label = QLabel("Пароль для сохранения:")
        password_label.setStyleSheet(
            "color: #e8eaed; font-weight: bold; background: transparent;"
        )
        password_row.addWidget(password_label)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedWidth(styles.scaled(120))
        self.password_input.returnPressed.connect(self.try_accept)
        self.password_input.setStyleSheet(
            "QLineEdit { background-color: #f0f0f0; color: #1c1e21; "
            f"border: 1px solid #6b6f75; border-radius: 4px; padding: {styles.scaled(2)}px {styles.scaled(6)}px; }}"
            "QLineEdit:hover, QLineEdit:focus { border: 1px solid #2ecc71; }"
        )
        setup_password_field(self.password_input, icon_color="#1c1e21")
        password_row.addWidget(self.password_input)
        password_row.addStretch(1)
        self.body_layout.addLayout(password_row)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Сохранить")
        ok_btn.setObjectName("chromeButton")
        ok_btn.setStyleSheet(GREEN_BTN_STYLE)
        ok_btn.setAutoDefault(False)
        ok_btn.setDefault(False)
        ok_btn.clicked.connect(self.try_accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("chromeButton")
        cancel_btn.setStyleSheet(GREEN_BTN_STYLE)
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        self.body_layout.addLayout(btn_layout)

        # У этого диалога обычно самое высокое содержимое из всех (3
        # таблицы испытаний + герметичность + пароль) - стандартные 92%
        # высоты экрана оставляют слишком мало отступов сверху/снизу,
        # из-за чего окно визуально выглядело смещённым вниз. Даём
        # заметно больше запаса специально для этого диалога.
        self._lock_size(clamp_to_screen=True, height_fraction=0.8)

    def _add_seal_field(self, initial_text="", relock=True):
        """Добавляет ещё одно поле ввода для последнего пункта проверки на
        герметичность (не более 3 в сумме). У каждого добавленного поля
        сразу есть своя кнопка "-" для его удаления.

        relock=False - используется при первоначальном построении диалога
        (когда остальной контент - примечание/пароль/кнопки - ещё не
        добавлен): фиксировать размер здесь рано, иначе следующий вызов
        _lock_size() в конце __init__ окажется "заперт" уже выставленным
        maximumSize и не сможет корректно посчитать размер под ПОЛНЫЙ
        контент - именно это и вызывало смещение окна вниз."""
        fields = self.seal_inputs[self._seal_last_key]
        if len(fields) >= 3:
            return

        row_widget = QWidget()
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(styles.scaled(6))
        spacer = QLabel("")
        spacer.setFixedWidth(self._seal_label_w)
        row.addWidget(spacer)

        edit = QLineEdit(initial_text)
        edit.setStyleSheet(self._seal_input_style)
        edit.setFixedWidth(self._seal_field_width)
        row.addWidget(edit)

        remove_btn = QPushButton("−")
        remove_btn.setObjectName("chromeButton")
        remove_btn.setFixedSize(26, 24)
        remove_btn.setToolTip("Удалить это поле")
        remove_btn.setStyleSheet(self._seal_btn_style)
        remove_btn.clicked.connect(lambda: self._remove_seal_field(row_widget, edit))
        row.addWidget(remove_btn)
        row.addStretch(1)

        self._seal_extra_layout.addWidget(row_widget)
        fields.append(edit)
        self._update_seal_add_button()
        if relock:
            self._lock_size(clamp_to_screen=True)

    def _remove_seal_field(self, row_widget, edit):
        """Удаляет одно из добавленных полей (2е или 3е) - базовое (1е)
        поле удалить нельзя, у него и нет кнопки "-"."""
        fields = self.seal_inputs[self._seal_last_key]
        if edit in fields:
            fields.remove(edit)
        row_widget.setParent(None)
        row_widget.deleteLater()
        self._update_seal_add_button()
        self._lock_size(clamp_to_screen=True)

    def _update_seal_add_button(self):
        """Кнопка "+" видна, только пока полей меньше 3."""
        fields = self.seal_inputs[self._seal_last_key]
        self._add_seal_btn.setVisible(len(fields) < 3)

    def _section_title(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "color: #e8eaed; font-weight: bold; background: transparent;"
        )
        return lbl

    def try_accept(self):
        if not self.name_input.text().strip():
            GlowMessageDialog.show_error(self, "Ошибка", "Введите номер модификации.")
            return

        for label, widget in (("Испытание 1", self.test1), ("Испытание 2", self.test2), ("Испытание 3", self.test3)):
            ok, msg = widget.validate()
            if not ok:
                GlowMessageDialog.show_error(self, "Ошибка", f"{label}: {msg}")
                return

        try:
            float(self.pressure_min_input.text().strip())
            float(self.pressure_max_input.text().strip())
        except ValueError:
            GlowMessageDialog.show_error(self, "Ошибка", "Введите корректные числовые значения давления.")
            return

        for key, value in self.seal_inputs.items():
            first_field = value[0] if isinstance(value, list) else value
            if not first_field.text().strip():
                GlowMessageDialog.show_error(self, "Ошибка", "Заполните все требования по герметичности.")
                return

        if not auth.check_password(self.password_input.text()):
            GlowMessageDialog.show_error(self, "Ошибка", "Неверный пароль.")
            return

        self.accept()

    def get_data(self):
        x1, min1, max1 = self.test1.get_data()
        x2, min2, max2 = self.test2.get_data()
        x3, min3, max3 = self.test3.get_data()

        seal_rules = {}
        for key, value in self.seal_inputs.items():
            if isinstance(value, list):
                texts = [f.text().strip() for f in value if f.text().strip()]
                seal_rules[key] = "; ".join(texts) if texts else "отсутствуют"
            else:
                seal_rules[key] = value.text().strip()

        return {
            'name': self.name_input.text().strip(),
            'graph1_x': x1, 'graph1_min': min1, 'graph1_max': max1,
            'graph2_x': x2, 'graph2_min': min2, 'graph2_max': max2,
            'graph3_x': x3, 'graph3_min': min3, 'graph3_max': max3,
            'pressure_min': float(self.pressure_min_input.text().strip()),
            'pressure_max': float(self.pressure_max_input.text().strip()),
            'seal_rules': seal_rules,
        }


class ViewModificationsDialog(_GlowDialog):
    """Просмотр уже добавленных модификаций с их нормативами - фирменный
    стиль (бирюзовая подсветка), с возможностью редактирования и удаления
    выбранной модификации."""
    def __init__(self, parent=None):
        super().__init__(parent, title="Просмотр модификаций")

        main_row = QHBoxLayout()
        main_row.setSpacing(styles.scaled(14))

        # Левая колонка - список модификаций + кнопки
        left_col = QVBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.setFixedWidth(styles.scaled(200))
        self.list_widget.setMinimumHeight(styles.scaled(500))
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: #f0f0f0;
                color: #1c1e21;
                border: 1px solid #6b6f75;
                border-radius: 4px;
            }}
            QListWidget::item {{
                padding: {styles.scaled(3)}px {styles.scaled(4)}px;
            }}
            QListWidget::item:selected {{
                background-color: #bdeeff;
                color: #1c1e21;
            }}
            QListWidget::item:hover {{
                background-color: #d6f3ff;
            }}
        """)
        self._reload_list()
        self.list_widget.currentItemChanged.connect(self.show_details)
        left_col.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        self.btn_edit = QPushButton("Редактировать")
        self.btn_edit.setObjectName("chromeButton")
        self.btn_edit.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
        self.btn_edit.clicked.connect(self.edit_selected)
        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.setObjectName("chromeButton")
        self.btn_delete.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
        self.btn_delete.clicked.connect(self.delete_selected)
        btn_row.addWidget(self.btn_edit)
        btn_row.addWidget(self.btn_delete)
        left_col.addLayout(btn_row)
        main_row.addLayout(left_col)

        # Правая колонка - подробности, в прокручиваемой области с нашей
        # фирменной полосой прокрутки
        self.details_widget = QWidget()
        self.details_widget.setStyleSheet("background: transparent;")
        self.details_layout = QVBoxLayout(self.details_widget)
        self.details_layout.setSpacing(styles.scaled(10))
        # Правый отступ увеличен на ширину, которую резервирует под себя
        # наша полоса прокрутки (_GlowScrollBar.FULL_WIDTH + MARGIN_RIGHT =
        # 8+5=13px) - иначе визуально казалось бы, что отступ справа
        # меньше, чем слева
        self.details_layout.setContentsMargins(styles.scaled(8), styles.scaled(4), styles.scaled(21), styles.scaled(4))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setVerticalScrollBar(_GlowScrollBar())
        scroll.setWidget(self.details_widget)
        scroll.setMinimumWidth(styles.scaled(520))
        scroll.setMinimumHeight(styles.scaled(500))
        main_row.addWidget(scroll, 1)

        self.body_layout.addLayout(main_row)

        if self.list_widget.count() > 0:
            # Выбираем первую модификацию ДО фиксации размера окна - иначе
            # adjustSize() посчитал бы ширину по пустой заглушке, а не по
            # реальному содержимому (таблицы+графики), и при выборе любой
            # модификации графики оказывались бы обрезаны по уже
            # зафиксированной, слишком узкой ширине
            self.list_widget.setCurrentRow(0)
            # QScrollArea сама по себе не "прокидывает" наружу фактическую
            # ширину своего содержимого - измеряем её явно и задаём как
            # минимум области прокрутки, плюс запас под саму полосу
            # прокрутки справа (см. отступы details_layout выше)
            content_width = self.details_widget.sizeHint().width()
            scroll.setMinimumWidth(content_width + 20)
        else:
            self.show_details(None)
            self._clear_details_layout()
            self.details_layout.addWidget(
                self._plain_label("В базе пока нет ни одной модификации.")
            )
            self.details_layout.addStretch(1)
        self._update_buttons()

        self._lock_size(clamp_to_screen=True)

        # Разрешаем растягивание окна по ВЕРТИКАЛИ (ширина остаётся
        # зафиксированной, как обычно у наших диалогов) - у этого диалога
        # содержимое сильно варьируется по высоте в зависимости от
        # количества контрольных точек модификации, фиксированная высота
        # не всегда удобна. Тянуть можно за нижний край окна (см.
        # mousePressEvent/mouseMoveEvent/mouseReleaseEvent ниже).
        self.setMinimumHeight(styles.scaled(400))
        self.setMaximumHeight(16777215)
        self._resizing = False
        self.setMouseTracking(True)
        self.glow_frame.setMouseTracking(True)

    RESIZE_GRIP_HEIGHT = 10  # толщина зоны у нижнего края, за которую можно тянуть

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.y() >= self.height() - self.RESIZE_GRIP_HEIGHT:
            self._resizing = True
            self._resize_start_y = event.globalY()
            self._resize_start_height = self.height()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            delta = event.globalY() - self._resize_start_y
            new_height = self._resize_start_height + delta
            new_height = max(self.minimumHeight(), min(new_height, self.maximumHeight()))
            self.resize(self.width(), new_height)
            return
        if event.y() >= self.height() - self.RESIZE_GRIP_HEIGHT:
            self.setCursor(Qt.SizeVerCursor)
        else:
            self.unsetCursor()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing:
            self._resizing = False
            return
        super().mouseReleaseEvent(event)

    def _plain_label(self, text, bold=False, size=None):
        lbl = QLabel(text)
        weight = "bold" if bold else "normal"
        size_css = f"font-size: {styles.scaled_pt(size)}pt;" if size else ""
        text_color = styles.get_dialog_text_color()
        lbl.setStyleSheet(f"color: {text_color}; font-weight: {weight}; {size_css} background: transparent;")
        lbl.setWordWrap(True)
        return lbl

    def _clear_details_layout(self):
        while self.details_layout.count():
            item = self.details_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_sub_layout_rec(item.layout())

    def _clear_sub_layout_rec(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_sub_layout_rec(child.layout())

    def _reload_list(self):
        self.list_widget.clear()
        for mod_id, name in db.get_all_modifications():
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, mod_id)
            self.list_widget.addItem(item)

    def _update_buttons(self):
        has_selection = self.list_widget.currentItem() is not None
        self.btn_edit.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)

    def show_details(self, current, previous=None):
        self._update_buttons()
        self._clear_details_layout()

        if not current:
            self.details_layout.addWidget(
                self._plain_label("Выберите модификацию слева, чтобы увидеть нормативы.")
            )
            self.details_layout.addStretch(1)
            return

        mod_id = current.data(Qt.UserRole)
        mod = db.get_modification_by_id(mod_id)
        if not mod:
            return

        self.details_layout.addWidget(self._plain_label(f"Модификация - {mod['name']}", bold=True, size=12))
        self.details_layout.addWidget(self._plain_label("Нормативные требования для:", bold=True))

        section1, table1 = self._build_test_section(
            "Испытание 1:",
            "Зависимость объемной подачи от оборотов привода насоса ГУР, "
            "клапан ECO выкл (I = 0 A)",
            mod['norm_graph1_x'], mod['norm_graph1_min'], mod['norm_graph1_max'],
            "Обороты привода,\nоб/мин"
        )
        section2, table2 = self._build_test_section(
            "Испытание 2:",
            "Зависимость объемной подачи от оборотов привода насоса ГУР, "
            "клапан ECO вкл (I = 1 A)",
            mod['norm_graph2_x'], mod['norm_graph2_min'], mod['norm_graph2_max'],
            "Обороты привода,\nоб/мин"
        )
        section3, table3 = self._build_test_section(
            "Испытание 3:",
            "Зависимость объемной подачи от силы тока на управляющем клапане ECO",
            mod['norm_graph3_x'], mod['norm_graph3_min'], mod['norm_graph3_max'],
            "Сила тока, А", x_major_step=0.1
        )
        self.details_layout.addLayout(section1)
        self.details_layout.addLayout(section2)
        self.details_layout.addLayout(section3)

        # Все три таблицы - одной ширины (п.1 требований)
        max_table_width = max(table1.width(), table2.width(), table3.width())
        self._match_table_width(table1, max_table_width)
        self._match_table_width(table2, max_table_width)
        self._match_table_width(table3, max_table_width)

        self.details_layout.addWidget(self._plain_label("Испытание 4:", bold=True))
        self.details_layout.addWidget(
            self._plain_label("Максимальное давление срабатывания предохранительного клапана.")
        )
        self.details_layout.addWidget(self._plain_label(
            f"MIN давление: {mod['pressure_min']} бар<br>MAX давление: {mod['pressure_max']} бар"
        ))

        self.details_layout.addWidget(self._plain_label("Применяемые требования герметичности:", bold=True))
        seal_grid = QGridLayout()
        seal_grid.setHorizontalSpacing(10)
        seal_grid.setVerticalSpacing(2)
        text_color = styles.get_dialog_text_color()
        for row, key in enumerate(utils.SEAL_KEYS):
            label = QLabel(utils.SEAL_LABELS[key] + ":")
            label.setStyleSheet(f"color: {text_color}; background: transparent;")
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            value = QLabel(mod['seal_rules'].get(key, '—'))
            value.setStyleSheet(f"color: {text_color}; background: transparent;")
            value.setWordWrap(True)
            seal_grid.addWidget(label, row, 0)
            seal_grid.addWidget(value, row, 1)
        seal_grid.setColumnStretch(1, 1)
        self.details_layout.addLayout(seal_grid)

        self.details_layout.addStretch(1)
        # Перекрашиваем заново под текущую тему - при переключении между
        # модификациями это содержимое перестраивается с нуля (со
        # стилями "как в коде", т.е. всегда исходными тёмными), в обход
        # разовой перекраски, которая происходит только один раз при
        # самом открытии диалога
        styles.retheme_widget_tree(self)

    def _build_test_section(self, test_num_label, description, x_values, min_values, max_values,
                             x_label, x_major_step=None):
        section = QVBoxLayout()
        section.setSpacing(styles.scaled(4))
        section.addWidget(self._plain_label(test_num_label, bold=True))
        section.addWidget(self._plain_label(description))

        row = QHBoxLayout()
        row.setSpacing(styles.scaled(14))
        table = self._build_vertical_table(x_label, x_values, min_values, max_values)
        row.addWidget(table)
        row.addWidget(self._build_mini_chart(x_values, min_values, max_values, x_label, x_major_step))
        row.addStretch(1)
        section.addLayout(row)
        return section, table

    def _match_table_width(self, table, target_width):
        """Пропорционально растягивает/сжимает столбцы таблицы, чтобы её
        общая ширина точно совпала с target_width - используется, чтобы
        таблицы всех трёх испытаний были одной ширины (п.1 требований)."""
        col_count = table.columnCount()
        if col_count == 0:
            return
        current_cols_width = sum(table.columnWidth(c) for c in range(col_count))
        if current_cols_width == 0:
            return
        available = max(30 * col_count, target_width - 2)
        scale = available / current_cols_width
        for c in range(col_count):
            table.setColumnWidth(c, max(styles.scaled(30), int(table.columnWidth(c) * scale)))
        new_total = 2 + sum(table.columnWidth(c) for c in range(col_count))
        table.setFixedWidth(new_total)

    def _build_vertical_table(self, x_label, x_values, min_values, max_values):
        """Таблица испытания - X/MIN/MAX по столбцам, контрольные точки по
        строкам (та же ориентация, что и в PointsEditorWidget при
        редактировании модификации). Минимальные отступы в ячейках, без
        лишних полей по краям, без возможности изменения размера
        пользователем."""
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels([x_label, "MIN, л/мин", "MAX, л/мин"])
        table.setRowCount(len(x_values))
        table.verticalHeader().setVisible(False)
        table.setStyleSheet(f"""
            QTableWidget {{
                gridline-color: #b0b4b9;
                border: 1px solid #6b6f75;
                border-radius: 4px;
                background-color: #f0f0f0;
            }}
            QTableWidget::item {{
                padding: 0px;
            }}
            QHeaderView::section {{
                background-color: #3a3d42;
                color: #e8eaed;
                border: 1px solid #6b6f75;
                padding: {styles.scaled(1)}px {styles.scaled(4)}px;
            }}
        """)

        small_font = QFont()
        small_font.setPointSize(styles.scaled_pt(10))
        table.setFont(small_font)
        table.horizontalHeader().setFont(small_font)
        # Заголовок X-столбца обычно на 2 строки (например, "Обороты
        # привода,\nоб/мин") - специально, чтобы сжать ширину этого
        # столбца. Резервируем под заголовок высоту в 2 строки текста.
        header_line_height = QFontMetrics(small_font).lineSpacing()
        table.horizontalHeader().setFixedHeight(header_line_height * 2 + 8)

        cell_color = QColor("#1c1e21")
        for row, (x, mn, mx) in enumerate(zip(x_values, min_values, max_values)):
            for col, val in enumerate([x, mn, mx]):
                text = utils.format_number(val) if col == 0 else str(val)
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemIsEnabled)
                item.setTextAlignment(Qt.AlignCenter)
                item.setForeground(cell_color)
                table.setItem(row, col, item)

        table.resizeColumnsToContents()
        table.verticalHeader().setDefaultSectionSize(styles.scaled(20))
        table.resizeRowsToContents()
        min_col_width = styles.scaled(50)
        for c in range(table.columnCount()):
            table.setColumnWidth(c, max(min_col_width, table.columnWidth(c) + styles.scaled(2)))
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        total_width = 2
        for c in range(table.columnCount()):
            total_width += table.columnWidth(c)
        table.setFixedWidth(total_width)
        total_height = table.horizontalHeader().height() + 2
        for row in range(table.rowCount()):
            total_height += table.rowHeight(row)
        table.setFixedHeight(total_height)

        table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        return table

    def _build_mini_chart(self, x_values, min_values, max_values, x_label, x_major_step=None):
        """Минималистичный график норматива - только линии MIN/MAX и
        область между ними, без легенды и панели инструментов (только
        для наглядности).

        x_major_step - если задан, шаг делений оси X фиксируется этим
        значением (например, 0.1 для испытания 3 - чтобы совпадало с
        шагом значений в таблице), а не считается автоматически."""
        fig = Figure(figsize=(6.3, 3.6), dpi=100)
        fig.patch.set_alpha(0)
        ax = fig.add_subplot(111)
        ax.set_facecolor('none')
        ax.plot(x_values, min_values, color='#4fd1ff', linewidth=1.8)
        ax.plot(x_values, max_values, color='#4fd1ff', linewidth=1.8)
        ax.fill_between(x_values, min_values, max_values, color='#4fd1ff', alpha=0.2)
        graph_text_color = styles.get_dialog_text_color()
        ax.set_xlabel(x_label, fontsize=8, color=graph_text_color)
        ax.set_ylabel("Q, л/мин", fontsize=8, color=graph_text_color)
        ax.tick_params(labelsize=7.5, colors=graph_text_color)
        if x_major_step:
            ax.xaxis.set_major_locator(MultipleLocator(x_major_step))
        ax.grid(True, color=graph_text_color, alpha=0.15, linewidth=0.6)
        ax.set_axisbelow(True)  # сетка под линиями графика, а не поверх них
        for spine in ax.spines.values():
            spine.set_color('#6b6f75')
        fig.subplots_adjust(left=0.18, right=0.96, top=0.94, bottom=0.2)
        canvas = FigureCanvasQTAgg(fig)
        canvas.setFixedSize(475, 270)
        canvas.setStyleSheet("background: transparent;")
        return canvas

    def edit_selected(self):
        current = self.list_widget.currentItem()
        if not current:
            return
        mod_id = current.data(Qt.UserRole)
        mod = db.get_modification_by_id(mod_id)
        if not mod:
            return
        dialog = AddModificationDialog(self, existing_mod=mod)
        if dialog.exec_() != QDialog.Accepted:
            return
        data = dialog.get_data()
        try:
            db.update_modification(
                mod_id,
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
        except db_lock.DatabaseLockedError as e:
            GlowMessageDialog.show_error(self, "База данных занята", str(e))
            return
        self._reload_list()
        GlowMessageDialog.show_success(self, "Успех", f"Модификация «{data['name']}» обновлена.")

    def delete_selected(self):
        current = self.list_widget.currentItem()
        if not current:
            return
        mod_id = current.data(Qt.UserRole)
        name = current.text()
        linked_count = db.count_pumps_for_modification(mod_id)
        warning = ""
        if linked_count:
            warning = (
                f"\n\nС этой модификацией связано протоколов: {linked_count}. "
                "После удаления сами протоколы останутся в базе, но потеряют "
                "привязку к модификации."
            )
        if not GlowMessageDialog.confirm(
            self, "Подтверждение удаления",
            f"Удалить модификацию «{name}»?{warning}"
        ):
            return
        pwd_dialog = PasswordDialog(self, message="Для удаления модификации введите пароль:")
        if pwd_dialog.exec_() != QDialog.Accepted:
            return
        # Пароль уже проверен внутри диалога - если дошли сюда, значит верный
        try:
            db.delete_modification(mod_id)
        except db_lock.DatabaseLockedError as e:
            GlowMessageDialog.show_error(self, "База данных занята", str(e))
            return
        self._reload_list()
        self.show_details(None)
        self._update_buttons()


class RestoreBackupDialog(_GlowDialog):
    """Восстановление локальной базы данных из резервной копии - список
    доступных копий (см. db_sync.list_backups) с датой/временем,
    ревизией (если известна) и количеством насосов в каждой копии - для
    более уверенного выбора нужной, а не только по дате/ревизии."""
    def __init__(self, parent=None):
        super().__init__(parent, title="Восстановить из резервной копии")
        text_color = styles.get_dialog_text_color()

        hint_label = QLabel("Доступные резервные копии (сверху - самые новые):")
        hint_label.setStyleSheet(f"color: {text_color}; background: transparent; font-size: {styles.scaled_pt(11)}pt;")
        self.body_layout.addWidget(hint_label)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: #f0f0f0;
                color: #1c1e21;
                border: 1px solid #6b6f75;
                border-radius: 4px;
            }}
            QListWidget::item {{ padding: {styles.scaled(4)}px {styles.scaled(6)}px; }}
        """)
        self.list_widget.setMinimumSize(520, 300)

        self._reload_list()
        self.body_layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        restore_btn = QPushButton("Восстановить выбранную")
        restore_btn.setObjectName("chromeButton")
        restore_btn.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
        restore_btn.clicked.connect(self._on_restore_clicked)
        delete_btn = QPushButton("Удалить выбранную")
        delete_btn.setObjectName("chromeButton")
        delete_btn.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
        delete_btn.clicked.connect(self._on_delete_clicked)
        close_btn = QPushButton("Закрыть")
        close_btn.setObjectName("chromeButton")
        close_btn.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
        close_btn.clicked.connect(self.reject)
        btn_row.addWidget(restore_btn)
        btn_row.addWidget(delete_btn)
        btn_row.addWidget(close_btn)
        self.body_layout.addLayout(btn_row)

        self.setMinimumWidth(styles.scaled(560))
        self._lock_size(clamp_to_screen=True)

    def _reload_list(self):
        """Перечитывает список резервных копий с диска и заново
        заполняет виджет - используется и при первом открытии, и после
        удаления одной из копий (чтобы список сразу отразил изменение,
        без необходимости закрывать и открывать диалог заново)."""
        self.list_widget.clear()
        self._backups = db_sync.list_backups()
        if not self._backups:
            self.list_widget.addItem(QListWidgetItem("Резервных копий пока нет."))
            return
        for full_path, created_at, revision_display, source, is_manual, pump_count in self._backups:
            when = created_at.strftime('%d.%m.%Y %H:%M')
            rev_text = f"ревизия {revision_display}" if revision_display else "ревизия неизвестна (старый формат)"
            count_text = f", насосов: {pump_count}" if pump_count is not None else ""
            # Сетевые копии (см. db_sync._backup_network_copy - создаются
            # перед принудительной полной заменой сети локальной копией)
            # и копии, созданные вручную (см. db_sync.create_manual_backup) -
            # помечаем отдельно, чтобы не перепутать с обычными
            # автоматическими копиями локальной базы
            source_label = " · сетевая копия" if source == 'network' else ""
            manual_label = " · создано вручную" if is_manual else ""
            self.list_widget.addItem(
                QListWidgetItem(f"{when} - {rev_text}{count_text}{source_label}{manual_label}")
            )

    def _on_restore_clicked(self):
        row = self.list_widget.currentRow()
        if row < 0 or not self._backups:
            GlowMessageDialog.show_error(self, "Восстановление", "Сначала выберите резервную копию из списка.")
            return

        full_path, created_at, revision_display, source, is_manual, pump_count = self._backups[row]
        when = created_at.strftime('%d.%m.%Y %H:%M')
        rev_text = f"ревизия {revision_display}" if revision_display else "ревизия неизвестна"
        source_text = " (сетевая копия)" if source == 'network' else ""
        count_text = f", насосов в копии: {pump_count}" if pump_count is not None else ""
        if not GlowMessageDialog.confirm(
            self, "Подтверждение восстановления",
            f"Восстановить локальную базу данных из копии {when} ({rev_text}{count_text}){source_text}?\n\n"
            "Текущее состояние локальной базы будет заменено - все "
            "изменения, сделанные после этой копии, будут потеряны, если "
            "они не выгружены в сеть."
        ):
            return

        status, message = db_sync.restore_backup(full_path)
        if status == 'restored':
            GlowMessageDialog.show_success(self, "Восстановление", message)
            self.accept()
        else:
            GlowMessageDialog.show_error(self, "Восстановление", message)

    def _on_delete_clicked(self):
        row = self.list_widget.currentRow()
        if row < 0 or not self._backups:
            GlowMessageDialog.show_error(self, "Удаление копии", "Сначала выберите резервную копию из списка.")
            return

        full_path, created_at, revision_display, source, is_manual, pump_count = self._backups[row]
        when = created_at.strftime('%d.%m.%Y %H:%M')
        if not GlowMessageDialog.confirm(
            self, "Подтверждение удаления",
            f"Удалить резервную копию от {when} безвозвратно?\n\n"
            "Это действие нельзя отменить - сам файл резервной копии "
            "будет удалён с диска."
        ):
            return

        if db_sync.delete_backup(full_path):
            self._reload_list()
        else:
            GlowMessageDialog.show_error(self, "Удаление копии", "Не удалось удалить файл резервной копии.")

class KnownUsersDialog(_GlowDialog):
    """Список всех пользователей, когда-либо подключавшихся к сетевой
    базе данных - см. db_sync.get_known_users(). Отдельный лёгкий файл
    в сетевой папке, не в самой синхронизируемой базе (иначе статус
    "синхронизировано" дёргался бы при каждом отклике присутствия)."""
    def __init__(self, parent=None):
        super().__init__(parent, title="Пользователи сетевой базы")
        text_color = styles.get_dialog_text_color()

        hint_label = QLabel("Все, кто когда-либо подключался к сетевой базе:")
        hint_label.setStyleSheet(f"color: {text_color}; background: transparent; font-size: {styles.scaled_pt(11)}pt;")
        self.body_layout.addWidget(hint_label)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: #f0f0f0;
                color: #1c1e21;
                border: 1px solid #6b6f75;
                border-radius: 4px;
            }}
            QListWidget::item {{ padding: {styles.scaled(4)}px {styles.scaled(6)}px; }}
        """)
        self.list_widget.setMinimumSize(460, 280)

        users = db_sync.get_known_users()
        if not users:
            self.list_widget.addItem(QListWidgetItem(
                "Список пуст - либо сетевой режим не используется, либо "
                "ещё никто не подключался."
            ))
        else:
            for user, first_seen, last_seen in users:
                item = QListWidgetItem(f"{user}\nПервое подключение: {first_seen}\nПоследнее: {last_seen}")
                self.list_widget.addItem(item)
        self.body_layout.addWidget(self.list_widget)

        close_btn = QPushButton("Закрыть")
        close_btn.setObjectName("chromeButton")
        close_btn.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
        close_btn.clicked.connect(self.accept)
        self.body_layout.addWidget(close_btn)

        self.setMinimumWidth(styles.scaled(500))
        self._lock_size(clamp_to_screen=True)


class ChangeLogDialog(_GlowDialog):
    """Журнал последних изменений базы данных - список действий с датой
    и временем (см. database.get_recent_changes, database.bump_revision -
    там же и заполняется, при каждой операции записи). Хранится только
    последние database._CHANGE_LOG_KEEP_COUNT записей - старые
    автоматически вытесняются."""
    def __init__(self, parent=None):
        super().__init__(parent, title="Журнал изменений базы данных")
        text_color = styles.get_dialog_text_color()

        hint_label = QLabel(f"Последние {db._CHANGE_LOG_KEEP_COUNT} изменений (сверху - самые новые):")
        hint_label.setStyleSheet(f"color: {text_color}; background: transparent; font-size: {styles.scaled_pt(11)}pt;")
        self.body_layout.addWidget(hint_label)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: #f0f0f0;
                color: #1c1e21;
                border: 1px solid #6b6f75;
                border-radius: 4px;
            }}
            QListWidget::item {{ padding: {styles.scaled(4)}px {styles.scaled(6)}px; }}
        """)
        self.list_widget.setMinimumSize(480, 320)

        changes = db.get_recent_changes()
        if not changes:
            item = QListWidgetItem("Изменений пока не зафиксировано.")
            self.list_widget.addItem(item)
        else:
            for timestamp, description, revision in changes:
                when = timestamp
                if timestamp:
                    date_part, _, time_part = timestamp.partition('T')
                    when = f"{utils.format_date_display(date_part)} {time_part[:5]}"
                rev_display = db.format_revision_display(revision) if revision else "—"
                item = QListWidgetItem(f"{when}  (rev. {rev_display})\n{description or ''}")
                self.list_widget.addItem(item)
        self.body_layout.addWidget(self.list_widget)

        close_btn = QPushButton("Закрыть")
        close_btn.setObjectName("chromeButton")
        close_btn.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
        close_btn.clicked.connect(self.accept)
        self.body_layout.addWidget(close_btn)

        self.setMinimumWidth(styles.scaled(520))
        self._lock_size(clamp_to_screen=True)


class DatabaseLocationDialog(_GlowDialog):
    """Диалог выбора расположения базы данных - локальный ПК (по
    умолчанию, поведение как и всегда) или общая сетевая папка, плюс
    отдельный флаг "полный офлайн" - для тех, кто сознательно всегда
    работает только со своей локальной копией, даже если у остальных в
    группе включён сетевой режим."""
    def __init__(self, parent=None):
        super().__init__(parent, title="Расположение базы данных")

        text_color = styles.get_dialog_text_color()
        label_style = f"color: {text_color}; background: transparent; font-size: {styles.scaled_pt(11.5)}pt;"

        mode_label = QLabel("Режим работы с базой:")
        mode_label.setStyleSheet(label_style)
        self.body_layout.addWidget(mode_label)

        self.radio_local = QRadioButton("Локальный файл на этом ПК")
        self.radio_network = QRadioButton("Общая сетевая папка")
        for radio in (self.radio_local, self.radio_network):
            radio.setStyleSheet(f"color: {text_color}; background: transparent; font-size: {styles.scaled_pt(11)}pt;")
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.radio_local)
        self.mode_group.addButton(self.radio_network)
        self.body_layout.addWidget(self.radio_local)
        self.body_layout.addWidget(self.radio_network)

        self.body_layout.addSpacing(14)

        def path_row(label_text, initial_value):
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setStyleSheet(label_style)
            lbl.setFixedWidth(styles.scaled(160))
            field = QLineEdit(initial_value)
            field.setStyleSheet(styles.get_password_input_style())
            browse_btn = QPushButton("Обзор...")
            browse_btn.setObjectName("chromeButton")
            browse_btn.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
            row.addWidget(lbl)
            row.addWidget(field, 1)
            row.addWidget(browse_btn)
            self.body_layout.addLayout(row)
            return field, browse_btn

        self.local_path_field, local_browse = path_row(
            "Локальный файл:", db_settings.get_local_db_path()
        )
        self.network_path_field, network_browse = path_row(
            "Сетевой файл:", db_settings.get_network_db_path()
        )
        self.backup_path_field, backup_browse = path_row(
            "Папка резервных копий:", db_settings.get_backup_path()
        )

        local_browse.clicked.connect(lambda: self._browse_file(self.local_path_field))
        network_browse.clicked.connect(lambda: self._browse_file(self.network_path_field))
        backup_browse.clicked.connect(lambda: self._browse_folder(self.backup_path_field))

        self.body_layout.addSpacing(14)

        self.offline_checkbox = QCheckBox("Полный офлайн-режим (не проверять сетевую базу вообще)")
        self.offline_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {text_color};
                background: transparent;
                font-size: {styles.scaled_pt(11)}pt;
                spacing: {styles.scaled(8)}px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid #6b6f75;
                border-radius: 4px;
                background: #f0f0f0;
            }}
            QCheckBox::indicator:checked {{
                background: {styles.get_accent_color_hex()};
                border: 1px solid {styles.get_accent_color_hex()};
            }}
        """)
        self.body_layout.addWidget(self.offline_checkbox)

        hint_label = QLabel(
            "Полный офлайн-режим полезен, если вы сознательно всегда\n"
            "работаете только со своей локальной копией базы, даже если\n"
            "остальные в группе используют общую сетевую папку."
        )
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet(f"color: {text_color}; background: transparent; font-size: {styles.scaled_pt(9.5)}pt;")
        self.body_layout.addWidget(hint_label)

        # Заполняем текущим состоянием
        if db_settings.get_db_mode() == db_settings.MODE_NETWORK:
            self.radio_network.setChecked(True)
        else:
            self.radio_local.setChecked(True)
        self.offline_checkbox.setChecked(db_settings.is_full_offline_mode())

        self.body_layout.addSpacing(18)
        btn_row = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("chromeButton")
        save_btn.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
        save_btn.clicked.connect(self.save_and_close)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("chromeButton")
        cancel_btn.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        self.body_layout.addLayout(btn_row)

        self.setMinimumWidth(styles.scaled(460))
        self._lock_size()

    def _browse_file(self, field):
        path, _ = QFileDialog.getSaveFileName(
            self, "Выберите файл базы данных", field.text(), "SQLite (*.db)"
        )
        if path:
            field.setText(path)

    def _browse_folder(self, field):
        path = QFileDialog.getExistingDirectory(self, "Выберите папку", field.text())
        if path:
            field.setText(path)

    def save_and_close(self):
        new_mode = db_settings.MODE_NETWORK if self.radio_network.isChecked() else db_settings.MODE_LOCAL
        new_full_offline = self.offline_checkbox.isChecked()

        if new_mode == db_settings.MODE_NETWORK and not self.network_path_field.text().strip():
            GlowMessageDialog.show_error(
                self, "Ошибка",
                "Для сетевого режима нужно указать путь к сетевому файлу базы."
            )
            return

        # Если сетевой режим СЕЙЧАС активен, а после сохранения новых
        # настроек перестанет быть активным (переключение на локальный
        # режим или включение "полного офлайна") - убираем за собой
        # метку присутствия, пока настройки ещё не перезаписаны (иначе
        # remove_presence() искала бы уже в НОВОЙ сетевой папке, а не в
        # той, которую мы на самом деле покидаем)
        was_network_active = db_settings.is_network_mode_active()
        will_be_network_active = (
            new_mode == db_settings.MODE_NETWORK
            and bool(self.network_path_field.text().strip())
            and not new_full_offline
        )
        if was_network_active and not will_be_network_active:
            db_sync.remove_presence()

        db_settings.set_db_mode(new_mode)
        db_settings.set_local_db_path(self.local_path_field.text().strip())
        db_settings.set_network_db_path(self.network_path_field.text().strip())
        db_settings.set_backup_path(self.backup_path_field.text().strip())
        db_settings.set_full_offline_mode(new_full_offline)

        # Применяем сразу, без перезапуска программы - MainWindow делает
        # то же самое, что происходит при обычном старте (сверка/
        # копирование сетевой версии, обновление индикатора, перезагрузка
        # списка насосов). hasattr - на всякий случай, если этот диалог
        # вдруг откроют из контекста без такого метода у родителя.
        main_window = self.parent()
        if main_window is not None and hasattr(main_window, 'apply_db_settings_change'):
            sync_status, sync_message = main_window.apply_db_settings_change()
            if sync_message:
                if sync_status == 'network_unreachable':
                    GlowMessageDialog.show_error(self, "База данных", sync_message)
                else:
                    GlowMessageDialog.show_success(self, "База данных", sync_message)
            else:
                GlowMessageDialog.show_success(
                    self, "Сохранено",
                    "Настройки расположения базы данных сохранены и применены."
                )
        else:
            GlowMessageDialog.show_success(
                self, "Сохранено",
                "Настройки расположения базы данных сохранены.\n"
                "Изменения вступят в силу после перезапуска программы."
            )
        self.accept()


class SettingsDialog(_GlowDialog):
    """Меню настроек: управление модификациями насосов."""
    def __init__(self, parent=None):
        super().__init__(parent, title="Настройки")
        # Боковые отступы шире, чем у остальных диалогов - только здесь
        left, top, right, bottom = self.frame_layout.getContentsMargins()
        self.frame_layout.setContentsMargins(left + 10, top, right + 10, bottom)

        # Крупнее шрифт и отступы кнопок, чем стандартный chromeButton -
        # добавляем сверху ту же шапку стиля, но с более крупными числами
        big_button_style = styles.LEFT_PANEL_RESET_BTN_STYLE + f"""
            QPushButton#chromeButton {{
                font-size: {styles.scaled_pt(11.5)}pt;
                padding: {styles.scaled(9)}px {styles.scaled(16)}px;
            }}
        """

        def make_btn(text, slot):
            btn = QPushButton(text)
            btn.setObjectName("chromeButton")
            btn.setStyleSheet(big_button_style)
            btn.clicked.connect(slot)
            return btn

        # Блок 1: расположение базы данных (локальный ПК / сетевая папка)
        db_label = QLabel("База данных:")
        db_label.setStyleSheet(f"color: #e8eaed; background: transparent; font-size: {styles.scaled_pt(11.5)}pt;")
        self.body_layout.addWidget(db_label)
        self.body_layout.addWidget(make_btn("Расположение базы данных", self.open_database_location))
        self.body_layout.addWidget(make_btn("Журнал изменений базы данных", self.open_change_log))
        self.body_layout.addWidget(make_btn("Восстановить из резервной копии", self.open_restore_backup))
        self.body_layout.addWidget(make_btn("Пользователи сетевой базы", self.open_known_users))

        self.body_layout.addSpacing(22)

        # Блок 2: управление модификациями
        mod_label = QLabel("Модификации насосов ГУР:")
        mod_label.setStyleSheet(f"color: #e8eaed; background: transparent; font-size: {styles.scaled_pt(11.5)}pt;")
        self.body_layout.addWidget(mod_label)
        self.body_layout.addWidget(make_btn("Добавить модификацию", self.open_add_modification))
        self.body_layout.addWidget(make_btn("Просмотреть модификации", self.open_view_modifications))

        # Явный разделительный отступ - зрительно отделяет управление
        # модификациями от служебных действий (инструкция/закрытие)
        self.body_layout.addSpacing(22)

        # Блок 3: настройки интерфейса - пока только размытие фона за
        # диалогами; при добавлении переключателя темы в будущем стоит
        # сделать по тому же принципу (QCheckBox + QSettings)
        interface_label = QLabel("Интерфейс:")
        interface_label.setStyleSheet(f"color: #e8eaed; background: transparent; font-size: {styles.scaled_pt(11.5)}pt;")
        self.body_layout.addWidget(interface_label)

        self.blur_checkbox = QCheckBox("Размытие фона за диалогами")
        self.blur_checkbox.setChecked(_DialogBackgroundManager.enabled)
        self.blur_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: #e8eaed;
                background: transparent;
                font-size: {styles.scaled_pt(11)}pt;
                spacing: {styles.scaled(8)}px;
            }}
            QCheckBox::indicator {{
                width: {styles.scaled(18)}px;
                height: {styles.scaled(18)}px;
                border: 1px solid #6b6f75;
                border-radius: 4px;
                background: #f0f0f0;
            }}
            QCheckBox::indicator:checked {{
                background: #4fd1ff;
                border: 1px solid #4fd1ff;
            }}
        """)
        self.blur_checkbox.toggled.connect(_DialogBackgroundManager.set_enabled)
        self.body_layout.addWidget(self.blur_checkbox)

        self.body_layout.addSpacing(22)

        # Блок 4: служебные действия
        self.body_layout.addWidget(make_btn("Инструкция", self.open_instructions))
        self.body_layout.addWidget(make_btn("Обратная связь", self.open_feedback_email))
        self.body_layout.addWidget(make_btn("Закрыть", self.accept))

        self.body_layout.addSpacing(14)
        version_label = QLabel(f"Версия {version.VERSION}")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet(f"color: #8a8f96; background: transparent; font-size: {styles.scaled_pt(9.5)}pt;")
        self.body_layout.addWidget(version_label)

        self.setMinimumWidth(styles.scaled(340))
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
        self.hide()
        dialog = InstructionsDialog(self.parent())
        dialog.exec_()
        self.show()

    def open_feedback_email(self):
        """Открывает почтовый клиент пользователя (через обычную ссылку
        mailto:) с уже заполненной темой и телом письма - версия
        программы, локальная ревизия базы и сетевая ревизия (если
        сетевой режим активен и сеть сейчас доступна). Не отправляет
        ничего само - просто открывает то приложение, которое у
        пользователя на компьютере зарегистрировано как обработчик
        mailto: (Outlook, стандартная почта Windows и т.п.), с уже
        заполненными полями - без какой-либо серверной инфраструктуры
        отправки писем."""
        local_revision = db.get_current_revision()
        local_revision_display = db.format_revision_display(local_revision)

        network_revision_display = "сетевой режим не используется"
        if db_settings.is_network_mode_active():
            if db_sync.is_network_reachable():
                network_revision = db_sync.get_network_revision_now()
                network_revision_display = (
                    db.format_revision_display(network_revision)
                    if network_revision is not None else "не удалось прочитать"
                )
            else:
                network_revision_display = "сеть сейчас недоступна"

        subject = f"PumpTestApp - обратная связь (версия {version.VERSION})"
        body = (
            f"Версия программы: {version.VERSION}\n"
            f"Локальная ревизия базы: {local_revision_display}\n"
            f"Сетевая ревизия базы: {network_revision_display}\n"
            "\n"
            "Опишите, пожалуйста, вопрос или проблему ниже:\n\n"
        )

        url = QUrl("mailto:alexey.luschin@nami.ru")
        query = QUrlQuery()
        query.addQueryItem("subject", subject)
        query.addQueryItem("body", body)
        query.addQueryItem("bcc", "lushin.alexey@live.com")
        url.setQuery(query)
        QDesktopServices.openUrl(url)

    def open_add_modification(self):
        self.hide()
        dialog = AddModificationDialog(self.parent())
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            # Пароль уже проверен внутри диалога (try_accept) - если дошли
            # сюда, значит он верный
            try:
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
            except db_lock.DatabaseLockedError as e:
                GlowMessageDialog.show_error(self, "База данных занята", str(e))
                self.show()
                return
            GlowMessageDialog.show_success(self.parent(), "Успех", f"Модификация «{data['name']}» сохранена.")
        self.show()

    def open_view_modifications(self):
        self.hide()
        dialog = ViewModificationsDialog(self.parent())
        dialog.exec_()
        self.show()

    def open_database_location(self):
        self.hide()
        dialog = DatabaseLocationDialog(self.parent())
        dialog.exec_()
        self.show()

    def open_change_log(self):
        self.hide()
        dialog = ChangeLogDialog(self.parent())
        dialog.exec_()
        self.show()

    def open_known_users(self):
        self.hide()
        dialog = KnownUsersDialog(self.parent())
        dialog.exec_()
        self.show()

    def open_restore_backup(self):
        self.hide()
        dialog = RestoreBackupDialog(self.parent())
        if dialog.exec_() == QDialog.Accepted:
            # Локальный файл базы был заменён - перезагружаем данные и
            # статус-бар во всей программе, раз это применимо
            main_window = self.parent()
            if main_window is not None and hasattr(main_window, 'left_panel'):
                db.init_db()
                main_window.left_panel.load_data()
                if hasattr(main_window, 'update_status'):
                    main_window.update_status()
        self.show()


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
        SPACING = 7
        CHIP_PAD = 8 * 2 + 3  # внутренние отступы чипа (см. compact_field)
        arrow_path = os.path.join(ICONS_DIR, 'dropdown_arrow.svg').replace('\\', '/')
        INPUT_STYLE = (
            "QLineEdit, QComboBox, QDateEdit { "
            "background-color: #f0f0f0; color: #1c1e21; "
            f"border: 1px solid #6b6f75; border-radius: 4px; padding: {styles.scaled(1)}px {styles.scaled(6)}px; }}"
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
            box.setContentsMargins(styles.scaled(8), styles.scaled(3), styles.scaled(8), styles.scaled(3))
            box.setSpacing(styles.scaled(3))
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
        styles.apply_calendar_style(self.date_input.calendarWidget())
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
        self.tests_column.setSpacing(styles.scaled(22))
        self.extra_column = QVBoxLayout()   # проверка на герметичность
        self.extra_column.setSpacing(styles.scaled(4))
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
            f"background-color: #f0f0f0; color: #1c1e21; padding: {styles.scaled(2)}px {styles.scaled(6)}px; }}"
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
        pressure_col.setSpacing(styles.scaled(2))
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
            f"background-color: #f0f0f0; color: #1c1e21; padding: {styles.scaled(2)}px {styles.scaled(6)}px; }}"
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
            row.setSpacing(styles.scaled(6))
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
        # Эти виджеты (условия испытаний, герметичность) строятся
        # заново при каждом выборе модификации - со стилями "как в
        # коде" (исходно тёмными). Перекрашиваем сразу под текущую тему.
        styles.retheme_widget_tree(self)

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
                padding: {styles.scaled(2)}px {styles.scaled(6)}px;
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
            table.setColumnWidth(c, max(styles.scaled(30), int(table.columnWidth(c) * scale)))
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
        table.setStyleSheet(f"""
            QTableWidget {{
                gridline-color: #b0b4b9;
                border: 1px solid #6b6f75;
                border-radius: 4px;
                background-color: #f0f0f0;
            }}
            QTableWidget::item {{
                padding: {styles.scaled(1)}px;
            }}
            QTableWidget::item:hover {{
                background-color: #d6f3ff;
            }}
            QTableWidget::item:selected {{
                background-color: #bdeeff;
                color: #1c1e21;
            }}
            QHeaderView::section {{
                background-color: #3a3d42;
                color: #e8eaed;
                border: 1px solid #6b6f75;
                padding: {styles.scaled(2)}px {styles.scaled(6)}px;
            }}
        """)

        cell_text_color = QColor("#1c1e21")  # тёмный текст - на светлом фоне ячеек читается всегда
        for i, x in enumerate(x_values):
            x_item = QTableWidgetItem(utils.format_number(x))
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
        small_font.setPointSize(styles.scaled_pt(10))
        table.setFont(small_font)
        table.verticalHeader().setFont(small_font)
        table.resizeRowsToContents()
        table.resizeColumnsToContents()
        min_section = styles.scaled(55)
        for c in range(table.columnCount()):
            table.setColumnWidth(c, max(min_section, table.columnWidth(c) + styles.scaled(4)))
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

        if not self.order_input.text().strip():
            fix_it = GlowMessageDialog.confirm(
                self, "Внимание", "Вы не указали номер заказа.",
                yes_text="Исправить", no_text="Оставить без номера"
            )
            if fix_it:
                return
            # Оставляем без номера - автоматически присваиваем "Б/Н",
            # чтобы такие насосы группировались в собственную "Б/Н"
            # статистику наравне с остальными заказами
            self.order_input.setText("Б/Н")

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


class EditPumpDialog(_GlowDialog):
    """Комплексное редактирование существующего протокола - визуально в
    том же стиле, что и AddPumpDialog. Изменённые (относительно исходных)
    значения выделяются жирным оранжевым шрифтом. Идентификационный номер
    насоса не меняется - показывается как справочная информация."""

    _LEAK_OPTIONS = ["Отсутствуют", "Каплепадение", "Подтекание", "Иное"]
    _OIL_OPTIONS = [
        "Отсутствуют", "Присутствуют в допускаемой степени",
        "Присутствуют в чрезмерном объёме", "Иное"
    ]
    _CHANGED_COLOR = QColor("#cc6600")  # жирный оранжевый - изменённое значение
    _NORMAL_COLOR = QColor("#1c1e21")

    def __init__(self, pump_data, parent=None):
        pump_number = pump_data.get('pump_number')
        super().__init__(
            parent, title=f"Редактирование протокола - образец № {pump_number}",
            glow_color=(255, 140, 0)  # оранжевый вместо стандартного бирюзового (п.1)
        )
        self.pump_data = pump_data
        self.selected_mod = None
        self.value_tables = {}
        self.seal_inputs = {}
        self._seal_originals = {}
        # Исходные значения - используются при перестроении таблиц (смена
        # модификации), чтобы не терять уже введённые результаты испытаний,
        # и как эталон для подсветки изменённых значений
        self.original_results = dict(pump_data.get('results_json') or {})
        self.original_seal = dict(pump_data.get('seal_results_json') or {})

        self.mods = db.get_all_modifications()

        info_label = QLabel(f"Идентификационный № насоса: {pump_number}")
        info_label.setStyleSheet("color: #e8eaed; background: transparent;")
        self.body_layout.addWidget(info_label)

        SPACING = 7
        CHIP_PAD = 8 * 2 + 3
        arrow_path = os.path.join(ICONS_DIR, 'dropdown_arrow.svg').replace('\\', '/')
        # Эффекты наведения здесь оранжевые (не бирюзовые, как в остальных
        # диалогах) - п.6 требований
        INPUT_STYLE = (
            "QLineEdit, QComboBox, QDateEdit { "
            "background-color: #f0f0f0; color: #1c1e21; "
            f"border: 1px solid #6b6f75; border-radius: 4px; padding: {styles.scaled(1)}px {styles.scaled(6)}px; }}"
            "QLineEdit:hover, QComboBox:hover, QDateEdit:hover, "
            "QLineEdit:focus, QComboBox:focus, QDateEdit:focus { "
            "border: 1px solid #ff8c00; }"
            "QComboBox::drop-down, QDateEdit::drop-down { border: none; }"
            f"QComboBox::down-arrow, QDateEdit::down-arrow {{ "
            f"image: url({arrow_path}); width: 10px; height: 10px; }}"
        )

        def compact_field(label_text, widget, field_width):
            chip = QFrame()
            chip.setStyleSheet(styles.LEFT_PANEL_CHIP_STYLE)
            box = QHBoxLayout(chip)
            box.setContentsMargins(styles.scaled(8), styles.scaled(3), styles.scaled(8), styles.scaled(3))
            box.setSpacing(styles.scaled(3))
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #e8eaed; background: transparent;")
            widget.setFixedWidth(field_width)
            widget.setStyleSheet(INPUT_STYLE)
            box.addWidget(lbl)
            box.addWidget(widget)
            return chip

        # Строка 1: № насоса (только чтение, справочно) + Модификация
        self.mod_combo = QComboBox()
        current_index = 0
        for i, (mod_id, name) in enumerate(self.mods):
            self.mod_combo.addItem(name, mod_id)
            if mod_id == pump_data.get('modification_id'):
                current_index = i

        # Строка 2: № заказа + Дата проверки + Тип проверки
        FIELD_W_ROW2 = 90
        self.order_input = QLineEdit()
        order_num = pump_data.get('order_number')
        if order_num:
            self.order_input.setText(utils.format_order_number(order_num))

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        styles.apply_calendar_style(self.date_input.calendarWidget())
        existing_date = pump_data.get('test_date') or ''
        if existing_date and ' ' in existing_date:
            existing_date = existing_date.split(' ')[0]
        qdate = QDate.fromString(existing_date, 'yyyy-MM-dd')
        self.date_input.setDate(qdate if qdate.isValid() else QDate.currentDate())

        self.type_combo = QComboBox()
        self.type_combo.addItems(["первичная", "повторная"])
        idx = self.type_combo.findText(pump_data.get('test_type') or 'первичная')
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)

        chip_order = compact_field("№ заказа:", self.order_input, FIELD_W_ROW2)
        chip_date = compact_field("Дата проверки:", self.date_input, FIELD_W_ROW2)
        chip_type = compact_field("Тип проверки:", self.type_combo, FIELD_W_ROW2)
        ROW2_SPACING = 4  # меньше, чем SPACING строки 1 - плотнее группирует 3 поля
        row2_total = (
            chip_order.sizeHint().width() + chip_date.sizeHint().width()
            + chip_type.sizeHint().width() + 2 * ROW2_SPACING
        )

        trial_w = 150
        chip_pump = compact_field("№ насоса:", QLineEdit(str(pump_number)), trial_w)
        chip_pump.findChild(QLineEdit).setReadOnly(True)
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
        row2.addSpacing(ROW2_SPACING)
        row2.addWidget(chip_date)
        row2.addSpacing(ROW2_SPACING)
        row2.addWidget(chip_type)
        row2.addStretch(1)
        self.body_layout.addLayout(row2)

        self.values_widget = QWidget()
        self.values_main_layout = QVBoxLayout(self.values_widget)
        self.values_main_layout.setContentsMargins(0, 0, 0, 0)
        self.tests_column = QVBoxLayout()
        self.tests_column.setSpacing(styles.scaled(22))
        self.extra_column = QVBoxLayout()
        self.extra_column.setSpacing(styles.scaled(4))
        self.values_main_layout.addLayout(self.tests_column)
        self.values_main_layout.addSpacing(18)
        self.values_main_layout.addLayout(self.extra_column)
        self.body_layout.addWidget(self.values_widget)

        note_row = QHBoxLayout()
        self.note_label = QLabel("Примечание:")
        self.note_label.setStyleSheet("color: #e8eaed; background: transparent;")
        note_row.addWidget(self.note_label)
        self.note_input = QLineEdit()
        self.note_input.setText(pump_data.get('note', '') or '')
        self.note_input.setStyleSheet(
            "QLineEdit { border: 1px solid #6b6f75; border-radius: 6px; "
            f"background-color: #f0f0f0; color: #1c1e21; padding: {styles.scaled(2)}px {styles.scaled(6)}px; }}"
            "QLineEdit:hover, QLineEdit:focus { border: 1px solid #ff8c00; }"
        )
        note_row.addWidget(self.note_input)
        note_row.addStretch(1)
        self.body_layout.addLayout(note_row)

        # Отступ перед паролем, чтобы он визуально не сливался с примечанием (п.3)
        self.body_layout.addSpacing(16)

        password_row = QHBoxLayout()
        password_row.addStretch(1)
        password_label = QLabel("Пароль для сохранения:")
        password_label.setStyleSheet(
            "color: #e8eaed; font-weight: bold; background: transparent;"
        )
        password_row.addWidget(password_label)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedWidth(styles.scaled(120))
        self.password_input.setStyleSheet(
            "QLineEdit { background-color: #f0f0f0; color: #1c1e21; "
            f"border: 1px solid #6b6f75; border-radius: 4px; padding: {styles.scaled(2)}px {styles.scaled(6)}px; }}"
            "QLineEdit:hover, QLineEdit:focus { border: 1px solid #ff8c00; }"
        )
        self.password_input.returnPressed.connect(self.try_accept)
        setup_password_field(self.password_input, icon_color="#1c1e21")
        password_row.addWidget(self.password_input)
        password_row.addStretch(1)
        self.body_layout.addLayout(password_row)

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

        self.mod_combo.setCurrentIndex(current_index)
        self.mod_combo.currentIndexChanged.connect(self.on_modification_changed)
        if self.mods:
            self.on_modification_changed(current_index)
        else:
            GlowMessageDialog.show_error(
                self, "Нет модификаций",
                "В базе нет ни одной модификации. Сначала добавьте модификацию через Настройки → Добавить модификацию."
            )

        self._lock_size(clamp_to_screen=True)

    def on_modification_changed(self, index):
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
            self.selected_mod['norm_graph1_x'], "Обороты, об/мин", 5
        )
        _, self.value_tables['test2'] = self._build_value_table(
            "Испытание 2:\nЗависимость объемной подачи от оборотов привода насоса ГУР\n"
            "клапан ECO включен, I = 1 A",
            self.selected_mod['norm_graph2_x'], "Обороты, об/мин", 13
        )
        _, self.value_tables['test3'] = self._build_value_table(
            "Испытание 3:\nЗависимость объемной подачи от управляющего сигнала на клапане ECO\n"
            "клапан ECO выключен, I = 0 A",
            self.selected_mod['norm_graph3_x'], "Сила тока, А", 21
        )
        self._match_table_width(
            self.value_tables['test3'],
            self.value_tables['test1'].width(),
            self.value_tables['test1'].verticalHeader().width()
        )

        table_width = self.value_tables['test1'].width()

        pressure_col = QVBoxLayout()
        pressure_col.setSpacing(styles.scaled(2))
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

        line2_w = line2_label.sizeHint().width()
        line3_label_w = line3_label.sizeHint().width()
        PRESSURE_SPACING = 8
        input_w = max(60, line2_w - line3_label_w - PRESSURE_SPACING)

        self.pressure_input = QLineEdit()
        self.pressure_input.setFixedWidth(input_w)
        self.pressure_input.setStyleSheet(
            "QLineEdit { border: 1px solid #6b6f75; border-radius: 6px; "
            f"background-color: #f0f0f0; color: #1c1e21; padding: {styles.scaled(2)}px {styles.scaled(6)}px; }}"
            "QLineEdit:hover, QLineEdit:focus { border: 1px solid #ff8c00; }"
        )
        existing_pressure = self.original_results.get('g32')
        self._pressure_original = (
            str(int(existing_pressure)) if existing_pressure is not None else ''
        )
        if existing_pressure is not None:
            self.pressure_input.setText(self._pressure_original)
        self.pressure_input.textChanged.connect(self._on_pressure_changed)

        pressure_row = QHBoxLayout()
        pressure_row.setSpacing(PRESSURE_SPACING)
        pressure_row.addWidget(line3_label)
        pressure_row.addWidget(self.pressure_input)
        pressure_row.addStretch()
        pressure_col.addLayout(pressure_row)
        self.tests_column.addLayout(pressure_col)

        note_label_width = QFontMetrics(self.note_label.font()).horizontalAdvance("Примечание:") + 4
        self.note_input.setFixedWidth(max(80, table_width - note_label_width - 6))

        # Проверка на герметичность - те же выпадающие списки, что и в
        # AddPumpDialog (не свободный текст), с выбором исходного значения
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
            row.setSpacing(styles.scaled(6))
            lbl = QLabel(utils.SEAL_LABELS[key] + ":")
            lbl.setWordWrap(False)
            lbl.setFixedWidth(seal_label_w)
            lbl.setStyleSheet("color: #e8eaed; background: transparent;")
            row.addWidget(lbl)
            stored_value = self.original_seal.get(key) or self.selected_mod['seal_rules'].get(key, '')
            combo = self._make_seal_combo(key, stored_value)
            self._seal_originals[key] = stored_value
            combo.currentIndexChanged.connect(
                lambda _idx, k=key, c=combo: self._on_seal_changed(k, c)
            )
            row.addWidget(combo)
            row.addStretch(1)
            self.seal_inputs[key] = combo
            self.extra_column.addLayout(row)
        # Эти виджеты (условия испытаний, герметичность) строятся
        # заново при каждом выборе модификации - со стилями "как в
        # коде" (исходно тёмными). Перекрашиваем сразу под текущую тему.
        styles.retheme_widget_tree(self)

    def _make_seal_combo(self, key, stored_value):
        if key == 'g37':
            options, default_index = self._OIL_OPTIONS, 1
        else:
            options, default_index = self._LEAK_OPTIONS, 0
        combo = QComboBox()
        combo.addItems(options)
        idx = combo.findText(stored_value, Qt.MatchFixedString)
        combo.setCurrentIndex(idx if idx >= 0 else default_index)

        arrow_path = os.path.join(ICONS_DIR, 'dropdown_arrow.svg').replace('\\', '/')
        combo.setStyleSheet(f"""
            QComboBox {{
                background-color: #f0f0f0;
                color: #1c1e21;
                border: 1px solid #6b6f75;
                border-radius: 4px;
                padding: {styles.scaled(2)}px {styles.scaled(6)}px;
            }}
            QComboBox:hover, QComboBox:focus {{
                border: 1px solid #ff8c00;
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
                selection-background-color: #ffcc99;
                selection-color: #1c1e21;
                outline: none;
            }}
        """)

        longest = max(self._OIL_OPTIONS + self._LEAK_OPTIONS, key=len)
        text_width = QFontMetrics(combo.font()).horizontalAdvance(longest)
        combo.setFixedWidth(text_width + 45)
        return combo

    def _on_seal_changed(self, key, combo):
        """Подсвечивает выпадающий список жирным оранжевым, если значение
        отличается от исходного (сохранённого в протоколе)."""
        changed = combo.currentText() != self._seal_originals.get(key, '')
        weight = "bold" if changed else "normal"
        color = "#cc6600" if changed else "#1c1e21"
        combo.setStyleSheet(combo.styleSheet() + f"\nQComboBox {{ font-weight: {weight}; color: {color}; }}")

    def _on_pressure_changed(self, text):
        changed = text.strip() != self._pressure_original
        self.pressure_input.setStyleSheet(
            "QLineEdit { border: 1px solid #6b6f75; border-radius: 6px; "
            f"background-color: #f0f0f0; color: {'#cc6600' if changed else '#1c1e21'}; "
            f"font-weight: {'bold' if changed else 'normal'}; padding: {styles.scaled(2)}px {styles.scaled(6)}px; }}"
            "QLineEdit:hover, QLineEdit:focus { border: 1px solid #ff8c00; }"
        )

    def _clear_sub_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_sub_layout(child.layout())

    def _match_table_width(self, table, target_width, target_header_width=None):
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
            table.setColumnWidth(c, max(styles.scaled(30), int(table.columnWidth(c) * scale)))
        new_total = header_w + 2 + sum(table.columnWidth(c) for c in range(col_count))
        table.setFixedWidth(new_total)

    def _build_value_table(self, title, x_values, x_label, start_key):
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
        arrow_path = os.path.join(ICONS_DIR, 'dropdown_arrow.svg').replace('\\', '/')
        table.setStyleSheet(f"""
            QTableWidget {{
                gridline-color: #b0b4b9;
                border: 1px solid #6b6f75;
                border-radius: 4px;
                background-color: #f0f0f0;
            }}
            QTableWidget::item {{
                padding: {styles.scaled(1)}px;
            }}
            QTableWidget::item:hover {{
                background-color: #ffe0b3;
            }}
            QTableWidget::item:selected {{
                background-color: #ffd699;
                color: #1c1e21;
            }}
            QHeaderView::section {{
                background-color: #3a3d42;
                color: #e8eaed;
                border: 1px solid #6b6f75;
                padding: {styles.scaled(2)}px {styles.scaled(6)}px;
            }}
        """)

        for i, x in enumerate(x_values):
            x_item = QTableWidgetItem(utils.format_number(x))
            x_item.setFlags(Qt.ItemIsEnabled)
            x_item.setTextAlignment(Qt.AlignCenter)
            x_item.setForeground(self._NORMAL_COLOR)
            table.setItem(0, i, x_item)

            existing_val = self.original_results.get(f'g{start_key + i}')
            display_text = f"{existing_val:.2f}" if existing_val is not None else ''
            res_item = QTableWidgetItem(display_text)
            res_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)
            res_item.setTextAlignment(Qt.AlignCenter)
            res_item.setForeground(self._NORMAL_COLOR)
            res_item.setData(Qt.UserRole, display_text)  # эталон для подсветки изменений
            table.setItem(1, i, res_item)
        table.setEditTriggers(QTableWidget.AllEditTriggers)
        table.itemChanged.connect(self._on_value_item_changed)

        small_font = QFont()
        small_font.setPointSize(styles.scaled_pt(10))
        table.setFont(small_font)
        table.verticalHeader().setFont(small_font)
        table.resizeRowsToContents()
        table.resizeColumnsToContents()
        min_section = styles.scaled(55)
        for c in range(table.columnCount()):
            table.setColumnWidth(c, max(min_section, table.columnWidth(c) + styles.scaled(4)))
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

        table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        col.addWidget(table)
        container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.tests_column.addWidget(container)
        return container, table

    def _on_value_item_changed(self, item):
        """Подсвечивает жирным оранжевым ячейку измеренного значения
        (строка 1), если текст отличается от исходного, сохранённого в
        протоколе (п.3 требований)."""
        if item.row() != 1:
            return
        original = item.data(Qt.UserRole) or ''
        changed = item.text().strip() != original
        font = QFont()
        font.setPointSize(styles.scaled_pt(10))
        font.setBold(changed)
        item.setFont(font)
        item.setForeground(self._CHANGED_COLOR if changed else self._NORMAL_COLOR)

    def try_accept(self):
        if not self.mods or not self.selected_mod:
            GlowMessageDialog.show_error(self, "Ошибка", "Сначала добавьте модификацию через Настройки.")
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
            int(float(pressure_text))
        except ValueError:
            GlowMessageDialog.show_error(self, "Ошибка", "Некорректное значение давления.")
            return

        if not auth.check_password(self.password_input.text()):
            GlowMessageDialog.show_error(self, "Ошибка", "Неверный пароль.")
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
        results['g32'] = int(float(self.pressure_input.text().strip()))

        seal_results = {key: combo.currentText() for key, combo in self.seal_inputs.items()}

        return {
            'modification_id': self.selected_mod['id'],
            'modification_name': self.selected_mod['name'],
            'test_date': self.date_input.date().toString('yyyy-MM-dd'),
            'test_type': self.type_combo.currentText(),
            'order_number': utils.normalize_order_number(self.order_input.text().strip()) or None,
            'results': results,
            'seal_results': seal_results,
            'note': self.note_input.text().strip(),
        }


class EditHistoryDialog(_GlowDialog):
    """Диалог управления историей редактирования протокола - фирменный стиль."""
    def __init__(self, edit_history, pump_id, parent=None):
        super().__init__(parent, title="Управление историей редактирования")
        self.pump_id = pump_id
        self.clear_note = False  # по умолчанию не очищать примечание

        hint_label = QLabel("Выберите записи для удаления (отметьте галочками):")
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: #e8eaed; background: transparent;")
        self.body_layout.addWidget(hint_label)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: #f0f0f0;
                color: #1c1e21;
                border: 1px solid #6b6f75;
                border-radius: 4px;
            }}
            QListWidget::item {{
                padding: {styles.scaled(3)}px {styles.scaled(4)}px;
            }}
            QListWidget::item:selected {{
                background-color: #bdeeff;
                color: #1c1e21;
            }}
            QListWidget::item:hover {{
                background-color: #d6f3ff;
            }}
        """)
        self.list_widget.setMinimumSize(520, 320)
        self.body_layout.addWidget(self.list_widget)

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
        for btn in (btn_delete_selected, btn_delete_all, btn_cancel):
            btn.setObjectName("chromeButton")
            btn.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
            btn.setAutoDefault(False)
            btn.setDefault(False)

        btn_delete_selected.clicked.connect(self.delete_selected)
        btn_delete_all.clicked.connect(self.delete_all)
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_delete_selected)
        btn_layout.addWidget(btn_delete_all)
        btn_layout.addWidget(btn_cancel)
        self.body_layout.addLayout(btn_layout)

        self.result_history = edit_history
        self._lock_size(clamp_to_screen=True)

    def delete_selected(self):
        indices = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                indices.append(i)
        if not indices:
            GlowMessageDialog.show_error(self, "Информация", "Не выбрано ни одной записи.")
            return
        for i in reversed(indices):
            self.list_widget.takeItem(i)
        self.clear_note = False
        self.save_result()

    def delete_all(self):
        if not GlowMessageDialog.confirm(
            self, "Подтверждение",
            "Удалить все записи истории?\nПримечание также будет очищено."
        ):
            return
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