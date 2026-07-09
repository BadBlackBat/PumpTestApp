import pandas as pd
from PyQt5.QtWidgets import QApplication, QDialog, QListWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox
from PyQt5.QtCore import Qt
import os
import json
from datetime import datetime
import database as db

def read_excel_sheets(file_path):
    """Читает все листы Excel и возвращает список имён листов и данные."""
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
    # Предполагаем, что ячейки имеют фиксированные позиции (индексы строк и столбцов, начиная с 0)
    # В Pandas индексы: row, col (0-based)
    # G1 -> row=0, col=6 (G), но учтём, что в Excel G - 7-й столбец (индекс 6)
    # Но так как мы читаем header=None, то индексы соответствуют номерам столбцов (0=A, 1=B, ... 6=G)
    
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
    pump_number = get_val(1, 6)   # G2 -> row=1 (0-based), col=6
    test_date = get_val(0, 6)     # G1 -> row=0, col=6
    if test_date and isinstance(test_date, pd.Timestamp):
        test_date = test_date.strftime('%Y-%m-%d')
    else:
        test_date = str(test_date) if test_date else None
    
    test_type = get_val(1, 7)     # H2 -> row=1, col=7
    order_number = get_val(0, 10) # K1 -> row=0, col=10
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
            QMessageBox.warning(parent_widget, "Предупреждение", "В файле нет подходящих листов для импорта.")
            return 0
        
        # Диалог выбора листов
        dialog = QDialog(parent_widget)
        dialog.setWindowTitle("Выбор листов для импорта")
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
        
        # Импортируем каждый лист
        imported_count = 0
        errors = []
        for sheet in selected_sheets:
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
                # Предложить добавить модификацию (позже реализуем)
                errors.append(f"Лист {sheet}: модификация '{data['modification_name']}' не найдена в БД. Пропускаем.")
                continue
            
            # Поиск заказа (если есть)
            order_id = None
            if data['order_number']:
                order_id = db.get_order_by_number(data['order_number'])
                if not order_id:
                    # Автоматически добавляем заказ
                    order_id = db.add_order(data['order_number'])
            
            # Определение вердикта и герметичности
            # Проверяем все результаты на соответствие нормативам (упрощённо)
            # Здесь нужна логика сравнения с нормативами модификации
            # Пока ставим заглушку, позже реализуем
            verdict = "годен"  # пока всегда годен
            is_sealed = True   # пока всегда герметичен
            
            # Сохраняем
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
        
        # Показываем итог
        msg = f"Импортировано записей: {imported_count}"
        if errors:
            msg += f"\n\nОшибки:\n" + "\n".join(errors)
        QMessageBox.information(parent_widget, "Результат импорта", msg)
        return imported_count
        
    except Exception as e:
        QMessageBox.critical(parent_widget, "Ошибка", f"Не удалось выполнить импорт:\n{str(e)}")
        return 0