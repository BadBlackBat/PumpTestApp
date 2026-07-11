import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'pumps.db')

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    """Создаёт все таблицы, если их нет."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Таблица модификаций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS modifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                norm_graph1_min TEXT,   -- JSON массив 8 значений (мин)
                norm_graph1_max TEXT,   -- JSON массив 8 значений (макс)
                norm_graph2_min TEXT,
                norm_graph2_max TEXT,
                norm_graph3_min TEXT,   -- 11 значений для теста 3
                norm_graph3_max TEXT,
                pressure_min REAL,
                pressure_max REAL,
                seal_rules_json TEXT   -- дополнительные правила для герметичности (пока не обязательны)
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
                
        conn.commit()
        print("База данных инициализирована.")

# ---------- Работа с модификациями ----------
def add_modification(name, norm_graph1_min, norm_graph1_max, norm_graph2_min, norm_graph2_max,
                     norm_graph3_min, norm_graph3_max, pressure_min, pressure_max, seal_rules=None):
    """
    Добавляет новую модификацию.
    Все norm_* - это строки JSON (массивы чисел).
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO modifications 
            (name, norm_graph1_min, norm_graph1_max, norm_graph2_min, norm_graph2_max,
             norm_graph3_min, norm_graph3_max, pressure_min, pressure_max, seal_rules_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, norm_graph1_min, norm_graph1_max, norm_graph2_min, norm_graph2_max,
              norm_graph3_min, norm_graph3_max, pressure_min, pressure_max, seal_rules))
        conn.commit()
        return cursor.lastrowid

def get_modification_by_name(name):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM modifications WHERE name = ?', (name,))
        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'name': row[1],
                'norm_graph1_min': json.loads(row[2]) if row[2] else [],
                'norm_graph1_max': json.loads(row[3]) if row[3] else [],
                'norm_graph2_min': json.loads(row[4]) if row[4] else [],
                'norm_graph2_max': json.loads(row[5]) if row[5] else [],
                'norm_graph3_min': json.loads(row[6]) if row[6] else [],
                'norm_graph3_max': json.loads(row[7]) if row[7] else [],
                'pressure_min': row[8],
                'pressure_max': row[9],
                'seal_rules': json.loads(row[10]) if row[10] else {}
            }
        return None

def get_all_modifications():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, name FROM modifications ORDER BY name')
        return cursor.fetchall()

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
    with get_connection() as conn:
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
    """Возвращает список заказов, которые имеют хотя бы один связанный насос."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT o.id, o.order_number
            FROM orders o
            INNER JOIN pumps p ON p.order_id = o.id
            ORDER BY o.order_number
        ''')
        return cursor.fetchall()

# ---------- Работа с насосами (протоколами) ----------
def add_pump(pump_number, test_date, test_type, modification_id, order_id,
             results_json, seal_results_json, verdict, is_sealed, note=''):
    """
    results_json: dict с ключами 'g5'..'g32' (или список)
    seal_results_json: dict с ключами 'g33'..'g37'
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pumps 
            (pump_number, test_date, test_type, modification_id, order_id,
             results_json, seal_results_json, verdict, is_sealed, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (pump_number, test_date, test_type, modification_id, order_id,
              json.dumps(results_json), json.dumps(seal_results_json), verdict, is_sealed, note))
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
                o.order_number
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
                'order_number': row[14]
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
                query += ' AND (SELECT COUNT(*) FROM pumps p2 WHERE p2.pump_number = p.pump_number) > 1'
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
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM pumps WHERE id = ?', (pump_id,))
        conn.commit()

def update_pump(pump_id, **kwargs):
    """Обновляет поля записи, включая edit_history."""
    with get_connection() as conn:
        cursor = conn.cursor()
        set_clause = []
        params = []
        for key, value in kwargs.items():
            if key in ['pump_number', 'test_date', 'test_type', 'verdict', 'is_sealed', 'note', 'edit_history']:
                set_clause.append(f'{key} = ?')
                params.append(value)
            elif key == 'results_json':
                set_clause.append('results_json = ?')
                params.append(json.dumps(value))
            elif key == 'seal_results_json':
                set_clause.append('seal_results_json = ?')
                params.append(json.dumps(value))
            elif key == 'edit_history':
                set_clause.append(f'{key} = ?')
                params.append(value)
        if set_clause:
            params.append(pump_id)
            cursor.execute(f'UPDATE pumps SET {", ".join(set_clause)} WHERE id = ?', params)
            conn.commit()

# Функция получения всех заказов
def get_all_orders():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, order_number FROM orders ORDER BY order_number')
        return cursor.fetchall()
    
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
                query += ' AND (SELECT COUNT(*) FROM pumps p2 WHERE p2.pump_number = p.pump_number) > 1'
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
        cursor.execute('''
            SELECT 
                o.order_number,
                COUNT(p.id) as total,
                SUM(CASE WHEN p.verdict = 'годен' THEN 1 ELSE 0 END) as good,
                SUM(CASE WHEN p.verdict = 'годен' AND p.test_type = 'первичная' THEN 1 ELSE 0 END) as good_first,
                SUM(CASE WHEN p.verdict = 'не годен' THEN 1 ELSE 0 END) as bad,
                SUM(CASE WHEN p.is_sealed = 0 THEN 1 ELSE 0 END) as not_sealed
            FROM pumps p
            JOIN orders o ON p.order_id = o.id
            GROUP BY o.order_number
            ORDER BY o.order_number
        ''')
        rows = cursor.fetchall()
        for row in rows:
            order_number, total_o, good_o, good_first_o, bad_o, not_sealed_o = row
            stats['orders'].append({
                'order_number': order_number,
                'total': total_o,
                'good': good_o,
                'good_first': good_first_o,
                'bad': bad_o,
                'not_sealed': not_sealed_o,
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
    """Возвращает максимальную дату создания записи (created_at) или test_date."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT MAX(created_at) FROM pumps')
        row = cursor.fetchone()
        if row and row[0]:
            # обрезаем время, оставляем только дату
            date_str = row[0]
            if ' ' in date_str:
                date_str = date_str.split(' ')[0]
            return date_str
        return "нет данных"

# Инициализация при первом импорте
if __name__ == '__main__':
    init_db()