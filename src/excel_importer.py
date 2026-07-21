import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QDialog, QListWidget, QVBoxLayout,
    QPushButton, QLabel, QMessageBox, QProgressDialog
)
from PyQt5.QtCore import Qt
import os
import json
from datetime import datetime

from . import database as db
from . import utils


def read_excel_sheets(file_path):
    """Читает все листы Excel и возвращает словарь {имя_листа: DataFrame}."""
    try:
        xls = pd.ExcelFile(file_path)
        sheet_names = xls.sheet_names
        # Исключаем лист 'вспомогат' (регистронезависимо)
        sheets_to_read = [s for s in sheet_names if s.lower() != 'вспомогат']
        data = {}
        for sheet in sheets_to_read:
            df = pd.read_excel(file_path, sheet_name=sheet, header=None)
            data[sheet] = df
        return data
    except Exception as e:
        raise Exception(f"Ошибка чтения Excel: {e}")


def extract_pump_data(df):
    """
    Извлекает данные из DataFrame по описанной структуре.
    Возвращает словарь с ключами:
        pump_number, test_date, test_type, order_number, modification_name,
        results (dict g5..g32), seal_results (dict g33..g37), note
    """
    # Функция для безопасного получения значения
    def get_val(row, col):
        try:
            val = df.iat[row, col]
            if pd.isna(val):
                return None
            return val
        except:
            return None

    # Основные данные
    pump_number = get_val(1, 6)   # G2 -> row=1, col=6
    test_date = get_val(0, 6)     # G1 -> row=0, col=6
    if test_date and isinstance(test_date, pd.Timestamp):
        test_date = test_date.strftime('%Y-%m-%d')
    else:
        test_date = str(test_date) if test_date else None

    test_type = get_val(1, 7)     # H2 -> row=1, col=7
    order_number = get_val(0, 10) # K1 -> row=0, col=10
    if order_number is not None:
        order_number = str(order_number).replace('.0', '').strip()
        order_number = utils.normalize_order_number(order_number)
    modification_name = get_val(1, 1) # B2 -> row=1, col=1

    # Результаты тестов (G5-G32) -> строки 4..31, столбец 6
    results = {}
    for row in range(4, 32):  # G5 - G32
        key = f'g{row+1}'  # g5..g32
        val = get_val(row, 6)
        results[key] = val

    # Результаты герметичности (G33-G37) -> строки 32..36, столбец 6
    seal_results = {}
    for row in range(32, 37):  # G33-G37
        key = f'g{row+1}'
        val = get_val(row, 6)
        seal_results[key] = val

    # Доп. примечания (K35) -> строка 34 (0-based), столбец 10
    note = get_val(34, 10)

    return {
        'pump_number': pump_number,
        'test_date': test_date,
        'test_type': test_type,
        'order_number': order_number,
        'modification_name': modification_name,
        'results': results,
        'seal_results': seal_results,
        'note': note
    }


def import_excel_file(file_path, parent_widget=None):
    """
    Главная функция импорта: читает файл, показывает диалог выбора листов,
    и для каждого выбранного листа добавляет запись в БД.
    Возвращает количество успешно добавленных записей.
    """
    try:
        sheets_data = read_excel_sheets(file_path)
        if not sheets_data:
            QMessageBox.warning(
                parent_widget, 
                "Предупреждение", 
                "В файле нет подходящих листов для импорта (исключён лист 'вспомогат')."
            )
            return 0

        # Диалог выбора листов
        dialog = QDialog(parent_widget)
        dialog.setWindowTitle("Выбор листов для импорта")
        dialog.resize(400, 300)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Выберите листы, которые хотите импортировать:"))

        list_widget = QListWidget()
        list_widget.setSelectionMode(QListWidget.MultiSelection)
        for name in sheets_data.keys():
            list_widget.addItem(name)
        layout.addWidget(list_widget)

        btn_ok = QPushButton("Импортировать выбранные")
        btn_ok.clicked.connect(dialog.accept)
        layout.addWidget(btn_ok)

        if dialog.exec_() != QDialog.Accepted:
            return 0

        selected_items = list_widget.selectedItems()
        if not selected_items:
            QMessageBox.information(parent_widget, "Информация", "Ни один лист не выбран.")
            return 0

        selected_sheets = [item.text() for item in selected_items]

        # Прогресс-бар
        progress = QProgressDialog("Импорт данных...", "Отмена", 0, len(selected_sheets), parent_widget)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()

        imported_count = 0
        errors = []
        for idx, sheet in enumerate(selected_sheets):
            progress.setValue(idx)
            if progress.wasCanceled():
                break

            df = sheets_data[sheet]
            data = extract_pump_data(df)

            # Проверка обязательных данных
            if not data['pump_number']:
                errors.append(f"Лист {sheet}: не удалось определить идентификационный номер насоса.")
                continue
            if not data['test_date']:
                errors.append(f"Лист {sheet}: отсутствует дата проверки.")
                continue

            # Поиск модификации
            mod = db.get_modification_by_name(data['modification_name'])
            if not mod:
                errors.append(
                    f"Лист {sheet}: модификация '{data['modification_name']}' не найдена в БД. "
                    "Добавьте модификацию через настройки и повторите импорт."
                )
                continue

            # Поиск заказа (если есть)
            order_id = None
            if data['order_number']:
                order_id = db.get_order_by_number(data['order_number'])
                if not order_id:
                    # Автоматически добавляем заказ
                    order_id = db.add_order(data['order_number'])

            # ===== ВЫЧИСЛЯЕМ ВЕРДИКТ И ГЕРМЕТИЧНОСТЬ =====
            verdict, is_sealed = utils.compute_verdict_and_sealed(
                data['results'], 
                data['seal_results'], 
                mod
            )
            # Если вердикт не определён, ставим "не годен" по умолчанию
            if not verdict:
                verdict = "не годен"
            if is_sealed is None:
                is_sealed = False

            # ===== ПРОВЕРКА НА ДУБЛИКАТ (совпадение номера насоса И даты) =====
            existing_id = db.get_pump_by_number_and_date(data['pump_number'], data['test_date'])
            if existing_id:
                display_date = utils.format_date_display(data['test_date'])
                reply1 = QMessageBox.warning(
                    parent_widget,
                    "Возможный дубликат",
                    f"Лист {sheet}: протокол для насоса №{data['pump_number']} от "
                    f"{display_date} уже есть в базе.\n\n"
                    "Импортировать его ещё раз?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply1 != QMessageBox.Yes:
                    errors.append(f"Лист {sheet}: пропущен пользователем (дубликат).")
                    continue
                reply2 = QMessageBox.warning(
                    parent_widget,
                    "Подтверждение",
                    f"Вы уверены, что хотите добавить ещё одну запись для насоса "
                    f"№{data['pump_number']} от {display_date}?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply2 != QMessageBox.Yes:
                    errors.append(f"Лист {sheet}: пропущен пользователем (дубликат).")
                    continue

            # Сохраняем запись
            pump_id = db.add_pump(
                pump_number=data['pump_number'],
                test_date=data['test_date'],
                test_type=data['test_type'],
                modification_id=mod['id'],
                order_id=order_id,
                results_json=data['results'],
                seal_results_json=data['seal_results'],
                verdict=verdict,
                is_sealed=is_sealed,
                note=data['note'] or ''
            )
            imported_count += 1

        progress.setValue(len(selected_sheets))

        # Показываем итог
        msg = f"Импортировано записей: {imported_count}"
        if errors:
            msg += f"\n\nОшибки:\n" + "\n".join(errors)
        QMessageBox.information(parent_widget, "Результат импорта", msg)
        return imported_count

    except Exception as e:
        QMessageBox.critical(parent_widget, "Ошибка", f"Не удалось выполнить импорт:\n{str(e)}")
        return 0