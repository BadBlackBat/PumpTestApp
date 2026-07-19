import json
from datetime import datetime

# ---------- Константы структуры испытаний ----------
# Тест 1 и Тест 2: зависимость расхода от оборотов - до 8 точек (ограничение
# структуры БД: под них отведены строки g5-g12 и g13-g20 соответственно)
DEFAULT_GRAPH1_X = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 7500]
DEFAULT_GRAPH2_X = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 7500]
MAX_GRAPH1_POINTS = 8
MAX_GRAPH2_POINTS = 8

# Тест 3: зависимость расхода от силы тока ECO - до 11 точек (строки g21-g31)
DEFAULT_GRAPH3_X = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
MAX_GRAPH3_POINTS = 11

# Герметичность: 5 стандартных мест проверки
SEAL_KEYS = ['g33', 'g34', 'g35', 'g36', 'g37']
SEAL_LABELS = {
    'g33': 'Соединение с седлом клапана ECO',
    'g34': 'Внешняя поверхность катушки ECO',
    'g35': 'Внешняя поверхность с торца катушки ECO',
    'g36': 'Соединение крышки корпуса',
    'g37': 'Масляные образования на уплотнении',
}
# Требование по умолчанию для g33-g36: "отсутствуют"; для g37 допустимы два варианта
DEFAULT_SEAL_REQUIREMENTS = {
    'g33': 'отсутствуют',
    'g34': 'отсутствуют',
    'g35': 'отсутствуют',
    'g36': 'отсутствуют',
    'g37': 'отсутствуют или присутствуют в допускаемой степени',
}

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

def format_date_display(date_value):
    """Приводит дату из внутреннего формата хранения (ISO YYYY-MM-DD,
    возможно с временем через пробел) к единому формату отображения
    ДД-ММ-ГГГГ, без времени. Используется везде в интерфейсе, где дата
    показывается пользователю (таблицы, протокол, диалоги) - НЕ
    используется для дат, которые участвуют в сравнении/хранении/
    сортировке (там нужен именно ISO-формат)."""
    if not date_value:
        return ''
    date_part = str(date_value).split(' ')[0]
    try:
        return datetime.strptime(date_part, '%Y-%m-%d').strftime('%d-%m-%Y')
    except (ValueError, TypeError):
        return date_part  # неожиданный формат - хотя бы не падаем


def format_order_number(value):
    """Приводит номер заказа к строке без .0."""
    if value is None:
        return '—'
    s = str(value)
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    s = s.replace('.0', '')
    return s


def describe_changed_fields(changed_fields):
    """Превращает список технических ключей изменённых полей (например,
    ['order_number', 'test_type', 'g6', 'g14', 'g33']) в читаемую фразу:
    'Редактированию подвергались: номер заказа, тип проверки, результаты
    теста 1, теста 2, оценка герметичности'."""
    if not changed_fields:
        return ""

    field_labels = [
        ('order_number', 'номер заказа'),
        ('test_date', 'дата проверки'),
        ('test_type', 'тип проверки'),
        ('modification', 'модификация'),
    ]
    parts = []
    for key, label in field_labels:
        if key in changed_fields:
            parts.append(label)

    tests_changed = set()
    for key in changed_fields:
        if key.startswith('g') and key[1:].isdigit():
            idx = int(key[1:])
            if 5 <= idx <= 12:
                tests_changed.add(1)
            elif 13 <= idx <= 20:
                tests_changed.add(2)
            elif 21 <= idx <= 31:
                tests_changed.add(3)
            elif idx == 32:
                tests_changed.add('pressure')
            elif 33 <= idx <= 37:
                tests_changed.add('seal')

    test_numbers = sorted(n for n in tests_changed if isinstance(n, int))
    if test_numbers:
        test_phrases = [f"результаты теста {test_numbers[0]}"]
        for n in test_numbers[1:]:
            test_phrases.append(f"теста {n}")
        parts.append(", ".join(test_phrases))

    if 'pressure' in tests_changed:
        parts.append("давление")
    if 'seal' in tests_changed:
        parts.append("оценка герметичности")

    if not parts:
        return ""
    return "Редактированию подвергались: " + ", ".join(parts)