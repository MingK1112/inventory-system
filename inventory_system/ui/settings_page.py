import csv
import hashlib
import os
import json

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QMessageBox, QFileDialog, QLineEdit, QDialog, QDialogButtonBox,
)
from PySide6.QtGui import QFont

from database import Database
from config import CONTAINER_FIELDS, NUMERIC_INDICES, DB_PATH, CONFIG_FILE

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


class SettingsPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.db = Database()

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(16)

        title = QLabel('数据管理')
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        root.addWidget(title)

        # info
        info = QLabel(f'数据文件：{DB_PATH}\n关闭程序后复制该文件即可完整备份/迁移。')
        info.setObjectName('MutedLabel')
        info.setWordWrap(True)
        root.addWidget(info)

        root.addSpacing(8)

        # buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        export_btn = QPushButton('导出 CSV')
        export_btn.setObjectName('InfoBtn')
        export_btn.clicked.connect(self.export_csv)

        import_btn = QPushButton('导入数据')
        import_btn.setObjectName('InfoBtn')
        import_btn.clicked.connect(self.import_data)

        clear_btn = QPushButton('清空数据')
        clear_btn.setObjectName('DangerBtn')
        clear_btn.clicked.connect(self.clear_data)

        btn_row.addWidget(export_btn)
        btn_row.addWidget(import_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        root.addStretch()

    def _check_admin(self):
        if self.main_window.edit_locked:
            QMessageBox.warning(self, '权限不足', '请先在顶部工具栏开启「管理者模式:开」后再操作。')
            return False
        return True

    def export_csv(self):
        if not self._check_admin():
            return
        path, _ = QFileDialog.getSaveFileName(self, '导出CSV', '', 'CSV files (*.csv)')
        if not path:
            return
        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['表名'] + CONTAINER_FIELDS)
                for row in self.db.conn.execute("SELECT * FROM containers"):
                    writer.writerow(['入库登记'] + list(row))
                writer.writerow([])
                writer.writerow([
                    '表名', '出入库编号', '操作类型', '日期',
                    '批号', '位置', '类别', '名称', '规格', '操作重量'
                ])
                for row in self.db.conn.execute(
                    "SELECT 出入库编号,操作类型,日期,批号,位置,类别,名称,规格,操作重量 FROM transactions"
                ):
                    writer.writerow(['出入库'] + list(row))
            QMessageBox.information(self, '成功', f'数据已导出至：\n{path}')
        except Exception as e:
            QMessageBox.critical(self, '导出失败', str(e))

    def import_data(self):
        if not self._check_admin():
            return
        if HAS_OPENPYXL:
            filters = 'Excel/CSV files (*.xlsx *.xls *.csv);;Excel files (*.xlsx *.xls);;CSV files (*.csv)'
        else:
            filters = 'CSV files (*.csv)'
        path, _ = QFileDialog.getOpenFileName(self, '导入数据', '', filters)
        if not path:
            return
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext in ('.xlsx', '.xls') and HAS_OPENPYXL:
                count = self._import_excel(path)
            else:
                count = self._import_csv(path)
            self.db.conn.commit()
            self.refresh_all()
            QMessageBox.information(self, '成功', f'成功导入 {count} 条记录')
        except Exception as e:
            QMessageBox.critical(self, '导入失败', str(e))

    def _import_csv(self, path):
        count = 0
        with open(path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                if not row:
                    continue
                if row[0] == '入库登记' and len(row) >= len(CONTAINER_FIELDS) + 1:
                    vals = row[1:len(CONTAINER_FIELDS) + 1]
                    for i in NUMERIC_INDICES:
                        if i < len(vals):
                            try:
                                vals[i] = float(vals[i]) if vals[i] else None
                            except (ValueError, TypeError):
                                vals[i] = None
                    self.db.save_container(vals)
                    count += 1
        return count

    def _import_excel(self, path):
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            wb.close()
            return 0

        header = [str(h).strip() if h else '' for h in rows[0]]
        name_to_idx = {name: i for i, name in enumerate(header)}

        # Map Excel column names to CONTAINER_FIELDS positions
        # Support both exact match and common variants (V50 vs v50, V-20 vs v-20, etc.)
        def find_col(field_name):
            if field_name in name_to_idx:
                return name_to_idx[field_name]
            # Try case-insensitive
            for h, idx in name_to_idx.items():
                if h.lower() == field_name.lower():
                    return idx
            return None

        count = 0
        for row in rows[1:]:
            if not row:
                continue

            # Check if first column indicates a container row
            first_cell = str(row[0]).strip() if row[0] else ''
            if first_cell not in ('入库登记', '在库'):
                continue

            # Map each CONTAINER_FIELDS to Excel column by name
            vals = []
            for f in CONTAINER_FIELDS:
                col_idx = find_col(f)
                if col_idx is not None and col_idx < len(row):
                    val = row[col_idx]
                    # Convert datetime to string
                    if hasattr(val, 'strftime'):
                        val = val.strftime('%Y-%m-%d')
                    vals.append(str(val).strip() if val is not None else None)
                else:
                    vals.append(None)

            # Handle 状态: if not found in Excel, default to '在库'
            status_idx = find_col('状态')
            if status_idx is None:
                status_pos = CONTAINER_FIELDS.index('状态')
                vals[status_pos] = '在库'

            # Convert numeric fields
            for i in NUMERIC_INDICES:
                if i < len(vals):
                    try:
                        vals[i] = float(vals[i]) if vals[i] is not None and str(vals[i]).strip() else None
                    except (ValueError, TypeError):
                        vals[i] = None

            self.db.save_container(vals)
            count += 1

        wb.close()
        return count

    def clear_data(self):
        if not self._check_admin():
            return
        reply = QMessageBox.question(
            self, '确认', '清空所有桶与流水数据？',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.clear_all_data()
            self.refresh_all()
            QMessageBox.information(self, '完成', '数据已清空')

    def change_password(self):
        if not self._check_admin():
            return
        cfg = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
        old_hash = cfg.get('password', '')

        dlg = QDialog(self)
        dlg.setWindowTitle('修改密码')
        dlg.resize(360, 220)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)

        old_pwd = QLineEdit()
        old_pwd.setPlaceholderText('旧密码（首次设置请留空）')
        old_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(QLabel('旧密码:'))
        layout.addWidget(old_pwd)

        new_pwd = QLineEdit()
        new_pwd.setPlaceholderText('输入新密码')
        new_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(QLabel('新密码:'))
        layout.addWidget(new_pwd)

        confirm_pwd = QLineEdit()
        confirm_pwd.setPlaceholderText('确认新密码')
        confirm_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(QLabel('确认密码:'))
        layout.addWidget(confirm_pwd)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        old_input = old_pwd.text()
        new_input = new_pwd.text()
        confirm_input = confirm_pwd.text()

        # Verify old password
        if old_hash:
            old_input_hash = hashlib.sha256(old_input.encode()).hexdigest()
            if old_input_hash != old_hash:
                QMessageBox.critical(self, '错误', '旧密码不正确')
                return
        else:
            if old_input:
                QMessageBox.critical(self, '错误', '首次设置密码，旧密码请留空')
                return

        if not new_input:
            QMessageBox.critical(self, '错误', '新密码不能为空')
            return

        if new_input != confirm_input:
            QMessageBox.critical(self, '错误', '两次输入的新密码不一致')
            return

        if len(new_input) < 4:
            QMessageBox.critical(self, '错误', '密码长度不能少于 4 位')
            return

        # Save
        cfg['password'] = hashlib.sha256(new_input.encode()).hexdigest()
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f)
        QMessageBox.information(self, '成功', '密码已修改')

    def refresh_all(self):
        self.main_window.pages['home'].refresh()
        self.main_window.pages['inventory'].refresh_table()
        self.main_window.pages['statistics'].refresh_stat()
        self.main_window.pages['log'].search()
