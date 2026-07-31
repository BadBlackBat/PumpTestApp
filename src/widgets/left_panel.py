from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QCheckBox,
    QDateEdit, QHeaderView, QAbstractItemView, QMenu,
    QStyledItemDelegate, QStyle, QStyleOptionViewItem, QApplication,
    QFrame, QGraphicsDropShadowEffect, QGridLayout, QScrollBar, QStyleOptionSlider,
    QGraphicsOpacityEffect
)
from PyQt5.QtCore import (
    Qt, pyqtSignal, QDate, QPoint, QTimer, QEvent, QEasingCurve,
    QRect, QRectF, pyqtProperty, QPropertyAnimation, QSize, QObject
)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPolygon, QLinearGradient, QBrush, QPainterPath, QPen

from .. import database as db
from .. import utils
from .. import styles
from .. import icon_utils
import os
import weakref

RESOURCES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resources'
)
ICONS_DIR = os.path.join(RESOURCES_DIR, 'icons')


def _make_people_icon(color, size=14, count=1):
    """Рисует простую иконку "один монитор" (count=1) или "несколько
    мониторов" (count>1, два внахлёст) - программно через QPainter, без
    отдельных файлов ресурсов. Используется для индикатора количества
    активных пользователей сетевой базы (см. db_sync.get_active_user_count).

    Монитор (простой прямоугольник экрана + ножка-подставка), а не
    силуэт человека - при таком мелком размере (строка индикатора тонкая,
    под стать остальным подписям в ней) прямоугольная форма читается
    заметно чётче, чем скруглённые голова+тело, которые на этом
    масштабе превращались в нечитаемое пятно и не помещались по высоте."""
    pixmap = QPixmap(size, size + 2)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(color))

    def draw_monitor(cx, scale):
        screen_w = size * 0.62 * scale
        screen_h = size * 0.44 * scale
        screen_top = size * 0.06
        painter.drawRoundedRect(
            QRectF(cx - screen_w / 2, screen_top, screen_w, screen_h), 1, 1
        )
        stand_w = screen_w * 0.3
        stand_h = size * 0.12
        stand_top = screen_top + screen_h
        painter.drawRect(QRectF(cx - stand_w / 2, stand_top, stand_w, stand_h))
        base_w = screen_w * 0.55
        base_h = size * 0.07
        painter.drawRoundedRect(
            QRectF(cx - base_w / 2, stand_top + stand_h, base_w, base_h), 1, 1
        )

    if count <= 1:
        draw_monitor(size / 2, 1.0)
    else:
        draw_monitor(size * 0.38, 0.72)
        draw_monitor(size * 0.66, 0.72)

    painter.end()
    return pixmap


class _ButtonGlowBlinker(QObject):
    """Мигающее свечение вокруг кнопки для привлечения внимания
    (например, "есть несохранённые изменения - нужно выгрузить").

    Управляет разом тремя визуальными аспектами через одно анимируемое
    свойство intensity (0..1, туда-обратно, по кругу):
    - тень (QGraphicsDropShadowEffect) - яркая, с большим радиусом
      размытия, только композитинг, геометрия кнопки не меняется вообще
    - цвет рамки кнопки - тоже настоящая подсветка контура, но через
      обычный QSS (border-color не конфликтует с градиентным фоном
      кнопки, в отличие от background)
    - лёгкий цветной оттенок самого фона кнопки поверх алюминиевого
      градиента - полупрозрачный слой того же цвета, что и подсветка

    Ни один из этих трёх аспектов не меняет размеры/положение кнопки -
    соседние элементы не перестраиваются и не двигаются.

    В "спокойном" состоянии (intensity=0, или set_active(False)) кнопка
    выглядит РОВНО как обычная кнопка текущей темы - базовый стиль
    пересчитывается заново из исходного (всегда "тёмного", как написано
    в коде) литерала через styles.retheme_stylesheet() при каждом
    обращении, а не хранится статичным снимком с момента создания -
    иначе после переключения темы кнопка в состоянии покоя откатывалась
    бы к уже устаревшей теме, а не к текущей."""
    def __init__(self, button, color_rgb, original_style):
        super().__init__(button)
        self._button = button
        self._color_rgb = color_rgb
        # Исходный, всегда "тёмный" (как написано в коде) стиль - НЕ
        # используется напрямую, только как источник для
        # styles.retheme_stylesheet() при каждом обращении (см. _base_style)
        self._original_style = original_style
        self._intensity = 0.0

        self._effect = QGraphicsDropShadowEffect(button)
        self._effect.setBlurRadius(32)
        self._effect.setOffset(0, 0)
        r, g, b = color_rgb
        self._effect.setColor(QColor(r, g, b, 0))
        button.setGraphicsEffect(self._effect)

        self._anim = QPropertyAnimation(self, b"intensity", self)
        self._anim.setDuration(1100)
        self._anim.setLoopCount(-1)
        self._anim.setKeyValueAt(0.0, 0.08)
        self._anim.setKeyValueAt(0.5, 1.0)
        self._anim.setKeyValueAt(1.0, 0.08)

        self._active = False

    def _base_style(self):
        """Стиль обычной (не подсвеченной) кнопки под ТЕКУЩУЮ тему -
        пересчитывается заново каждый раз, а не берётся из сохранённого
        при создании кнопки снимка (см. объяснение в docstring класса)."""
        return styles.retheme_stylesheet(self._original_style)

    def _get_intensity(self):
        return self._intensity

    def _set_intensity(self, value):
        self._intensity = value
        r, g, b = self._color_rgb
        # Тень - заметно ярче и крупнее, чем было
        self._effect.setColor(QColor(r, g, b, int(40 + value * 215)))
        # Рамка кнопки - от обычной серой (при value=0 - без всякой
        # добавленной подсветки, никакого базового сдвига) до полностью
        # залитой цветом подсветки; фон - лёгкий полупрозрачный оттенок
        # того же цвета поверх обычного алюминиевого градиента
        border_alpha = int(value * 220)
        bg_alpha = int(value * 90)
        self._button.setStyleSheet(self._base_style() + f"""
            QPushButton#chromeButton {{
                border: 2px solid rgba({r}, {g}, {b}, {border_alpha});
                background-color: rgba({r}, {g}, {b}, {bg_alpha});
            }}
        """)

    intensity = pyqtProperty(float, _get_intensity, _set_intensity)

    def set_active(self, active):
        if active == self._active:
            return
        self._active = active
        if active:
            self._anim.start()
        else:
            self._anim.stop()
            self._set_intensity(0.0)
            self._button.setStyleSheet(self._base_style())



class _ArrowHoverLineEdit(QLineEdit):
    """Обычный QLineEdit показывает I-образный курсор уже при простом
    наведении мыши, даже если поле неактивно. Здесь курсор остаётся
    стрелкой при наведении и меняется на I-образный только при реальном
    клике/вводе (фокусе)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.ArrowCursor)

    def enterEvent(self, event):
        if not self.hasFocus():
            self.setCursor(Qt.ArrowCursor)
        super().enterEvent(event)

    def mousePressEvent(self, event):
        self.setCursor(Qt.IBeamCursor)
        super().mousePressEvent(event)

    def focusInEvent(self, event):
        self.setCursor(Qt.IBeamCursor)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.setCursor(Qt.ArrowCursor)
        super().focusOutEvent(event)


class _DateTableItem(QTableWidgetItem):
    """Ячейка с датой - отображает ДД-ММ-ГГГГ (единый формат отображения
    во всём приложении), но сортируется по настоящей хронологии, а не по
    тексту (иначе строковая сортировка "05-12-2024" vs "20-01-2024" дала
    бы неверный порядок - хранит оригинальную ISO-дату отдельно для
    сравнения)."""
    def __init__(self, display_text, iso_date):
        super().__init__(display_text)
        self._iso_date = iso_date or ''

    def __lt__(self, other):
        if isinstance(other, _DateTableItem):
            return self._iso_date < other._iso_date
        return super().__lt__(other)


class _CtrlWheelZoomWidget(QWidget):
    """Обычный QWidget, который перехватывает Ctrl+колесо мыши и вызывает
    переданный обработчик - используется для масштабирования обзорного
    снимка протокола и текста статистики колёсиком мыши (без Ctrl колесо
    работает как обычно - прокрутка, если она вообще где-то есть)."""
    def __init__(self, on_ctrl_wheel, parent=None):
        super().__init__(parent)
        self._on_ctrl_wheel = on_ctrl_wheel
        # Обычный QWidget (в отличие от QFrame) не рисует фон, заданный
        # через QSS, без этого атрибута - без него весь наш тёмно-синий
        # градиент просто не отрисовывался
        self.setAttribute(Qt.WA_StyledBackground, True)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            self._on_ctrl_wheel(event)
            event.accept()
        else:
            super().wheelEvent(event)


class _GlowScrollBar(QScrollBar):
    """Полоса прокрутки в фирменном стиле - собственная отрисовка (QSS не
    умеет ни плавную анимацию ширины, ни "бегущую" динамическую подсветку).

    Желоб не рисуется вовсе (полностью прозрачный) - виден только сам
    бегунок. В состоянии покоя - тонкая линия акцентного цвета. При
    наведении мыши плавно расширяется СИММЕТРИЧНО в обе стороны от центра
    до полного вида со скруглёнными краями (35% от ширины) и настоящим
    свечением (ярче по центру бегунка, гаснет к его краям - тот же приём,
    что и у _GlowFrame/_GlowLine). Такое же временное раскрытие
    происходит и просто при прокрутке колесом мыши, даже если курсор не
    касается самой полосы - и плавно гаснет обратно через небольшую паузу
    после того, как прокрутка прекратилась.

    color - RGB кортеж акцентного цвета (по умолчанию фирменный
    бирюзовый) - можно задать другой (зелёный/оранжевый) для диалогов с
    другой акцентной подсветкой."""

    THIN_WIDTH = 3
    FULL_WIDTH = 8
    MARGIN_TOP = 4
    MARGIN_BOTTOM = 4
    MARGIN_RIGHT = 5          # отступ справа - ощущение "парящей" полосы
    SCROLL_ACTIVITY_LEVEL = 0.65  # насколько раскрывается при прокрутке колесом (без наведения)
    SCROLL_ACTIVITY_HOLD_MS = 700  # сколько ждать после остановки прокрутки перед затуханием

    def __init__(self, parent=None, color=None):
        super().__init__(Qt.Vertical, parent)
        self._explicit_color = color  # None - подстраивается под тему динамически, см. _color
        self._hover_progress = 0.0  # 0 - состояние покоя, 1 - полностью раскрыта
        self._is_hovering = False
        self.setStyleSheet("QScrollBar { background: transparent; border: none; }")
        # Без этого атрибута Qt рисует собственный фон виджета (из
        # палитры/стиля) ДО нашего paintEvent
        self.setAttribute(Qt.WA_NoSystemBackground, True)

        self._anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._anim.setDuration(160)

        self._activity_timer = QTimer(self)
        self._activity_timer.setSingleShot(True)
        self._activity_timer.timeout.connect(self._on_activity_timeout)

        self.valueChanged.connect(self._on_value_changed)

    def _current_color(self):
        return self._explicit_color or styles.get_accent_color_rgb()

    def getHoverProgress(self):
        return self._hover_progress

    def setHoverProgress(self, value):
        self._hover_progress = value
        self.update()

    hoverProgress = pyqtProperty(float, getHoverProgress, setHoverProgress)

    def enterEvent(self, event):
        self._is_hovering = True
        self._animate_to(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovering = False
        if not self._activity_timer.isActive():
            self._animate_to(0.0)
        super().leaveEvent(event)

    def _on_value_changed(self, _value):
        """Прокрутка колесом мыши - временно раскрывает полосу, даже если
        курсор её не касается, и держит раскрытой, пока прокрутка активна."""
        if not self._is_hovering:
            self._animate_to(self.SCROLL_ACTIVITY_LEVEL)
        self._activity_timer.start(self.SCROLL_ACTIVITY_HOLD_MS)

    def _on_activity_timeout(self):
        if not self._is_hovering:
            self._animate_to(0.0)

    def _animate_to(self, target):
        self._anim.stop()
        self._anim.setStartValue(self._hover_progress)
        self._anim.setEndValue(target)
        self._anim.start()

    def sizeHint(self):
        base = super().sizeHint()
        return QSize(self.FULL_WIDTH + self.MARGIN_RIGHT, base.height())

    def _handle_rect(self):
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        return self.style().subControlRect(QStyle.CC_ScrollBar, opt, QStyle.SC_ScrollBarSlider, self)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        current_width = self.THIN_WIDTH + (self.FULL_WIDTH - self.THIN_WIDTH) * self._hover_progress
        radius = current_width * 0.35

        # Центр полосы фиксирован (по максимальной ширине) - при
        # раскрытии она растёт СИММЕТРИЧНО в обе стороны от этого центра,
        # а не только влево
        center_x = self.width() - self.MARGIN_RIGHT - self.FULL_WIDTH / 2
        track_x = center_x - current_width / 2

        handle_qrect = self._handle_rect()
        handle_top = handle_qrect.top()
        handle_h = max(1, handle_qrect.height())
        handle_rect = QRectF(track_x, handle_top, current_width, handle_h)

        # Лёгкая тень - слегка смещённый затемнённый дубликат формы прямо
        # под самой полосой (для контраста на светлом фоне)
        shadow_rect = handle_rect.translated(0.6, 1.2)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 60))
        painter.drawRoundedRect(shadow_rect, radius, radius)

        r, g, b = self._current_color()
        if self._hover_progress < 0.05:
            # Состояние покоя - просто тонкая линия акцентного цвета, без свечения
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(r, g, b, 220))
            painter.drawRoundedRect(handle_rect, radius, radius)
        else:
            # При раскрытии - настоящее свечение: ярче по центру бегунка,
            # гаснет к его собственным краям (тот же приём, что и у рамок)
            handle_gradient = QLinearGradient(0, handle_top, 0, handle_top + handle_h)
            handle_gradient.setColorAt(0.0, QColor(r, g, b, 50))
            handle_gradient.setColorAt(0.5, QColor(r, g, b, 235))
            handle_gradient.setColorAt(1.0, QColor(r, g, b, 50))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(handle_gradient))
            painter.drawRoundedRect(handle_rect, radius, radius)


class _GlowFrame(QFrame):
    """Панель с фирменной подсветкой по всем четырём сторонам.

    На тёмной теме - графитовый фон + яркое бирюзовое свечение (как и
    было). На светлой - мягкий длинный серебристый градиент + блик
    полированного металла по краям (яркая почти-белая полоса у одной
    стороны, имитирующая отражение света от кромки детали, и лёгкая
    тень с противоположной - вместо неонового свечения, которое на
    светлом фоне просто не читалось бы как "свечение").

    Все живые экземпляры отслеживаются в _instances (WeakSet - не
    мешает сборке мусора) - при переключении темы gui.py вызывает
    _GlowFrame.refresh_all(), и каждая панель (левая панель, ЛЮБОЙ
    открытый диалог - они все используют этот же класс) перекрашивается
    сразу, без пересоздания."""
    _instances = weakref.WeakSet()

    def __init__(self, parent=None, glow_color=None):
        super().__init__(parent)
        self.setObjectName("filtersPanel")
        # Без этого атрибута Qt в некоторых стилях может некорректно
        # применять border-radius из QSS у QFrame - виджет визуально
        # выглядит скруглённым, но его "форма" для целей эффектов (см.
        # QGraphicsDropShadowEffect ниже) остаётся прямоугольной. Это и
        # есть вероятная причина "углов поверх скруглений".
        self.setAttribute(Qt.WA_StyledBackground, True)
        # Цвет свечения - явно заданный (например, оранжевый для
        # EditPumpDialog, зелёный для AddModificationDialog) остаётся
        # тем же независимо от темы - это семантический цвет конкретного
        # диалога. None (обычные диалоги/левая панель) - подстраивается
        # под тему автоматически через styles.get_accent_color_rgb().
        self._explicit_glow_color = glow_color
        self._apply_base_style()

        blur, alpha = styles.get_glow_shadow_params()
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(blur)
        shadow.setColor(QColor(0, 0, 0, alpha))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)
        self._shadow_effect = shadow

        _GlowFrame._instances.add(self)
        # Помечаем, что тема этого виджета управляется его собственным
        # механизмом (refresh_all/refresh_theme выше) - иначе общий
        # retheme_widget_tree() (см. styles.py) конфликтовал бы с ним:
        # найдя этот виджет ПОСЛЕ того, как _GlowFrame.refresh_all() уже
        # применил светлый стиль, retheme_widget_tree ошибочно принял бы
        # УЖЕ светлый CSS за "исходный тёмный" и запомнил бы его как
        # такой - при следующем переключении обратно в тёмную тему это
        # привело бы к тому, что панель осталась бы светлой навсегда.
        self.setProperty("_self_themed", True)

    @property
    def _glow_color(self):
        return self._explicit_glow_color or styles.get_accent_color_rgb()

    def _apply_base_style(self):
        self.setStyleSheet(styles.get_glow_panel_style())

    def refresh_theme(self):
        """Перечитывает стиль/цвета под текущую тему - вызывается из
        refresh_all() при переключении темы."""
        self._apply_base_style()
        blur, alpha = styles.get_glow_shadow_params()
        self._shadow_effect.setBlurRadius(blur)
        self._shadow_effect.setColor(QColor(0, 0, 0, alpha))
        self.update()

    @classmethod
    def refresh_all(cls):
        for instance in list(cls._instances):
            instance.refresh_theme()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        t = styles.LEFT_PANEL_GLOW_THICKNESS

        # Ограничиваем область рисования той же скруглённой формой, что
        # и border-radius в QSS (10px) - иначе прямоугольная заливка
        # полос ниже (fillRect на всю ширину/высоту) рисуется буквально
        # поверх скруглённых углов, создавая видимые квадратные
        # "заплатки" именно там, где что-то рисуется от края до края.
        # Это и объясняло замеченную асимметрию: на светлой теме полоса
        # рисуется только сверху и по бокам (снизу ничего нет вообще) -
        # поэтому квадратные уголки были видны только сверху.
        clip_path = QPainterPath()
        clip_path.addRoundedRect(QRectF(0, 0, w, h), 10, 10)
        painter.setClipPath(clip_path)

        if styles.is_light_theme():
            # Светлая тема - блик полированного металла: яркая почти-белая
            # полоса сверху и по бокам (имитация отражения света от
            # скруглённой кромки). Без тёмных элементов (тень снизу/
            # затемнение по бокам) - именно они, судя по всему, и читались
            # как "тень по углам панели" поверх и так уже смягчённой тени
            # QGraphicsDropShadowEffect.
            grad_top = QLinearGradient(0, 0, w, 0)
            grad_top.setColorAt(0.0, QColor(255, 255, 255, 0))
            grad_top.setColorAt(0.5, QColor(255, 255, 255, 200))
            grad_top.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.fillRect(QRectF(0, 0, w, t), grad_top)

            grad_side = QLinearGradient(0, 0, 0, h)
            grad_side.setColorAt(0.0, QColor(255, 255, 255, 150))
            grad_side.setColorAt(0.5, QColor(255, 255, 255, 60))
            grad_side.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.fillRect(QRectF(0, 0, t, h), grad_side)
            painter.fillRect(QRectF(w - t, 0, t, h), grad_side)
        else:
            # Тёмная тема - фирменное бирюзовое (или явно заданное, см.
            # _explicit_glow_color) свечение, яркое по центру каждой
            # стороны, гаснущее к углам
            r, g, b = self._glow_color

            grad_h = QLinearGradient(0, 0, w, 0)
            grad_h.setColorAt(0.0, QColor(r, g, b, 0))
            grad_h.setColorAt(0.5, QColor(r, g, b, 230))
            grad_h.setColorAt(1.0, QColor(r, g, b, 0))
            painter.fillRect(QRectF(0, 0, w, t), grad_h)
            painter.fillRect(QRectF(0, h - t, w, t), grad_h)

            grad_v = QLinearGradient(0, 0, 0, h)
            grad_v.setColorAt(0.0, QColor(r, g, b, 0))
            grad_v.setColorAt(0.5, QColor(r, g, b, 230))
            grad_v.setColorAt(1.0, QColor(r, g, b, 0))
            painter.fillRect(QRectF(0, 0, t, h), grad_v)
            painter.fillRect(QRectF(w - t, 0, t, h), grad_v)


class _NoSelectionPaintDelegate(QStyledItemDelegate):
    """Обычно Qt при отрисовке выделенной ячейки полностью игнорирует её
    собственный фон (Qt::BackgroundRole) и вместо этого рисует заливку
    состояния ":selected" (даже если в QSS она задана как transparent -
    это всё равно перекрывает то, что мы красим через setBackground()).
    Этот делегат перед отрисовкой снимает флаг "выделено" у копии опций -
    ячейка визуально рисуется как обычная, со своим настоящим фоном,
    а выделение как таковое (сигналы, модель) продолжает работать штатно."""
    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.state &= ~QStyle.State_Selected
        opt.state &= ~QStyle.State_HasFocus
        super().paint(painter, opt, index)


class _DbNotificationBanner(QWidget):
    """Настоящая бегущая строка - уведомление о том, что кто-то другой
    изменил сетевую базу данных, пока программа уже была открыта (см.
    MainWindow._check_remote_changes, gui.py - опрашивает сеть раз в
    несколько секунд).

    Устроено из ДВУХ отдельных дочерних виджетов - фона (self._bg_widget,
    со своим собственным QGraphicsOpacityEffect для плавного появления/
    исчезания) и текста (self._text_label, полностью независимого от
    прозрачности фона - иначе при затухании/появлении фона точно так же
    тускнел бы и сам текст, а он должен оставаться ярким всегда). Текст
    едет через видимую область слева направо и обратно средствами
    QPropertyAnimation, естественно обрезаясь по границам этого виджета.

    Точная последовательность показа:
        1) фон плавно появляется (1с) - текст в это время уже уведён за
           правый край (не виден) - иначе на этот момент он на мгновение
           показывался бы статично там, где остался с прошлого раза
        2) текст въезжает с правого края и пробегает в левую часть
        3) через 1с паузы (фон остаётся как есть, не гаснет) - второй круг
        4) фон плавно гаснет (1с)

    Все шаги защищены "номером текущего показа" (self._seq) - если новое
    уведомление прерывает ещё не закончившуюся последовательность, все
    отложенные обратные вызовы от СТАРОЙ последовательности проверяют
    номер и просто ничего не делают.

    Абсолютное позиционирование самого окошка (задаётся в
    _DbStatusIndicator.resizeEvent) - специально, чтобы не увеличивать
    высоту панели фильтров добавлением ещё одной строки в обычный layout."""
    LAPS = 2
    LAP_DURATION_MS = 9000
    GAP_BETWEEN_LAPS_MS = 1000
    FADE_MS = 1000
    # Пик непрозрачности ФОНА (не текста - он теперь отдельный виджет и
    # всегда полностью непрозрачный/яркий) - около 85-90% прозрачности
    BG_PEAK_OPACITY = 0.13

    def __init__(self, parent=None):
        super().__init__(parent)
        self._seq = 0
        self._laps_done = 0
        self._laps_target = self.LAPS

        # Фон - отдельный виджет-подложка на всю область (см. resizeEvent),
        # со своим собственным эффектом прозрачности
        self._bg_widget = QWidget(self)
        self._bg_widget.setAttribute(Qt.WA_StyledBackground, True)
        self._bg_opacity_effect = QGraphicsOpacityEffect(self._bg_widget)
        self._bg_opacity_effect.setOpacity(0.0)
        self._bg_widget.setGraphicsEffect(self._bg_opacity_effect)

        # Текст - отдельный виджет ПОВЕРХ фона, без какого-либо эффекта
        # прозрачности - всегда полностью яркий, независимо от фона
        self._text_label = QLabel(self)
        self._text_label.setWordWrap(False)
        self._text_label.setFont(QFont("Segoe UI", 11, QFont.Bold))

        self.hide()

        self._bg_fade_in = QPropertyAnimation(self._bg_opacity_effect, b"opacity", self)
        self._bg_fade_in.setDuration(self.FADE_MS)
        self._bg_fade_in.setStartValue(0.0)
        self._bg_fade_in.setEndValue(self.BG_PEAK_OPACITY)

        self._bg_fade_out = QPropertyAnimation(self._bg_opacity_effect, b"opacity", self)
        self._bg_fade_out.setDuration(self.FADE_MS)
        self._bg_fade_out.setStartValue(self.BG_PEAK_OPACITY)
        self._bg_fade_out.setEndValue(0.0)

        # Линейная (постоянная скорость) анимация пробега - без плавного
        # разгона/торможения, как и положено настоящей бегущей строке.
        # Раньше движение выглядело "дёрганным" - разделение фона и
        # текста на два независимых виджета (см. выше) снимает лишнюю
        # нагрузку на композитинг при одновременной анимации прозрачности
        # и позиции одного и того же слоя, что и было вероятной причиной.
        self._scroll_anim = QPropertyAnimation(self._text_label, b"pos", self)
        self._scroll_anim.setEasingCurve(QEasingCurve.Linear)

        self._gap_timer = QTimer(self)
        self._gap_timer.setSingleShot(True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._bg_widget.setGeometry(0, 0, self.width(), self.height())

    def show_message(self, text, text_color_override=None, laps=None):
        """Показывает текст бегущей строкой - см. описание класса для
        точной последовательности. Прерывает и полностью отменяет любую
        ещё не закончившуюся предыдущую последовательность.

        text_color_override - если задан, используется вместо обычного
        бирюзового (например, тёмно-оранжевый - для уведомления о том,
        что база данных была автоматически обновлена из сети "тихо",
        без спроса - см. MainWindow._check_remote_changes, gui.py).

        laps - если задан, переопределяет количество прогонов текста
        (по умолчанию - self.LAPS, обычно 2) только для этого показа -
        например, 1 для менее значимых/разовых уведомлений вроде "база
        данных инициализирована" при старте программы."""
        self._seq += 1
        seq = self._seq
        self._laps_target = laps if laps is not None else self.LAPS

        self._bg_fade_in.stop()
        self._bg_fade_out.stop()
        self._scroll_anim.stop()
        self._gap_timer.stop()

        # Цвета - под текущую тему. Текст - тот же контрастный бирюзовый,
        # что и раньше (если не переопределён явно). Фон - НЕ нейтральный
        # чёрный/белый, а чуть светлее (тёмная тема) или чуть темнее
        # (светлая тема) собственного фона панели фильтров - тонкая, но
        # узнаваемая разница, а не резкий контраст. Фон - горизонтальный
        # градиент, гаснущий к обоим краям (тень в тон самого фона) -
        # ощущение "парящей" плашки.
        if styles.is_light_theme():
            bg_rgb = "184, 188, 194"    # чуть темнее светлого фона панели
            text_color = text_color_override or "#4fd1ff"
        else:
            bg_rgb = "77, 80, 88"       # чуть светлее тёмного фона панели
            text_color = text_color_override or "#0d7a99"
        self._bg_widget.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba({bg_rgb}, 0),
                    stop:0.12 rgba({bg_rgb}, 255),
                    stop:0.88 rgba({bg_rgb}, 255),
                    stop:1 rgba({bg_rgb}, 0));
                border-radius: 4px;
            }}
        """)
        self._text_label.setStyleSheet(f"background: transparent; color: {text_color};")

        self._text_label.setText(text)
        self._text_label.adjustSize()

        # Сразу уводим текст за правый край - иначе на время появления
        # фона (1с) он на мгновение показывался бы статично на месте
        # своей ПРЕЖНЕЙ позиции (например, прижатым к верхнему краю от
        # прошлого прогона) - именно так и проявлялся замеченный баг
        y = (self.height() - self._text_label.height()) // 2
        self._text_label.move(self.width(), y)

        self.show()
        self.raise_()
        self._laps_done = 0

        self._connect_once(self._bg_fade_in, lambda: self._start_first_lap(seq))
        self._bg_fade_in.start()

    def _connect_once(self, animation, slot):
        """Переподключает finished к ровно одному, новому обработчику -
        без накопления старых подключений от прошлых вызовов show_message."""
        try:
            animation.finished.disconnect()
        except TypeError:
            pass
        animation.finished.connect(slot)

    def _start_first_lap(self, seq):
        if seq != self._seq:
            return
        self._run_lap(seq)

    def _run_lap(self, seq):
        if seq != self._seq:
            return
        text_w = self._text_label.width()
        y = (self.height() - self._text_label.height()) // 2
        start_point = QPoint(self.width(), y)
        end_point = QPoint(-text_w, y)
        self._text_label.move(start_point)
        self._scroll_anim.setDuration(self.LAP_DURATION_MS)
        self._scroll_anim.setStartValue(start_point)
        self._scroll_anim.setEndValue(end_point)
        self._connect_once(self._scroll_anim, lambda: self._on_lap_finished(seq))
        self._scroll_anim.start()

    def _on_lap_finished(self, seq):
        if seq != self._seq:
            return
        self._laps_done += 1
        if self._laps_done < self._laps_target:
            # Пауза между кругами - фон остаётся как есть, не гаснет
            self._connect_once_timer(lambda: self._run_lap(seq))
            self._gap_timer.start(self.GAP_BETWEEN_LAPS_MS)
        else:
            self._connect_once(self._bg_fade_out, lambda: self._on_fade_out_finished(seq))
            self._bg_fade_out.start()

    def _connect_once_timer(self, slot):
        try:
            self._gap_timer.timeout.disconnect()
        except TypeError:
            pass
        self._gap_timer.timeout.connect(slot)

    def _on_fade_out_finished(self, seq):
        if seq != self._seq:
            return
        self.hide()



class _DbStatusIndicator(QWidget):
    """Четыре мелкие подписи (Network/Local/Offline/Full offline) с
    кружком-индикатором перед каждой - наглядно показывает, с какой
    базой данных программа сейчас реально работает. Активная подпись
    светится своим цветом, и её кружок мигает; остальные три -
    приглушённо-серые, неактивные.

    'network'      - реально работаем с сетевой базой прямо сейчас
    'local'        - выбран локальный режим (сеть вообще не используется)
    'offline'      - сетевой режим выбран/нужен, но сеть сейчас
                     недоступна - работаем с локальной копией вынужденно
    'full_offline' - явно включён режим "полный офлайн" в настройках -
                     сеть не используется осознанно, по выбору
                     пользователя (а не потому что недоступна)
    """
    # Яркие, узнаваемые цвета - специально НЕ зависят от темы (кроме
    # full_offline) - должны одинаково хорошо читаться и на графитовой
    # тёмной панели, и на светлой серебристой
    _COLORS = {
        'network': (79, 209, 255),   # фирменный бирюзовый
        'local': (46, 204, 113),     # яркий зелёный
        'offline': (255, 59, 59),    # яркий красный
    }
    _LABELS = {
        'network': 'Network',
        'local': 'Local',
        'offline': 'Offline',
        'full_offline': 'Full offline',
    }
    _INACTIVE_COLOR = (140, 144, 150)  # серый - для неактивных подписей

    def __init__(self, parent=None, banner_parent=None):
        super().__init__(parent)
        self._active_mode = 'local'
        self._blink_on = True

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(14)

        self._dot_labels = {}
        for key in ('network', 'local', 'offline', 'full_offline'):
            item_layout = QHBoxLayout()
            item_layout.setSpacing(4)
            dot = QLabel("●")
            text = QLabel(self._LABELS[key])
            # Текст ВСЕГДА жирный (и активный, и неактивный) - раньше
            # жирность включалась только у активной подписи, из-за чего
            # её ширина увеличивалась и соседние подписи слегка
            # "прыгали" влево-вправо при переключении режима. Меняется
            # только цвет, начертание - всегда одинаковое.
            font = QFont("Segoe UI", 7, QFont.Bold)
            dot.setFont(font)
            text.setFont(font)
            item_layout.addWidget(dot)
            item_layout.addWidget(text)
            layout.addLayout(item_layout)
            self._dot_labels[key] = (dot, text)

        # Статус синхронизации локальной и сетевой базы - сразу после
        # четырёх подписей режима. Зелёный - всё выгружено в сеть,
        # оранжевый - есть локальные изменения, ещё не отправленные
        self._sync_label = QLabel("")
        self._sync_label.setFont(QFont("Segoe UI", 8, QFont.Bold))
        layout.addWidget(self._sync_label)

        # Индикатор количества активных пользователей сетевой базы -
        # иконка одного человека или группы (см. db_sync.get_active_user_count)
        self._presence_icon_label = QLabel()
        self._presence_icon_label.setToolTip("Пользователей активно с базой: неизвестно")
        layout.addWidget(self._presence_icon_label)
        self._presence_count = None

        layout.addStretch(1)

        # Уведомление об изменениях сетевой базы во время работы - поверх
        # правой половины этой же строки (см. resizeEvent). Родитель -
        # ВСЯ панель фильтров (banner_parent), а НЕ эта строка сама по
        # себе - дочерний виджет Qt всегда обрезается по границам своего
        # непосредственного родителя, а строка индикатора узкая; сделав
        # баннер дочерним у всей (более высокой) панели, ему можно
        # свободно задавать бОльшую высоту без обрезания текста.
        self._banner_parent = banner_parent or self
        self.notification_banner = _DbNotificationBanner(self._banner_parent)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_blink)
        self._timer.start(600)  # пол-секунды примерно на "вдох-выдох" мигания

        self._refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        half_w = self.width() // 2
        if self._banner_parent is self:
            # Родитель не передан явно - старое поведение (баннер
            # ограничен высотой самой строки индикатора)
            self.notification_banner.setGeometry(self.width() - half_w, 0, half_w, self.height())
        else:
            # Баннер - дочерний у ВСЕЙ панели фильтров, а не у этой узкой
            # строки - можно дать ему запас по высоте без обрезания
            # шрифта. Стартует от НИЖНЕГО края строки индикатора (гаранти-
            # рованно неотрицательная координата) и расширяется ВНИЗ, в
            # сторону строки поиска - раньше расширение было в обе
            # стороны от строки индикатора (self.y() - extra), из-за чего
            # верхняя граница легко уходила в отрицательные координаты и
            # обрезалась по верхнему краю панели, оставляя видимой только
            # узкую полоску.
            banner_height = 26
            x = self.x() + self.width() - half_w
            y = self.y() + self.height()
            self.notification_banner.setGeometry(x, y, half_w, banner_height)

    def set_active_mode(self, mode):
        """mode - 'network' / 'local' / 'offline' / 'full_offline'."""
        if mode not in self._LABELS:
            mode = 'local'
        self._active_mode = mode
        self._refresh()

    def set_sync_status(self, synced):
        """Обновляет метку "База данных синхронизирована"/"не
        синхронизирована. Есть изменения" - синхронизировано - тёмно-
        зелёным на светлой теме, ярко-зелёным на тёмной; есть изменения -
        тёмно-оранжевым на светлой теме, ярко-оранжевым на тёмной.
        synced=None - скрывает метку (например, сетевой режим не
        используется вообще - тут нечего показывать)."""
        if synced is None:
            self._sync_label.setText("")
            return
        if synced:
            text = "База данных синхронизирована"
            color = "#1a7a1a" if styles.is_light_theme() else "#3ddc3d"
        else:
            text = "База данных не синхронизирована. Есть изменения"
            color = "#a05a00" if styles.is_light_theme() else "#ff8c00"
        self._sync_label.setText(text)
        self._sync_label.setStyleSheet(f"color: {color}; background: transparent;")

    def set_active_user_count(self, count, force=False):
        """Обновляет иконку количества пользователей, активных с сетевой
        базой прямо сейчас (см. db_sync.get_active_user_count).
        count=None - сеть недоступна/не используется, скрываем иконку.
        force=True - пересчитать в любом случае, даже если число не
        изменилось (нужно при переключении темы - цвет иконки иначе не
        пересчитался бы, если количество осталось прежним)."""
        if count == self._presence_count and not force:
            return
        self._presence_count = count
        if count is None:
            self._presence_icon_label.setPixmap(QPixmap())
            self._presence_icon_label.setToolTip("")
            return
        color = "#4fd1ff" if not styles.is_light_theme() else "#0d7a99"
        pixmap = _make_people_icon(color, size=13, count=count)
        self._presence_icon_label.setPixmap(pixmap)
        if count <= 1:
            self._presence_icon_label.setToolTip("Сейчас с базой работаете только вы")
        else:
            self._presence_icon_label.setToolTip(f"Сейчас активно пользователей: {count}")

    def _on_blink(self):
        self._blink_on = not self._blink_on
        self._refresh()

    def _active_color(self):
        if self._active_mode == 'full_offline':
            # Единственный режим, зависящий от темы - чёрный на светлой,
            # белый на тёмной (у остальных трёх цвет фиксированный и
            # одинаково яркий на обеих темах)
            return (28, 30, 33) if styles.is_light_theme() else (245, 245, 245)
        return self._COLORS[self._active_mode]

    def _refresh(self):
        active_color = self._active_color()
        for key, (dot, text) in self._dot_labels.items():
            if key == self._active_mode:
                r, g, b = active_color
                # Мигание - кружок то в полную силу цвета, то заметно
                # приглушённый (не совсем гаснет - иначе было бы похоже
                # на "неактивно", а не на "мигает")
                if self._blink_on:
                    dot_color = f"rgb({r}, {g}, {b})"
                else:
                    dot_color = f"rgba({r}, {g}, {b}, 90)"
                dot.setStyleSheet(f"color: {dot_color}; background: transparent;")
                text.setStyleSheet(f"color: rgb({r}, {g}, {b}); background: transparent;")
            else:
                r, g, b = self._INACTIVE_COLOR
                dot.setStyleSheet(f"color: rgb({r}, {g}, {b}); background: transparent;")
                text.setStyleSheet(f"color: rgb({r}, {g}, {b}); background: transparent;")


class _RowHighlightOverlay(QWidget):
    """Полупрозрачная подсветка поверх строки таблицы. В отличие от ячеек
    QTableWidget, это настоящий QWidget с настоящим Qt-свойством - поэтому
    его цвет можно по-настоящему плавно анимировать через
    QPropertyAnimation (аппаратно поддерживаемая Qt анимация), без ручной
    покадровой интерполяции и без конфликтов с отрисовкой выделения."""
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._color = QColor(0, 0, 0, 0)
        self.hide()

    def _get_color(self):
        return self._color

    def _set_color(self, color):
        self._color = color
        self.update()

    color = pyqtProperty(QColor, _get_color, _set_color)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self._color)


class LeftPanel(QWidget):
    pump_selected = pyqtSignal(dict)
    pump_status_selected = pyqtSignal(dict)
    group_selected = pyqtSignal(list)
    request_import = pyqtSignal()
    request_upload = pyqtSignal()
    request_force_pull = pyqtSignal()
    request_add = pyqtSignal()
    request_delete = pyqtSignal(int)
    request_edit = pyqtSignal(int)
    filters_applied = pyqtSignal(dict)

    def refresh_theme(self):
        """Перекрашивает всю левую панель (фильтры, таблица, кнопки) под
        текущую тему - вызывается из gui.py при переключении. Левая
        панель - постоянный (не пересоздаваемый) виджет, в отличие от
        диалогов, поэтому ей отдельно нужен этот метод, а не только
        showEvent."""
        styles.retheme_widget_tree(self)
        if hasattr(self, 'date_from'):
            styles.apply_calendar_style(self.date_from.calendarWidget())
        if hasattr(self, 'date_to'):
            styles.apply_calendar_style(self.date_to.calendarWidget())

    def set_db_status(self, mode):
        """Обновляет индикатор режима базы данных (Network/Local/
        Offline) над строкой поиска - см. _DbStatusIndicator. mode -
        'network' / 'local' / 'offline'."""
        self.db_status_indicator.set_active_mode(mode)

    def set_sync_status(self, synced):
        """Обновляет метку "синхронизировано"/"есть изменения" рядом с
        индикатором режима базы. synced=None - скрывает метку."""
        self.db_status_indicator.set_sync_status(synced)

    def set_active_user_count(self, count, force=False):
        """Обновляет иконку количества активных пользователей сетевой
        базы. count=None - скрывает иконку."""
        self.db_status_indicator.set_active_user_count(count, force=force)

    def set_upload_glow(self, active):
        """Включает/выключает зелёное мигающее свечение кнопки
        "Выгрузить" - привлекает внимание, когда есть несохранённые
        локальные изменения."""
        self._upload_glow.set_active(active)

    def set_pull_glow(self, active):
        """Включает/выключает голубое мигающее свечение кнопки "N->L" -
        привлекает внимание, когда сетевая база ушла вперёд."""
        self._pull_glow.set_active(active)

    def show_db_notification(self, text, text_color_override=None, laps=None):
        """Показывает всплывающее уведомление об изменении сетевой базы
        данных другим пользователем (см. MainWindow._check_remote_changes,
        gui.py) - мягкое появление/исчезание поверх строки индикатора."""
        self.db_status_indicator.notification_banner.show_message(text, text_color_override, laps)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.compact_mode = True
        self.current_page = 0
        self.page_size = 20  # начальное значение, пересчитывается под размер окна
        self.total_records = 0
        self.current_filters = {}
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._on_resize_settled)
        self.setup_ui()
        self.load_data()

    def _make_duplicates_cell(self):
        """Объединяет чекбокс "Дубли" и кнопку принудительного скачивания
        сети "N->L" в одной небольшой ячейке - чтобы кнопка не добавляла
        отдельный столбец в сетке (компактный режим) и не выходила за
        пределы блока фильтров, а делила ту же колонку, что и "Дубли"."""
        cell = QWidget()
        cell_layout = QHBoxLayout(cell)
        cell_layout.setContentsMargins(0, 0, 0, 0)
        cell_layout.setSpacing(6)
        cell_layout.addWidget(self.only_duplicates)
        cell_layout.addWidget(self.btn_force_pull)
        return cell

    def _make_filter_chip(self, label_text, control_widget):
        """Небольшая полупрозрачная "плашка", объединяющая подпись
        фильтра и её виджет в одну визуальную группу - вместо разбросанных
        по всей панели label+widget с большим отступом между ними."""
        chip = QFrame()
        chip.setStyleSheet(styles.LEFT_PANEL_CHIP_STYLE)
        chip_layout = QHBoxLayout(chip)
        chip_layout.setContentsMargins(8, 0, 8, 0)
        chip_layout.setSpacing(6)
        label = QLabel(label_text)
        label.setStyleSheet(styles.LEFT_PANEL_FILTER_LABEL_STYLE)
        chip_layout.addWidget(label)
        chip_layout.addWidget(control_widget)
        return chip

    def _build_filters_body(self, expanded):
        """Строит тело фильтров (без строки поиска) - в компактном режиме
        грид в 2 строки, в расширенном - всё в одну строку (больше места
        по ширине). Сами контролы (комбобоксы, чекбокс, кнопка) не
        создаются заново - переиспользуются, только перекладываются в
        новые чипы-обёртки."""
        if expanded:
            body = QHBoxLayout()
            body.setSpacing(14)
            body.addWidget(self._make_filter_chip("Вердикт:", self.filter_verdict))
            body.addWidget(self._make_filter_chip("Тип проверки:", self.filter_test_type))
            body.addWidget(self._make_filter_chip("Герметичность:", self.filter_sealed))
            body.addWidget(self._make_filter_chip("Заказ №:", self.filter_order))
            body.addWidget(self._make_filter_chip("С:", self.date_from))
            body.addWidget(self._make_filter_chip("По:", self.date_to))
            body.addWidget(self._make_duplicates_cell())
            body.addWidget(self.btn_reset_filters)
            body.addStretch()
        else:
            body = QGridLayout()
            body.setHorizontalSpacing(14)
            body.setVerticalSpacing(8)
            body.addWidget(self._make_filter_chip("Вердикт:", self.filter_verdict), 0, 0)
            body.addWidget(self._make_filter_chip("Тип проверки:", self.filter_test_type), 0, 1)
            body.addWidget(self._make_filter_chip("Герметичность:", self.filter_sealed), 0, 2)
            body.addWidget(self._make_duplicates_cell(), 0, 3)
            body.addWidget(self._make_filter_chip("С:", self.date_from), 1, 0)
            body.addWidget(self._make_filter_chip("По:", self.date_to), 1, 1)
            body.addWidget(self._make_filter_chip("Заказ №:", self.filter_order), 1, 2)
            body.addWidget(self.btn_reset_filters, 1, 3)
            body.setColumnStretch(4, 1)
        return body

    def _detach_filter_controls(self):
        """Отсоединяет контролы фильтров от их текущих чипов-обёрток, НЕ
        уничтожая сами контролы - перед удалением старых чипов, чтобы
        контролы (self.filter_verdict и т.д.) пережили перестроение."""
        for w in (self.filter_verdict, self.filter_test_type, self.filter_sealed,
                  self.filter_order, self.date_from, self.date_to,
                  self.only_duplicates, self.btn_force_pull, self.btn_reset_filters):
            w.setParent(None)

    def _clear_layout_and_delete(self, layout):
        """Рекурсивно удаляет все элементы layout (виджеты и вложенные
        layout) - используется для сноса старых чипов при перестроении.
        Вызывать ПОСЛЕ _detach_filter_controls(), иначе вместе с чипами
        удалятся и сами контролы фильтров."""
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                self._clear_layout_and_delete(item.layout())
                item.layout().deleteLater()

    def _reflow_filters(self, expanded):
        """Перестраивает раскладку фильтров под текущий режим просмотра -
        грид в 2 строки (компактный) или всё в одну строку (расширенный,
        больше места по ширине). Вызывается из toggle_view()."""
        self._detach_filter_controls()
        self._clear_layout_and_delete(self.filters_grid)
        self.filters_layout.removeItem(self.filters_grid)
        self.filters_grid.deleteLater()

        self.filters_grid = self._build_filters_body(expanded)
        self.filters_layout.addLayout(self.filters_grid)
        # Новые виджеты фильтров построены с исходным (тёмным) стилем -
        # перекрашиваем их под текущую тему сразу же, иначе (на светлой
        # теме) их текст остался бы белым до следующего переключения
        # темы, что дополнительно путало бы всё при следующей перекраске
        # (см. подробное объяснение бага в retheme_widget_tree, styles.py)
        styles.retheme_widget_tree(self)

    def setup_ui(self):
      layout = QVBoxLayout(self)
      layout.setSpacing(6)
      layout.setContentsMargins(4, 4, 4, 4)

      # Вся панель фильтров - в одной графитовой "карточке" с бирюзовым
      # свечением по всем четырём сторонам (см. класс _GlowFrame)
      filters_panel = _GlowFrame()
      filters_layout = QVBoxLayout(filters_panel)
      filters_layout.setContentsMargins(14, 6, 14, 12)
      filters_layout.setSpacing(8)

      # Индикатор режима работы с базой данных (Network/Local/Offline) -
      # прямо над строкой поиска, чтобы всегда быть на виду
      self.db_status_indicator = _DbStatusIndicator(banner_parent=filters_panel)
      filters_layout.addWidget(self.db_status_indicator)

      # Ряд 1: Поиск
      search_layout = QHBoxLayout()
      search_layout.setSpacing(10)
      search_label = QLabel("Поиск:")
      search_label.setStyleSheet(styles.LEFT_PANEL_SEARCH_LABEL_STYLE)
      search_label.setFixedWidth(50)
      self.search_input = _ArrowHoverLineEdit()
      self.search_input.setObjectName("searchInput")
      self.search_input.setPlaceholderText("Введите номер насоса...")
      self.search_input.setFixedHeight(34)
      self.search_input.setStyleSheet(styles.LEFT_PANEL_SEARCH_INPUT_STYLE)
      self.search_input.textChanged.connect(self.apply_filters)
      search_layout.addWidget(search_label)
      search_layout.addWidget(self.search_input)
      filters_layout.addLayout(search_layout)

      # Создаём сами виджеты фильтров (раскладка - ниже, через грид)
      self.filter_verdict = QComboBox()
      self.filter_verdict.addItems(["Все", "Годен", "Не годен"])
      self.filter_verdict.currentTextChanged.connect(self.apply_filters)
      self.filter_verdict.setStyleSheet(styles.LEFT_PANEL_COMBO_STYLE)

      self.filter_test_type = QComboBox()
      self.filter_test_type.addItems(["Все", "Первичная", "Повторная"])
      self.filter_test_type.currentTextChanged.connect(self.apply_filters)
      self.filter_test_type.setStyleSheet(styles.LEFT_PANEL_COMBO_STYLE)

      self.filter_sealed = QComboBox()
      self.filter_sealed.addItems(["Все", "Герметичен", "Не герметичен"])
      self.filter_sealed.currentTextChanged.connect(self.apply_filters)
      self.filter_sealed.setStyleSheet(styles.LEFT_PANEL_COMBO_STYLE)

      self.filter_order = QComboBox()
      self.filter_order.addItem("Все заказы")
      self.filter_order.currentTextChanged.connect(self.apply_filters)
      self.filter_order.setStyleSheet(styles.LEFT_PANEL_COMBO_STYLE)

      self.date_from = QDateEdit()
      self.date_from.setCalendarPopup(True)
      self.date_from.setDate(QDate(2000, 1, 1))
      self.date_from.dateChanged.connect(self.apply_filters)
      self.date_from.setStyleSheet(styles.LEFT_PANEL_COMBO_STYLE)
      self.date_from.setMinimumWidth(115)  # шире, симметрично с Вердикт/Тип проверки сверху
      styles.apply_calendar_style(self.date_from.calendarWidget())

      self.date_to = QDateEdit()
      self.date_to.setCalendarPopup(True)
      self.date_to.setDate(QDate.currentDate())
      self.date_to.dateChanged.connect(self.apply_filters)
      self.date_to.setStyleSheet(styles.LEFT_PANEL_COMBO_STYLE)
      self.date_to.setMinimumWidth(115)
      styles.apply_calendar_style(self.date_to.calendarWidget())

      self.only_duplicates = QCheckBox("Дубли")
      self.only_duplicates.setStyleSheet(styles.LEFT_PANEL_CHECKBOX_STYLE)
      self.only_duplicates.stateChanged.connect(self.apply_filters)

      # Принудительное скачивание сетевой базы поверх локальной - "N->L"
      # текстом (второй вариант из тех, что обсуждали) - без иконки,
      # компактно, не растягивает общий блок фильтров
      self.btn_force_pull = QPushButton("N\u2192L")
      self.btn_force_pull.setObjectName("chromeButton")
      self.btn_force_pull.setFixedHeight(26)
      self.btn_force_pull.setToolTip("Загрузить сетевую базу поверх локальной")
      self.btn_force_pull.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE + """
          QPushButton#chromeButton { padding: 2px 6px; font-size: 9pt; }
      """)
      self.btn_force_pull.clicked.connect(self.request_force_pull.emit)
      # Голубое мигающее свечение - включается, когда сетевая база ушла
      # вперёд (см. LeftPanel.set_pull_glow)
      self._pull_glow = _ButtonGlowBlinker(
          self.btn_force_pull, (79, 209, 255), self.btn_force_pull.styleSheet()
      )

      self.btn_reset_filters = QPushButton("Сбросить фильтры")
      self.btn_reset_filters.setObjectName("chromeButton")
      self.btn_reset_filters.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
      self.btn_reset_filters.clicked.connect(self.reset_filters)

      # Грид: Вердикт/Тип проверки/Герметичность/Дубли сверху, Заказ № - под
      # Герметичностью (тот же столбец, та же ширина), Сброс - под Дубли
      # (тот же столбец). Пустой растянутый столбец справа поглощает
      # лишнюю ширину при увеличении окна - сами фильтры при этом
      # остаются компактно слева, не расползаются
      self.filters_grid = QGridLayout()
      self.filters_grid.setHorizontalSpacing(14)
      self.filters_grid.setVerticalSpacing(8)

      # Одинаковая ширина у Герметичность/Заказ № - чтобы смотрелись
      # симметрично друг под другом
      self.filter_sealed.setMinimumWidth(130)
      self.filter_order.setMinimumWidth(130)

      self.filters_grid.addWidget(self._make_filter_chip("Вердикт:", self.filter_verdict), 0, 0)
      self.filters_grid.addWidget(self._make_filter_chip("Тип проверки:", self.filter_test_type), 0, 1)
      self.filters_grid.addWidget(self._make_filter_chip("Герметичность:", self.filter_sealed), 0, 2)
      self.filters_grid.addWidget(self._make_duplicates_cell(), 0, 3)

      self.filters_grid.addWidget(self._make_filter_chip("С:", self.date_from), 1, 0)
      self.filters_grid.addWidget(self._make_filter_chip("По:", self.date_to), 1, 1)
      self.filters_grid.addWidget(self._make_filter_chip("Заказ №:", self.filter_order), 1, 2)
      self.filters_grid.addWidget(self.btn_reset_filters, 1, 3)

      self.filters_grid.setColumnStretch(4, 1)  # пустой "хвостовой" столбец - забирает лишнюю ширину
      filters_layout.addLayout(self.filters_grid)
      self.filters_layout = filters_layout  # нужна для перестроения при переключении вида (см. _reflow_filters)

      layout.addWidget(filters_panel)

      # Статистика по заказу (скрыта по умолчанию)
      self.stats_label = QLabel()
      self.stats_label.setWordWrap(True)
      self.stats_label.setStyleSheet(styles.LEFT_PANEL_STATS_LABEL_STYLE)
      self.stats_label.hide()
      layout.addWidget(self.stats_label)

      # Таблица
      self.table = QTableWidget()
      arrow_down_path = os.path.join(RESOURCES_DIR, 'arrow_down_red.png').replace('\\', '/')
      arrow_up_path = os.path.join(RESOURCES_DIR, 'arrow_up_red.png').replace('\\', '/')
      if not (os.path.exists(arrow_down_path) and os.path.exists(arrow_up_path)):
          arrow_down_path = arrow_up_path = None
      # Шрифт Terminator для заголовков таблицы пробовали в качестве
      # эксперимента - оказался слишком массивным и не вписался, поэтому
      # здесь остаёмся на обычном системном шрифте. Terminator оставлен
      # только для надписи "Лаборатория Рулевого Управления" в gui.py
      self.table.setStyleSheet(
          styles.build_left_panel_table_style(arrow_down_path, arrow_up_path)
      )
      # Отключаем штатную заливку выделения Qt - иначе она перекрывает наш
      # собственный (анимированный) цвет ячейки, даже если в QSS задать
      # ":selected { background-color: transparent }"
      self.table.setItemDelegate(_NoSelectionPaintDelegate(self.table))
      # Жирные заголовки - обычным системным шрифтом
      font = self.table.horizontalHeader().font()
      font.setBold(True)
      self.table.horizontalHeader().setFont(font)

      self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
      self.table.setSelectionMode(QAbstractItemView.SingleSelection)
      self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
      self.table.verticalHeader().setVisible(False)
      self.table.setSortingEnabled(True)
      self.table.itemSelectionChanged.connect(self.on_selection_changed)
      self.table.setContextMenuPolicy(Qt.CustomContextMenu)
      self.table.customContextMenuRequested.connect(self.show_context_menu)
      self.table.cellClicked.connect(self.on_cell_clicked)

      # Эффект наведения/выделения строки - через два независимых
      # полупрозрачных оверлея поверх таблицы (см. _RowHighlightOverlay),
      # с настоящей QPropertyAnimation. Сама таблица и её ячейки при этом
      # не трогаются - оверлеи просто рисуются поверх.
      self._hovered_row = -1
      self._selected_row = -1
      self._base_font_size = float(self.table.font().pointSize() or 9)
      self._hover_overlay = _RowHighlightOverlay(self.table.viewport())
      self._selection_overlay = _RowHighlightOverlay(self.table.viewport())
      self._hover_anim = None
      self._selection_anim = None
      self.table.setMouseTracking(True)
      self.table.entered.connect(self.on_row_hover)
      self.table.viewport().installEventFilter(self)

      # Обёртка таблицы - та же графитовая панель со свечением по контуру,
      # что и у фильтров/нижнего блока кнопок (см. класс _GlowFrame)
      table_panel = _GlowFrame()
      table_panel_layout = QVBoxLayout(table_panel)
      table_panel_layout.setContentsMargins(8, 8, 8, 8)
      table_panel_layout.addWidget(self.table)
      layout.addWidget(table_panel)

      # Центрирование таблицы в левой панели
      self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

      # Нижний блок (кнопки управления + пагинация) - в такой же
      # графитовой панели со свечением, как и фильтры сверху
      bottom_panel = _GlowFrame()
      bottom_layout = QVBoxLayout(bottom_panel)
      bottom_layout.setContentsMargins(14, 10, 14, 10)
      bottom_layout.setSpacing(8)

      # Кнопки управления
      btn_layout = QHBoxLayout()
      btn_layout.setSpacing(8)
      self.btn_add = QPushButton("Добавить насос")
      self.btn_add.setObjectName("chromeButton")
      self.btn_add.setFixedHeight(26)
      self.btn_add.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
      self.btn_add.clicked.connect(self.request_add.emit)
      self.btn_delete = QPushButton("Удалить запись")
      self.btn_delete.setObjectName("chromeButton")
      self.btn_delete.setFixedHeight(26)
      self.btn_delete.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
      self.btn_delete.clicked.connect(self.on_delete_clicked)
      # Выгрузка локальных изменений в сеть - в компактном режиме только
      # символ-стрелка (маленькая, не растягивает общий блок), в
      # расширенном - та же стрелка с подписью (см. toggle_view)
      self.btn_upload = QPushButton()
      self.btn_upload.setObjectName("chromeButton")
      self.btn_upload.setFixedHeight(26)
      self.btn_upload.setFixedWidth(40)
      self.btn_upload.setToolTip("Выгрузить изменения в сетевую базу")
      # Тот же алюминиевый стиль, что и у остальных кнопок, но со своим,
      # минимальным паддингом - обычный (16px с каждой стороны) не
      # оставлял места для содержимого при такой узкой ширине кнопки
      self.btn_upload.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE + """
          QPushButton#chromeButton { padding: 2px 4px; }
      """)
      upload_icon_path = os.path.join(ICONS_DIR, 'data-transfer-upload_128x128.svg')
      self.btn_upload.setIcon(icon_utils.tinted_icon(upload_icon_path, "#2b2d31", 22))
      self.btn_upload.setIconSize(QSize(22, 22))
      self.btn_upload.clicked.connect(self.request_upload.emit)
      # Зелёное мигающее свечение - включается, когда есть несохранённые
      # локальные изменения (см. LeftPanel.set_upload_glow)
      self._upload_glow = _ButtonGlowBlinker(
          self.btn_upload, (46, 204, 113), self.btn_upload.styleSheet()
      )
      self.btn_import = QPushButton("Импорт Excel")
      self.btn_import.setObjectName("chromeButton")
      self.btn_import.setFixedHeight(26)
      self.btn_import.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
      self.btn_import.clicked.connect(self.request_import.emit)
      self.btn_view_toggle = QPushButton("Расширить")
      self.btn_view_toggle.setObjectName("chromeButton")
      self.btn_view_toggle.setFixedHeight(26)
      self.btn_view_toggle.setStyleSheet(styles.LEFT_PANEL_RESET_BTN_STYLE)
      self.btn_view_toggle.setCheckable(True)
      self.btn_view_toggle.toggled.connect(self.toggle_view)

      btn_layout.addWidget(self.btn_add)
      btn_layout.addWidget(self.btn_delete)
      btn_layout.addWidget(self.btn_upload)
      btn_layout.addWidget(self.btn_import)
      btn_layout.addWidget(self.btn_view_toggle)
      bottom_layout.addLayout(btn_layout)

      # Легенда
      # self.legend_label = QLabel()
      # self.legend_label.setWordWrap(True)
      # self.legend_label.setStyleSheet("background-color: #f9f9f9; border: 1px solid #ddd; padding: 2px; font-size: 9px;")
      # self.update_legend()
      # layout.addWidget(self.legend_label)

      # Пагинация
      pagination_layout = QHBoxLayout()
      pagination_layout.setSpacing(6)
      self.btn_prev = QPushButton("◀")
      self.btn_prev.setObjectName("chromeButton")
      self.btn_prev.setFixedSize(30, 22)
      self.btn_prev.setStyleSheet(styles.LEFT_PANEL_PAGINATION_BTN_STYLE)
      self.btn_prev.clicked.connect(self.prev_page)
      self.btn_next = QPushButton("▶")
      self.btn_next.setObjectName("chromeButton")
      self.btn_next.setFixedSize(30, 22)
      self.btn_next.setStyleSheet(styles.LEFT_PANEL_PAGINATION_BTN_STYLE)
      self.btn_next.clicked.connect(self.next_page)
      self.page_label = QLabel("1/1")
      self.page_label.setAlignment(Qt.AlignCenter)
      self.page_label.setStyleSheet(styles.LEFT_PANEL_FILTER_LABEL_STYLE)
      # Пояснение "Группировка по дублям" - по центру панели, между
      # пагинацией и счётчиком записей. Пусто и скрыто, пока фильтр
      # "Дубли" не включён (см. update_pagination_label)
      self.duplicates_note_label = QLabel("")
      self.duplicates_note_label.setAlignment(Qt.AlignCenter)
      self.duplicates_note_label.setStyleSheet(styles.LEFT_PANEL_FILTER_LABEL_STYLE)
      self.count_label = QLabel("Показано записей: 0")
      self.count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
      self.count_label.setStyleSheet(styles.LEFT_PANEL_FILTER_LABEL_STYLE)
      pagination_layout.addWidget(self.btn_prev)
      pagination_layout.addWidget(self.page_label)
      pagination_layout.addWidget(self.btn_next)
      pagination_layout.addStretch()
      pagination_layout.addWidget(self.duplicates_note_label)
      pagination_layout.addStretch()
      pagination_layout.addWidget(self.count_label)
      bottom_layout.addLayout(pagination_layout)

      layout.addWidget(bottom_panel)

    # def update_legend(self):
    #     legend_text = (
    #         "Легенда: "
    #         "<span style='color:green;'>●</span> годен  "
    #         "<span style='color:red;'>●</span> не годен  "
    #         "<span style='color:blue;'>●</span> герметичен  "
    #         "<span style='color:gray;'>●</span> не герметичен  "
    #         "I — первичная  II — повторная"
    #     )
    #     self.legend_label.setText(legend_text)

    def toggle_view(self, checked):
        """Переключает компактный/расширенный режим списка."""
        parent = self.parent()
        while parent and not hasattr(parent, 'splitter'):
            parent = parent.parent()
        if not parent or not hasattr(parent, 'splitter'):
            return

        if checked:
            # Расширенный режим
            self.compact_mode = False
            self.btn_view_toggle.setText("Свернуть список")
            self.btn_upload.setText("Выгрузить")
            self.btn_upload.setFont(QFont("Segoe UI", 9))
            self.btn_upload.setFixedWidth(120)
            self._reflow_filters(expanded=True)
            # Снимаем ограничение максимальной ширины (см. gui.py,
            # _apply_minimal_left_width) - иначе панель не может занять
            # весь экран в расширенном режиме
            self.setMaximumWidth(16777215)
            parent.splitter.setSizes([parent.width(), 0])
            # Правая панель визуально сжимается до нуля - но открытый
            # протокол/статистика и кнопки для них в верхней панели без
            # этого остались бы видны поверх расширенного списка
            if hasattr(parent, 'right_panel'):
                parent.right_panel.hide_content_only()
        else:
            # Компактный режим (минимальный)
            self.compact_mode = True
            self.btn_view_toggle.setText("Расширенный вид")
            self.btn_upload.setText("")
            self.btn_upload.setFixedWidth(40)
            self._reflow_filters(expanded=False)
            # Возвращаем ограничение по минимально нужной ширине - тем же
            # методом, что применяется при старте/разворачивании окна
            if hasattr(parent, '_apply_minimal_left_width'):
                parent._apply_minimal_left_width()
            else:
                parent.splitter.setSizes([int(parent.width() * 0.10), int(parent.width() * 0.9)])
        self.apply_filters()
        self.table.clearSelection()

    def _setup_table_columns(self, compact=True):
        """Настраивает количество и заголовки колонок таблицы."""
        font = self.table.horizontalHeader().font()
        font.setBold(True)
        self.table.horizontalHeader().setFont(font)

        if compact:
            col_count = 5
            self.table.setColumnCount(col_count)
            self.table.setHorizontalHeaderLabels(["Номер насоса", "Дата проверки", "Вердикт", "Тип проверки", "Герметичность"])
            for col in range(5, self.table.columnCount()):
                self.table.setColumnHidden(col, True)
            self.table.verticalHeader().setVisible(False)
            self.table.setColumnWidth(0, 100)
            self.table.setColumnWidth(1, 110)
            self.table.setColumnWidth(2, 100)
            self.table.setColumnWidth(3, 110)
            self.table.setColumnWidth(4, 100)
        else:
            col_count = 7
            self.table.setColumnCount(col_count)
            self.table.setHorizontalHeaderLabels(
                ["Номер насоса", "Дата проверки", "Модификация", "Герметичность", "Тип проверки", "Заказ", "Вердикт"]
            )
            for col in range(self.table.columnCount()):
                self.table.setColumnHidden(col, False)
            self.table.verticalHeader().setVisible(False)
            self.table.setColumnWidth(0, 110)
            self.table.setColumnWidth(1, 110)
            self.table.setColumnWidth(2, 150)
            self.table.setColumnWidth(3, 110)
            self.table.setColumnWidth(4, 100)
            self.table.setColumnWidth(5, 100)
            self.table.setColumnWidth(6, 250)
        return col_count

    def _fill_pump_row(self, row, p, compact=True):
        """Заполняет одну строку таблицы данными насоса p."""
        # ---- Номер ----
        item_num = QTableWidgetItem(p['pump_number'])
        item_num.setData(Qt.UserRole, p['id'])
        item_num.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 0, item_num)

        # ---- Дата ----
        date_str = p['test_date']
        item_date = _DateTableItem(utils.format_date_display(date_str), date_str)
        item_date.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 1, item_date)

        if compact:
            # ---- Вердикт ----
            verdict_text = p['verdict'] if p['verdict'] else '—'
            item_verdict = QTableWidgetItem(verdict_text)
            item_verdict.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, item_verdict)

            # ---- Тип ----
            type_text = p['test_type'] if p['test_type'] else '—'
            item_type = QTableWidgetItem(type_text)
            item_type.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, item_type)

            # ---- Герметичность ----
            sealed_text = 'Герметичен' if p['is_sealed'] else 'Негерметичен'
            item_sealed = QTableWidgetItem(sealed_text)
            item_sealed.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, item_sealed)

        else:
            # ---- Модификация ----
            mod_name = p.get('mod_name', '—')
            item_mod = QTableWidgetItem(mod_name if mod_name else '—')
            item_mod.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, item_mod)

            # ---- Герметичность (текст) ----
            sealed_text = 'Герметичен' if p['is_sealed'] else 'Негерметичен'
            item_sealed = QTableWidgetItem(sealed_text)
            item_sealed.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, item_sealed)

            # ---- Тип ----
            type_text = p['test_type'] if p['test_type'] else '—'
            item_type = QTableWidgetItem(type_text)
            item_type.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, item_type)

            # ---- Заказ ----
            order_num = p.get('order_number', '—')
            order_str = str(order_num).replace('.0', '') if order_num and order_num != '—' else '—'
            item_order = QTableWidgetItem(order_str)
            item_order.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, item_order)

            # ---- Вердикт ----
            verdict_text = p['verdict'] if p['verdict'] else '—'
            item_verdict = QTableWidgetItem(verdict_text)
            item_verdict.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 6, item_verdict)

        # ---- Подсветка всей строки по вердикту ----
        if p['verdict'] == 'годен':
            bg_color = QColor(232, 253, 232)
        elif p['verdict'] == 'не годен':
            bg_color = QColor(245, 230, 230)
        else:
            bg_color = None
        base_font = QFont()
        base_font.setPointSizeF(self._base_font_size)
        base_font.setWeight(QFont.Normal)
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                if bg_color:
                    item.setBackground(bg_color)
                item.setFont(base_font)

    def populate_table(self, pumps, compact=True):
        self.table.setSortingEnabled(False)
        self.table.clearSpans()  # сбрасываем объединения ячеек, оставшиеся от группового режима (дубли)
        self.table.setRowCount(len(pumps))
        self._hovered_row = -1
        self._selected_row = -1
        self._hover_overlay.hide()
        self._selection_overlay.hide()

        col_count = self._setup_table_columns(compact)

        for row, p in enumerate(pumps):
            self._fill_pump_row(row, p, compact)

        self.table.setSortingEnabled(True)
        if compact:
            self.table.sortByColumn(1, Qt.DescendingOrder)
        else:
            self.table.sortByColumn(0, Qt.AscendingOrder)

    def populate_table_grouped(self, pumps, compact=True):
        """Отображает насосы, сгруппированные по номеру + модификации (для
        фильтра 'Дубли'): строка-заголовок 'Образец № X — N шт.', а под ней
        сами протоколы, отсортированные по дате (сначала новые). Если у
        насоса с одинаковым номером разные модификации - это разные группы,
        а не дубликаты."""
        self.table.setSortingEnabled(False)
        self.table.clearSpans()
        self._hovered_row = -1
        self._selected_row = -1
        self._hover_overlay.hide()
        self._selection_overlay.hide()

        # Группируем по (номер насоса, модификация)
        groups = {}
        for p in pumps:
            key = (p['pump_number'], p.get('mod_name'))
            groups.setdefault(key, []).append(p)

        # Сортируем группы: сначала по убыванию количества найденных протоколов,
        # при равном количестве - по номеру насоса
        sorted_groups = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0][0]))

        # Внутри группы - сортировка протоколов по дате (сначала новые)
        for _, items in sorted_groups:
            items.sort(key=lambda p: p['test_date'] or '', reverse=True)

        col_count = self._setup_table_columns(compact)

        total_rows = sum(1 + len(items) for _, items in sorted_groups)
        self.table.setRowCount(total_rows)

        row = 0
        for (pump_number, mod_name), items in sorted_groups:
            # ---- Строка-заголовок группы ----
            header_text = f"Образец № {pump_number} — {len(items)} шт."
            header_item = QTableWidgetItem(header_text)
            header_item.setTextAlignment(Qt.AlignCenter)
            header_item.setFlags(Qt.ItemIsEnabled)  # не выделяется и не открывается как протокол
            header_font = QFont()
            header_font.setBold(True)
            header_item.setFont(header_font)
            header_item.setBackground(QColor(210, 224, 240))
            # Сохраняем сами дублирующиеся протоколы на заголовке -
            # понадобится, чтобы по клику показать сравнение (пункт 5)
            header_item.setData(Qt.UserRole + 1, items)
            self.table.setItem(row, 0, header_item)
            self.table.setSpan(row, 0, 1, col_count)
            row += 1

            for p in items:
                self._fill_pump_row(row, p, compact)
                row += 1

        # Сортировка кликом по заголовку в режиме дублей отключена,
        # т.к. порядок строк задан группировкой
        self.table.setSortingEnabled(False)


    def display_pumps(self, pumps, group_by_number=False):
        if group_by_number:
            self.populate_table_grouped(pumps, compact=self.compact_mode)
        else:
            self.populate_table(pumps, compact=self.compact_mode)

    # Методы создания иконок
    # def create_verdict_icon(self, is_good):
    #     pixmap = QPixmap(24, 24)
    #     pixmap.fill(Qt.transparent)
    #     painter = QPainter(pixmap)
    #     painter.setBrush(QColor(0, 200, 0) if is_good else QColor(200, 0, 0))
    #     painter.setPen(Qt.NoPen)
    #     painter.drawEllipse(6, 6, 12, 12)
    #     painter.end()
    #     return QIcon(pixmap)

    # def create_type_icon(self, type_str):
    #     pixmap = QPixmap(24, 24)
    #     pixmap.fill(Qt.transparent)
    #     painter = QPainter(pixmap)
    #     painter.setPen(QColor(0, 0, 200))
    #     painter.setFont(QFont("Arial", 10, QFont.Bold))
    #     painter.drawText(pixmap.rect(), Qt.AlignCenter, "I" if "первичная" in str(type_str).lower() else "II")
    #     painter.end()
    #     return QIcon(pixmap)

    # def create_sealed_icon(self, is_sealed):
    #     pixmap = QPixmap(24, 24)
    #     pixmap.fill(Qt.transparent)
    #     painter = QPainter(pixmap)
    #     painter.setBrush(QColor(0, 100, 255) if is_sealed else QColor(180, 180, 180))
    #     painter.setPen(Qt.NoPen)
    #     painter.drawEllipse(6, 9, 12, 9)
    #     points = [QPoint(6, 9), QPoint(12, 3), QPoint(18, 9)]
    #     polygon = QPolygon(points)
    #     painter.drawPolygon(polygon)
    #     painter.end()
    #     return QIcon(pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_timer.start(200)
        # Оверлеи привязаны к ширине viewport - если их сейчас видно,
        # подгоняем геометрию под новый размер
        if self._hovered_row != -1:
            rect = self._row_rect(self._hovered_row)
            if rect:
                self._hover_overlay.setGeometry(rect)
        if self._selected_row != -1:
            rect = self._row_rect(self._selected_row)
            if rect:
                self._selection_overlay.setGeometry(rect)

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, '_initial_size_done', False):
            self._initial_size_done = True
            QTimer.singleShot(0, self._on_resize_settled)

    def _compute_dynamic_page_size(self):
        """Считает, сколько строк реально помещается в видимую область
        таблицы сейчас. viewport().height() уже НЕ включает область
        заголовка колонок - вычитать её ещё раз не нужно (это и было
        причиной заниженного расчёта)."""
        row_height = self.table.verticalHeader().defaultSectionSize() or 24
        available = self.table.viewport().height()
        return max(5, available // row_height)

    def _on_resize_settled(self):
        if self.only_duplicates.isChecked():
            return  # в режиме дублей пагинация отключена - не трогаем
        new_page_size = self._compute_dynamic_page_size()
        if new_page_size != self.page_size:
            self.page_size = new_page_size
            self.current_page = 0
            self.apply_filters()

    def on_cell_clicked(self, row, col):
        """Клик по заголовку группы дублей открывает сравнение в правой панели.
        Для обычных строк отдельного эффекта не нужно - выделение само по
        себе (см. on_selection_changed) уже даёт мгновенную яркую реакцию
        на клик; отдельная "вспышка" здесь только маскировала её и
        создавала впечатление задержки."""
        item = self.table.item(row, 0)
        if item is None:
            return
        group_items = item.data(Qt.UserRole + 1)
        if group_items:
            self.group_selected.emit(group_items)

    def _row_is_group_header(self, row):
        item0 = self.table.item(row, 0)
        return bool(item0 and item0.data(Qt.UserRole + 1))

    def _row_items(self, row):
        if row < 0 or row >= self.table.rowCount() or self._row_is_group_header(row):
            return []
        return [it for it in (self.table.item(row, c) for c in range(self.table.columnCount())) if it]

    def _row_rect(self, row):
        """Прямоугольник строки во viewport-координатах, во всю ширину -
        именно сюда позиционируется оверлей подсветки."""
        if row < 0 or row >= self.table.rowCount():
            return None
        top = self.table.rowViewportPosition(row)
        height = self.table.rowHeight(row)
        width = self.table.viewport().width()
        if height <= 0:
            return None
        return QRect(0, top, width, height)

    def _vivid(self, color):
        """Яркая, насыщенная версия цвета строки (для выделения) - тот же
        оттенок, что и обычная подсветка по вердикту, но гораздо
        насыщеннее, с прозрачностью (это оверлей поверх ячейки, а не
        замена её цвета). Для нейтральных строк - акцентный синий."""
        h, s, v, _ = color.getHsv()
        if h < 0 or s < 12:
            c = QColor(120, 165, 235)
        else:
            c = QColor()
            c.setHsv(h, 200, 230)
        c.setAlpha(150)
        return c

    def _vivid_text(self, color):
        """Цвет текста для выделенной строки - почти чёрный (не зависит
        от оттенка строки), для чёткого контраста поверх яркого оверлея."""
        return QColor(15, 15, 15)

    def _refresh_row_font(self, row):
        """Жирность/размер шрифта и цвет текста строки - мгновенно, по
        текущему состоянию (наведена и/или выделена ли она сейчас)."""
        if row < 0 or self._row_is_group_header(row):
            return
        emphasize = (row == self._hovered_row or row == self._selected_row)
        items = self._row_items(row)
        if row == self._selected_row:
            item0 = self.table.item(row, 0)
            base = item0.background().color() if item0 else QColor(255, 255, 255)
            text_color = self._vivid_text(base)
        else:
            text_color = QColor(0, 0, 0)
        for item in items:
            f = item.font()
            f.setBold(emphasize)
            f.setPointSizeF(self._base_font_size + (1 if emphasize else 0))
            item.setFont(f)
            item.setForeground(text_color)

    def _start_overlay_animation(self, overlay, anim_attr, target_color, duration):
        """Плавно (по-настоящему, через QPropertyAnimation) меняет цвет
        оверлея. Останавливает предыдущую анимацию этого же оверлея, если
        она ещё идёт."""
        old = getattr(self, anim_attr, None)
        if old is not None:
            old.stop()
        anim = QPropertyAnimation(overlay, b"color", self.table)
        anim.setDuration(duration)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.setStartValue(overlay.color)
        anim.setEndValue(target_color)
        setattr(self, anim_attr, anim)
        anim.start()

    def _set_overlay_instant(self, overlay, anim_attr, color):
        """Мгновенно (без анимации) задаёт цвет оверлея - останавливает
        текущую анимацию этого оверлея, если она идёт. Перерисовывает
        СРАЗУ (repaint, а не отложенный update) - иначе Qt откладывает
        реальную отрисовку до конца текущего обработчика события, и цвет
        визуально появится только после (возможно медленной) остальной
        части клика - запроса к БД и перестроения правой панели."""
        old = getattr(self, anim_attr, None)
        if old is not None:
            old.stop()
            setattr(self, anim_attr, None)
        overlay.color = color
        overlay.repaint()

    def on_row_hover(self, index):
        """Наведение мыши на строку - полупрозрачный белый оверлей плавно
        проявляется поверх строки (осветление на ~50% за счёт alpha),
        текст мгновенно становится жирным и чуть крупнее."""
        row = index.row()
        if self._row_is_group_header(row):
            row = -1
        if row == self._hovered_row:
            return
        old_hover = self._hovered_row
        self._hovered_row = row
        if old_hover != -1:
            self._start_overlay_animation(self._hover_overlay, '_hover_anim',
                                          QColor(255, 255, 255, 0), 350)
            self._refresh_row_font(old_hover)
        if row != -1:
            rect = self._row_rect(row)
            if rect:
                self._hover_overlay.setGeometry(rect)
                self._hover_overlay.show()
                self._hover_overlay.raise_()
            self._start_overlay_animation(self._hover_overlay, '_hover_anim',
                                          QColor(255, 255, 255, 128), 350)
            self._refresh_row_font(row)

    def eventFilter(self, obj, event):
        if obj is self.table.viewport():
            if event.type() == QEvent.Leave:
                if self._hovered_row != -1:
                    old_hover = self._hovered_row
                    self._hovered_row = -1
                    self._start_overlay_animation(self._hover_overlay, '_hover_anim',
                                                  QColor(255, 255, 255, 0), 350)
                    self._refresh_row_font(old_hover)
            elif event.type() == QEvent.MouseMove:
                # Курсор мог уйти на пустое пространство под последней
                # строкой - там нет валидного индекса, и сигнал entered()
                # в этом случае не срабатывает вообще
                index = self.table.indexAt(event.pos())
                if not index.isValid() and self._hovered_row != -1:
                    old_hover = self._hovered_row
                    self._hovered_row = -1
                    self._start_overlay_animation(self._hover_overlay, '_hover_anim',
                                                  QColor(255, 255, 255, 0), 350)
                    self._refresh_row_font(old_hover)
        return super().eventFilter(obj, event)

    def on_selection_changed(self):
        """Обработка выбора строки. В компактном режиме открывает протокол
        (как раньше); в расширенном - только обновляет статус-бар, не
        переключая вид и не открывая протокол. Плюс - мгновенная (без
        анимации перехода) смена оверлея выделения на яркий цвет строки
        вместо стандартного синего."""
        selected = self.table.selectedItems()
        new_row = selected[0].row() if selected else -1

        if new_row != self._selected_row:
            old_selected = self._selected_row
            self._selected_row = new_row
            if old_selected != -1:
                self._set_overlay_instant(self._selection_overlay, '_selection_anim',
                                          QColor(0, 0, 0, 0))
                self._refresh_row_font(old_selected)
            if new_row != -1:
                rect = self._row_rect(new_row)
                if rect:
                    self._selection_overlay.setGeometry(rect)
                    self._selection_overlay.show()
                    self._selection_overlay.raise_()
                item0 = self.table.item(new_row, 0)
                base = item0.background().color() if item0 else QColor(255, 255, 255)
                self._set_overlay_instant(self._selection_overlay, '_selection_anim',
                                          self._vivid(base))
                self._refresh_row_font(new_row)

            # Принудительно сбрасываем очередь отрисовки ПРЯМО СЕЙЧАС - иначе
            # Qt отложит реальную покраску экрана до конца этого обработчика,
            # а он ещё пойдёт в БД и перестроит всю правую панель (таблицы,
            # графики matplotlib), из-за чего цвет визуально "запаздывал бы"
            self.table.viewport().repaint()
            QApplication.processEvents()

        if not selected:
            return
        row = new_row
        item = self.table.item(row, 0)
        if item is None:
            return
        pump_id = item.data(Qt.UserRole)
        if pump_id is None:
            return
        pump_data = db.get_pump_by_id(pump_id)
        if not pump_data:
            return
        if self.compact_mode:
            self.pump_selected.emit(pump_data)
        else:
            self.pump_status_selected.emit(pump_data)

    def show_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        item = self.table.item(row, 0)
        if not item:
            return
        pump_id = item.data(Qt.UserRole)
        if not pump_id:
            return

        menu = QMenu(self)
        action_view = menu.addAction("Показать протокол")
        action_edit = menu.addAction("Редактировать")
        action_delete = menu.addAction("Удалить")

        action = menu.exec_(self.table.mapToGlobal(pos))

        if action == action_view:
            # Сворачиваем расширенный вид, если он включён
            if not self.compact_mode:
                self.btn_view_toggle.setChecked(False)
            # Выбираем строку и отправляем сигнал
            self.table.selectRow(row)
            self.on_selection_changed()
        elif action == action_edit:
            self.request_edit.emit(pump_id)
        elif action == action_delete:
            self.request_delete.emit(pump_id)

    def on_delete_clicked(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        pump_id = self.table.item(row, 0).data(Qt.UserRole)
        if pump_id:
            self.request_delete.emit(pump_id)

    def load_data(self):
        self.all_pumps = db.get_all_pumps()
        orders = db.get_all_orders()  # возвращает список (id, order_number)
        self.order_map = {}  # словарь {id: отформатированный_номер}
        self.filter_order.blockSignals(True)
        self.filter_order.clear()
        self.filter_order.addItem("Все заказы")
        for oid, onum in orders:
            # Форматируем номер
            order_str = str(onum)
            if '.' in order_str:
                order_str = order_str.rstrip('0').rstrip('.')
            self.order_map[oid] = order_str
            self.filter_order.addItem(order_str, oid)
        self.filter_order.blockSignals(False)
        self.apply_filters()

    def apply_filters(self):
        filters = {}
        search_text = self.search_input.text().strip()
        if search_text:
            filters['pump_number'] = search_text

        verdict = self.filter_verdict.currentText()
        if verdict != 'Все':
            filters['verdict'] = verdict.lower()

        test_type = self.filter_test_type.currentText()
        if test_type != 'Все':
            filters['test_type'] = test_type.lower()

        sealed = self.filter_sealed.currentText()
        if sealed == 'Герметичен':
            filters['is_sealed'] = 1
        elif sealed == 'Не герметичен':
            filters['is_sealed'] = 0

        order_index = self.filter_order.currentIndex()
        if order_index > 0:  # 0 - "Все заказы"
            order_id = self.filter_order.itemData(order_index)
            filters['order_id'] = order_id

        date_from = self.date_from.date().toString('yyyy-MM-dd')
        date_to = self.date_to.date().toString('yyyy-MM-dd')
        if date_from != '2000-01-01' or date_to != QDate.currentDate().toString('yyyy-MM-dd'):
            filters['date_from'] = date_from
            filters['date_to'] = date_to

        if self.only_duplicates.isChecked():
            filters['only_duplicates'] = True

        self.current_filters = filters

        # Подсчёт общего количества
        self.total_records = db.count_pumps(filters)

        # Определяем группировку по номеру (только если включён фильтр дублей)
        group_by_number = self.only_duplicates.isChecked()

        if group_by_number:
            # В режиме дублей группы не должны разрываться постраничной разбивкой -
            # показываем все найденные записи целиком
            filtered = db.get_all_pumps(filters)
        else:
            # Подстраховка: пересчитываем размер страницы прямо сейчас (а не
            # только по событию resize) - гарантирует актуальное значение,
            # даже если окно ещё не успело прислать событие изменения размера
            fresh_page_size = self._compute_dynamic_page_size()
            if fresh_page_size != self.page_size:
                self.page_size = fresh_page_size
                self.current_page = 0
            offset = self.current_page * self.page_size
            filtered = db.get_all_pumps(filters, limit=self.page_size, offset=offset)

        self.display_pumps(filtered, group_by_number=group_by_number)
        self.update_stats(filtered)

        self.update_pagination_label()

        if hasattr(self, 'filters_applied'):
            self.filters_applied.emit(filters)

    def update_stats(self, filtered_pumps):
        if 'order_id' in self.current_filters and self.current_filters['order_id']:
            order_id = self.current_filters['order_id']
            order_str = self.order_map.get(order_id)
            if not order_str:
                self.stats_label.hide()
                return
            total = len(filtered_pumps)
            if total == 0:
                self.stats_label.setText(f"Для заказа №{order_str} нет данных с учётом текущих фильтров.")
                self.stats_label.show()
                return

            good = sum(1 for p in filtered_pumps if p.get('verdict') == 'годен')
            not_sealed = sum(1 for p in filtered_pumps if p.get('is_sealed') is False)
            good_first = sum(1 for p in filtered_pumps if p.get('verdict') == 'годен' and p.get('test_type') == 'первичная')

            good_percent = round(good / total * 100, 1)
            not_sealed_percent = round(not_sealed / total * 100, 1)
            good_first_percent = round(good_first / total * 100, 1)

            if self.compact_mode:
                # Компактный (узкий) режим - фраза "годных с первого
                # предъявления" явно переносится на отдельную строку,
                # иначе слова разрываются посередине при автопереносе
                text = (f"Для заказа №{order_str} проверено <b>{total}</b> насосов: "
                        f"годных — <b>{good}</b> ({good_percent}%), "
                        f"негерметичных — <b>{not_sealed}</b> ({not_sealed_percent}%)<br>"
                        f"годных с первого предъявления — <b>{good_first}</b> ({good_first_percent}%)")
            else:
                # Расширенный режим - места достаточно, вся статистика в
                # одну строку без принудительного переноса
                text = (f"Для заказа №{order_str} проверено <b>{total}</b> насосов: "
                        f"годных — <b>{good}</b> ({good_percent}%), "
                        f"негерметичных — <b>{not_sealed}</b> ({not_sealed_percent}%), "
                        f"годных с первого предъявления — <b>{good_first}</b> ({good_first_percent}%)")
            self.stats_label.setText(text)
            self.stats_label.show()
        else:
            self.stats_label.hide()

    def reset_filters(self):
        self.search_input.clear()
        self.filter_verdict.setCurrentIndex(0)
        self.filter_test_type.setCurrentIndex(0)
        self.filter_sealed.setCurrentIndex(0)
        self.filter_order.setCurrentIndex(0)
        self.date_from.setDate(QDate(2000, 1, 1))
        self.date_to.setDate(QDate.currentDate())
        self.only_duplicates.setChecked(False)
        self.current_page = 0
        self.apply_filters()

    def refresh(self):
        self.current_page = 0
        self.load_data()

    def next_page(self):
        if (self.current_page + 1) * self.page_size < self.total_records:
            self.current_page += 1
            self.apply_filters()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.apply_filters()

    def update_pagination_label(self):
        if self.only_duplicates.isChecked():
            # В режиме дублей показываются сразу все найденные группы,
            # постраничная разбивка не применяется - саму панель пагинации
            # не трогаем (просто отключаем кнопки), пояснение показываем
            # по центру, между пагинацией и счётчиком записей
            self.page_label.setText("Страница 1 из 1")
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)
            self.duplicates_note_label.setText("Группировка по дублям")
            self.count_label.setText(f"Показано записей: {self.total_records}")
            return

        self.duplicates_note_label.setText("")
        total_pages = max(1, (self.total_records + self.page_size - 1) // self.page_size)
        self.page_label.setText(f"Страница {self.current_page + 1} из {total_pages}")
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled((self.current_page + 1) * self.page_size < self.total_records)
        self.count_label.setText(f"Показано записей: {self.total_records}")