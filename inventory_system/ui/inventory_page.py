import tempfile
import webbrowser
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea,
    QLineEdit, QLabel, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMenu, QApplication, QAbstractItemView, QComboBox,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QFont, QMouseEvent

from database import Database
from config import CONTAINER_FIELDS, NUMERIC_INDICES


class DoubleClickComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pending = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(400)
        self._timer.timeout.connect(self._reset)

    def _reset(self):
        self._pending = False

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            if self._pending:
                self._timer.stop()
                self._pending = False
                super().mousePressEvent(event)
            else:
                self._pending = True
                self._timer.start()
        else:
            super().mousePressEvent(event)


class InventoryPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.db = Database()
        self._table = None
        self._loading = False
        self.undo_stack = []
        self.original_batch = None

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # ---- title + search ----
        header = QHBoxLayout()
        title = QLabel('入库登记')
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        header.addWidget(title)
        header.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('输入批号定位...')
        self.search_input.setFixedWidth(220)
        header.addWidget(self.search_input)

        locate_btn = QPushButton('定位')
        locate_btn.setObjectName('ToolBtn')
        locate_btn.clicked.connect(self.locate_batch)
        header.addWidget(locate_btn)
        root.addLayout(header)

        # ---- form fields (no GroupBox, just labels + inputs in a grid) ----
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_widget = QWidget()
        form = QVBoxLayout(form_widget)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(14)

        self.entries = {}

        def add_field_row(layout, label_text, fields, cols=6):
            lbl = QLabel(label_text)
            section_font = QFont()
            section_font.setPointSize(13)
            section_font.setBold(True)
            lbl.setFont(section_font)
            lbl.setObjectName('FieldLabel')
            layout.addWidget(lbl)

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 2, 0, 0)
            row_layout.setSpacing(10)
            for f in fields:
                ent = QLineEdit()
                ent.setPlaceholderText(f)
                ent.setMinimumWidth(90)
                row_layout.addWidget(ent, 1)
                self.entries[f] = ent
            row_layout.addStretch()
            layout.addWidget(row_widget)

        add_field_row(form, '基本信息', ['批号', '位置', '类别', '名称', '规格'], cols=5)
        add_field_row(form, '粘度参数 (cSt)', ['V100', 'V40', 'v50', 'v20', 'v-20', 'v-40', 'v-51'], cols=7)
        add_field_row(form, '理化指标', ['酸值', '闪点', '凝点', '粘度指数', '密度', '溴值'], cols=6)
        add_field_row(form, '库存信息', ['重量', '单位', '单价', '日期'], cols=4)
        add_field_row(form, '入库人员', ['入库经手人', '入库登记人', '领用单位', '领用人'], cols=4)

        self.entries['日期'].setText(datetime.now().strftime("%Y-%m-%d"))

        # Replace '单位' QLineEdit with QComboBox
        unit_edit = self.entries['单位']
        unit_parent = unit_edit.parent()
        unit_layout = unit_parent.layout()
        if unit_layout is None:
            unit_layout = unit_parent.parentWidget().layout()
        idx = unit_layout.indexOf(unit_edit)
        self.unit_combo = DoubleClickComboBox()
        self.unit_combo.addItems(['公斤', '吨', '个'])
        self.unit_combo.setMinimumWidth(90)
        unit_layout.insertWidget(idx, self.unit_combo)
        unit_edit.hide()
        self.entries['单位'] = self.unit_combo

        scroll.setWidget(form_widget)
        root.addWidget(scroll)

        # ---- action buttons ----
        btn_row = QHBoxLayout()
        save_btn = QPushButton('入库登记')
        save_btn.clicked.connect(self.save_container)
        clear_btn = QPushButton('清空表单')
        clear_btn.setObjectName('ToolBtn')
        clear_btn.clicked.connect(self.clear_form)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(clear_btn)
        print_btn = QPushButton('打印单据')
        print_btn.setObjectName('ToolBtn')
        print_btn.clicked.connect(self.print_last_inbound)
        btn_row.addWidget(print_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # ---- table ----
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setColumnCount(len(CONTAINER_FIELDS))
        self.table.setHorizontalHeaderLabels(CONTAINER_FIELDS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.itemChanged.connect(self._on_cell_changed)
        root.addWidget(self.table, 1)

        self.refresh_table()

    def _get_form_values(self):
        vals = []
        for f in CONTAINER_FIELDS:
            if f == '状态':
                vals.append('在库')
            elif f not in self.entries:
                vals.append('')
            elif isinstance(self.entries[f], QComboBox):
                vals.append(self.entries[f].currentText())
            else:
                text = self.entries[f].text().strip()
                vals.append(text)
        return vals

    def _set_form_values(self, row_data):
        for i, f in enumerate(CONTAINER_FIELDS):
            if f == '状态' or f not in self.entries:
                continue
            val = row_data[i] if i < len(row_data) else ''
            if isinstance(self.entries[f], QComboBox):
                idx = self.entries[f].findText(str(val) if val is not None else '公斤')
                if idx >= 0:
                    self.entries[f].setCurrentIndex(idx)
            else:
                self.entries[f].setText(str(val) if val is not None else '')

    def clear_form(self):
        for f in CONTAINER_FIELDS:
            if f == '状态':
                continue
            if isinstance(self.entries[f], QComboBox):
                self.entries[f].setCurrentIndex(0)
            else:
                self.entries[f].setText('')
        self.entries['日期'].setText(datetime.now().strftime("%Y-%m-%d"))
        self.original_batch = None
        self.entries['批号'].setReadOnly(False)

    def locate_batch(self):
        batch = self.search_input.text().strip()
        if not batch:
            return
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text() == batch:
                self.table.selectRow(row)
                self.table.scrollToItem(item)
                return
        QMessageBox.information(self, '提示', '未找到该批号')

    def load_container(self):
        batch = self.search_input.text().strip()
        if not batch:
            QMessageBox.warning(self, '提示', '请输入批号')
            return
        row = self.db.get_container(batch)
        if row:
            self.original_batch = batch
            self._set_form_values(row)
            self.entries['批号'].setText(batch)
        else:
            QMessageBox.information(self, '提示', '未找到该批号')
            self.original_batch = None

    def save_container(self):
        try:
            vals = self._get_form_values()
            if not vals[0]:
                QMessageBox.critical(self, '错误', '批号不能为空')
                return

            num_vals = []
            for i, v in enumerate(vals):
                if i in NUMERIC_INDICES:
                    num_vals.append(float(v) if v else None)
                else:
                    num_vals.append(v)

            new_batch = num_vals[0]
            old_row = None
            if self.original_batch:
                old_row = self.db.get_container(self.original_batch)

            # Check if this is a NEW container (not an edit)
            existing = self.db.get_container(new_batch)
            is_new = (existing is None)

            if self.original_batch and new_batch != self.original_batch:
                self.db.update_container_batch_in_transactions(new_batch, self.original_batch)
                self.db.conn.execute("DELETE FROM containers WHERE 批号=?", (self.original_batch,))
                self.db.conn.commit()

            self.db.save_container(num_vals)

            # For new containers, create an inbound transaction record
            if is_new:
                io_date = num_vals[CONTAINER_FIELDS.index('日期')] or datetime.now().strftime("%Y-%m-%d")
                date_part = io_date.replace('-', '')
                prefix = 'R'
                seq = self.db.get_transaction_seq(f"{prefix}{date_part}") + 1
                io_id = f"{prefix}{date_part}{seq:03d}"
                weight_idx = CONTAINER_FIELDS.index('重量')
                op_weight = num_vals[weight_idx] if num_vals[weight_idx] else 0.0
                trans_vals = [
                    io_id, '入库', io_date, '',
                    new_batch,
                    num_vals[CONTAINER_FIELDS.index('位置')] or '',
                    num_vals[CONTAINER_FIELDS.index('类别')] or '',
                    num_vals[CONTAINER_FIELDS.index('名称')] or '',
                    num_vals[CONTAINER_FIELDS.index('规格')] or '',
                    op_weight,
                    num_vals[CONTAINER_FIELDS.index('入库经手人')] or '',
                    num_vals[CONTAINER_FIELDS.index('入库登记人')] or '',
                    num_vals[CONTAINER_FIELDS.index('领用单位')] or '',
                    num_vals[CONTAINER_FIELDS.index('领用人')] or '',
                    '',
                ]
                self.db.add_transaction(trans_vals)

            if not is_new:
                self.db.sync_container_to_transactions(new_batch)

            if old_row:
                self.undo_stack.append({
                    'type': 'container_update',
                    'old_vals': list(old_row)
                })
                if len(self.undo_stack) > 10:
                    self.undo_stack.pop(0)

            self._update_table_row(new_batch, num_vals)
            self.main_window.pages['home'].refresh()
            self.main_window.pages['statistics'].refresh_stat()
            msg = f'批号 {new_batch} 入库登记成功'
            if is_new:
                msg += f'\n入库流水号：{io_id}'
                self.main_window.pages['log'].search()
            QMessageBox.information(self, '成功', msg)
            self.clear_form()
        except Exception as e:
            QMessageBox.critical(self, '保存失败', str(e))

    def delete_container(self, batch):
        reply = QMessageBox.question(
            self, '确认删除',
            f'永久删除批号 [{batch}] 及其所有记录？',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                self.db.delete_container(batch)
                self.refresh_table()
                self.main_window.pages['home'].refresh()
                self.main_window.pages['statistics'].refresh_stat()
                self.main_window.pages['log'].search()
                QMessageBox.information(self, '成功', '已删除')
            except Exception as e:
                QMessageBox.critical(self, '删除失败', str(e))

    def _update_table_row(self, batch, vals):
        self._loading = True
        self.table.setUpdatesEnabled(False)
        # Find existing row for this batch, or add a new one
        row_idx = -1
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item and item.text().strip() == batch:
                row_idx = r
                break
        if row_idx < 0:
            row_idx = self.table.rowCount()
            self.table.setRowCount(row_idx + 1)
        for c, val in enumerate(vals):
            item = QTableWidgetItem(str(val) if val is not None else '')
            if c == 0:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row_idx, c, item)
        self.table.setUpdatesEnabled(True)
        self._loading = False

    def refresh_table(self):
        self._loading = True
        self.table.setUpdatesEnabled(False)
        rows = self.db.get_all_containers()
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                item = QTableWidgetItem(str(val) if val is not None else '')
                if c == 0:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(r, c, item)
        self.table.setUpdatesEnabled(True)
        self._loading = False

    def _on_cell_changed(self, item):
        if self._loading:
            return
        row = item.row()
        col = item.column()
        batch_item = self.table.item(row, 0)
        if not batch_item:
            return
        batch = batch_item.text().strip()
        field = CONTAINER_FIELDS[col]
        new_val = item.text().strip()

        # Get current full row and update the changed field
        cur = self.db.get_container(batch)
        if not cur:
            return
        vals = list(cur)
        vals[col] = new_val if new_val else None

        # Convert numeric fields
        if col in NUMERIC_INDICES:
            try:
                vals[col] = float(new_val) if new_val else None
            except (ValueError, TypeError):
                return

        self.db.save_container(vals)
        self.main_window.pages['home'].refresh()
        self.main_window.pages['statistics'].refresh_stat()


    def _show_context_menu(self, pos):
        row = self.table.currentRow()
        if row < 0:
            return
        batch = self.table.item(row, 0).text()
        menu = QMenu(self)
        menu.addAction('复制批号', lambda b=batch: self._copy_batch(b))
        menu.addAction('修改信息', lambda b=batch: self._edit_batch(b))
        menu.addSeparator()
        menu.addAction('彻底删除', lambda b=batch: self.delete_container(b))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _copy_batch(self, batch):
        QApplication.clipboard().setText(batch)
        QMessageBox.information(self, '提示', f'已复制批号: {batch}')

    def _edit_batch(self, batch):
        self.search_input.setText(batch)
        self.load_container()

    def perform_undo(self):
        if not self.undo_stack:
            QMessageBox.information(self, '提示', '没有可撤销的操作')
            return
        last = self.undo_stack.pop()
        if last['type'] == 'container_update':
            try:
                old_vals = last['old_vals']
                self.db.save_container(old_vals)
                self.refresh_table()
                self.main_window.pages['home'].refresh()
                self.main_window.pages['statistics'].refresh_stat()
                QMessageBox.information(self, '撤销成功', '已恢复桶信息修改')
            except Exception as e:
                QMessageBox.critical(self, '撤销失败', str(e))

    def print_last_inbound(self):
        row = self.db.conn.execute(
            "SELECT 出入库编号,操作类型,日期,批号,位置,类别,名称,规格,操作重量,入库经手人,入库登记人,领用单位,领用人,出库领用人 "
            "FROM transactions WHERE 操作类型='入库' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not row:
            QMessageBox.information(self, '提示', '暂无入库记录')
            return
        io_id, op_type, date, batch, loc, cat, name, spec, weight, in_handler, in_registrar, use_unit, user, _ = [
            str(x) if x is not None else '' for x in row]
        # 查询单位、单价
        unit, price = '', ''
        if batch:
            c = self.db.conn.execute(
                "SELECT 单位, 单价 FROM containers WHERE 批号=?", (batch,)
            ).fetchone()
            if c:
                unit = str(c[0]) if c[0] else ''
                price = str(c[1]) if c[1] else ''
        # 计算金额：无单价则金额留空
        amount = ''
        if price:
            try:
                w = float(weight or 0)
                p = float(price)
                if p:
                    amount = round(w * p, 2)
            except ValueError:
                pass
        # 备注：批号+位置
        remark = f'{batch} / {loc}'.strip(' / ')
        # 来料单位：优先用领用单位，否则用入库经手人
        lai_liao = use_unit or in_handler or ''
        # 数据行：1行填充 + 7行空白
        data_rows = f'''<tr>
                <td>1</td><td>{cat}</td><td>{name}</td><td>{spec}</td>
                <td>{unit}</td><td>{price}</td><td>{weight}</td><td>{amount}</td><td>{remark}</td>
            </tr>'''
        for _ in range(7):
            data_rows += '<tr><td>&nbsp;</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>'
        html = f"""<html><head><meta charset="utf-8"><style>
            @page {{ size: A4; margin: 12mm 15mm; }}
            body {{ font-family: 'SimSun','宋体',serif; font-size: 12pt; margin: 0; padding: 10px; }}
            .lian-ci {{ position: absolute; right: 10px; top: 2px; font-size: 7pt; text-align: right; line-height: 1.5; }}
            .lian-ci .white {{ color: #999; }}
            .lian-ci .red {{ color: #c00; }}
            .lian-ci .yellow {{ color: #b90; }}
            .header-table {{ width: 100%; border-collapse: collapse; margin-bottom: 2px; }}
            .header-table td {{ padding: 4px 0; }}
            .company {{ text-align: center; font-size: 14pt; font-weight: bold; }}
            .title-wrapper {{ position: relative; text-align: center; margin: 6px 0; }}
            .title-text {{ font-size: 20pt; font-weight: bold; letter-spacing: 1em; }}
            .no-abs {{ position: absolute; right: 0; top: 50%; transform: translateY(-50%); font-size: 10pt; white-space: nowrap; }}
            .info-table {{ width: 100%; border-collapse: collapse; margin-bottom: 6px; }}
            .info-table td {{ font-size: 11pt; padding: 3px 0; }}
            table.data {{ width: 100%; border-collapse: collapse; }}
            table.data th, table.data td {{ border: 1.5px solid #000; padding: 6px 4px; text-align: center; font-size: 11pt; }}
            table.data th {{ background: #f0f0f0; font-weight: bold; }}
            .heji-label {{ text-align: right !important; font-weight: bold; }}
            .heji-amount {{ font-weight: bold; }}
            .footer-table {{ width: 100%; border-collapse: collapse; margin-top: 0; }}
            .footer-table td {{ border: 1.5px solid #000; padding: 6px 4px; text-align: center; font-size: 11pt; }}
            .footer-table .fl {{ text-align: center; font-weight: bold; width: 10%; }}
            .footer-table .fv {{ width: 15%; }}
            .no-print {{ color: #666; margin-top: 20px; font-size: 10pt; }}
            @media print {{ .no-print {{ display: none; }} }}
        </style></head><body>
        <div style="position:relative;">
            <div class="lian-ci">
                <span class="white">白色:存根联</span>
                <span class="red">红色:领料员</span>
                <span class="yellow">黄色:财务联</span>
            </div>
        </div>
        <table class="header-table">
            <tr><td class="company">抚顺市德隆石化制品有限公司</td></tr>
        </table>
        <div class="title-wrapper">
            <span class="title-text">入 库 单</span>
            <span class="no-abs"><b>NO.</b> {io_id}</span>
        </div>
        <table class="info-table">
            <tr>
                <td style="width:33%;">来料单位: {lai_liao}</td>
                <td style="width:33%;text-align:center;">日期: {date}</td>
                <td style="width:34%;text-align:right;">单位: {unit}</td>
            </tr>
        </table>
        <table class="data">
            <tr><th>编号</th><th>类别</th><th>名称</th><th>型号</th><th>单位</th><th>单价</th><th>数量</th><th>金额</th><th>备注</th></tr>
            {data_rows}
            <tr><td class="heji-label" colspan="7">合&emsp;&emsp;计</td><td class="heji-amount">{amount}</td><td></td></tr>
        </table>
        <table class="footer-table">
            <tr>
                <td class="fl">主管</td><td class="fv">&nbsp;</td>
                <td class="fl">财会</td><td class="fv">&nbsp;</td>
                <td class="fl">领用人</td><td class="fv">&nbsp;</td>
                <td class="fl">制表</td><td class="fv">&nbsp;</td>
            </tr>
        </table>
        <p class="no-print">按 Ctrl+P / Cmd+P 选择"另存为PDF"即可生成正式单据。</p>
        </body></html>"""
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8")
        tmp.write(html)
        tmp.close()
        webbrowser.open(f"file://{tmp.name}")
        QMessageBox.information(self, '打印就绪', '入库单已在浏览器打开，请使用打印功能生成入库凭证。')

    def set_edit_mode(self, locked):
        trigger = QAbstractItemView.EditTrigger.NoEditTriggers if locked else QAbstractItemView.EditTrigger.DoubleClicked
        self.table.setEditTriggers(trigger)

    def refresh_all(self):
        self.refresh_table()
        self.main_window.pages['home'].refresh()
        self.main_window.pages['log'].search()
