# -*- coding: utf-8 -*-
"""
add_modification.py - разовый скрипт добавления новой модификации
(норматива) в базу данных.

НЕ является частью самой программы PumpTestApp - отдельная утилита,
как и populate_real_data.py. Можно запускать сколько угодно раз - если
модификация с таким именем уже существует, она будет ЗАМЕНЕНА новыми
значениями (INSERT OR REPLACE - см. database.add_modification), а не
продублирована.

Запуск (из корня проекта, где лежит папка src):
    .venv\\Scripts\\python.exe add_modification.py

ВАЖНО: числовые значения ниже (норм_graph1_min и так далее) - ЗАГЛУШКИ
для примера структуры, а НЕ реальные нормативы. Перед запуском их
обязательно нужно заменить настоящими значениями для вашей конкретной
модификации - взять их неоткуда, кроме как из вашей собственной
технической документации/таблицы нормативов.
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src import database as db
from src import utils


# ---------------------------------------------------------------------
# НИЖЕ - ЗАМЕНИТЬ НА РЕАЛЬНЫЕ ЗНАЧЕНИЯ ПЕРЕД ЗАПУСКОМ
# ---------------------------------------------------------------------

MODIFICATION_NAME = "412300-1002580-30"  # <- точное название модификации

# Тест 1 и Тест 2 (расход от оборотов, ECO выкл./вкл.) - строго 8 точек
# каждый (ограничение структуры БД: utils.MAX_GRAPH1_POINTS == 8).
# По умолчанию точки оборотов - utils.DEFAULT_GRAPH1_X, можно оставить
# как есть или заменить своими, если модификация использует другие
# обороты для замера.
GRAPH1_X = list(utils.DEFAULT_GRAPH1_X)        # [1000, 2000, 3000, 4000, 5000, 6000, 7000, 7500]
GRAPH1_MIN = [6.30, 6.70, 6.80, 6.90, 7.10, 7.00, 7.10, 7.10]                          # <- заменить: минимальный расход, л/мин, ECO выкл.
GRAPH1_MAX = [7.70, 8.10, 8.20, 8.30, 8.50, 8.60, 8.70, 8.90]                          # <- заменить: максимальный расход, л/мин, ECO выкл.

GRAPH2_X = list(utils.DEFAULT_GRAPH2_X)        # те же обороты, что и для теста 1, обычно
GRAPH2_MIN = [13.80, 14.60, 15.10, 15.30, 15.40, 15.40, 15.50, 15.50]                          # <- заменить: минимальный расход, л/мин, ECO вкл.
GRAPH2_MAX = [15.20, 16.00, 16.50, 16.70, 16.90, 17.20, 17.40, 17.45]                          # <- заменить: максимальный расход, л/мин, ECO вкл.

# Тест 3 (расход от силы тока ECO) - строго 11 точек
# (utils.MAX_GRAPH3_POINTS == 11)
GRAPH3_X = list(utils.DEFAULT_GRAPH3_X)        # [0.0, 0.1, 0.2, ..., 1.0]
GRAPH3_MIN = [6.60, 6.60, 6.60, 7.80, 8.80, 10.00, 11.10, 12.10, 13.20, 14.30, 14.30]                         # <- заменить: минимальный расход, л/мин
GRAPH3_MAX = [8.00, 8.00, 8.00, 9.20, 10.20, 11.40, 12.50, 13.50, 14.60, 15.70, 15.70]                         # <- заменить: максимальный расход, л/мин

# Давление - одно значение (не массив)
PRESSURE_MIN = 125                              # <- заменить
PRESSURE_MAX = 135                              # <- заменить

# Требования герметичности - по одному текстовому требованию на каждую
# из 5 стандартных точек проверки (utils.SEAL_KEYS/SEAL_LABELS).
# ВАЖНО: значения здесь - это ТРЕБОВАНИЕ (что допустимо), а не
# результат конкретного измерения - в отличие от насосов, у модификации
# хранится именно норма, с которой потом сравниваются реальные
# протоколы испытаний.
SEAL_REQUIREMENTS = {
    'g33': 'отсутствуют',                       # Соединение с седлом клапана ECO
    'g34': 'отсутствуют',                       # Внешняя поверхность катушки ECO
    'g35': 'отсутствуют',                       # Внешняя поверхность с торца катушки ECO
    'g36': 'отсутствуют',                       # Соединение крышки корпуса
    'g37': 'отсутствуют',                       # Масляные образования на подшипнике
}

# ---------------------------------------------------------------------
# Дальше - сама логика, менять не нужно
# ---------------------------------------------------------------------


def validate():
    """Проверяет структуру ПЕРЕД записью в базу - лучше остановиться
    здесь с понятной ошибкой, чем записать модификацию с неверным
    количеством точек, которая потом будет странно себя вести при
    сравнении с реальными протоколами."""
    errors = []

    for label, x, mn, mx, expected_len in [
        ('Тест 1 (ECO выкл.)', GRAPH1_X, GRAPH1_MIN, GRAPH1_MAX, utils.MAX_GRAPH1_POINTS),
        ('Тест 2 (ECO вкл.)', GRAPH2_X, GRAPH2_MIN, GRAPH2_MAX, utils.MAX_GRAPH2_POINTS),
        ('Тест 3 (сила тока)', GRAPH3_X, GRAPH3_MIN, GRAPH3_MAX, utils.MAX_GRAPH3_POINTS),
    ]:
        if len(x) != expected_len:
            errors.append(f"{label}: ожидалось {expected_len} точек по оси X, получено {len(x)}")
        if len(mn) != expected_len:
            errors.append(f"{label}: ожидалось {expected_len} минимальных значений, получено {len(mn)}")
        if len(mx) != expected_len:
            errors.append(f"{label}: ожидалось {expected_len} максимальных значений, получено {len(mx)}")
        if len(mn) == len(mx) == expected_len:
            for i, (lo, hi) in enumerate(zip(mn, mx)):
                if lo > hi:
                    errors.append(f"{label}: точка {i} (x={x[i] if i < len(x) else '?'}) - минимум ({lo}) больше максимума ({hi})")

    if PRESSURE_MIN > PRESSURE_MAX:
        errors.append(f"Давление: минимум ({PRESSURE_MIN}) больше максимума ({PRESSURE_MAX})")

    missing_seal_keys = set(utils.SEAL_KEYS) - set(SEAL_REQUIREMENTS.keys())
    if missing_seal_keys:
        errors.append(f"Не заданы требования герметичности для: {', '.join(sorted(missing_seal_keys))}")

    return errors


def main():
    if not MODIFICATION_NAME or MODIFICATION_NAME.startswith('000000'):
        print("Похоже, MODIFICATION_NAME оставлен как заглушка - замените на реальное")
        print("название модификации перед запуском.")
        sys.exit(1)

    errors = validate()
    if errors:
        print("Обнаружены проблемы структуры - запись в базу отменена:\n")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    existing = db.get_modification_by_name(MODIFICATION_NAME)
    if existing:
        print(f"Модификация «{MODIFICATION_NAME}» уже существует (id={existing['id']}) -")
        answer = input("значения будут ЗАМЕНЕНЫ новыми. Продолжить? (yes/нет): ")
        if answer.strip().lower() != 'yes':
            print("Отменено.")
            return

    mod_id = db.add_modification(
        name=MODIFICATION_NAME,
        norm_graph1_min=json.dumps(GRAPH1_MIN),
        norm_graph1_max=json.dumps(GRAPH1_MAX),
        norm_graph1_x=json.dumps(GRAPH1_X),
        norm_graph2_min=json.dumps(GRAPH2_MIN),
        norm_graph2_max=json.dumps(GRAPH2_MAX),
        norm_graph2_x=json.dumps(GRAPH2_X),
        norm_graph3_min=json.dumps(GRAPH3_MIN),
        norm_graph3_max=json.dumps(GRAPH3_MAX),
        norm_graph3_x=json.dumps(GRAPH3_X),
        pressure_min=PRESSURE_MIN,
        pressure_max=PRESSURE_MAX,
        seal_rules=json.dumps(SEAL_REQUIREMENTS),
    )

    print(f"\nМодификация «{MODIFICATION_NAME}» сохранена (id={mod_id}).")
    print(f"  Тест 1: {len(GRAPH1_X)} точек, обороты {GRAPH1_X}")
    print(f"  Тест 2: {len(GRAPH2_X)} точек, обороты {GRAPH2_X}")
    print(f"  Тест 3: {len(GRAPH3_X)} точек, сила тока {GRAPH3_X}")
    print(f"  Давление: {PRESSURE_MIN} - {PRESSURE_MAX}")


if __name__ == "__main__":
    main()