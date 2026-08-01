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
import re
import time
import getpass
import sqlite3
import shutil
from datetime import datetime
from . import db_settings
from . import db_lock
from . import database

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
    path = os.path.normpath(path)
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
    (или рядом с самой базой, если папка не указана явно). Имя файла
    включает ревизию на момент копирования - удобно для экрана
    "Восстановить из резервной копии" (видно не просто дату, а конкретное
    состояние базы, к которому можно вернуться)."""
    backup_dir = db_settings.get_backup_path()
    if not backup_dir:
        backup_dir = os.path.join(os.path.dirname(local_path), 'backups')
    os.makedirs(backup_dir, exist_ok=True)

    revision = database.get_current_revision()
    revision_display = database.format_revision_display(revision).replace('.', '_')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"pumps_rev{revision_display}_{timestamp}.db"
    shutil.copy2(local_path, os.path.join(backup_dir, backup_name))

    _cleanup_old_backups(backup_dir)


def _cleanup_old_backups(backup_dir):
    """Оставляет только последние _BACKUP_KEEP_COUNT резервных копий,
    созданных этим механизмом - чтобы папка не росла бесконечно.
    Учитывает и старый формат имени файла (pumps_before_sync_...), и
    новый, с ревизией (pumps_rev...) - на случай, если старые копии уже
    существуют на диске с прошлых версий программы."""
    try:
        files = [
            os.path.join(backup_dir, f) for f in os.listdir(backup_dir)
            if (f.startswith('pumps_before_sync_') or f.startswith('pumps_rev')) and f.endswith('.db')
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


def _read_network_revision_and_description():
    """Читает (ревизия, описание последнего действия) прямо из сетевого
    файла базы - общая часть для check_for_remote_changes() и
    get_network_revision_now(). Возвращает (None, None), если сеть не
    активна/недоступна/файл не похож на нашу базу."""
    if not db_settings.is_network_mode_active():
        return None, None
    if not is_network_reachable():
        return None, None

    network_path = os.path.normpath(db_settings.get_network_db_path())
    try:
        conn = sqlite3.connect(network_path, timeout=2)
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT revision, last_action_description FROM db_meta WHERE id = 1')
            row = cursor.fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return None, None

    if not row:
        return None, None
    return row[0], row[1]


def get_network_revision_now():
    """Текущая ревизия СЕТЕВОЙ базы прямо сейчас - используется для
    инициализации отслеживания изменений (см. MainWindow.__init__,
    gui.py) именно сетевым значением, а НЕ локальным
    (database.get_current_revision()).

    Это важно: локальная и сетевая ревизии могут ЗАКОННО отличаться (в
    частности, check_and_sync_at_startup() может решить "мы не старше
    сети, всё в порядке" - up_to_date - не будучи РОВНО равной сети, а
    просто не будучи СТАРШЕ). Если бы отслеживание стартовало со
    значения локальной базы, каждая последующая периодическая проверка
    сравнивала бы сеть с числом, которое никогда с ней не совпадёт -
    и бегущая строка срабатывала бы постоянно, с самого начала работы
    программы, показывая уже неактуальное "последнее действие"."""
    revision, _ = _read_network_revision_and_description()
    return revision


def check_for_remote_changes(last_known_revision):
    """Проверяет, изменилась ли сетевая база с момента last_known_revision -
    вызывается периодически (раз в несколько секунд) ВО ВРЕМЯ работы
    программы, в отличие от check_and_sync_at_startup() (тот - только
    один раз при запуске). Специально ничего не копирует и не
    синхронизирует - только сообщает, что что-то изменилось и что именно
    (описание последнего действия) - решение, что делать дальше (пока -
    просто показать уведомление), остаётся за вызывающим кодом.

    ВАЖНО: last_known_revision должен быть получен через
    get_network_revision_now() (сетевое значение), а НЕ через
    database.get_current_revision() (локальное) - см. подробное
    объяснение в get_network_revision_now().

    Возвращает (новая_ревизия, описание_последнего_действия), если
    изменение обнаружено, иначе None (в том числе если сетевой режим не
    активен или сеть сейчас недоступна - опрос в этом случае просто
    тихо ничего не делает, не показывая никаких ошибок - в отличие от
    check_and_sync_at_startup, здесь недоступность сети не повод
    беспокоить пользователя лишним сообщением каждые несколько секунд)."""
    revision, description = _read_network_revision_and_description()
    if revision is not None and revision != last_known_revision:
        return revision, description
    return None



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

    network_path = os.path.normpath(db_settings.get_network_db_path())
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
        if local_revision == network_revision:
            # Действительно совпадают - фиксируем точку синхронизации
            db_settings.set_last_sync_revision(local_revision)
        # local_revision > network_revision - значит, есть локальные
        # правки, которые ещё НЕ выгружены в сеть (например, накопились
        # до включения сетевого режима) - точку синхронизации специально
        # НЕ трогаем, чтобы статус "не синхронизировано" остался верным
        return 'up_to_date', None

    # Сетевая версия новее (или локальной копии ещё нет вовсе) -
    # копируем к себе. Резервная копия локальной версии - на всякий
    # случай, если только что была локальная копия, которую мы заменяем.
    try:
        if local_exists:
            _backup_local_copy(local_path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        shutil.copy2(network_path, local_path)
        db_settings.set_last_sync_revision(network_revision)
        return 'synced', (
            f"Загружена более свежая версия базы данных из сетевой папки "
            f"(ревизия {network_revision})."
        )
    except OSError:
        return 'network_unreachable', (
            "Не удалось скопировать сетевую базу данных - возможно, "
            "сеть только что стала недоступна.\n"
            "Программа продолжит работу с локальной копией данных."
        )


def _get_backup_dir():
    """Папка резервных копий - из настроек, или рядом с локальной базой,
    если явно не указана (та же логика, что и в _backup_local_copy)."""
    backup_dir = db_settings.get_backup_path()
    if not backup_dir:
        local_path = os.path.normpath(db_settings.get_local_db_path())
        backup_dir = os.path.join(os.path.dirname(local_path), 'backups')
    return backup_dir


def list_backups():
    """Список доступных резервных копий - для диалога "Восстановить из
    резервной копии" (настройки). Каждый элемент -
    (путь_к_файлу, дата_время_создания, ревизия_или_None) - новые
    сначала. Ревизия - None для копий старого формата имени (до того,
    как мы стали дописывать её в название файла)."""
    backup_dir = _get_backup_dir()
    if not os.path.isdir(backup_dir):
        return []

    results = []
    for fname in os.listdir(backup_dir):
        if not fname.endswith('.db'):
            continue
        if not (fname.startswith('pumps_before_sync_') or fname.startswith('pumps_rev')):
            continue
        full_path = os.path.join(backup_dir, fname)
        revision_display = None
        m = re.match(r'pumps_rev(\d+_\d+)_', fname)
        if m:
            revision_display = m.group(1).replace('_', '.')
        try:
            mtime = os.path.getmtime(full_path)
        except OSError:
            continue
        results.append((full_path, datetime.fromtimestamp(mtime), revision_display))

    results.sort(key=lambda item: item[1], reverse=True)
    return results


def restore_backup(backup_path):
    """Восстанавливает локальную базу из выбранной резервной копии -
    просто перезаписывает локальный файл содержимым резервной копии.
    Не трогает сетевую базу и точку синхронизации никак не обновляет -
    после восстановления локальная база, скорее всего, будет "не
    синхронизирована" (что и корректно - раз мы вернулись к более
    старому состоянию, отличному от того, что видела сеть)."""
    local_path = os.path.normpath(db_settings.get_local_db_path())
    try:
        shutil.copy2(backup_path, local_path)
    except OSError as e:
        return 'error', f"Не удалось восстановить базу данных: {e}"
    return 'restored', "Локальная база данных восстановлена из резервной копии."


# Порог "устарел" для метки присутствия - если файл не обновлялся
# дольше этого времени, считаем, что пользователь закрыл программу.
# Обновление метки привязано к тому же тику опроса сети (раз в 8 секунд,
# см. gui.py), поэтому 30 секунд дают достаточный запас (3-4 обновления),
# но всё ещё быстро отражают реальность, а не спустя долгие минуты.
PRESENCE_STALE_SECONDS = 30
_PRESENCE_SUBDIR = 'active_users'

# Кэш: для каждого файла присутствия - (последнее замеченное содержимое,
# когда мы его в последний раз ЗАМЕТИЛИ - по нашим собственным часам).
# Используется в get_active_user_count(), чтобы не сравнивать чужое
# встроенное время с текущим временем этого компьютера напрямую (часы
# разных компьютеров в сети не обязательно синхронизированы).
_presence_seen_cache = {}


def _presence_dir():
    network_path = os.path.normpath(db_settings.get_network_db_path())
    return os.path.join(os.path.dirname(network_path), _PRESENCE_SUBDIR)


def update_presence():
    """Обновляет метку "я тут" - маленький файл с именем текущего
    пользователя, внутри - время последнего отклика (по НАШИМ собственным
    часам, не полагаемся на метаданные файловой системы сетевой шары -
    та же история, что и с лок-файлом в db_lock.py, где mtime сетевой
    папки оказался ненадёжен). Молча ничего не делает, если сетевой
    режим не используется или сеть недоступна прямо сейчас."""
    if not db_settings.is_network_mode_active():
        return
    if not is_network_reachable():
        return
    try:
        presence_dir = _presence_dir()
        os.makedirs(presence_dir, exist_ok=True)
        user = getpass.getuser()
        path = os.path.join(presence_dir, f"{user}.presence")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(str(time.time()))
    except OSError:
        pass


def get_active_user_count():
    """Сколько пользователей сейчас активно работают с сетевой базой -
    по свежести меток присутствия (см. update_presence). Возвращает
    None, если сетевой режим не используется или сеть недоступна прямо
    сейчас (не можем узнать) - иначе число активных пользователей
    (минимум 1 - мы сами, раз смогли дойти до этой проверки).

    ВАЖНО: не сравнивает встроенное в чужой файл время напрямую с
    текущим временем этого компьютера - на практике часы разных
    компьютеров в сети не обязательно синхронизированы (даже на
    несколько минут расхождение приводит к тому, что один компьютер
    всегда видит метки другого как "протухшие", хотя они свежие).
    Вместо этого отслеживается, изменилось ли СОДЕРЖИМОЕ конкретного
    файла с момента последней проверки - а "сколько времени прошло с
    последнего замеченного изменения" меряется ИСКЛЮЧИТЕЛЬНО по
    собственным часам этого компьютера (см. _presence_seen_cache) -
    чужое время в этом сравнении не участвует вообще."""
    if not db_settings.is_network_mode_active():
        return None
    if not is_network_reachable():
        return None
    try:
        presence_dir = _presence_dir()
        if not os.path.isdir(presence_dir):
            return 1
        now = time.time()
        count = 0
        seen_files = set()
        for fname in os.listdir(presence_dir):
            if not fname.endswith('.presence'):
                continue
            seen_files.add(fname)
            try:
                with open(os.path.join(presence_dir, fname), 'r', encoding='utf-8') as f:
                    current_value = f.read().strip()
            except OSError:
                continue

            cached = _presence_seen_cache.get(fname)
            if cached is None or cached[0] != current_value:
                # Значение изменилось (или видим этот файл впервые) -
                # прямо сейчас, по нашим собственным часам, точно "свежее"
                _presence_seen_cache[fname] = (current_value, now)
                count += 1
            else:
                _, last_seen_locally = cached
                if now - last_seen_locally <= PRESENCE_STALE_SECONDS:
                    count += 1
                # иначе - значение не менялось дольше порога (по нашим
                # же часам) - считаем пользователя неактивным

        # Подчищаем кэш от файлов, которые вообще исчезли (пользователь
        # закрыл программу достаточно давно, файл мог быть удалён кем-то
        # ещё, или просто больше не существует) - не даём кэшу расти
        # бесконечно
        for stale_fname in list(_presence_seen_cache.keys()):
            if stale_fname not in seen_files:
                del _presence_seen_cache[stale_fname]
        return max(count, 1)
    except OSError:
        return None


def is_synced():
    """True, если локальная база не отличается от той точки, когда она
    последний раз точно совпадала с сетью (после подтягивания или
    успешной выгрузки) - т.е. нет накопленных, ещё не выгруженных
    локальных изменений. См. db_settings.get_last_sync_revision()."""
    return database.get_current_revision() == db_settings.get_last_sync_revision()


def push_local_to_network():
    """Выгружает локальные изменения в сетевую базу - по кнопке (не
    происходит автоматически).

    Возвращает (status, message):
        'not_network_mode'     - сетевой режим не используется
        'network_unreachable'  - сеть недоступна прямо сейчас
        'nothing_to_push'      - нет несохранённых локальных изменений
        'network_ahead'        - сеть уже изменилась с последней точки
                                  синхронизации - нужно сначала подтянуть
                                  свежую версию (force_pull_network_to_local),
                                  повторить свои правки поверх нее и
                                  попробовать выгрузить снова
        'locked'                - сейчас идёт запись другого пользователя
        'error'                 - не удалось скопировать файл
        'pushed'                - успешно выгружено
    """
    if not db_settings.is_network_mode_active():
        return 'not_network_mode', "Сетевой режим не используется."
    if not is_network_reachable():
        return 'network_unreachable', "Сетевая папка сейчас недоступна. Попробуйте позже."

    local_revision = database.get_current_revision()
    last_sync = db_settings.get_last_sync_revision()
    if local_revision == last_sync:
        return 'nothing_to_push', "Нет несохранённых изменений - уже всё синхронизировано."

    network_revision = get_network_revision_now()
    if network_revision is not None and network_revision != last_sync:
        return 'network_ahead', (
            "Пока вы работали, сеть уже изменилась (кто-то другой успел "
            "выгрузить свои правки). Сначала подтяните свежую версию из "
            "сети (кнопка Network -> Local), затем внесите свои изменения "
            "заново поверх неё и повторите выгрузку."
        )

    try:
        with db_lock.acquire_write_lock():
            local_path = os.path.normpath(db_settings.get_local_db_path())
            network_path = os.path.normpath(db_settings.get_network_db_path())
            shutil.copy2(local_path, network_path)
    except db_lock.DatabaseLockedError as e:
        return 'locked', str(e)
    except OSError:
        return 'error', (
            "Не удалось выгрузить изменения в сеть - сеть, возможно, "
            "только что стала недоступна. Попробуйте ещё раз."
        )

    db_settings.set_last_sync_revision(local_revision)
    return 'pushed', (
        f"Изменения выгружены в сетевую базу "
        f"(ревизия {database.format_revision_display(local_revision)})."
    )


def force_pull_network_to_local():
    """Принудительно копирует сетевую базу поверх локальной - по кнопке
    Network -> Local. В отличие от check_and_sync_at_startup(), делает
    это БЕЗОСЛОВНО (не сравнивает ревизии) - вызывающий код должен сам
    заранее предупредить пользователя, если у него есть несохранённые
    локальные изменения (is_synced() == False), которые будут потеряны.

    Возвращает (status, message) в том же духе, что и другие функции
    этого модуля."""
    if not db_settings.is_network_mode_active():
        return 'not_network_mode', "Сетевой режим не используется."
    if not is_network_reachable():
        return 'network_unreachable', "Сетевая папка сейчас недоступна. Попробуйте позже."

    network_revision, _ = _read_network_revision_and_description()
    if network_revision is None:
        return 'error', "Не удалось прочитать сетевую базу данных."

    local_path = os.path.normpath(db_settings.get_local_db_path())
    network_path = os.path.normpath(db_settings.get_network_db_path())
    try:
        if os.path.exists(local_path):
            _backup_local_copy(local_path)
        shutil.copy2(network_path, local_path)
    except OSError:
        return 'error', (
            "Не удалось скопировать сетевую базу данных - сеть, "
            "возможно, только что стала недоступна. Попробуйте ещё раз."
        )

    db_settings.set_last_sync_revision(network_revision)
    return 'pulled', (
        f"Локальная копия обновлена из сети "
        f"(ревизия {database.format_revision_display(network_revision)})."
    )