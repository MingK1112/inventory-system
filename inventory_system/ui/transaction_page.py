import tempfile
import webbrowser
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QLabel, QMessageBox, QComboBox,
)
from PySide6.QtGui import QFont, QMouseEvent
from PySide6.QtCore import Qt, QTimer

from database import Database


class DoubleClickComboBox(QComboBox):
    """QComboBox that opens popup only on double-click (within 400ms)."""
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


class TransactionPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.db = Database()
        self.undo_stack = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(14)

        # title
        title = QLabel('出库登记')
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        root.addWidget(title)

        # --- operation section ---
        sec1 = QLabel('操作信息')
        sec1_font = QFont()
        sec1_font.setPointSize(12)
        sec1_font.setBold(True)
        sec1.setFont(sec1_font)
        sec1.setObjectName('FieldLabel')
        root.addWidget(sec1)

        # date + type
        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        date_lbl = QLabel('操作日期')
        date_lbl.setObjectName('MutedLabel')
        top_row.addWidget(date_lbl)
        self.date_input = QLineEdit(datetime.now().strftime("%Y-%m-%d"))
        self.date_input.setFixedWidth(160)
        top_row.addWidget(self.date_input)

        top_row.addStretch()
        root.addLayout(top_row)

        # batch search
        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        batch_lbl = QLabel('批号')
        batch_lbl.setObjectName('MutedLabel')
        search_row.addWidget(batch_lbl)
        self.batch_search = QLineEdit()
        self.batch_search.setPlaceholderText('输入批号自动带出')
        self.batch_search.setFixedWidth(180)
        search_row.addWidget(self.batch_search)
        auto_btn = QPushButton('自动带出')
        auto_btn.setObjectName('ToolBtn')
        auto_btn.clicked.connect(self.auto_fill)
        search_row.addWidget(auto_btn)
        search_row.addStretch()
        root.addLayout(search_row)

        # --- detail section ---
        sec2 = QLabel('出库明细')
        sec2_font = QFont()
        sec2_font.setPointSize(12)
        sec2_font.setBold(True)
        sec2.setFont(sec2_font)
        sec2.setObjectName('FieldLabel')
        root.addWidget(sec2)

        self.io_entries = {}

        def add_detail_row(layout, label_text, fields):
            lbl = QLabel(label_text)
            lbl_font = QFont()
            lbl_font.setPointSize(11)
            lbl_font.setBold(True)
            lbl.setFont(lbl_font)
            lbl.setObjectName('FieldLabel')
            layout.addWidget(lbl)

            row = QHBoxLayout()
            row.setSpacing(10)
            for f in fields:
                ent = QLineEdit()
                ent.setPlaceholderText(f)
                ent.setMinimumWidth(100)
                row.addWidget(ent, 1)
                self.io_entries[f] = ent
            row.addStretch()
            layout.addLayout(row)

        add_detail_row(root, '基本信息', ['批号', '位置', '类别', '名称', '规格'])
        # 库存信息 row with unit combo
        inv_lbl = QLabel('库存信息')
        inv_font = QFont()
        inv_font.setPointSize(11)
        inv_font.setBold(True)
        inv_lbl.setFont(inv_font)
        inv_lbl.setObjectName('FieldLabel')
        root.addWidget(inv_lbl)
        inv_row = QHBoxLayout()
        inv_row.setSpacing(10)
        self.io_entries['操作重量'] = QLineEdit()
        self.io_entries['操作重量'].setPlaceholderText('操作重量')
        self.io_entries['操作重量'].setMinimumWidth(100)
        inv_row.addWidget(self.io_entries['操作重量'], 1)
        self.unit_combo = DoubleClickComboBox()
        self.unit_combo.addItems(['公斤', '吨', '个'])
        self.unit_combo.setMinimumWidth(80)
        inv_row.addWidget(self.unit_combo)
        inv_row.addStretch()
        root.addLayout(inv_row)
        add_detail_row(root, '出库信息', ['出库领用人'])

        root.addSpacing(4)

        # buttons
        btn_row = QHBoxLayout()
        self.submit_btn = QPushButton('提交登记')
        self.submit_btn.clicked.connect(self.submit)
        print_btn = QPushButton('打印最新单据')
        print_btn.setObjectName('ToolBtn')
        print_btn.clicked.connect(self.print_last_slip)
        btn_row.addWidget(self.submit_btn)
        btn_row.addWidget(print_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        root.addStretch()

    def auto_fill(self):
        batch = self.batch_search.text().strip()
        if not batch:
            return
        row = self.db.get_container(batch)
        if row:
            self.io_entries['批号'].setText(batch)
            self.io_entries['位置'].setText(str(row[1] or ''))
            self.io_entries['类别'].setText(str(row[2] or ''))
            self.io_entries['名称'].setText(str(row[3] or ''))
            self.io_entries['规格'].setText(str(row[4] or ''))
            self.io_entries['操作重量'].setText(str(row[10] or '0.00'))
        else:
            QMessageBox.warning(self, '提示', '未找到该批号，请先在入库登记中录入')

    def submit(self):
        try:
            batch = self.io_entries['批号'].text().strip()
            if not batch:
                QMessageBox.critical(self, '错误', '请输入或带出批号')
                return
            try:
                op_weight = float(self.io_entries['操作重量'].text() or 0)
            except ValueError:
                QMessageBox.critical(self, '错误', '操作重量必须为数字')
                return
            if op_weight <= 0:
                QMessageBox.critical(self, '错误', '操作重量必须大于0')
                return
            cur_row = self.db.get_container(batch)
            if not cur_row:
                QMessageBox.critical(self, '错误', '该批号不存在')
                return
            current_w = cur_row[10] or 0.0
            current_status = cur_row[18]
            io_date = self.date_input.text().strip() or datetime.now().strftime("%Y-%m-%d")
            if op_weight > current_w:
                QMessageBox.critical(self, '错误', f'出库重量({op_weight})不能大于当前库存({current_w})')
                return
            new_w = current_w - op_weight
            new_status = '在库' if new_w > 0.01 else '已出库'
            prefix = 'C'
            date_part = io_date.replace('-', '')
            seq = self.db.get_transaction_seq(f"{prefix}{date_part}") + 1
            io_id = f"{prefix}{date_part}{seq:03d}"
            dl_seq = self.db.get_transaction_seq(f"DL{date_part}") + 1
            out_code = f"DL{date_part}{dl_seq:03d}"
            vals = [io_id, '出库', io_date, out_code, batch,
                    self.io_entries['位置'].text(), self.io_entries['类别'].text(),
                    self.io_entries['名称'].text(), self.io_entries['规格'].text(),
                    op_weight, '', '', '', '', self.io_entries['出库领用人'].text()]
            self.db.add_transaction(vals)
            self.db.update_container_weight_status(new_w, new_status, io_date, batch)
            self.undo_stack.append({
                'type': 'transaction_insert', 'io_id': io_id, 'batch': batch,
                'old_weight': current_w, 'old_status': current_status,
            })
            if len(self.undo_stack) > 10:
                self.undo_stack.pop(0)
            self.refresh_all()
            for ent in self.io_entries.values():
                ent.setText('')
            QMessageBox.information(self, '成功', f'出库完成！流水号：{io_id}\n当前重量：{new_w:.2f} kg')
        except Exception as e:
            import traceback
            self.db.conn.rollback()
            QMessageBox.critical(self, '提交失败', f'{e}\n{traceback.format_exc()}')

    def print_last_slip(self):
        row = self.db.get_last_transaction()
        if not row:
            QMessageBox.information(self, '提示', '暂无出入库记录')
            return
        # 查询单位、单价等额外信息
        io_id, op_type, date, code, batch, loc, cat, name, spec, weight, in_handler, in_registrar, use_unit, user, out_handler = [
            str(x) if x is not None else '' for x in row]
        unit, price = '', ''
        if batch:
            c = self.db.conn.execute(
                "SELECT 单位, 单价 FROM containers WHERE 批号=?", (batch,)
            ).fetchone()
            if c:
                unit = str(c[0]) if c[0] else ''
                price = str(c[1]) if c[1] else ''
        self._gen_html_outbound(io_id, date, batch, loc, cat, name, spec, weight, unit, price, use_unit, out_handler)

    def _gen_html_outbound(self, io_id, date, batch, loc, cat, name, spec, weight, unit, price, use_unit, out_handler):
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
        # 8行数据表格：1行填充 + 7行空白
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
            <span class="title-text">出 库 单</span>
            <span class="no-abs"><b>NO.</b> {io_id}</span>
        </div>
        <table class="info-table">
            <tr>
                <td style="width:33%;">领料单位: {use_unit}</td>
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
        QMessageBox.information(self, '打印就绪', '出库单已在浏览器打开，请使用打印功能另存为PDF。')

    def perform_undo(self):
        if not self.undo_stack:
            QMessageBox.information(self, '提示', '没有可撤销的操作')
            return
        last = self.undo_stack.pop()
        if last['type'] == 'transaction_insert':
            try:
                self.db.delete_transaction(last['io_id'])
                self.db.conn.execute(
                    "UPDATE containers SET 重量=?, 状态=? WHERE 批号=?",
                    (last['old_weight'], last['old_status'], last['batch']))
                self.db.conn.commit()
                self.refresh_all()
                QMessageBox.information(self, '撤销成功', '已撤销出库登记')
            except Exception as e:
                QMessageBox.critical(self, '撤销失败', str(e))

    def refresh_all(self):
        self.main_window.pages['home'].refresh()
        self.main_window.pages['inventory'].refresh_table()
        self.main_window.pages['statistics'].refresh_stat()
        self.main_window.pages['log'].search()
