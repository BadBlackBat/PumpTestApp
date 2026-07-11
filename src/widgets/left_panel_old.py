from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QCheckBox,
    QDateEdit, QHeaderView, QAbstractItemView, QMenu
)
from PyQt5.QtCore import Qt, pyqtSignal, QDate, QPoint
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPolygon

from .. import database as db
from .. import utils

class LeftPanel(QWidget):
    pump_selected = pyqtSignal(dict)
    request_import = pyqtSignal()
    request_add = pyqtSignal()
    request_delete = pyqtSignal(int)
    request_edit = pyqtSignal(int)
    filters_applied = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Инициализация атрибутов ДО вызова setup_ui и load_data
        self.compact_mode = True   # по умолчанию компактный вид списка насосов
        self.current_page = 0
        self.page_size = 20
        self.total_records = 0
        self.current_filters = {}
        self.all_pumps = []
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Строка поиска
        search_layout = QHBoxLayout()
        search_label = QLabel("Поиск:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите номер насоса...")
        self.search_input.textChanged.connect(self.apply_filters)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)

        # Кнопка сброса
        self.btn_reset_filters = QPushButton("Сбросить фильтры")
        self.btn_reset_filters.clicked.connect(self.reset_filters)
        search_layout.addWidget(self.btn_reset_filters)

        layout.addLayout(search_layout)

        # Фильтры
        filter_layout = QHBoxLayout()
        self.filter_verdict = QComboBox()
        self.filter_verdict.addItems(["Все", "Годен", "Не годен"])
        self.filter_verdict.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Вердикт:"))
        filter_layout.addWidget(self.filter_verdict)

        self.filter_test_type = QComboBox()
        self.filter_test_type.addItems(["Все", "Первичная", "Повторная"])
        self.filter_test_type.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Тип:"))
        filter_layout.addWidget(self.filter_test_type)

        self.filter_sealed = QComboBox()
        self.filter_sealed.addItems(["Все", "Герметичен", "Не герметичен"])
        self.filter_sealed.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Герметичность:"))
        filter_layout.addWidget(self.filter_sealed)

        # Фильтр по заказам
        self.filter_order = QComboBox()
        self.filter_order.addItem("Все заказы")
        self.filter_order.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Заказ:"))
        filter_layout.addWidget(self.filter_order)

        layout.addLayout(filter_layout)

        # Дополнительные фильтры (дата, дубли)
        extra_layout = QHBoxLayout()
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate(2000, 1, 1))
        self.date_from.dateChanged.connect(self.apply_filters)
        extra_layout.addWidget(QLabel("Дата с:"))
        extra_layout.addWidget(self.date_from)

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.dateChanged.connect(self.apply_filters)
        extra_layout.addWidget(QLabel("по:"))
        extra_layout.addWidget(self.date_to)

        self.only_duplicates = QCheckBox("Только дубли")
        self.only_duplicates.stateChanged.connect(self.apply_filters)
        extra_layout.addWidget(self.only_duplicates)

        layout.addLayout(extra_layout)

        # Статистика по заказу
        self.stats_label = QLabel("")
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("background-color: #e8f4f8; border-radius: 5px; border: 1px solid #b0d4e3; padding: 5px;")
        self.stats_label.hide()  # по умолчанию скрыт
        layout.addWidget(self.stats_label)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Номер насоса", "Дата", "Вердикт", "Тип", "Герметичность", "Кол-во проверок"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(1, Qt.DescendingOrder)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        # Контекстное меню
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table)

        # Пагинация
        pagination_layout = QHBoxLayout()
        self.btn_prev = QPushButton("◀ Назад")
        self.btn_prev.clicked.connect(self.prev_page)
        self.btn_next = QPushButton("Вперед ▶")
        self.btn_next.clicked.connect(self.next_page)
        self.page_label = QLabel("Страница 1 из 1")
        self.count_label = QLabel("Всего: 0")
        pagination_layout.addWidget(self.btn_prev)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.btn_next)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.count_label)
        layout.addLayout(pagination_layout)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Добавить")
        self.btn_add.clicked.connect(self.request_add.emit)
        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.clicked.connect(self.on_delete_clicked)
        self.btn_import = QPushButton("Импорт из Excel")
        self.btn_import.clicked.connect(self.request_import.emit)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_import)
        layout.addLayout(btn_layout)

        # Кнопка переключения вида
        self.btn_view_toggle = QPushButton("Расширенный вид")
        self.btn_view_toggle.setCheckable(True)
        self.btn_view_toggle.toggled.connect(self.toggle_view)

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_import)
        btn_layout.addWidget(self.btn_view_toggle)
        layout.addLayout(btn_layout)

        # Легенда (показывается только в компактном режиме)
        self.legend_label = QLabel()
        self.legend_label.setWordWrap(True)
        self.legend_label.setStyleSheet("background-color: #f9f9f9; border: 1px solid #ddd; padding: 5px;")
        self.update_legend()
        layout.addWidget(self.legend_label)

    def update_legend(self):
        # HTML-разметка с цветными кружками
        legend_text = (
            "Легенда: "
            "<span style='color:green;'>●</span> годен  "
            "<span style='color:red;'>●</span> не годен  "
            "<span style='color:gray;'>●</span> герметичен  "
            "<span style='color:blue;'>●</span> не герметичен  "
            "I — первичная  II — повторная"
        )
        self.legend_label.setText(legend_text)

    def toggle_view(self, checked):
        parent = self.parent()
        while parent and not hasattr(parent, 'splitter'):
            parent = parent.parent()
        if not parent or not hasattr(parent, 'splitter'):
            return

        if checked:
            self.compact_mode = False
            self.btn_view_toggle.setText("Свернуть список")
            # Прячем правую панель
            right_widget = parent.splitter.widget(1)
            if right_widget:
                right_widget.hide()
            # Устанавливаем ширину левой панели на 100% (но сплиттер с одним виджетом)
            parent.splitter.setSizes([parent.width(), 0])
            self.legend_label.hide()
        else:
            self.compact_mode = True
            self.btn_view_toggle.setText("Расширенный вид")
            # Показываем правую панель
            right_widget = parent.splitter.widget(1)
            if right_widget:
                right_widget.show()
            # Возвращаем пропорции 20% / 80% (или 30/70, но вы просили 20%)
            parent.splitter.setSizes([int(parent.width() * 0.2), int(parent.width() * 0.8)])
            self.legend_label.show()
        self.apply_filters()

    # def toggle_view(self, checked):
    #     """Переключает компактный/расширенный режим списка."""
    #     parent = self.parent()
    #     while parent and not hasattr(parent, 'splitter'):
    #         parent = parent.parent()
    #     if not parent or not hasattr(parent, 'splitter'):
    #         return

    #     if checked:
    #         # Расширенный режим
    #         self.compact_mode = False
    #         self.btn_view_toggle.setText("Свернуть список")
    #         # Устанавливаем ширину левой панели 70%, правой 30% (но скрываем правую)
    #         parent.splitter.setSizes([int(parent.width() * 0.75), int(parent.width() * 0.25)])
    #         # Скрываем легенду
    #         self.legend_label.hide()
    #         # Скрываем правую панель (устанавливаем размер 0)
    #         # Для этого сохраняем текущие размеры, но чтобы скрыть, устанавливаем 0 для правой
    #         # но лучше установить минимальную ширину правой в 0 и коллапс
    #         parent.splitter.setSizes([int(parent.width() * 0.95), int(parent.width() * 0.05)])
    #         # Также можно сделать правую панель невидимой
    #         # Но проще просто сжать до минимума
    #     else:
    #         # Компактный режим
    #         self.compact_mode = True
    #         self.btn_view_toggle.setText("Расширенный вид")
    #         # Возвращаем пропорции 30% / 70%
    #         parent.splitter.setSizes([int(parent.width() * 0.3), int(parent.width() * 0.7)])
    #         # Показываем легенду
    #         self.legend_label.show()
    #     # Перезаполняем таблицу с новым режимом
    #     self.apply_filters()

    def populate_table(self, pumps, compact=True):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(pumps))

        if compact:
            self.table.setColumnCount(5)
            self.table.setHorizontalHeaderLabels(["Номер", "Дата", "Вердикт", "Тип", "Герметичность"])
            for col in range(5, self.table.columnCount()):
                self.table.setColumnHidden(col, True)
            self.table.verticalHeader().setVisible(False)
            self.table.setColumnWidth(0, 100)
            self.table.setColumnWidth(1, 100)
            self.table.setColumnWidth(2, 50)
            self.table.setColumnWidth(3, 50)
            self.table.setColumnWidth(4, 50)
        else:
            self.table.setColumnCount(7)
            self.table.setHorizontalHeaderLabels(
                ["Номер", "Дата", "Модификация", "Герметичность", "Тип", "Заказ", "Вердикт"]
            )
            for col in range(self.table.columnCount()):
                self.table.setColumnHidden(col, False)
            self.table.verticalHeader().setVisible(False)
            self.table.setColumnWidth(0, 100)
            self.table.setColumnWidth(1, 100)
            self.table.setColumnWidth(2, 150)
            self.table.setColumnWidth(3, 100)
            self.table.setColumnWidth(4, 100)
            self.table.setColumnWidth(5, 100)
            self.table.setColumnWidth(6, 100)

        for row, p in enumerate(pumps):
            item_num = QTableWidgetItem(p['pump_number'])
            item_num.setData(Qt.UserRole, p['id'])
            self.table.setItem(row, 0, item_num)

            date_str = p['test_date']
            if date_str and ' ' in date_str:
                date_str = date_str.split(' ')[0]
            self.table.setItem(row, 1, QTableWidgetItem(date_str))

            if compact:
                # Вердикт
                verdict_icon = self.create_verdict_icon(p['verdict'] == 'годен')
                item_verdict = QTableWidgetItem()
                item_verdict.setIcon(verdict_icon)
                item_verdict.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 2, item_verdict)

                # Тип
                type_icon = self.create_type_icon(p['test_type'])
                item_type = QTableWidgetItem()
                item_type.setIcon(type_icon)
                item_type.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 3, item_type)

                # Герметичность
                sealed_icon = self.create_sealed_icon(p['is_sealed'])
                item_sealed = QTableWidgetItem()
                item_sealed.setIcon(sealed_icon)
                item_sealed.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 4, item_sealed)
            else:
                # Модификация
                mod_name = p.get('mod_name', '—')
                self.table.setItem(row, 2, QTableWidgetItem(mod_name if mod_name else '—'))
                # Герметичность
                sealed_text = 'Да' if p['is_sealed'] else 'Нет'
                self.table.setItem(row, 3, QTableWidgetItem(sealed_text))
                # Тип
                test_type = p.get('test_type') or '—'
                self.table.setItem(row, 4, QTableWidgetItem(test_type))
                # Заказ
                order_num = p.get('order_number', '—')
                self.table.setItem(row, 5, QTableWidgetItem(str(order_num) if order_num else '—'))
                # Вердикт
                verdict_text = p['verdict'] or '—'
                self.table.setItem(row, 6, QTableWidgetItem(verdict_text))

                # Подсветка строки
                if p['verdict'] == 'годен':
                    bg_color = QColor(200, 255, 200, 200)
                elif p['verdict'] == 'не годен':
                    bg_color = QColor(255, 200, 200, 200)
                else:
                    bg_color = None
                if bg_color:
                    for col in range(self.table.columnCount()):
                        item = self.table.item(row, col)
                        if item:
                            item.setBackground(bg_color)

        self.table.setSortingEnabled(True)
        if compact:
            self.table.sortByColumn(1, Qt.DescendingOrder)
        else:
            self.table.sortByColumn(0, Qt.AscendingOrder)
    # заполнение таблицы в зависимости от режима
    # def populate_table(self, pumps, compact=True):
    #     """Заполняет таблицу данными в компактном или расширенном виде."""
    #     self.table.setSortingEnabled(False)
    #     self.table.setRowCount(len(pumps))

    #     if compact:
    #         # Компактный режим: 5 столбцов (номер, дата, вердикт, тип, герметичность)
    #         self.table.setColumnCount(5)
    #         self.table.setHorizontalHeaderLabels(
    #             ["Номер насоса", "Дата", "Вердикт", "Тип", "Герметичность"]
    #         )
    #         # Скрываем столбцы, которые не используются (если были)
    #         for col in range(5, self.table.columnCount()):
    #             self.table.setColumnHidden(col, True)
    #         # Убираем нумерацию строк
    #         self.table.verticalHeader().setVisible(False)
    #     else:
    #         # Расширенный режим: 7 столбцов (номер, дата, модификация, герметичность, тип, заказ, вердикт)
    #         self.table.setColumnCount(7)
    #         self.table.setHorizontalHeaderLabels(
    #             ["Номер", "Дата", "Модификация", "Герметичность", "Тип", "Заказ", "Вердикт"]
    #         )
    #         # Показываем все столбцы
    #         for col in range(self.table.columnCount()):
    #             self.table.setColumnHidden(col, False)
    #         self.table.verticalHeader().setVisible(False)

    #     if not compact:
    #         # Подсветка строки
    #         if p['verdict'] == 'годен':
    #             bg_color = QColor(200, 255, 200, 200)  # бледно-зелёный с прозрачностью
    #         elif p['verdict'] == 'не годен':
    #             bg_color = QColor(255, 200, 200, 200)  # бледно-красный с прозрачностью
    #         else:
    #             bg_color = None
    #         if bg_color:
    #             for col in range(self.table.columnCount()):
    #                 item = self.table.item(row, col)
    #                 if item:
    #                     item.setBackground(bg_color)

    #     # Заполняем строки
    #     for row, p in enumerate(pumps):
    #         # Номер с ID
    #         item_num = QTableWidgetItem(p['pump_number'])
    #         item_num.setData(Qt.UserRole, p['id'])
    #         self.table.setItem(row, 0, item_num)

    #         # Дата (обрезаем время)
    #         date_str = p['test_date']
    #         if date_str and ' ' in date_str:
    #             date_str = date_str.split(' ')[0]
    #         self.table.setItem(row, 1, QTableWidgetItem(date_str))

    #         if compact:
    #             # Компактный режим: иконки для вердикта, типа, герметичности
    #             # Вердикт
    #             verdict_icon = self.create_verdict_icon(p['verdict'] == 'годен')
    #             item_verdict = QTableWidgetItem()
    #             item_verdict.setIcon(verdict_icon)
    #             item_verdict.setTextAlignment(Qt.AlignCenter)
    #             self.table.setItem(row, 2, item_verdict)

    #             # Тип проверки
    #             type_icon = self.create_type_icon(p['test_type'])
    #             item_type = QTableWidgetItem()
    #             item_type.setIcon(type_icon)
    #             item_type.setTextAlignment(Qt.AlignCenter)
    #             self.table.setItem(row, 3, item_type)

    #             # Герметичность
    #             sealed_icon = self.create_sealed_icon(p['is_sealed'])
    #             item_sealed = QTableWidgetItem()
    #             item_sealed.setIcon(sealed_icon)
    #             item_sealed.setTextAlignment(Qt.AlignCenter)
    #             self.table.setItem(row, 4, item_sealed)

    #         else:
    #             # Расширенный режим: текстовые значения
    #             # Модификация
    #             self.table.setItem(row, 2, QTableWidgetItem(p.get('mod_name', '—')))
    #             # Герметичность (текст)
    #             sealed_text = 'Да' if p['is_sealed'] else 'Нет'
    #             self.table.setItem(row, 3, QTableWidgetItem(sealed_text))
    #             # Тип проверки
    #             self.table.setItem(row, 4, QTableWidgetItem(p['test_type'] or '—'))
    #             # Заказ
    #             self.table.setItem(row, 5, QTableWidgetItem(p.get('order_number', '—')))
    #             # Вердикт (текст)
    #             verdict_text = p['verdict'] or '—'
    #             self.table.setItem(row, 6, QTableWidgetItem(verdict_text))

    #             # Подсветка строки в расширенном режиме
    #             row_color = QColor(200, 255, 200) if p['verdict'] == 'годен' else QColor(255, 200, 200) if p['verdict'] == 'не годен' else None
    #             if row_color:
    #                 for col in range(self.table.columnCount()):
    #                     item = self.table.item(row, col)
    #                     if item:
    #                         item.setBackground(row_color)

    #         # Дополнительно: в компактном режиме можно не подсвечивать строки, оставить прозрачными.

    #     # Включаем сортировку
    #     self.table.setSortingEnabled(True)
    #     # Сортировка по дате по умолчанию (только в компактном режиме)
    #     if compact:
    #         self.table.sortByColumn(1, Qt.DescendingOrder)
    #     else:
    #         self.table.sortByColumn(0, Qt.AscendingOrder)

    def create_verdict_icon(self, is_good):
        """Зелёный круг – годен, красный – не годен."""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QColor(0, 200, 0) if is_good else QColor(200, 0, 0))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        return QIcon(pixmap)

    def create_type_icon(self, type_str):
        """Иконка: I – первичная, II – повторная."""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setPen(QColor(0, 0, 200))
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "I" if "первичная" in str(type_str).lower() else "II")
        painter.end()
        return QIcon(pixmap)

    def create_sealed_icon(self, is_sealed):
        """Капля: синяя – герметичен, серая – не герметичен."""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QColor(0, 100, 255) if is_sealed else QColor(180, 180, 180))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, 8, 8, 6)
        points = [QPoint(4, 8), QPoint(8, 2), QPoint(12, 8)]
        polygon = QPolygon(points)
        painter.drawPolygon(polygon)
        painter.end()
        return QIcon(pixmap)

    def load_data(self):
        self.all_pumps = db.get_all_pumps()
        # Обновляем список заказов
        orders = db.get_all_orders()
        self.filter_order.blockSignals(True)
        self.filter_order.clear()
        self.filter_order.addItem("Все заказы")
        for oid, onum in orders:
            self.filter_order.addItem(onum, oid)
        self.filter_order.blockSignals(False)
        self.apply_filters()

    def update_stats(self, filtered_pumps):
        """Обновляет статистику по заказу, если выбран конкретный заказ."""
        # Проверяем, выбран ли заказ в фильтрах
        if 'order_number' in self.current_filters and self.current_filters['order_number']:
            order_number = self.current_filters['order_number']
            total = len(filtered_pumps)
            if total == 0:
                self.stats_label.setText(f"Для заказа №{order_number} нет данных с учётом текущих фильтров.")
                self.stats_label.show()
                return

            good = sum(1 for p in filtered_pumps if p.get('verdict') == 'годен')
            not_sealed = sum(1 for p in filtered_pumps if p.get('is_sealed') is False)
            good_first = sum(1 for p in filtered_pumps if p.get('verdict') == 'годен' and p.get('test_type') == 'первичная')

            good_percent = round(good / total * 100, 1)
            not_sealed_percent = round(not_sealed / total * 100, 1)
            good_first_percent = round(good_first / total * 100, 1)

            text = (f"Для заказа <b>№{order_number}</b> проверено <b>{total}</b> насосов: <br>"
                    f"годных — <b>{good}</b> ({good_percent}%), <br>"
                    f"годных с первого предъявления — <b>{good_first}</b> ({good_first_percent}%), <br>"
                    f"негерметичных — <b>{not_sealed}</b> ({not_sealed_percent}%), ")
            self.stats_label.setText(text)
            self.stats_label.show()
        else:
            self.stats_label.hide()

    def apply_filters(self):
        filters = {}
        search_text = self.search_input.text().strip()
        if search_text:
            filters['pump_number'] = search_text

        verdict = self.filter_verdict.currentText()
        if verdict != 'Все':
            filters['verdict'] = verdict.lower()  # приводим к нижнему регистру для сравнения с БД

        test_type = self.filter_test_type.currentText()
        if test_type != 'Все':
            filters['test_type'] = test_type.lower()

        sealed = self.filter_sealed.currentText()
        if sealed == 'Герметичен':
            filters['is_sealed'] = 1
        elif sealed == 'Не герметичен':
            filters['is_sealed'] = 0

        # Фильтр по заказу
        if hasattr(self, 'filter_order'):
            order_text = self.filter_order.currentText()
            if order_text != "Все заказы":
                filters['order_number'] = order_text

        # Дата
        date_from = self.date_from.date().toString('yyyy-MM-dd')
        date_to = self.date_to.date().toString('yyyy-MM-dd')
        if date_from != '2000-01-01' or date_to != QDate.currentDate().toString('yyyy-MM-dd'):
            filters['date_from'] = date_from
            filters['date_to'] = date_to

        if self.only_duplicates.isChecked():
            filters['only_duplicates'] = True

        self.current_filters = filters

        # Подсчёт общего количества
        self.total_records = db.count_pumps(filters)

        # Пагинация
        offset = self.current_page * self.page_size
        filtered = db.get_all_pumps(filters, limit=self.page_size, offset=offset)

        # Определяем, нужно ли группировать по номеру (если включён фильтр "Только дубли")
        group_by_number = self.only_duplicates.isChecked()

        # Отображаем данные и статистику
        self.display_pumps(filtered, group_by_number=group_by_number)
        self.update_stats(filtered)

        self.update_pagination_label()

        # Сигнал для статус-бара
        if hasattr(self, 'filters_applied'):
            self.filters_applied.emit(filters)

    def display_pumps(self, pumps, group_by_number=False):

        self.populate_table(pumps, compact=self.compact_mode)
        # Отключаем сортировку перед заполнением
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(pumps))

        # Если включена группировка по номеру, сортируем данные по номеру насоса
        if group_by_number:
            # Сортируем по номеру насоса, затем по дате (чтобы внутри группы были по дате)
            pumps = sorted(pumps, key=lambda x: (x['pump_number'], x['test_date']))
            # Создаём карту цветов для уникальных номеров
            colors = [QColor(212, 230, 241), QColor(253, 235, 208)]  # бледно-голубой и бледно-оранжевый
            unique_numbers = {}
            color_index = 0
            for p in pumps:
                num = p['pump_number']
                if num not in unique_numbers:
                    unique_numbers[num] = colors[color_index % len(colors)]
                    color_index += 1
        else:
            unique_numbers = None

        for row, p in enumerate(pumps):
            # Номер с ID
            item_num = QTableWidgetItem(p['pump_number'])
            item_num.setData(Qt.UserRole, p['id'])
            self.table.setItem(row, 0, item_num)

            # Дата (обрезаем время)
            date_str = p['test_date']
            if date_str and ' ' in date_str:
                date_str = date_str.split(' ')[0]
            self.table.setItem(row, 1, QTableWidgetItem(date_str))

            # Вердикт
            verdict_item = QTableWidgetItem(p['verdict'] or '')
            if p['verdict'] == 'годен':
                verdict_item.setBackground(QColor(200, 255, 200))  # светло-зелёный
            elif p['verdict'] == 'не годен':
                verdict_item.setBackground(QColor(255, 200, 200))  # светло-красный
            self.table.setItem(row, 2, verdict_item)

            # Тип
            self.table.setItem(row, 3, QTableWidgetItem(p['test_type'] or ''))

            # Герметичность
            sealed_text = 'Да' if p['is_sealed'] else 'Нет'
            sealed_item = QTableWidgetItem(sealed_text)
            if p['is_sealed']:
                sealed_item.setBackground(QColor(200, 255, 200))
            else:
                sealed_item.setBackground(QColor(255, 200, 200))
            self.table.setItem(row, 4, sealed_item)

            # Кол-во проверок
            count = p.get('check_count', 0)
            self.table.setItem(row, 5, QTableWidgetItem(str(count)))

            # Устанавливаем цвет группы для всей строки (если включена группировка)
            if group_by_number and unique_numbers:
                group_color = unique_numbers.get(p['pump_number'])
                if group_color:
                    for col in range(self.table.columnCount()):
                        # Пропускаем столбцы 2 (вердикт) и 4 (герметичность) – у них свой фон
                        if col in [2, 4]:
                            continue
                        item = self.table.item(row, col)
                        if item:
                            item.setBackground(group_color)

            print(f"display_pumps: row={row}, id={p['id']}, number={p['pump_number']}")

        # Включаем сортировку обратно
        self.table.setSortingEnabled(True)
        # Если группировка выключена, сортируем по дате по умолчанию
        if not group_by_number:
            self.table.sortByColumn(1, Qt.DescendingOrder)
        else:
            # Если группировка включена, сортируем по номеру насоса (по возрастанию)
            self.table.sortByColumn(0, Qt.AscendingOrder)

    def on_selection_changed(self):
        """Обработка выбора строки (только в компактном режиме)."""
        if not self.compact_mode:
            # В расширенном режиме просто выделяем строку, ничего не делаем
            return
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        item = self.table.item(row, 0)
        if item is None:
            return
        pump_id = item.data(Qt.UserRole)
        if pump_id is None:
            return
        pump_data = db.get_pump_by_id(pump_id)
        if pump_data:
            self.pump_selected.emit(pump_data)
    # в расширенном режиме ничего не делаем, только выделение

    def show_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        item = self.table.item(row, 0)
        if not item:
            return
        pump_id = item.data(Qt.UserRole)
        if not pump_id:
            return

        menu = QMenu(self)
        action_view = menu.addAction("Показать протокол....")
        action_edit = menu.addAction("Вставить примечание")
        action_delete = menu.addAction("Удалить")

        action = menu.exec_(self.table.mapToGlobal(pos))

        if action == action_view:
            # Сворачиваем расширенный вид, если он включён
            if not self.compact_mode:
                self.btn_view_toggle.setChecked(False)  # переключаем в компактный
            # Теперь выбираем строку и отправляем сигнал
            self.table.selectRow(row)
            self.on_selection_changed()
        elif action == action_edit:
            self.request_edit.emit(pump_id)
        elif action == action_delete:
            self.request_delete.emit(pump_id)

    def on_delete_clicked(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        item = self.table.item(row, 0)
        if not item:
            return
        pump_id = item.data(Qt.UserRole)
        if pump_id:
            self.request_delete.emit(pump_id)

    def reset_filters(self):
        self.search_input.clear()
        self.filter_verdict.setCurrentIndex(0)
        self.filter_test_type.setCurrentIndex(0)
        self.filter_sealed.setCurrentIndex(0)
        self.filter_order.setCurrentIndex(0)
        self.date_from.setDate(QDate(2000, 1, 1))
        self.date_to.setDate(QDate.currentDate())
        self.only_duplicates.setChecked(False)
        self.current_page = 0
        self.apply_filters()

    def refresh(self):
        self.current_page = 0
        self.load_data()

    def next_page(self):
        if (self.current_page + 1) * self.page_size < self.total_records:
            self.current_page += 1
            self.apply_filters()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.apply_filters()

    def update_pagination_label(self):
        total_pages = max(1, (self.total_records + self.page_size - 1) // self.page_size)
        self.page_label.setText(f"Страница {self.current_page + 1} из {total_pages}")
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled((self.current_page + 1) * self.page_size < self.total_records)
        self.count_label.setText(f"Всего записей: {self.total_records}")
    