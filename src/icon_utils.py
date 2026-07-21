# -*- coding: utf-8 -*-
"""
icon_utils.py - перекраска монохромных SVG-иконок в рантайме.

Иконки в resources/icons/ - силуэты (просто залитая форма, без своего
осмысленного цвета). Вместо того чтобы держать по несколько цветных
копий каждого файла, рендерим SVG в pixmap и перекрашиваем его целиком
через QPainter.CompositionMode_SourceIn - эта операция заменяет цвет
всех непрозрачных пикселей на нужный, сохраняя исходную форму/альфа-
канал. Работает одинаково независимо от того, задан ли в исходном SVG
явный fill или используется чёрный по умолчанию.
"""
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QPainter, QColor, QIcon, QImage
from PyQt5.QtSvg import QSvgRenderer
import numpy as np


def content_fill_ratio(svg_path, reference_size=128):
    """Измеряет, какую долю от общего холста реально занимает непрозрачное
    содержимое SVG (по большей стороне bounding box непрозрачных пикселей).

    Нужно потому, что разные иконки могут иметь разный "запас" пустого
    поля внутри своего viewBox - при рендере в один и тот же пиксельный
    размер такая иконка визуально выглядит МЕНЬШЕ, хотя формально
    запрошен тот же размер. Зная соотношение, можно скорректировать
    размер рендера так, чтобы видимое содержимое совпадало по размеру
    у разных иконок (см. gui.py, _ThemeToggleButton)."""
    renderer = QSvgRenderer(svg_path)
    pixmap = QPixmap(reference_size, reference_size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    image = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
    ptr = image.bits()
    ptr.setsize(image.byteCount())
    arr = np.frombuffer(ptr, dtype=np.uint8).reshape(reference_size, reference_size, 4)
    alpha = arr[:, :, 3]

    rows = np.any(alpha > 10, axis=1)
    cols = np.any(alpha > 10, axis=0)
    if not rows.any():
        return 1.0

    y_indices = np.where(rows)[0]
    x_indices = np.where(cols)[0]
    content_h = y_indices[-1] - y_indices[0] + 1
    content_w = x_indices[-1] - x_indices[0] + 1
    return max(content_w, content_h) / reference_size


def tinted_pixmap(svg_path, color, size=24):
    """Рендерит SVG-файл в QPixmap нужного размера, целиком перекрашенный
    в color (может быть строкой "#rrggbb" или кортежем (r,g,b))."""
    if isinstance(color, tuple):
        color = QColor(*color)
    else:
        color = QColor(color)

    renderer = QSvgRenderer(svg_path)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), color)
    painter.end()

    return pixmap


def plain_pixmap(svg_path, size=24):
    """Рендерит SVG в исходных цветах, БЕЗ перекраски - для иконок,
    у которых несколько значимых цветов (например, красный треугольник
    с белым восклицательным знаком) - tinted_pixmap() в этом случае не
    подходит, т.к. красит вообще всё в один сплошной цвет."""
    renderer = QSvgRenderer(svg_path)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


def tinted_icon(svg_path, color, size=24):
    """То же самое, что tinted_pixmap(), но сразу оборачивает в QIcon -
    удобно для setIcon() у кнопок."""
    return QIcon(tinted_pixmap(svg_path, color, size))


def tinted_pixmap_from_image(path, color, size=24):
    """То же самое, что tinted_pixmap(), но источник - обычная растровая
    картинка (PNG и т.п.), а не SVG - для неё нужен QSvgRenderer, а не
    прямая загрузка через QPixmap()."""
    if isinstance(color, tuple):
        color = QColor(*color)
    else:
        color = QColor(color)

    source = QPixmap(path)
    if source.isNull():
        return QPixmap()
    source = source.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    pixmap = QPixmap(source.size())
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.drawPixmap(0, 0, source)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), color)
    painter.end()
    return pixmap


def tinted_icon_from_image(path, color, size=24):
    return QIcon(tinted_pixmap_from_image(path, color, size))