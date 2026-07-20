# 全局配置
import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 妙手ERP配置
MIAOSHOU_BASE_URL = "https://erp.91miaoshou.com"

# 飞书多维表格配置
FEISHU_BASE_TOKEN = "Z69Pb8Zpua8h3PsKiumcidJ0nEg"
FEISHU_APP_ID = "cli_aad2542de4b81cfd"
FEISHU_APP_SECRET = "vMwvpzPe8kgvFN6H274DYg7MNH310NXy"
LARK_CLI_PATH = "lark-cli"  # 备用，默认用原生API

# 图床配置（七牛云）
IMAGE_BED_CONFIG = {
    "provider": "qiniu",
    "access_key": "xM7D9vFRx3VbrUOhpXjaW9wKOnbCfBl5-osy1olS",
    "secret_key": "leEl6B9ls_NuFYXYgAxcnpz3UNwZhtQuvrHa7tSH",
    "bucket": "a0602",
    "domain": "http://httx7f0o.hn-bkt.clouddn.com",
}

# 各表table_id
TABLE_STYLE = "tblgsBQC5kMCaDr4"        # 款式库表
TABLE_TEMPLATE = "tbl8MDtm0cijDycp"     # 模板表
TABLE_SHOP = "tblcstU6w77Klawo"         # 店铺表
TABLE_COLOR = "tblxluGYXQyNK36g"        # 颜色明细表
TABLE_PRODUCT = "tbl8vDRirTY5Cv3Y"      # 商品链接表

# 款式库Excel路径
STYLE_LIBRARY_PATH = os.path.join(BASE_DIR, "款式库模板_v4_填尺码_最终版.xlsx")

# 核价公式
PRICE_MULTIPLIER = 2  # 成本 × 2 = 供货价

# RPA配置
RPA_HEADLESS = False  # 有头模式（用户要看浏览器）
RPA_SLOW_MO = 200     # 操作延迟（毫秒）

# 登录方式选择
# "storage_state" → 推荐，保存登录状态到json文件，不用关Chrome
# "local_chrome" → 复用本地Chrome Profile，需要关闭对应Profile的窗口
# "standalone" → 独立浏览器持久化目录
LOGIN_MODE = "storage_state"

# 本地Chrome配置（LOGIN_MODE=local_chrome时用）
LOCAL_CHROME_USER_DATA = r"C:\Users\Administrator\AppData\Local\Google\Chrome\User Data"
LOCAL_CHROME_PROFILE = "Profile 26"

# 独立浏览器数据目录（LOGIN_MODE=standalone时用）
RPA_USER_DATA_DIR = os.path.join(BASE_DIR, "browser_data")

# 登录状态文件
STORAGE_STATE_PATH = os.path.join(BASE_DIR, "storage_state.json")


class Config:
    """配置类，兼容旧代码"""
    def __init__(self):
        self.BASE_DIR = BASE_DIR
        self.MIAOSHOU_BASE_URL = MIAOSHOU_BASE_URL
        self.FEISHU_BASE_TOKEN = FEISHU_BASE_TOKEN
        self.LARK_CLI_PATH = LARK_CLI_PATH
        self.STYLE_LIBRARY_PATH = STYLE_LIBRARY_PATH
        self.PRICE_MULTIPLIER = PRICE_MULTIPLIER
        self.RPA_HEADLESS = RPA_HEADLESS
        self.RPA_SLOW_MO = RPA_SLOW_MO
        self.LOGIN_MODE = LOGIN_MODE
        self.LOCAL_CHROME_USER_DATA = LOCAL_CHROME_USER_DATA
        self.LOCAL_CHROME_PROFILE = LOCAL_CHROME_PROFILE
        self.RPA_USER_DATA_DIR = RPA_USER_DATA_DIR
        self.STORAGE_STATE_PATH = STORAGE_STATE_PATH
