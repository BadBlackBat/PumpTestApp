import json
import sys
import os

# Добавляем путь к src, чтобы импортировать database
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from src import database as db

def add_test_modification():
    # Данные для модификации 412300-1002585-31 (пример)
    # Вы можете заменить числа на реальные нормативы
    mod_data = {
        "name": "412300-1002585-31",
        "norm_graph1_min": [3.60, 3.80, 4.00, 4.20, 4.25, 4.30, 4.35, 4.37],
        "norm_graph1_max": [5.70, 5.90, 6.20, 6.40, 6.60, 6.70, 6.80, 6.85],
        "norm_graph2_min": [13.40, 14.50, 15.40, 16.0, 16.20, 16.0, 15.70, 15.53],
        "norm_graph2_max": [16.30, 17.60, 18.80, 19.50, 19.90, 20.20, 20.50, 20.60],
        "norm_graph3_min": [4.30, 4.40, 4.90, 5.95, 7.30, 9.00, 10.70, 12.15, 13.40, 14.40, 14.50],
        "norm_graph3_max": [5.90, 6.00, 6.70, 7.80, 9.30, 10.90, 12.70, 14.10, 15.60, 16.70, 16.80],
        "pressure_min": 125,
        "pressure_max": 135
    }

    db.add_modification(
        name=mod_data["name"],
        norm_graph1_min=json.dumps(mod_data["norm_graph1_min"]),
        norm_graph1_max=json.dumps(mod_data["norm_graph1_max"]),
        norm_graph2_min=json.dumps(mod_data["norm_graph2_min"]),
        norm_graph2_max=json.dumps(mod_data["norm_graph2_max"]),
        norm_graph3_min=json.dumps(mod_data["norm_graph3_min"]),
        norm_graph3_max=json.dumps(mod_data["norm_graph3_max"]),
        pressure_min=mod_data["pressure_min"],
        pressure_max=mod_data["pressure_max"]
    )
    print(f"✅ Модификация '{mod_data['name']}' добавлена в БД.")

if __name__ == "__main__":
    add_test_modification()