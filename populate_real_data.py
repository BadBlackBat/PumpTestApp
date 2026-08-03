# -*- coding: utf-8 -*-
"""
populate_real_data.py - разовый скрипт наполнения базы данных реальными
данными насосов.

НЕ является частью самой программы PumpTestApp - отдельная утилита,
запускается вручную ОДИН РАЗ перед передачей программы в реальную
эксплуатацию. Не устанавливается пользователям, не доступна из
интерфейса программы.

Перед запуском:
    1. Убедитесь, что таблица насосов в базе данных, с которой будет
       работать скрипт, ПУСТАЯ (старые тестовые/примерные записи удалены
       вручную) - модификации трогать не нужно, они используются реальные
       и должны остаться как есть.
    2. Файл с данными (текстовый файл с JS-подобным массивом объектов,
       без кавычек у ключей) должен быть доступен по указанному пути.
    3. Положите этот скрипт РЯДОМ с папкой src (то есть на том же
       уровне, где лежит сама папка src), либо поправьте путь импорта
       ниже под ваше реальное расположение.

Запуск:
    python populate_real_data.py путь_к_файлу_с_данными.txt

Что делает скрипт:
    - Разбирает файл с данными (формат: const data = [ {...}, {...} ]; )
    - Для каждой записи ищет модификацию по имени, создаёт заказ (если
      его ещё нет), добавляет насос через обычную функцию базы данных
      add_pump() - то есть точно так же, как это сделало бы обычное
      добавление через интерфейс программы
    - Приводит регистр/формулировки полей герметичности и вердикта к
      точным вариантам, которые использует программа (см. словари
      TIGHTNESS_MAP, LEAK_MAP, OIL_MAP ниже)
    - Дополнительно ПЕРЕСЧИТЫВАЕТ вердикт и герметичность через ту же
      логику, что использует сама программа (utils.compute_verdict_and_sealed),
      и сравнивает с тем, что указано в файле данных - если есть
      расхождение, запись всё равно добавляется (доверяем данным из
      файла), но расхождение отдельно выводится в конце для проверки
    - В конце ОЧИЩАЕТ таблицу change_log (журнал изменений) - наполнение
      не должно оставлять служебных записей в истории изменений, это
      разовая техническая операция, а не часть обычной работы программы
"""
import sys
import os
import re
import json

# Путь к пакету программы - поправьте, если скрипт лежит не рядом с src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src import database as db
from src import utils


# ---- Сопоставление регистра/формулировок исходного файла с точными
# вариантами, которые использует сама программа (см. dialogs.py:
# _LEAK_OPTIONS, _OIL_OPTIONS) ----

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
    # "образования в чрезмерном объеме" - опечатка/иная формулировка в
    # исходных данных, означающая то же самое, что и вариант выше
    # (подтверждено при подготовке скрипта)
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
    """ДД.ММ.ГГГГ -> ГГГГ-ММ-ДД (формат, который использует программа
    внутри базы данных).

    Отдельный случай: некоторые записи содержат ВТОРУЮ дату в скобках -
    "11.12.2025(20.01.2026)" - в этом случае нужно использовать именно
    дату из скобок (подтверждено при подготовке скрипта)."""
    m = re.search(r'\(([\d.]+)\)', date_str)
    if m:
        date_str = m.group(1)
    day, month, year = date_str.strip().split('.')
    return f"{year}-{month}-{day}"


def build_results(record):
    """Собирает словарь результатов теста (g5-g32) из полей исходного
    файла - порядок и группировка (тест1/тест2/тест3/давление) - по
    той же структуре, что использует обычный импорт из Excel
    (excel_importer.py: extract_pump_data)."""
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
    порядок ПОЗИЦИЙ (не буквальное совпадение по названию поля в файле)
    подтверждён как совпадающий с порядком в базе данных при подготовке
    скрипта."""
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


def main():
    if len(sys.argv) < 2:
        print("Использование: python populate_real_data.py путь_к_файлу_с_данными.txt")
        return

    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"Файл не найден: {path}")
        return

    records = parse_js_array(path)
    print(f"Найдено записей в файле: {len(records)}")

    existing = db.get_all_pumps()
    if existing:
        print(f"\nВНИМАНИЕ: в базе данных уже есть {len(existing)} записей насосов.")
        answer = input("Продолжить и добавить данные из файла поверх существующих? (yes/нет): ")
        if answer.strip().lower() != 'yes':
            print("Отменено.")
            return

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

        order_id = db.add_order(record['order'])
        results = build_results(record)
        seal_results = build_seal_results(record)

        usable_from_json = bool(record['usable'])
        verdict_from_json = 'годен' if usable_from_json else 'не годен'

        # Дополнительная проверка через ту же логику, что использует
        # сама программа - не заменяет данные из файла, только сверяет
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
            test_date=convert_date(record['date']),
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

    # Наполнение - разовая техническая операция, не должна оставлять
    # служебных записей в журнале изменений (по договорённости)
    with db.get_connection() as conn:
        conn.execute('DELETE FROM change_log')
        conn.commit()
    print("\nЖурнал изменений очищен.")


if __name__ == '__main__':
    main()