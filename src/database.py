import sqlite3
import os
import json
import re
import uuid
from datetime import datetime
from . import db_settings
from . import db_lock

def get_active_db_path():
    """Возвращает путь к файлу базы, с которым программа реально
    работает прямо сейчас.

    По умолчанию (пользователь ничего не настраивал) - тот же локальный
    путь, что был всегда, поведение не меняется. Если явно выбран
    сетевой режим - используется ЛОКАЛЬНАЯ РАБОЧАЯ КОПИЯ (см.
    get_local_db_path) - сама программа всегда читает/пишет локальный
    файл; синхронизация с сетевым файлом - отдельный, более поздний шаг
    (проверка версий, лок, слияние), не часть этой функции."""
    return db_settings.get_local_db_path()

# Оставлено для обратной совместимости - код, ссылающийся на
# database.DB_PATH напрямую, продолжит работать. Новый код должен
# использовать get_active_db_path().
DB_PATH = get_active_db_path()

def get_connection():
    path = get_active_db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return sqlite3.connect(path)

def init_db():
    """Создаёт все таблицы, если их нет."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Таблица модификаций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS modifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                norm_graph1_min TEXT,   -- JSON массив значений (мин)
                norm_graph1_max TEXT,   -- JSON массив значений (макс)
                norm_graph1_x TEXT,     -- JSON массив точек оборотов (по умолчанию 8 точек)
                norm_graph2_min TEXT,
                norm_graph2_max TEXT,
                norm_graph2_x TEXT,
                norm_graph3_min TEXT,   -- значения для теста 3
                norm_graph3_max TEXT,
                norm_graph3_x TEXT,     -- JSON массив точек силы тока (по умолчанию 11 точек)
                pressure_min REAL,
                pressure_max REAL,
                seal_rules_json TEXT   -- JSON: {"g33": "отсутствуют", ...} требования по герметичности
            )
        ''')
        
        # Таблица заказов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT UNIQUE NOT NULL
            )
        ''')
        
        # Таблица насосов (протоколы)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pumps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pump_number TEXT NOT NULL,
                test_date TEXT NOT NULL,   -- ISO формат YYYY-MM-DD
                test_type TEXT,            -- 'первичная' / 'повторная'
                modification_id INTEGER,
                order_id INTEGER,
                results_json TEXT,         -- JSON с данными G5-G32 (все измерения)
                seal_results_json TEXT,    -- JSON с G33-G37
                verdict TEXT,              -- 'годен' / 'не годен'
                is_sealed BOOLEAN,
                note TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (modification_id) REFERENCES modifications(id) ON DELETE SET NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL
            )
        ''')
        
        # Индексы для быстрого поиска
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pump_number ON pumps(pump_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_test_date ON pumps(test_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_modification ON pumps(modification_id)')

        cursor.execute("PRAGMA table_info(pumps)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'edit_history' not in columns:
            cursor.execute('ALTER TABLE pumps ADD COLUMN edit_history TEXT')
        if 'edit_date' not in columns:
            cursor.execute('ALTER TABLE pumps ADD COLUMN edit_date TEXT')
        if 'changed_fields_json' not in columns:
            cursor.execute('ALTER TABLE pumps ADD COLUMN changed_fields_json TEXT')
        if 'last_edited_at' not in columns:
            # Точная (до секунды) метка последнего изменения ИМЕННО этой
            # записи - в отличие от edit_date (только дата, без времени),
            # нужна для защиты от одновременного редактирования одной и
            # той же записи двумя пользователями (см. check_pump_unchanged)
            cursor.execute('ALTER TABLE pumps ADD COLUMN last_edited_at TEXT')
        if 'uuid' not in columns:
            # Уникальный идентификатор записи, НЕ зависящий от внутреннего
            # автоинкрементного id - тот может совпасть у двух записей,
            # независимо созданных на разных компьютерах (оба стартовали
            # с одной и той же версии базы). uuid нужен для надёжного
            # сопоставления "это та же самая запись или разные" при умном
            # слиянии добавлений (см. db_sync.smart_merge_push).
            cursor.execute('ALTER TABLE pumps ADD COLUMN uuid TEXT')
            # Существующие записи (созданные до этой доработки) ещё не
            # имеют uuid - генерируем его задним числом ПРЕДСКАЗУЕМО (не
            # случайно!) - по стабильным полям (id, created_at), которые
            # уже были одинаковыми на всех синхронизированных копиях этой
            # записи. Если бы здесь использовался uuid.uuid4() (случайный),
            # запись, уже синхронизированная между компьютерами ДО
            # появления uuid, получила бы РАЗНЫЕ значения на разных
            # машинах (миграция выполняется независимо на каждой) - из-за
            # этого умное слияние не находило бы совпадений вообще ни для
            # одной старой записи и считало бы все их "новыми", приводя к
            # полному дублированию базы. uuid.uuid5() с одинаковым входом
            # всегда даёт одинаковый результат - на любом компьютере.
            cursor.execute('SELECT id, created_at FROM pumps WHERE uuid IS NULL')
            for pump_id, created_at in cursor.fetchall():
                stable_key = f"pump-{pump_id}-{created_at}"
                deterministic_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, stable_key))
                cursor.execute('UPDATE pumps SET uuid = ? WHERE id = ?', (deterministic_uuid, pump_id))
        else:
            # Отдельный, безусловный шаг (выполняется при каждом запуске,
            # но дёшево - трогает только реально расходящиеся значения):
            # пересчитывает uuid по той же предсказуемой формуле для ВСЕХ
            # записей и обновляет только те, что не совпадают с уже
            # сохранённым значением.
            #
            # Нужен, чтобы исправить уже существующие базы, успевшие
            # получить НЕПРАВИЛЬНЫЕ, случайные uuid от более ранней
            # (ошибочной) версии этой миграции - та использовала
            # uuid.uuid4() (случайный), из-за чего одна и та же, уже
            # синхронизированная между компьютерами запись получала на
            # разных машинах разные uuid, и умное слияние считало все
            # старые записи "новыми", приводя к полному дублированию базы
            # при первой же попытке слияния. Безопасно применять и к
            # записям, у которых uuid уже был правильным - формула даёт
            # тот же результат, реального обновления не происходит.
            cursor.execute('SELECT id, created_at, uuid FROM pumps')
            for pump_id, created_at, current_uuid in cursor.fetchall():
                stable_key = f"pump-{pump_id}-{created_at}"
                deterministic_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, stable_key))
                if current_uuid != deterministic_uuid:
                    cursor.execute('UPDATE pumps SET uuid = ? WHERE id = ?', (deterministic_uuid, pump_id))

        # Миграция: если БД создана до появления колонок с X-значениями - добавляем их
        cursor.execute("PRAGMA table_info(modifications)")
        mod_columns = [col[1] for col in cursor.fetchall()]
        for col_name in ('norm_graph1_x', 'norm_graph2_x', 'norm_graph3_x'):
            if col_name not in mod_columns:
                cursor.execute(f'ALTER TABLE modifications ADD COLUMN {col_name} TEXT')

        # Флажок расширенного шаблона (больше точек по оборотам) - явно
        # задаётся при создании модификации, а не вычисляется по
        # количеству точек (см. обсуждение: вычисление по количеству
        # рискованно ошибиться, если кто-то случайно наполнит обычную
        # модификацию бОльшим числом точек)
        if 'is_extended_template' not in mod_columns:
            cursor.execute(
                'ALTER TABLE modifications ADD COLUMN is_extended_template BOOLEAN DEFAULT 0'
            )

        # Однострочная таблица метаданных базы - нужна для многопользова-
        # тельской работы (сверка версий при старте, уведомления об
        # изменениях у других пользователей). revision растёт при любой
        # операции записи (см. bump_revision ниже).
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS db_meta (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                revision INTEGER NOT NULL DEFAULT 0,
                last_modified_at TEXT,
                last_modified_by TEXT,
                last_action_description TEXT
            )
        ''')
        cursor.execute('INSERT OR IGNORE INTO db_meta (id, revision) VALUES (1, 0)')

        # Журнал действий - нужен для офлайн-слияния (см. обсуждение):
        # при восстановлении сети после офлайн-работы проигрывается
        # запись за записью, с проверкой конфликтов по record_revision
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS change_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action_type TEXT NOT NULL,       -- 'add' / 'update' / 'delete'
                entity_type TEXT NOT NULL,       -- 'pump' / 'modification' / 'order'
                entity_id INTEGER,
                record_revision INTEGER,         -- ревизия базы на момент действия
                description TEXT
            )
        ''')

        conn.commit()
        print("База данных инициализирована.")


# Сколько последних записей журнала изменений хранить (см. bump_revision,
# get_recent_changes) - старые автоматически удаляются
_CHANGE_LOG_KEEP_COUNT = 30


def bump_revision(description, conn=None):
    """Увеличивает ревизию базы и записывает, что именно произошло -
    вызывать при любой операции записи (добавление/изменение/удаление
    насоса, модификации, заказа).

    Ревизия хранится как одно целое число ГГММДД*1000 + счётчик (год
    идёт первым - чтобы обычное числовое сравнение "какая ревизия
    больше" совпадало с хронологическим порядком; если бы день шёл
    первым - как в привычном отображении, см. format_revision_display -
    сравнение чисел ломалось бы на стыке месяцев/годов, например
    01.01.27 -> 010127 оказалось бы МЕНЬШЕ, чем 31.12.26 -> 311226,
    хотя по факту позже). Счётчик растёт в течение дня при каждом
    изменении и сбрасывается на 1 с началом нового дня.

    conn - если операция уже идёт внутри своего соединения/транзакции
    (обычный случай - большинство функций ниже открывают with
    get_connection() as conn), нужно передать именно его, чтобы
    увеличение ревизии было частью той же транзакции и не оказалось
    рассинхронизировано, если основная операция вдруг не сохранится.

    Пока просто обновляет db_meta - привязка к change_log (для будущего
    офлайн-слияния) добавится отдельным шагом, когда будем реализовывать
    сам механизм слияния."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        # Имя пользователя, внёсшего изменение - то же самое (учётная
        # запись Windows), что уже используется для лок-файла (db_lock.py)
        # - единообразно, не нужно ничего отдельно настраивать
        import getpass
        user = getpass.getuser()
        description_with_user = f"{user}: {description}"

        cursor = conn.cursor()
        cursor.execute('SELECT revision FROM db_meta WHERE id = 1')
        row = cursor.fetchone()
        current_revision = row[0] if row and row[0] else 0

        now = datetime.now()
        today_prefix = int(now.strftime('%y%m%d'))  # ГГММДД
        current_prefix = current_revision // 1000
        current_counter = current_revision % 1000

        new_counter = current_counter + 1 if current_prefix == today_prefix else 1
        new_revision = today_prefix * 1000 + new_counter

        cursor.execute(
            'UPDATE db_meta SET revision = ?, last_modified_at = ?, '
            'last_modified_by = ?, last_action_description = ? WHERE id = 1',
            (new_revision, now.isoformat(timespec='seconds'), user, description_with_user)
        )

        # Журнал изменений - для просмотра в "Журнал изменений базы
        # данных" (настройки). Храним только последние
        # _CHANGE_LOG_KEEP_COUNT записей - старые автоматически удаляются,
        # чтобы таблица не росла бесконечно.
        cursor.execute(
            'INSERT INTO change_log '
            '(timestamp, action_type, entity_type, entity_id, record_revision, description) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (now.isoformat(timespec='seconds'), 'write', 'unknown', None, new_revision, description_with_user)
        )
        cursor.execute('''
            DELETE FROM change_log WHERE id NOT IN (
                SELECT id FROM change_log ORDER BY id DESC LIMIT ?
            )
        ''', (_CHANGE_LOG_KEEP_COUNT,))

        if own_conn:
            conn.commit()
    finally:
        if own_conn:
            conn.close()


def get_recent_changes(limit=_CHANGE_LOG_KEEP_COUNT):
    """Возвращает последние записи журнала изменений (самые новые -
    первыми) - для диалога "Журнал изменений базы данных" в настройках.
    Каждая запись - (timestamp, description, record_revision)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT timestamp, description, record_revision FROM change_log '
            'ORDER BY id DESC LIMIT ?', (limit,)
        )
        return cursor.fetchall()


def format_revision_display(revision):
    """Преобразует внутреннее значение ревизии (см. bump_revision - там
    год идёт первым, для правильной сортировки) в привычный человеку вид
    ДДММГГ.счётчик - например, 280726.1 для 28 июля 2026 года, первое
    изменение за день."""
    if not revision:
        return "—"
    prefix = revision // 1000
    counter = revision % 1000
    yy = prefix // 10000
    mm = (prefix // 100) % 100
    dd = prefix % 100
    return f"{dd:02d}{mm:02d}{yy:02d}.{counter}"


def get_current_revision():
    """Текущая ревизия локальной базы - для сверки с сетевой копией при
    старте программы (следующий шаг реализации)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT revision FROM db_meta WHERE id = 1')
        row = cursor.fetchone()
        return row[0] if row else 0

# ---------- Работа с модификациями ----------
def add_modification(name, norm_graph1_min, norm_graph1_max, norm_graph1_x,
                     norm_graph2_min, norm_graph2_max, norm_graph2_x,
                     norm_graph3_min, norm_graph3_max, norm_graph3_x,
                     pressure_min, pressure_max, seal_rules=None):
    """
    Добавляет новую модификацию (или заменяет существующую с тем же именем).
    Все norm_* - это строки JSON (массивы чисел).
    """
    with db_lock.acquire_write_lock(), get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO modifications 
            (name, norm_graph1_min, norm_graph1_max, norm_graph1_x,
             norm_graph2_min, norm_graph2_max, norm_graph2_x,
             norm_graph3_min, norm_graph3_max, norm_graph3_x,
             pressure_min, pressure_max, seal_rules_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, norm_graph1_min, norm_graph1_max, norm_graph1_x,
              norm_graph2_min, norm_graph2_max, norm_graph2_x,
              norm_graph3_min, norm_graph3_max, norm_graph3_x,
              pressure_min, pressure_max, seal_rules))
        bump_revision(f"Добавлена модификация «{name}»", conn)
        conn.commit()
        return cursor.lastrowid

MOD_COLUMNS = '''
    id, name, norm_graph1_min, norm_graph1_max, norm_graph1_x,
    norm_graph2_min, norm_graph2_max, norm_graph2_x,
    norm_graph3_min, norm_graph3_max, norm_graph3_x,
    pressure_min, pressure_max, seal_rules_json
'''

def get_modification_by_name(name):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f'SELECT {MOD_COLUMNS} FROM modifications WHERE name = ?', (name,))
        row = cursor.fetchone()
        if row:
            return _row_to_modification_dict(row)
        return None

def get_modification_by_id(mod_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f'SELECT {MOD_COLUMNS} FROM modifications WHERE id = ?', (mod_id,))
        row = cursor.fetchone()
        if row:
            return _row_to_modification_dict(row)
        return None

def _row_to_modification_dict(row):
    from . import utils
    return {
        'id': row[0],
        'name': row[1],
        'norm_graph1_min': json.loads(row[2]) if row[2] else [],
        'norm_graph1_max': json.loads(row[3]) if row[3] else [],
        'norm_graph1_x': json.loads(row[4]) if row[4] else list(utils.DEFAULT_GRAPH1_X),
        'norm_graph2_min': json.loads(row[5]) if row[5] else [],
        'norm_graph2_max': json.loads(row[6]) if row[6] else [],
        'norm_graph2_x': json.loads(row[7]) if row[7] else list(utils.DEFAULT_GRAPH2_X),
        'norm_graph3_min': json.loads(row[8]) if row[8] else [],
        'norm_graph3_max': json.loads(row[9]) if row[9] else [],
        'norm_graph3_x': json.loads(row[10]) if row[10] else list(utils.DEFAULT_GRAPH3_X),
        'pressure_min': row[11],
        'pressure_max': row[12],
        'seal_rules': json.loads(row[13]) if row[13] else dict(utils.DEFAULT_SEAL_REQUIREMENTS)
    }

def get_all_modifications():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, name FROM modifications ORDER BY name')
        return cursor.fetchall()

def update_modification(mod_id, name, norm_graph1_min, norm_graph1_max, norm_graph1_x,
                         norm_graph2_min, norm_graph2_max, norm_graph2_x,
                         norm_graph3_min, norm_graph3_max, norm_graph3_x,
                         pressure_min, pressure_max, seal_rules=None):
    """Обновляет существующую модификацию по её id (а не через INSERT OR
    REPLACE по имени, как add_modification) - id остаётся тем же, поэтому
    ссылки насосов на эту модификацию (modification_id) не теряются."""
    with db_lock.acquire_write_lock(), get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE modifications SET
                name = ?, norm_graph1_min = ?, norm_graph1_max = ?, norm_graph1_x = ?,
                norm_graph2_min = ?, norm_graph2_max = ?, norm_graph2_x = ?,
                norm_graph3_min = ?, norm_graph3_max = ?, norm_graph3_x = ?,
                pressure_min = ?, pressure_max = ?, seal_rules_json = ?
            WHERE id = ?
        ''', (name, norm_graph1_min, norm_graph1_max, norm_graph1_x,
              norm_graph2_min, norm_graph2_max, norm_graph2_x,
              norm_graph3_min, norm_graph3_max, norm_graph3_x,
              pressure_min, pressure_max, seal_rules, mod_id))
        bump_revision(f"Изменена модификация «{name}»", conn)
        conn.commit()

def delete_modification(mod_id):
    """Удаляет модификацию. У насосов, которые на неё ссылались, поле
    modification_id автоматически станет NULL (см. FOREIGN KEY ... ON
    DELETE SET NULL в схеме) - сами протоколы насосов не удаляются."""
    with db_lock.acquire_write_lock(), get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM modifications WHERE id = ?', (mod_id,))
        row = cursor.fetchone()
        mod_name = row[0] if row else str(mod_id)
        cursor.execute('DELETE FROM modifications WHERE id = ?', (mod_id,))
        bump_revision(f"Удалена модификация «{mod_name}»", conn)
        conn.commit()

def count_pumps_for_modification(mod_id):
    """Сколько существующих протоколов насосов сейчас ссылаются на эту
    модификацию - используется, чтобы предупредить пользователя перед
    удалением, если такие протоколы есть."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM pumps WHERE modification_id = ?', (mod_id,))
        return cursor.fetchone()[0]

# ---------- Работа с заказами ----------
# def add_order(order_number):
#     with get_connection() as conn:
#         cursor = conn.cursor()
#         cursor.execute('INSERT OR IGNORE INTO orders (order_number) VALUES (?)', (order_number,))
#         conn.commit()
#         return cursor.lastrowid

def add_order(order_number):
    if order_number is None:
        return None
    # Нормализация: убираем .0
    order_number = str(order_number).replace('.0', '').strip()
    with db_lock.acquire_write_lock(), get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO orders (order_number) VALUES (?)', (order_number,))
        conn.commit()
        cursor.execute('SELECT id FROM orders WHERE order_number = ?', (order_number,))
        row = cursor.fetchone()
        return row[0] if row else None

def get_order_by_number(order_number):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM orders WHERE order_number = ?', (order_number,))
        row = cursor.fetchone()
        return row[0] if row else None

def get_all_orders():
    """Возвращает список заказов, которые имеют хотя бы один связанный
    насос - отсортированных по убыванию ЧИСЛОВОЙ части номера заказа,
    без учёта буквенного префикса (например, "К5666" должен идти выше
    "5487", несмотря на буквенный префикс - обычная текстовая сортировка
    в SQL расставила бы их в порядке, не соответствующем реальной
    величине числа)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT o.id, o.order_number
            FROM orders o
            INNER JOIN pumps p ON p.order_id = o.id
        ''')
        rows = cursor.fetchall()
        rows.sort(key=lambda row: _order_number_sort_key(row[1]), reverse=True)
        return rows


def _order_number_sort_key(order_number):
    """Извлекает числовую часть номера заказа (игнорируя любые буквы) -
    общая функция для сортировки заказов по убыванию величины числа, а
    не по алфавитному порядку строки."""
    digits = re.sub(r'\D', '', str(order_number))
    return int(digits) if digits else 0

# ---------- Работа с насосами (протоколами) ----------
def get_pump_by_number_and_date(pump_number, test_date):
    """Возвращает существующую запись с тем же номером насоса и датой проверки,
    либо None. Используется для предупреждения о повторном импорте/добавлении
    одного и того же протокола."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id FROM pumps WHERE pump_number = ? AND test_date = ?',
            (pump_number, test_date)
        )
        row = cursor.fetchone()
        return row[0] if row else None

def add_pump(pump_number, test_date, test_type, modification_id, order_id,
             results_json, seal_results_json, verdict, is_sealed, note='', pump_uuid=None):
    """
    results_json: dict с ключами 'g5'..'g32' (или список)
    seal_results_json: dict с ключами 'g33'..'g37'

    pump_uuid - если не задан, генерируется новый (обычное добавление).
    При повторном добавлении в рамках умного слияния (см.
    db_sync.smart_merge_push) передаётся исходный uuid записи - это
    делает повторный запуск слияния безопасным (идентификатор не
    задвоится, если процесс случайно выполнится дважды).
    """
    with db_lock.acquire_write_lock(), get_connection() as conn:
        cursor = conn.cursor()
        now_str = datetime.now().isoformat(timespec='seconds')
        final_uuid = pump_uuid or str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO pumps 
            (pump_number, test_date, test_type, modification_id, order_id,
             results_json, seal_results_json, verdict, is_sealed, note, last_edited_at, uuid)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (pump_number, test_date, test_type, modification_id, order_id,
              json.dumps(results_json), json.dumps(seal_results_json), verdict, is_sealed, note, now_str, final_uuid))
        bump_revision(f"Добавлен насос №{pump_number}", conn)
        conn.commit()
        return cursor.lastrowid

def get_pump_by_id(pump_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                p.id, 
                p.pump_number, 
                p.test_date, 
                p.test_type, 
                p.modification_id, 
                p.order_id, 
                p.results_json, 
                p.seal_results_json, 
                p.verdict, 
                p.is_sealed, 
                p.note, 
                p.created_at, 
                p.edit_history,
                m.name as mod_name,
                o.order_number,
                p.edit_date,
                p.changed_fields_json,
                p.last_edited_at,
                p.uuid
            FROM pumps p
            LEFT JOIN modifications m ON p.modification_id = m.id
            LEFT JOIN orders o ON p.order_id = o.id
            WHERE p.id = ?
        ''', (pump_id,))
        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'pump_number': row[1],
                'test_date': row[2],
                'test_type': row[3],
                'modification_id': row[4],
                'order_id': row[5],
                'results_json': json.loads(row[6]) if row[6] else {},
                'seal_results_json': json.loads(row[7]) if row[7] else {},
                'verdict': row[8],
                'is_sealed': bool(row[9]) if row[9] is not None else None,
                'note': row[10],
                'created_at': row[11],
                'edit_history': row[12],
                'mod_name': row[13],
                'order_number': row[14],
                'edit_date': row[15],
                'changed_fields': json.loads(row[16]) if row[16] else [],
                'last_edited_at': row[17],
                'uuid': row[18],
            }
        return None

def get_all_pumps(filters=None, order_by='test_date DESC', limit=None, offset=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        query = '''
            SELECT 
                p.id,
                p.pump_number,
                p.test_date,
                p.test_type,
                p.verdict,
                p.is_sealed,
                p.note,
                p.edit_history,
                m.name as mod_name,
                o.order_number,
                (SELECT COUNT(*) FROM pumps p2 WHERE p2.pump_number = p.pump_number) as check_count
            FROM pumps p
            LEFT JOIN modifications m ON p.modification_id = m.id
            LEFT JOIN orders o ON p.order_id = o.id
            WHERE 1=1
        '''
        params = []
        if filters:
            if filters.get('pump_number'):
                query += ' AND p.pump_number LIKE ?'
                params.append(f'%{filters["pump_number"]}%')
            if filters.get('verdict') and filters['verdict'] != 'Все':
                query += ' AND p.verdict = ?'
                params.append(filters['verdict'])
            if filters.get('test_type') and filters['test_type'] != 'Все':
                query += ' AND p.test_type = ?'
                params.append(filters['test_type'])
            if filters.get('is_sealed') is not None and filters['is_sealed'] != -1:
                query += ' AND p.is_sealed = ?'
                params.append(filters['is_sealed'])
            if filters.get('date_from'):
                query += ' AND p.test_date >= ?'
                params.append(filters['date_from'])
            if filters.get('date_to'):
                query += ' AND p.test_date <= ?'
                params.append(filters['date_to'])
            if filters.get('only_duplicates'):
                query += ''' AND (
                    SELECT COUNT(*) FROM pumps p2
                    WHERE p2.pump_number = p.pump_number
                      AND (p2.modification_id = p.modification_id
                           OR (p2.modification_id IS NULL AND p.modification_id IS NULL))
                ) > 1'''
            if filters.get('order_id'):
                query += ' AND p.order_id = ?'
                params.append(filters['order_id'])

        query += f' ORDER BY {order_by}'

        if limit is not None:
            query += ' LIMIT ?'
            params.append(limit)
        if offset is not None:
            query += ' OFFSET ?'
            params.append(offset)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                'id': row[0],
                'pump_number': row[1],
                'test_date': row[2],
                'test_type': row[3],
                'verdict': row[4],
                'is_sealed': bool(row[5]) if row[5] is not None else None,
                'note': row[6],
                'edit_history': row[7],
                'mod_name': row[8],
                'order_number': row[9],
                'check_count': row[10]
            })
        return result
    
def delete_pump(pump_id):
    with db_lock.acquire_write_lock(), get_connection() as conn:
        cursor = conn.cursor()

        # Узнаём номер насоса и заказ, к которому была привязана запись,
        # ДО удаления
        cursor.execute('SELECT pump_number, order_id FROM pumps WHERE id = ?', (pump_id,))
        row = cursor.fetchone()
        pump_number = row[0] if row else str(pump_id)
        order_id = row[1] if row else None

        cursor.execute('DELETE FROM pumps WHERE id = ?', (pump_id,))

        # Если у заказа не осталось ни одной записи - удаляем и сам заказ,
        # чтобы он не "оседал" в БД и не попадал в фильтр
        if order_id is not None:
            cursor.execute('SELECT COUNT(*) FROM pumps WHERE order_id = ?', (order_id,))
            remaining = cursor.fetchone()[0]
            if remaining == 0:
                cursor.execute('DELETE FROM orders WHERE id = ?', (order_id,))

        bump_revision(f"Удалён насос №{pump_number}", conn)
        conn.commit()

def get_all_pumps_full_for_merge():
    """Возвращает ПОЛНЫЕ данные всех насосов (включая uuid, результаты
    испытаний и last_edited_at) - специально для умного слияния (см.
    db_sync.smart_merge_push). В отличие от get_all_pumps() (только
    сводные поля для таблицы списка), здесь нужны все поля, чтобы можно
    было заново добавить запись целиком, если выяснится, что её нет в
    сетевой базе."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, uuid, pump_number, test_date, test_type, modification_id,
                   order_id, results_json, seal_results_json, verdict, is_sealed,
                   note, last_edited_at
            FROM pumps
            WHERE uuid IS NOT NULL
        ''')
        return [
            {
                'id': row[0],
                'uuid': row[1],
                'pump_number': row[2],
                'test_date': row[3],
                'test_type': row[4],
                'modification_id': row[5],
                'order_id': row[6],
                'results_json': json.loads(row[7]) if row[7] else {},
                'seal_results_json': json.loads(row[8]) if row[8] else {},
                'verdict': row[9],
                'is_sealed': bool(row[10]) if row[10] is not None else None,
                'note': row[11],
                'last_edited_at': row[12],
            }
            for row in cursor.fetchall()
        ]


def update_pump(pump_id, **kwargs):
    """Обновляет поля записи, включая edit_history."""
    with db_lock.acquire_write_lock(), get_connection() as conn:
        cursor = conn.cursor()
        set_clause = []
        params = []
        simple_fields = [
            'pump_number', 'test_date', 'test_type', 'verdict', 'is_sealed',
            'note', 'edit_history', 'modification_id', 'order_id',
            'edit_date', 'changed_fields_json',
        ]
        for key, value in kwargs.items():
            if key in simple_fields:
                set_clause.append(f'{key} = ?')
                params.append(value)
            elif key == 'results_json':
                set_clause.append('results_json = ?')
                params.append(json.dumps(value))
            elif key == 'seal_results_json':
                set_clause.append('seal_results_json = ?')
                params.append(json.dumps(value))
        if set_clause:
            # last_edited_at обновляется ВСЕГДА при любом реальном
            # изменении записи, независимо от того, какие именно поля
            # менялись - это и есть "версия записи" для защиты от
            # одновременного редактирования (см. check_pump_unchanged)
            set_clause.append('last_edited_at = ?')
            params.append(datetime.now().isoformat(timespec='seconds'))

            params.append(pump_id)
            cursor.execute(f'UPDATE pumps SET {", ".join(set_clause)} WHERE id = ?', params)
            pump_number = kwargs.get('pump_number')
            if pump_number is None:
                cursor.execute('SELECT pump_number FROM pumps WHERE id = ?', (pump_id,))
                row = cursor.fetchone()
                pump_number = row[0] if row else pump_id
            bump_revision(f"Изменён насос №{pump_number}", conn)
            conn.commit()


def check_pump_unchanged(pump_id, expected_last_edited_at):
    """Проверяет, не изменилась ли запись насоса с момента, когда она
    была открыта на редактирование - сверяет текущую метку last_edited_at
    в базе с той, что была запомнена в момент открытия диалога
    редактирования.

    Возвращает:
        True  - запись не менялась, можно спокойно сохранять
        False - запись изменилась (кто-то другой её сохранил, пока мы
                редактировали) - показать предупреждение, не сохранять молча
        None  - запись больше не существует (кто-то её удалил) - сохранить
                в принципе невозможно
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT last_edited_at FROM pumps WHERE id = ?', (pump_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return row[0] == expected_last_edited_at

# Функция статистики по выбранному заказу
def get_order_stats(order_number):
    """Возвращает статистику по заказу: общее количество, годные, негерметичные, первичные."""
    with get_connection() as conn:
        cursor = conn.cursor()
        # Всего записей для заказа
        cursor.execute('''
            SELECT COUNT(*) FROM pumps p
            LEFT JOIN orders o ON p.order_id = o.id
            WHERE o.order_number = ?
        ''', (order_number,))
        total = cursor.fetchone()[0]

        # Годные
        cursor.execute('''
            SELECT COUNT(*) FROM pumps p
            LEFT JOIN orders o ON p.order_id = o.id
            WHERE o.order_number = ? AND p.verdict = 'годен'
        ''', (order_number,))
        good = cursor.fetchone()[0]

        # Негерметичные
        cursor.execute('''
            SELECT COUNT(*) FROM pumps p
            LEFT JOIN orders o ON p.order_id = o.id
            WHERE o.order_number = ? AND p.is_sealed = 0
        ''', (order_number,))
        not_sealed = cursor.fetchone()[0]

        # Первичные
        cursor.execute('''
            SELECT COUNT(*) FROM pumps p
            LEFT JOIN orders o ON p.order_id = o.id
            WHERE o.order_number = ? AND p.test_type = 'первичная'
        ''', (order_number,))
        primary = cursor.fetchone()[0]

        return {
            'total': total,
            'good': good,
            'not_sealed': not_sealed,
            'primary': primary
        }

# Пагинация
def count_pumps(filters=None):
    """
    Возвращает общее количество записей с учётом фильтров (без пагинации).
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        query = 'SELECT COUNT(*) FROM pumps p LEFT JOIN orders o ON p.order_id = o.id WHERE 1=1'
        params = []
        # Повторяем условия фильтров (копируем из get_all_pumps)
        if filters:
            if filters.get('pump_number'):
                query += ' AND p.pump_number LIKE ?'
                params.append(f'%{filters["pump_number"]}%')
            if filters.get('verdict') and filters['verdict'] != 'Все':
                query += ' AND p.verdict = ?'
                params.append(filters['verdict'])
            if filters.get('test_type') and filters['test_type'] != 'Все':
                query += ' AND p.test_type = ?'
                params.append(filters['test_type'])
            if filters.get('is_sealed') is not None and filters['is_sealed'] != -1:
                query += ' AND p.is_sealed = ?'
                params.append(filters['is_sealed'])
            if filters.get('order_id'):
                query += ' AND p.order_id = ?'
                params.append(filters['order_id'])
            if filters.get('date_from'):
                query += ' AND p.test_date >= ?'
                params.append(filters['date_from'])
            if filters.get('date_to'):
                query += ' AND p.test_date <= ?'
                params.append(filters['date_to'])
            if filters.get('only_duplicates'):
                query += ''' AND (
                    SELECT COUNT(*) FROM pumps p2
                    WHERE p2.pump_number = p.pump_number
                      AND (p2.modification_id = p.modification_id
                           OR (p2.modification_id IS NULL AND p.modification_id IS NULL))
                ) > 1'''
        cursor.execute(query, params)
        return cursor.fetchone()[0]

# Сбор данных для общей статистики
def get_statistics():
    """Возвращает словарь со статистикой по всем насосам и по заказам."""
    with get_connection() as conn:
        cursor = conn.cursor()
        # Общая статистика
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN verdict = 'годен' THEN 1 ELSE 0 END) as good,
                SUM(CASE WHEN verdict = 'годен' AND test_type = 'первичная' THEN 1 ELSE 0 END) as good_first,
                SUM(CASE WHEN verdict = 'не годен' THEN 1 ELSE 0 END) as bad,
                SUM(CASE WHEN is_sealed = 0 THEN 1 ELSE 0 END) as not_sealed
            FROM pumps
        ''')
        row = cursor.fetchone()
        total, good, good_first, bad, not_sealed = row
        total = total or 0
        good = good or 0
        good_first = good_first or 0
        bad = bad or 0
        not_sealed = not_sealed or 0

        stats = {
            'total': total,
            'good': good,
            'good_first': good_first,
            'bad': bad,
            'not_sealed': not_sealed,
            'good_percent': (good / total * 100) if total else 0,
            'good_first_percent': (good_first / total * 100) if total else 0,
            'bad_percent': (bad / total * 100) if total else 0,
            'not_sealed_percent': (not_sealed / total * 100) if total else 0,
            'orders': []
        }

        # Статистика по заказам
        # Статистика по заказам
        cursor.execute('''
            SELECT 
                o.order_number,
                COUNT(p.id) as total,
                SUM(CASE WHEN p.verdict = 'годен' THEN 1 ELSE 0 END) as good,
                SUM(CASE WHEN p.verdict = 'годен' AND p.test_type = 'первичная' THEN 1 ELSE 0 END) as good_first,
                SUM(CASE WHEN p.verdict = 'не годен' THEN 1 ELSE 0 END) as bad,
                SUM(CASE WHEN p.is_sealed = 0 THEN 1 ELSE 0 END) as not_sealed,
                MIN(p.test_date) as date_min,
                MAX(p.test_date) as date_max
            FROM pumps p
            JOIN orders o ON p.order_id = o.id
            GROUP BY o.order_number
        ''')
        rows = cursor.fetchall()
        # Сортировка по убыванию ЧИСЛОВОЙ части номера заказа, без учёта
        # буквенного префикса - та же логика, что и в get_all_orders()
        rows.sort(key=lambda row: _order_number_sort_key(row[0]), reverse=True)
        for row in rows:
            (order_number, total_o, good_o, good_first_o, bad_o, not_sealed_o,
             date_min, date_max) = row
            stats['orders'].append({
                'order_number': order_number,
                'total': total_o,
                'good': good_o,
                'good_first': good_first_o,
                'bad': bad_o,
                'not_sealed': not_sealed_o,
                'date_min': date_min,
                'date_max': date_max,
            })

        return stats

# def get_order_by_id(order_id):
#     with get_connection() as conn:
#         cursor = conn.cursor()
#         cursor.execute('SELECT order_number FROM orders WHERE id = ?', (order_id,))
#         row = cursor.fetchone()
#         if row:
#             val = row[0]
#             # Если это float, преобразуем в int (если целое) и потом в строку
#             if isinstance(val, float):
#                 if val.is_integer():
#                     return str(int(val))
#                 else:
#                     return str(val).rstrip('0').rstrip('.')
#             return str(val)
#         return None

def get_order_by_id(order_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT order_number FROM orders WHERE id = ?', (order_id,))
        row = cursor.fetchone()
        if row:
            val = row[0]
            print(f"[DEBUG get_order_by_id] Сырое значение из БД: {val}, тип: {type(val)}")
            # Пробуем преобразовать
            if isinstance(val, float):
                if val.is_integer():
                    result = str(int(val))
                else:
                    result = str(val).rstrip('0').rstrip('.')
            elif isinstance(val, int):
                result = str(val)
            else:
                result = str(val)
            print(f"[DEBUG get_order_by_id] Результат: {result}")
            return result
        print("[DEBUG get_order_by_id] Заказ не найден")
        return None

# ---------- Вспомогательные функции ----------
def get_check_count_for_pump(pump_number):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM pumps WHERE pump_number = ?', (pump_number,))
        return cursor.fetchone()[0]
    
# Дата последнего обновления в статус-баре
def get_last_update_date():
    """Возвращает дату последнего изменения базы данных - ЛЮБого:
    добавление/изменение/удаление насоса, модификации, заказа (читает
    db_meta.last_modified_at, обновляется функцией bump_revision() при
    каждой операции записи).

    Раньше эта функция смотрела только на MAX(created_at) в таблице
    насосов - то есть учитывала только СОЗДАНИЕ нового насоса (что
    вручную, что через импорт из Excel), но не его последующее
    редактирование и вообще никак не учитывала модификации/заказы."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT last_modified_at FROM db_meta WHERE id = 1')
        row = cursor.fetchone()
        if row and row[0]:
            date_str = row[0]
            if ' ' in date_str:
                date_str = date_str.split(' ')[0]
            elif 'T' in date_str:
                # datetime.isoformat() без пробела использует "T" как
                # разделитель даты и времени (см. bump_revision)
                date_str = date_str.split('T')[0]
            return date_str
        return "нет данных"

# Инициализация при первом импорте
if __name__ == '__main__':
    init_db()