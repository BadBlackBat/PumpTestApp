# -*- coding: utf-8 -*-
"""
db_settings.py - настройки расположения базы данных (локальный ПК или
общая сетевая папка) и режима работы с ней.

ВАЖНО: по умолчанию (если пользователь ничего не настраивал) поведение
программы должно остаться РОВНО таким же, как было всегда - локальный
файл базы рядом с программой. Сетевой режим - это осознанный выбор
пользователя через настройки, а не что-то, что включается само.

Хранится через QSettings - тот же принцип, что уже используется для
темы оформления и переключателя размытия (см. styles.py).
"""
import os
from PyQt5.QtCore import QSettings

# Путь по умолчанию - ровно тот же, что был в database.py изначально,
# до появления многопользовательской работы. Ничего не меняется для
# тех, кто не открывал эти настройки ни разу.
_DEFAULT_LOCAL_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'pumps.db'
)

# Режимы работы с базой:
#   'local'  - обычный локальный файл на этом ПК (умолчание, как и было)
#   'network' - общий файл в сетевой папке, с проверкой версии при
#               старте и (в дальнейших шагах) защитой от одновременной
#               записи и уведомлениями об изменениях
MODE_LOCAL = 'local'
MODE_NETWORK = 'network'


def _settings():
    return QSettings("PumpTestApp", "MainSettings")


def get_db_mode():
    """'local' (умолчание) или 'network'."""
    return _settings().value("db_mode", MODE_LOCAL, type=str)


def set_db_mode(mode):
    assert mode in (MODE_LOCAL, MODE_NETWORK)
    _settings().setValue("db_mode", mode)


def get_local_db_path():
    """Путь к локальной копии базы - используется всегда в режиме
    'local', и как рабочая копия (кэш) в режиме 'network'."""
    return _settings().value("local_db_path", _DEFAULT_LOCAL_DB_PATH, type=str)


def set_local_db_path(path):
    _settings().setValue("local_db_path", path)


def get_network_db_path():
    """Путь к общему файлу базы в сетевой папке. Пустая строка - сетевой
    путь ещё не настроен (даже если режим уже переключён на 'network' -
    в этом случае стоит считать сетевой режим не готовым к работе)."""
    return _settings().value("network_db_path", "", type=str)


def set_network_db_path(path):
    _settings().setValue("network_db_path", path)


def get_backup_path():
    """Папка для резервных копий на локальном ПК пользователя. Пусто -
    используется папка рядом с локальной базой (см. database.py)."""
    return _settings().value("backup_path", "", type=str)


def set_backup_path(path):
    _settings().setValue("backup_path", path)


def is_full_offline_mode():
    """Полный офлайн-режим - программа даже не пытается обращаться к
    сетевой базе (не проверяет версию при старте, не предлагает
    слияние). Полезно для пользователей, которые сознательно всегда
    работают только с локальной копией, даже если формально выбран
    режим 'network' у остальных в группе."""
    return _settings().value("db_full_offline", False, type=bool)


def set_full_offline_mode(value):
    _settings().setValue("db_full_offline", bool(value))


def is_network_mode_active():
    """Сетевой режим реально активен только если: выбран режим
    'network', задан сетевой путь, и НЕ включён полный офлайн-режим.
    Используется вместо прямой проверки get_db_mode() везде, где нужно
    решить "работать ли сейчас с сетью" - одна точка правды вместо
    повторения всех трёх условий в разных местах."""
    return (
        get_db_mode() == MODE_NETWORK
        and bool(get_network_db_path())
        and not is_full_offline_mode()
    )