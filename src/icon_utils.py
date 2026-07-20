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
from PyQt5.QtGui import QPixmap, QPainter, QColor, QIcon
from PyQt5.QtSvg import QSvgRenderer


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


def tinted_icon(svg_path, color, size=24):
    """То же самое, что tinted_pixmap(), но сразу оборачивает в QIcon -
    удобно для setIcon() у кнопок."""
    return QIcon(tinted_pixmap(svg_path, color, size))