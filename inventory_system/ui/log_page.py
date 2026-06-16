import tempfile
import webbrowser

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QMenu,
    QAbstractItemView, QApplication, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont

from database import Database


class LogPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.db = Database()

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # title
        title = QLabel('出入库查询')
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        root.addWidget(title)

        # filter row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        filter_row.addWidget(QLabel('日期'))
        self.start_date = QLineEdit()
        self.start_date.setPlaceholderText('起始 YYYY-MM')
        self.start_date.setFixedWidth(120)
        filter_row.addWidget(self.start_date)
        filter_row.addWidget(QLabel('-'))
        self.end_date = QLineEdit()
        self.end_date.setPlaceholderText('结束 YYYY-MM')
        self.end_date.setFixedWidth(120)
        filter_row.addWidget(self.end_date)

        filter_row.addSpacing(16)
        filter_row.addWidget(QLabel('关键词'))
        self.kw_input = QLineEdit()
        self.kw_input.setPlaceholderText('批号/出入库编号/类别/名称')
        self.kw_input.setFixedWidth(180)
        filter_row.addWidget(self.kw_input)

        search_btn = QPushButton('查询')
        search_btn.setObjectName('ToolBtn')
        search_btn.clicked.connect(self.search)
        filter_row.addWidget(search_btn)
        filter_row.addStretch()
        root.addLayout(filter_row)

        # table
        self.cols = ['出入库编号', '操作类型', '日期', '编码', '批号', '位置', '类别', '名称', '规格', '重量', '入库经手人', '入库登记人', '领用单位', '领用人']
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setColumnCount(len(self.cols))
        self.table.setHorizontalHeaderLabels(self.cols)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_menu)
        root.addWidget(self.table, 1)

        # bottom
        bottom = QHBoxLayout()
        print_btn = QPushButton('打印选中单据')
        print_btn.setObjectName('ToolBtn')
        print_btn.clicked.connect(self.print_selected)
        bottom.addWidget(print_btn)
        bottom.addStretch()
        root.addLayout(bottom)

        self.search()

    def search(self):
        try:
            kw = f"%{self.kw_input.text().strip()}%"
            start = self.start_date.text().strip()
            end = self.end_date.text().strip()
            rows = self.db.search_transactions(kw, start, end)
            self.table.setUpdatesEnabled(False)
            self.table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                vals = list(row)
                # Combine weight (index 9) + unit (index 14): "675 (公斤)"
                weight = vals[9] if len(vals) > 9 else ''
                unit = vals[14] if len(vals) > 14 else ''
                if weight is not None and str(weight).strip():
                    vals[9] = f"{weight} ({unit})" if unit else str(weight)
                else:
                    vals[9] = ''
                for c in range(len(self.cols)):
                    val = vals[c]
                    self.table.setItem(r, c, QTableWidgetItem(str(val) if val is not None else ''))
            self.table.setUpdatesEnabled(True)
            self.table.resizeColumnsToContents()
        except Exception as e:
            self.table.setUpdatesEnabled(True)
            QMessageBox.critical(self, '查询失败', str(e))

    def _show_menu(self, pos):
        row = self.table.currentRow()
        if row < 0:
            return
        io_id = self.table.item(row, 0).text()
        batch = self.table.item(row, 4).text()
        menu = QMenu(self)
        menu.addAction('复制出入库编号', lambda: QApplication.clipboard().setText(io_id))
        menu.addAction('复制批号', lambda: QApplication.clipboard().setText(batch))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def print_selected(self):
        # 获取所有选中的行
        selected_rows = set()
        for idx in self.table.selectedIndexes():
            selected_rows.add(idx.row())
        if not selected_rows:
            QMessageBox.warning(self, '提示', '请先选中至少一条记录（可按住 Ctrl 或 Shift 多选）')
            return

        # 收集选中行的数据
        records = []
        for row_idx in selected_rows:
            row_data = [self.table.item(row_idx, c).text() if self.table.item(row_idx, c) else '' for c in range(len(self.cols))]
            io_id, op_type, date, code, batch, loc, cat, name, spec, weight_display, in_handler, in_registrar, use_unit, user = row_data
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
                    w = float(weight_display.split('(')[0].strip()) if '(' in weight_display else float(weight_display or 0)
                    p = float(price)
                    if p:
                        amount = round(w * p, 2)
                except (ValueError, AttributeError):
                    pass
            records.append({
                'io_id': io_id, 'op_type': op_type, 'date': date, 'batch': batch,
                'loc': loc, 'cat': cat, 'name': name, 'spec': spec,
                'weight_display': weight_display, 'unit': unit, 'price': price,
                'amount': amount, 'in_handler': in_handler, 'in_registrar': in_registrar,
                'use_unit': use_unit, 'user': user,
            })

        # 按日期 ASC，再按出入库编号 ASC 排序
        records.sort(key=lambda r: (r['date'], r['io_id']))

        # 多选时不允许混合出库和入库
        has_outbound = any('出库' in r['op_type'] for r in records)
        has_inbound = any('入库' in r['op_type'] for r in records)
        if len(records) > 1 and has_outbound and has_inbound:
            QMessageBox.warning(self, '提示', '出库单和入库单不能同时打印，请只选择同一类型的记录。')
            return

        # 统计信息
        numeric_amounts = [r['amount'] for r in records if isinstance(r['amount'], (int, float)) and r['amount']]
        total_amount = round(sum(numeric_amounts), 2) if numeric_amounts else ''
        has_outbound = any('出库' in r['op_type'] for r in records)
        has_inbound = any('入库' in r['op_type'] for r in records)

        # 标题
        if has_outbound:
            title = '出 库 单'
        else:
            title = '入 库 单'

        # NO. 显示范围
        if len(records) == 1:
            no_display = records[0]['io_id']
        else:
            first_id = records[0]['io_id']
            last_id = records[-1]['io_id']
            no_display = f'{first_id} ～ {last_id}'

        # 日期
        if len(records) == 1:
            date_display = records[0]['date']
        else:
            dates = sorted(set(r['date'] for r in records))
            date_display = f"{dates[0]} ~ {dates[-1]}"

        # 单位（取公共值）
        units = set(r['unit'] for r in records if r['unit'])
        unit_display = units.pop() if len(units) == 1 else ('/'.join(units) if units else '')

        # 来料/领料单位
        info_values = set()
        for r in records:
            if has_outbound:
                info_values.add(r['use_unit'])
            else:
                info_values.add(r['use_unit'] or r['in_handler'] or '')
        info_label = '领料单位' if has_outbound else '来料单位'
        info_value = next(iter(info_values)) if len(info_values) == 1 else ('/'.join(str(v) for v in info_values if v) or '')

        # 生成数据行（最多8行为一个单据页，超出可滚动）
        data_rows = ''
        max_per_page = 8
        display_records = records[:max_per_page]  # 取前8条
        for i, r in enumerate(display_records):
            remark = f"{r['batch']} / {r['loc']}".strip(' / ')
            data_rows += f'''<tr>
                <td>{i+1}</td><td>{r['cat']}</td><td>{r['name']}</td><td>{r['spec']}</td>
                <td>{r['unit']}</td><td>{r['price']}</td><td>{r['weight_display']}</td><td>{r['amount']}</td><td>{remark}</td>
            </tr>'''
        # 补齐空行到至少8行
        remaining = max(0, 8 - len(display_records))
        for _ in range(remaining):
            data_rows += '<tr><td>&nbsp;</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>'

        # 超出提示
        extra_info = ''
        if len(records) > max_per_page:
            extra_info = f'<p style="color:#c00;font-size:10pt;">（共选中 {len(records)} 条记录，本页仅展示前 {max_per_page} 条，超出部分请分批打印）</p>'

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
            <span class="title-text">{title}</span>
            <span class="no-abs"><b>NO.</b> {no_display}</span>
        </div>
        <table class="info-table">
            <tr>
                <td style="width:33%;">{info_label}: {info_value}</td>
                <td style="width:33%;text-align:center;">日期: {date_display}</td>
                <td style="width:34%;text-align:right;">单位: {unit_display}</td>
            </tr>
        </table>
        {extra_info}
        <table class="data">
            <tr><th>编号</th><th>类别</th><th>名称</th><th>型号</th><th>单位</th><th>单价</th><th>数量</th><th>金额</th><th>备注</th></tr>
            {data_rows}
            <tr><td class="heji-label" colspan="7">合&emsp;&emsp;计</td><td class="heji-amount">{total_amount}</td><td></td></tr>
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
        QMessageBox.information(self, '打印就绪', f'已选中 {len(records)} 条记录，单据已在浏览器打开。')

    def set_edit_mode(self, locked):
        trigger = QAbstractItemView.EditTrigger.NoEditTriggers if locked else QAbstractItemView.EditTrigger.DoubleClicked
        self.table.setEditTriggers(trigger)
