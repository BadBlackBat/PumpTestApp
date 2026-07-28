# -*- coding: utf-8 -*-
"""
db_sync.py - сверка локальной и сетевой копии базы данных при старте
программы.

Логика применяется ТОЛЬКО если реально включён и настроен сетевой режим
(см. db_settings.is_network_mode_active()) - в локальном режиме (по
умолчанию) этот модуль вообще не используется, поведение программы не
меняется.

Пока реализована только "первая половина" плана - сверка версий и
копирование более свежей сетевой копии при старте. Одновременная
защита от параллельной записи (лок-файл) и офлайн-слияние с журналом
действий - следующие отдельные шаги.
"""
import os
import sqlite3
import shutil
from datetime import datetime
from . import db_settings

# Сколько последних резервных копий хранить перед перезаписью локальной
# базы сетевой версией - старые сверх этого числа удаляются
_BACKUP_KEEP_COUNT = 20


def is_network_reachable():
    """Быстрая проверка доступности сетевого пути - существование файла.
    Не гарантирует, что сеть не отвалится через секунду (на то и есть
    отдельная обработка ошибок при самом копировании), но для целей
    проверки при старте программы этого достаточно."""
    path = db_settings.get_network_db_path()
    if not path:
        return False
    try:
        return os.path.exists(path)
    except OSError:
        return False


def _read_revision(path):
    """Читает revision из файла базы по указанному пути через отдельное,
    короткое подключение - не трогает основное соединение программы.
    Возвращает None, если файл не похож на нашу базу (нет таблицы
    db_meta - например, версия базы старше, чем появление
    многопользовательской работы, или файл повреждён).

    Подключаемся обычным способом (без URI-режима "file:...?mode=ro") -
    ручная сборка URI-строки из пути ненадёжна для сетевых путей вида
    \\\\сервер\\папка\\... (обратные слэши и двойной слэш UNC-пути не
    превращаются в корректный URI простой конкатенацией строк, из-за
    этого сетевые пути и не читались - "неверный формат"). Обычный
    sqlite3.connect(path) принимает путь как есть и работает одинаково
    для локальных и сетевых путей, читать здесь нужно всего одно число,
    полноценная защита "только для чтения" тут не критична."""
    try:
        conn = sqlite3.connect(path, timeout=3)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT revision FROM db_meta WHERE id = 1")
            row = cursor.fetchone()
            return row[0] if row else 0
        finally:
            conn.close()
    except sqlite3.Error:
        return None


def _backup_local_copy(local_path):
    """Резервная копия локальной базы перед тем, как её перезапишет
    более свежая сетевая версия - в папку резервных копий из настроек
    (или рядом с самой базой, если папка не указана явно)."""
    backup_dir = db_settings.get_backup_path()
    if not backup_dir:
        backup_dir = os.path.join(os.path.dirname(local_path), 'backups')
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"pumps_before_sync_{timestamp}.db"
    shutil.copy2(local_path, os.path.join(backup_dir, backup_name))

    _cleanup_old_backups(backup_dir)


def _cleanup_old_backups(backup_dir):
    """Оставляет только последние _BACKUP_KEEP_COUNT резервных копий,
    созданных этим механизмом - чтобы папка не росла бесконечно."""
    try:
        files = [
            os.path.join(backup_dir, f) for f in os.listdir(backup_dir)
            if f.startswith('pumps_before_sync_') and f.endswith('.db')
        ]
        files.sort(key=os.path.getmtime, reverse=True)
        for old_file in files[_BACKUP_KEEP_COUNT:]:
            try:
                os.remove(old_file)
            except OSError:
                pass
    except OSError:
        pass


def get_indicator_mode(sync_status):
    """Переводит статус синхронизации (см. check_and_sync_at_startup) в
    один из четырёх режимов индикатора Network/Local/Offline/Full
    offline (см. widgets/left_panel.py, _DbStatusIndicator).

    'full_offline' проверяется отдельно и имеет приоритет - это
    осознанный выбор пользователя, а не просто "сеть не настроена"."""
    if db_settings.is_full_offline_mode():
        return 'full_offline'
    if sync_status in ('synced', 'up_to_date'):
        return 'network'
    if sync_status == 'network_unreachable':
        return 'offline'
    return 'local'


def check_and_sync_at_startup():
    """Вызывать один раз при старте программы - ДО db.init_db(), чтобы
    миграция схемы применилась уже к финальной (возможно, только что
    скопированной с сети) версии локального файла.

    Возвращает (status, message):
        status - 'local'               - сетевой режим не используется
                  'network_unreachable' - сеть недоступна/повреждена,
                                          работаем с локальной копией
                  'synced'              - скопирована более свежая
                                          сетевая версия
                  'up_to_date'          - локальная копия не старше сети
        message - готовый текст для показа пользователю, либо None
    """
    if not db_settings.is_network_mode_active():
        return 'local', None

    network_path = db_settings.get_network_db_path()
    if not is_network_reachable():
        return 'network_unreachable', (
            "Сетевая папка с базой данных недоступна.\n"
            "Программа продолжит работу с локальной копией данных."
        )

    network_revision = _read_revision(network_path)
    if network_revision is None:
        # Файл по указанному пути существует, но это не похоже на нашу
        # базу (нет db_meta) - не рискуем ничего копировать поверх
        # локальной копии на основании непонятного файла
        return 'network_unreachable', (
            "Не удалось прочитать сетевую базу данных (файл повреждён\n"
            "или имеет неожиданный формат).\n"
            "Программа продолжит работу с локальной копией данных."
        )

    local_path = db_settings.get_local_db_path()
    local_exists = os.path.exists(local_path)
    local_revision = _read_revision(local_path) if local_exists else None

    if local_revision is not None and local_revision >= network_revision:
        return 'up_to_date', None

    # Сетевая версия новее (или локальной копии ещё нет вовсе) -
    # копируем к себе. Резервная копия локальной версии - на всякий
    # случай, если только что была локальная копия, которую мы заменяем.
    try:
        if local_exists:
            _backup_local_copy(local_path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        shutil.copy2(network_path, local_path)
        return 'synced', (
            f"Загружена более свежая версия базы данных из сетевой папки "
            f"(ревизия {network_revision})."
        )
    except OSError as e:
        return 'network_unreachable', (
            f"Не удалось скопировать сетевую базу данных ({e}).\n"
            "Программа продолжит работу с локальной копией данных."
        )