import json
from datetime import datetime

def parse_date(date_str):
    """Преобразует строку в объект date, если возможно."""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        return None

def is_value_in_range(value, min_val, max_val):
    """Проверяет, попадает ли значение в диапазон (включительно)."""
    if value is None or min_val is None or max_val is None:
        return False
    return min_val <= value <= max_val

def compute_verdict_and_sealed(results, seal_results, mod_data):
    """
    Вычисляет вердикт ('годен'/'не годен') и герметичность (True/False).
    results: dict g5..g32
    seal_results: dict g33..g37
    mod_data: словарь с нормативами из БД
    """
    # Проверка результатов тестов (G5-G32) на соответствие диапазонам
    # Данные для теста 1: g5-g12 (8 точек)
    # Данные для теста 2: g13-g20 (8 точек)
    # Данные для теста 3: g21-g31 (11 точек)
    # Данные для давления: g32 (одно значение)
    
    # Нормативы из модификации
    norm_graph1_min = mod_data.get('norm_graph1_min', [])
    norm_graph1_max = mod_data.get('norm_graph1_max', [])
    norm_graph2_min = mod_data.get('norm_graph2_min', [])
    norm_graph2_max = mod_data.get('norm_graph2_max', [])
    norm_graph3_min = mod_data.get('norm_graph3_min', [])
    norm_graph3_max = mod_data.get('norm_graph3_max', [])
    pressure_min = mod_data.get('pressure_min')
    pressure_max = mod_data.get('pressure_max')
    
    # Списки результатов
    # Тест 1: g5-g12
    test1_values = [results.get(f'g{i}') for i in range(5, 13)]
    # Тест 2: g13-g20
    test2_values = [results.get(f'g{i}') for i in range(13, 21)]
    # Тест 3: g21-g31
    test3_values = [results.get(f'g{i}') for i in range(21, 32)]
    # Давление: g32
    pressure_value = results.get('g32')
    
    # Проверка соответствия
    all_in_range = True
    
    # Тест 1
    for i, val in enumerate(test1_values):
        if val is not None:
            if i < len(norm_graph1_min) and i < len(norm_graph1_max):
                if not is_value_in_range(val, norm_graph1_min[i], norm_graph1_max[i]):
                    all_in_range = False
                    break
    if all_in_range:
        # Тест 2
        for i, val in enumerate(test2_values):
            if val is not None:
                if i < len(norm_graph2_min) and i < len(norm_graph2_max):
                    if not is_value_in_range(val, norm_graph2_min[i], norm_graph2_max[i]):
                        all_in_range = False
                        break
    if all_in_range:
        # Тест 3
        for i, val in enumerate(test3_values):
            if val is not None:
                if i < len(norm_graph3_min) and i < len(norm_graph3_max):
                    if not is_value_in_range(val, norm_graph3_min[i], norm_graph3_max[i]):
                        all_in_range = False
                        break
    if all_in_range and pressure_value is not None:
        if not is_value_in_range(pressure_value, pressure_min, pressure_max):
            all_in_range = False
    
    verdict = 'годен' if all_in_range else 'не годен'
    
    # Определение герметичности
    # Поля G33-G37
    # Если в G33-G36 написано "отсутствуют" – норма
    # Если что-то другое – негерметичен
    # G37: "отсутствуют" или "присутствуют в допускаемой степени" – норма, иначе негерметичен
    sealed = True
    for key in ['g33', 'g34', 'g35', 'g36']:
        val = seal_results.get(key)
        if val is not None and str(val).strip().lower() != 'отсутствуют':
            sealed = False
            break
    if sealed:
        val_g37 = seal_results.get('g37')
        if val_g37 is not None:
            text = str(val_g37).strip().lower()
            if text not in ['отсутствуют', 'присутствуют в допускаемой степени']:
                sealed = False
    
    return verdict, sealed

def format_order_number(value):
    """Приводит номер заказа к строке без .0."""
    if value is None:
        return '—'
    s = str(value)
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    s = s.replace('.0', '')
    return s