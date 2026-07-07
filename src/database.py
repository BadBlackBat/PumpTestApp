import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'pumps.db')

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pumps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pump_number TEXT UNIQUE NOT NULL,
                test_date TEXT,
                order_number TEXT,
                verdict TEXT,
                test_type TEXT,
                is_sealed BOOLEAN,
                details_json TEXT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pump_number ON pumps(pump_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_test_date ON pumps(test_date)')
        conn.commit()
        print("База данных инициализирована.")

if __name__ == "__main__":
    init_db()