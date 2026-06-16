import os
import sys
import json
import shutil
import platform

# ---- 资源目录（只读，放 QSS / assets 等） ----
if getattr(sys, 'frozen', False):
    RESOURCE_DIR = sys._MEIPASS
else:
    RESOURCE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---- 数据目录（可写，放 DB / config.json） ----
if getattr(sys, 'frozen', False):
    system = platform.system()
    if system == "Darwin":
        DATA_DIR = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "出入库系统")
    elif system == "Windows":
        DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "出入库系统")
    else:
        DATA_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "出入库系统")
else:
    DATA_DIR = RESOURCE_DIR  # 开发时用项目目录

os.makedirs(DATA_DIR, exist_ok=True)

APP_NAME = "德隆石化仓储系统"
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 820
DB_PATH = os.path.join(DATA_DIR, "oil_inventory.db")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

# 首次运行：把初始 DB / config 从资源目录复制到数据目录
for _fname in ("oil_inventory.db", "config.json"):
    _src = os.path.join(RESOURCE_DIR, _fname)
    _dst = os.path.join(DATA_DIR, _fname)
    if os.path.exists(_src) and not os.path.exists(_dst):
        shutil.copy2(_src, _dst)

CONTAINER_FIELDS = [
    "批号", "位置", "类别", "名称", "规格",
    "V100", "V40", "酸值", "闪点", "凝点",
    "重量", "单位", "单价", "日期", "入库经手人", "入库登记人", "领用单位", "领用人", "状态",
    "v50", "v20", "v-20", "v-40", "v-51",
    "粘度指数", "密度", "溴值"
]

NUMERIC_INDICES = [5, 6, 7, 8, 9, 10, 12] + list(range(19, 27))


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f)
    except Exception:
        pass
