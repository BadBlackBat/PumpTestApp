# -*- coding: utf-8 -*-
"""
add_more_pumps.py - добавление новых насосов к уже существующей,
действующей базе данных (в отличие от populate_real_data.py, который
был разовым скриптом именно для ПЕРВОГО наполнения перед началом
работы).

НЕ является частью самой программы PumpTestApp - отдельная утилита,
как и populate_real_data.py/add_modification.py. Можно запускать
сколько угодно раз по мере накопления новых данных - в отличие от
populate_real_data.py:
    - НЕ требует, чтобы таблица насосов была пустой (наоборот,
      предполагает, что в ней уже есть данные)
    - НЕ очищает журнал изменений в конце - раз база уже в обычной
      работе, новые добавления должны нормально попадать в журнал, как
      и любое другое обычное добавление через интерфейс программы
    - Проверяет вероятные дубли ПЕРЕД добавлением (тот же насос и та
      же дата проверки уже есть в базе) и даёт решить, добавлять их
      всё равно или пропустить - полезно, если не до конца уверены,
      какие записи из файла уже заносились раньше

Формат входного файла - тот же самый JS-подобный массив объектов, что
и у populate_real_data.py (см. пример структуры записи там же).

Запуск (из корня проекта, где лежит папка src):
    .venv\\Scripts\\python.exe add_more_pumps.py путь_к_файлу_с_новыми_данными.txt
"""
import sys
import os
import re
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src import database as db
from src import utils


# ---- Те же самые словари нормализации, что и в populate_real_data.py -
# см. там подробные комментарии о происхождении каждого варианта ----

TIGHTNESS_MAP = {
    'герметичен': True,
    'негерметичен': False,
    'не герметичен': False,
}

LEAK_MAP = {
    'отсутствуют': 'Отсутствуют',
    'подтекание': 'Подтекание',
    'каплепадение': 'Каплепадение',
    'иное': 'Иное',
}

OIL_MAP = {
    'отсутствуют': 'Отсутствуют',
    'присутствуют в допускаемой степени': 'Присутствуют в допускаемой степени',
    'присутствуют в чрезмерном объеме': 'Присутствуют в чрезмерном объёме',
    'образования в чрезмерном объеме': 'Присутствуют в чрезмерном объёме',
    'иное': 'Иное',
}


def parse_js_array(path):
    """Разбирает файл вида "const data = [ {...}, {...} ];" - объекты
    без кавычек у ключей (не валидный JSON сам по себе), поэтому ключи
    оборачиваются в кавычки перед разбором через json.loads()."""
    with open(path, encoding='utf-8') as f:
        content = f.read()
    objects_raw = re.findall(r'\{[^{}]*\}', content)
    records = []
    for raw in objects_raw:
        s = re.sub(r'(\w+)\s*:', r'"\1":', raw)
        records.append(json.loads(s))
    return records


def convert_date(date_str):
    """ДД.ММ.ГГГГ -> ГГГГ-ММ-ДД. Если есть вторая дата в скобках
    (ДД.ММ.ГГГГ(ДД.ММ.ГГГГ)) - берём именно её (см. populate_real_data.py)."""
    m = re.search(r'\(([\d.]+)\)', date_str)
    if m:
        date_str = m.group(1)
    day, month, year = date_str.strip().split('.')
    return f"{year}-{month}-{day}"


def build_results(record):
    """Собирает словарь результатов теста (g5-g32) - та же структура,
    что и у populate_real_data.py/excel_importer.py."""
    return {
        'g5': record['ecoOff_1000'], 'g6': record['ecoOff_2000'],
        'g7': record['ecoOff_3000'], 'g8': record['ecoOff_4000'],
        'g9': record['ecoOff_5000'], 'g10': record['ecoOff_6000'],
        'g11': record['ecoOff_7000'], 'g12': record['ecoOff_7500'],
        'g13': record['ecoOn_1000'], 'g14': record['ecoOn_2000'],
        'g15': record['ecoOn_3000'], 'g16': record['ecoOn_4000'],
        'g17': record['ecoOn_5000'], 'g18': record['ecoOn_6000'],
        'g19': record['ecoOn_7000'], 'g20': record['ecoOn_7500'],
        'g21': record['I00'], 'g22': record['I01'], 'g23': record['I02'],
        'g24': record['I03'], 'g25': record['I04'], 'g26': record['I05'],
        'g27': record['I06'], 'g28': record['I07'], 'g29': record['I08'],
        'g30': record['I09'], 'g31': record['I10'],
        'g32': record['Pmax'],
    }


def build_seal_results(record):
    """Собирает словарь результатов проверки герметичности (g33-g37) -
    порядок позиций совпадает с базой (см. populate_real_data.py)."""
    def norm_leak(value):
        return LEAK_MAP.get(value.strip().lower(), value)

    def norm_oil(value):
        return OIL_MAP.get(value.strip().lower(), value)

    return {
        'g33': norm_leak(record['valueConnectEcoSeat']),
        'g34': norm_leak(record['valueOilLeak']),
        'g35': norm_leak(record['valueOuterMagneticCoilEnd']),
        'g36': norm_leak(record['valueConnectPumpCover']),
        'g37': norm_oil(record['valueOilBearing']),
    }


def find_probable_duplicates(records):
    """Проверяет КАЖДУЮ запись файла на совпадение по номеру насоса И
    дате проверки с уже существующей записью в базе - возвращает список
    таких записей (сама запись не удаляется из общего списка, решение
    принимается позже, все разом)."""
    duplicates = []
    for record in records:
        idname = record.get('idname', '???')
        try:
            test_date = convert_date(record['date'])
        except (KeyError, ValueError):
            continue  # разберётся (и сообщит) основной цикл добавления
        existing_id = db.get_pump_by_number_and_date(idname, test_date)
        if existing_id:
            duplicates.append((idname, test_date, existing_id))
    return duplicates


def main():
    if len(sys.argv) < 2:
        print("Использование: python add_more_pumps.py путь_к_файлу_с_новыми_данными.txt")
        return

    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"Файл не найден: {path}")
        return

    records = parse_js_array(path)
    print(f"Найдено записей в файле: {len(records)}")

    total_before, _ = db.get_pump_counts()
    print(f"Насосов в базе сейчас: {total_before}")

    # Проверка вероятных дублей - тот же насос и та же дата уже есть в
    # базе. Не блокирует добавление автоматически - просто предупреждает
    # и даёт решить, что делать со ВСЕЙ группой таких записей разом
    duplicates = find_probable_duplicates(records)
    skip_idnames = set()
    if duplicates:
        print(f"\nВНИМАНИЕ: {len(duplicates)} записей из файла, похоже, уже есть в базе")
        print("(совпадает номер насоса И дата проверки):")
        for idname, test_date, existing_id in duplicates:
            print(f"  {idname} от {test_date} (id в базе: {existing_id})")
        answer = input("\nПропустить эти записи (yes) или всё равно добавить их ещё раз (нет): ")
        if answer.strip().lower() == 'yes':
            skip_idnames = {(idname, test_date) for idname, test_date, _ in duplicates}
            print(f"Пропущено как дубли: {len(skip_idnames)}")
        else:
            print("Записи будут добавлены ещё раз, несмотря на совпадение.")
        print()

    added = 0
    skipped = []
    mismatches = []

    for record in records:
        idname = record.get('idname', '???')

        mod = db.get_modification_by_name(record['mod'])
        if not mod:
            skipped.append((idname, f"модификация «{record['mod']}» не найдена в базе"))
            continue

        tightness_key = record['tightness'].strip().lower()
        if tightness_key not in TIGHTNESS_MAP:
            skipped.append((idname, f"нераспознанное значение tightness: «{record['tightness']}»"))
            continue
        is_sealed_from_json = TIGHTNESS_MAP[tightness_key]

        test_date = convert_date(record['date'])
        if (idname, test_date) in skip_idnames:
            skipped.append((idname, "пропущено как вероятный дубль"))
            continue

        order_id = db.add_order(record['order'])
        results = build_results(record)
        seal_results = build_seal_results(record)

        usable_from_json = bool(record['usable'])
        verdict_from_json = 'годен' if usable_from_json else 'не годен'

        computed_verdict, computed_sealed = utils.compute_verdict_and_sealed(
            results, seal_results, mod
        )
        if computed_verdict != verdict_from_json or computed_sealed != is_sealed_from_json:
            mismatches.append({
                'idname': idname,
                'json_verdict': verdict_from_json, 'computed_verdict': computed_verdict,
                'json_sealed': is_sealed_from_json, 'computed_sealed': computed_sealed,
            })

        note = (record.get('other') or '').strip()

        db.add_pump(
            pump_number=idname,
            test_date=test_date,
            test_type=record['check'],
            modification_id=mod['id'],
            order_id=order_id,
            results_json=results,
            seal_results_json=seal_results,
            verdict=verdict_from_json,
            is_sealed=is_sealed_from_json,
            note=note,
        )
        added += 1

    print(f"\nДобавлено записей: {added}")

    if skipped:
        print(f"\nПропущено записей: {len(skipped)}")
        for idname, reason in skipped:
            print(f"  {idname}: {reason}")

    if mismatches:
        print(f"\nРасхождения между данными файла и расчётом программы: {len(mismatches)}")
        print("(запись всё равно добавлена с данными ИЗ ФАЙЛА - для проверки)")
        for m in mismatches:
            print(
                f"  {m['idname']}: вердикт файл={m['json_verdict']} / расчёт={m['computed_verdict']}, "
                f"герметичность файл={m['json_sealed']} / расчёт={m['computed_sealed']}"
            )
    else:
        print("\nРасхождений между данными файла и расчётом программы не обнаружено.")

    total_after, _ = db.get_pump_counts()
    print(f"\nНасосов в базе теперь: {total_after} (было {total_before})")
    print("Журнал изменений НЕ очищался - новые записи видны в обычной истории программы.")


if __name__ == '__main__':
    main()