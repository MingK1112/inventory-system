import sqlite3
from config import DB_PATH, CONTAINER_FIELDS


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute('PRAGMA synchronous=NORMAL')
        self.create_tables()

    def _container_cols(self):
        return ','.join(f'"{f}"' if '-' in f else f for f in CONTAINER_FIELDS)

    def create_tables(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS containers (
            批号 TEXT PRIMARY KEY, 位置 TEXT, 类别 TEXT, 名称 TEXT, 规格 TEXT,
            V100 REAL, V40 REAL, 酸值 REAL, 闪点 REAL, 凝点 REAL,
            重量 REAL, 单位 TEXT DEFAULT '公斤', 单价 REAL, 日期 TEXT,
            入库经手人 TEXT, 入库登记人 TEXT, 领用单位 TEXT, 领用人 TEXT, 状态 TEXT DEFAULT '在库',
            v50 REAL, v20 REAL, "v-20" REAL, "v-40" REAL, "v-51" REAL,
            粘度指数 REAL, 密度 REAL, 溴值 REAL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 出入库编号 TEXT UNIQUE,
            操作类型 TEXT, 日期 TEXT, 编码 TEXT, 批号 TEXT,
            位置 TEXT, 类别 TEXT, 名称 TEXT, 规格 TEXT, 操作重量 REAL,
            入库经手人 TEXT, 入库登记人 TEXT, 领用单位 TEXT, 领用人 TEXT, 出库领用人 TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS thresholds (
            类别 TEXT, 名称 TEXT, 规格 TEXT, 预警值 REAL DEFAULT 100.0,
            PRIMARY KEY (类别, 名称, 规格)
        )''')

        # Migrate: add missing columns
        t_cols = [info[1] for info in c.execute("PRAGMA table_info(transactions)")]
        for col in ["操作重量", "编码", "出库领用人", "入库经手人", "入库登记人", "领用单位", "领用人"]:
            if col not in t_cols:
                c.execute(f"ALTER TABLE transactions ADD COLUMN {col} TEXT DEFAULT ''")

        c_cols = [info[1] for info in c.execute("PRAGMA table_info(containers)")]
        for col in ["单位", "入库经手人", "入库登记人", "领用单位", "领用人"]:
            if col not in c_cols:
                c.execute(f"ALTER TABLE containers ADD COLUMN {col} TEXT DEFAULT ''")

        # Rename legacy column
        if "桶号" in c_cols:
            try:
                c.execute("ALTER TABLE containers RENAME COLUMN 桶号 TO 批号")
            except sqlite3.OperationalError:
                pass
        if "桶号" in t_cols:
            try:
                c.execute("ALTER TABLE transactions RENAME COLUMN 桶号 TO 批号")
            except sqlite3.OperationalError:
                pass

        # Clean up obsolete columns
        for col in ["货物单位", "来货单位", "入库领用单位", "入库领用人", "出库领用单位"]:
            if col in c_cols:
                try:
                    c.execute(f"ALTER TABLE containers DROP COLUMN {col}")
                except sqlite3.OperationalError:
                    pass
        for col in ["货物单位", "来货单位", "入库领用单位", "入库领用人", "出库领用单位"]:
            if col in t_cols:
                try:
                    c.execute(f"ALTER TABLE transactions DROP COLUMN {col}")
                except sqlite3.OperationalError:
                    pass

        self.conn.commit()

    # ---- containers ----
    def get_container(self, batch):
        return self.conn.execute(
            f"SELECT {self._container_cols()} FROM containers WHERE 批号=?", (batch,)
        ).fetchone()

    def get_all_containers(self):
        return self.conn.execute(
            f"SELECT {self._container_cols()} FROM containers ORDER BY 日期 DESC"
        ).fetchall()

    def save_container(self, vals):
        cols = self._container_cols()
        placeholders = ','.join(['?'] * len(CONTAINER_FIELDS))
        self.conn.execute(
            f"INSERT OR REPLACE INTO containers ({cols}) VALUES ({placeholders})", vals
        )
        self.conn.commit()

    def delete_container(self, batch):
        self.conn.execute("DELETE FROM transactions WHERE 批号=?", (batch,))
        self.conn.execute("DELETE FROM containers WHERE 批号=?", (batch,))
        self.conn.commit()

    def update_container_batch_in_transactions(self, new_batch, old_batch):
        self.conn.execute(
            "UPDATE transactions SET 批号=? WHERE 批号=?", (new_batch, old_batch)
        )

    def sync_container_to_transactions(self, batch):
        """Sync container field changes to all transactions of this batch."""
        self.conn.execute(
            '''UPDATE transactions SET
               位置=(SELECT 位置 FROM containers WHERE 批号=?),
               类别=(SELECT 类别 FROM containers WHERE 批号=?),
               名称=(SELECT 名称 FROM containers WHERE 批号=?),
               规格=(SELECT 规格 FROM containers WHERE 批号=?)
               WHERE 批号=?''',
            (batch, batch, batch, batch, batch)
        )
        self.conn.commit()

    # ---- transactions ----
    def add_transaction(self, vals):
        self.conn.execute(
            '''INSERT INTO transactions
               (出入库编号,操作类型,日期,编码,批号,位置,类别,名称,规格,操作重量,入库经手人,入库登记人,领用单位,领用人,出库领用人)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', vals
        )
        self.conn.commit()

    def get_transaction_seq(self, prefix):
        return self.conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE 出入库编号 LIKE ?", (f"{prefix}%",)
        ).fetchone()[0]

    def get_last_transaction(self):
        return self.conn.execute(
            "SELECT 出入库编号,操作类型,日期,编码,批号,位置,类别,名称,规格,操作重量,入库经手人,入库登记人,领用单位,领用人,出库领用人 "
            "FROM transactions ORDER BY id DESC LIMIT 1"
        ).fetchone()

    def search_transactions(self, kw, start, end):
        query = (
            "SELECT t.出入库编号,t.操作类型,t.日期,t.编码,t.批号,t.位置,t.类别,t.名称,t.规格,t.操作重量,"
            "t.入库经手人,t.入库登记人,t.领用单位,t.领用人,c.单位 "
            "FROM transactions t LEFT JOIN containers c ON t.批号 = c.批号 WHERE "
            "(t.批号 LIKE ? OR t.出入库编号 LIKE ? OR t.编码 LIKE ? OR t.类别 LIKE ? OR t.名称 LIKE ?)"
        )
        params = [kw, kw, kw, kw, kw]
        if start:
            query += " AND t.日期 >= ?"
            params.append(start + "-01")
        if end:
            query += " AND t.日期 <= ?"
            params.append(end + "-31")
        query += " ORDER BY t.日期 DESC"
        return self.conn.execute(query, params).fetchall()

    def get_transaction_by_id(self, io_id):
        return self.conn.execute(
            "SELECT * FROM transactions WHERE 出入库编号=?", (io_id,)
        ).fetchone()

    def delete_transaction(self, io_id):
        self.conn.execute("DELETE FROM transactions WHERE 出入库编号=?", (io_id,))
        self.conn.commit()

    # ---- thresholds ----
    def set_threshold(self, cat, name, spec, val):
        self.conn.execute(
            "INSERT OR REPLACE INTO thresholds VALUES (?,?,?,?)",
            (cat, name, spec, val)
        )
        self.conn.commit()

    # ---- statistics ----
    def get_stat_summary(self):
        return self.conn.execute(
            '''SELECT c.类别, c.名称, c.规格,
                      COUNT(c.批号) as 桶数, SUM(c.重量) as 总重,
                      MAX(c.日期) as 最新日期,
                      COALESCE(t.预警值, 100.0) as 阈值
               FROM containers c
               LEFT JOIN thresholds t
                 ON c.类别 = t.类别 AND c.名称 = t.名称 AND c.规格 = t.规格
               WHERE c.状态='在库'
               GROUP BY c.类别, c.名称, c.规格
               ORDER BY c.类别'''
        ).fetchall()

    def get_stat_detail(self, cat, name, spec):
        return self.conn.execute(
            f"SELECT {self._container_cols()} FROM containers WHERE 类别=? AND 名称=? AND 规格=? AND 状态='在库' ORDER BY 日期 DESC",
            (cat, name, spec)
        ).fetchall()

    def search_by_category(self, kw):
        like = f"%{kw}%"
        return self.conn.execute(
            f"SELECT {self._container_cols()} FROM containers WHERE 批号 LIKE ? OR 位置 LIKE ? OR 类别 LIKE ? OR 名称 LIKE ? OR 规格 LIKE ? ORDER BY 日期 DESC",
            (like, like, like, like, like)
        ).fetchall()

    def update_container_weight_status(self, new_w, new_status, date, batch):
        self.conn.execute(
            "UPDATE containers SET 重量=?, 状态=?, 日期=? WHERE 批号=?",
            (new_w, new_status, date, batch)
        )
        self.conn.commit()

    # ---- data management ----
    def clear_all_data(self):
        self.conn.execute("DELETE FROM transactions")
        self.conn.execute("DELETE FROM containers")
        self.conn.execute("DELETE FROM thresholds")
        self.conn.commit()

    def close(self):
        self.conn.close()
