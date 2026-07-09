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
def add_order(order_number):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO orders (order_number) VALUES (?)', (order_number,))
        conn.commit()
        return cursor.lastrowid

def get_order_by_number(order_number):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM orders WHERE order_number = ?', (order_number,))
        row = cursor.fetchone()
        return row[0] if row else None

def get_all_orders():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, order_number FROM orders ORDER BY order_number')
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
            SELECT p.*, m.name as mod_name, o.order_number 
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
                'is_sealed': row[9],
                'note': row[10],
                'created_at': row[11],
                'mod_name': row[12],
                'order_number': row[13]
            }
        return None

def get_all_pumps(filters=None, order_by='test_date DESC'):
    """
    Возвращает список насосов с дополнительным полем 'check_count' (количество проверок для этого номера).
    filters: dict с ключами: 'pump_number', 'verdict', 'test_type', 'is_sealed', 'date_from', 'date_to', 'only_duplicates'
    """
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
            # if filters.get('verdict') and filters['verdict'] != 'Все':
            #     query += ' AND p.verdict = ?'
            #     params.append(filters['verdict'])
            verdict = filters.get('verdict')
            if verdict and verdict != 'Все':
                query += ' AND LOWER(p.verdict) = ?'
                params.append(verdict.lower())

            # if filters.get('test_type') and filters['test_type'] != 'Все':
            #     query += ' AND p.test_type = ?'
            #     params.append(filters['test_type'])
            test_type = filters.get('test_type')
            if test_type and test_type != 'Все':
                query += ' AND LOWER(p.test_type) = ?'
                params.append(test_type.lower())
                
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
        
        query += f' ORDER BY {order_by}'
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
                'mod_name': row[7],
                'order_number': row[8],
                'check_count': row[9]
            })
        return result

def delete_pump(pump_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM pumps WHERE id = ?', (pump_id,))
        conn.commit()

def update_pump(pump_id, **kwargs):
    """Обновляет поля записи (используется при редактировании)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        set_clause = []
        params = []
        for key, value in kwargs.items():
            if key in ['pump_number', 'test_date', 'test_type', 'verdict', 'is_sealed', 'note']:
                set_clause.append(f'{key} = ?')
                params.append(value)
            elif key == 'results_json':
                set_clause.append('results_json = ?')
                params.append(json.dumps(value))
            elif key == 'seal_results_json':
                set_clause.append('seal_results_json = ?')
                params.append(json.dumps(value))
        if set_clause:
            params.append(pump_id)
            cursor.execute(f'UPDATE pumps SET {", ".join(set_clause)} WHERE id = ?', params)
            conn.commit()

# ---------- Вспомогательные функции ----------
def get_check_count_for_pump(pump_number):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM pumps WHERE pump_number = ?', (pump_number,))
        return cursor.fetchone()[0]

# Инициализация при первом импорте
if __name__ == '__main__':
    init_db()