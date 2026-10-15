from datetime import datetime, timedelta, timezone
import json
import re
import sqlite3
from openai import OpenAI
import streamlit as st
import streamlit.components.v1 as components

/* 彻底隐藏右下角的 Streamlit 官方浮动徽标与红白广告 */
[data-testid="stDecoration"], footer, #MainMenu, .viewerBadge_container__1QSob {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
}


# 0. 严格锁定中国标准时间 (UTC+8 公历日历)
CHINA_TZ = timezone(timedelta(hours=8))


def get_china_now():
    return datetime.now(CHINA_TZ)


# 1. 页面极简配置
st.set_page_config(
    page_title="极简记账",
    page_icon="⚪",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# 2. 全局样式注入（纯白苹果风 + 胶囊外框锁定 + 心愿单微卡片）
st.markdown(
    """
    <style>
        :root, html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            color-scheme: light !important;
            background-color: #F5F5F7 !important;
            color: #1D1D1F !important;
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", sans-serif !important;
        }
        #MainMenu, footer, header {visibility: hidden;}
        
        .block-container {
            padding-top: 1.4rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 460px !important;
        }

        /* 1. 顶部 Gemini 胶囊外框：精准锁定主页面第一行 */
        .block-container > div > div > div[data-testid="stHorizontalBlock"]:first-of-type,
        [data-testid="stMainBlockContainer"] > div > div > div[data-testid="stHorizontalBlock"]:first-of-type {
            background-color: #FFFFFF !important;
            border-radius: 999px !important;
            padding: 6px 10px 6px 12px !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.02) !important;
            border: 1px solid rgba(0, 0, 0, 0.04) !important;
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
            justify-content: space-between !important;
            margin-bottom: 18px !important;
            gap: 6px !important;
        }
        .block-container > div > div > div[data-testid="stHorizontalBlock"]:first-of-type > div:nth-child(1),
        [data-testid="stMainBlockContainer"] > div > div > div[data-testid="stHorizontalBlock"]:first-of-type > div:nth-child(1) {
            flex: 0 0 38px !important;
            width: 38px !important;
            min-width: 38px !important;
        }
        .block-container > div > div > div[data-testid="stHorizontalBlock"]:first-of-type > div:nth-child(2),
        [data-testid="stMainBlockContainer"] > div > div > div[data-testid="stHorizontalBlock"]:first-of-type > div:nth-child(2) {
            flex: 1 1 auto !important;
            width: auto !important;
            min-width: 150px !important;
        }

        /* 2. 左侧 + 号按钮 */
        div[data-testid="stPopover"] > button,
        div[data-testid="stPopover"] > div > button {
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            background-color: #FFFFFF !important;
            width: 36px !important;
            height: 36px !important;
            min-height: 36px !important;
            padding: 0 !important;
            border-radius: 50% !important;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='22' height='22' viewBox='0 0 24 24' fill='none' stroke='%231D1D1F' stroke-width='2.0' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='12' y1='5' x2='12' y2='19'%3E%3C/line%3E%3Cline x1='5' y1='12' x2='19' y2='12'%3E%3C/line%3E%3C/svg%3E") !important;
            background-repeat: no-repeat !important;
            background-position: center !important;
            background-size: 22px 22px !important;
        }
        div[data-testid="stPopover"] > button *,
        div[data-testid="stPopover"] > div > button * { display: none !important; }

        /* 3. 顶部输入框纯白色底 + 预留右侧动态箭头空间 */
        div[data-testid="stTextInput"],
        div[data-testid="stTextInput"] *,
        div[data-baseweb="input"],
        div[data-baseweb="input"] *,
        div[data-baseweb="base-input"],
        div[data-baseweb="base-input"] * {
            background-color: #FFFFFF !important;
            background: #FFFFFF !important;
            border: none !important;
            box-shadow: none !important;
            outline: none !important;
        }
        div[data-testid="stTextInput"] input {
            font-size: 16px !important;
            font-weight: 400 !important;
            color: #1D1D1F !important;
            -webkit-text-fill-color: #1D1D1F !important;
            caret-color: #1D1D1F !important;
            padding: 6px 42px 6px 4px !important;
            opacity: 1 !important;
        }
        div[data-testid="stTextInput"] input::placeholder {
            color: #8E8E93 !important;
            -webkit-text-fill-color: #8E8E93 !important;
            opacity: 1 !important;
        }
        div[data-testid="InputInstructions"] { display: none !important; }

        /* 4. 弹出菜单 (Popover) 内部样式 */
        div[data-testid="stPopoverBody"],
        div[data-baseweb="popover"] > div {
            background-color: #FFFFFF !important;
            color: #1D1D1F !important;
            border-radius: 22px !important;
            border: 1px solid rgba(0, 0, 0, 0.08) !important;
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12) !important;
            min-width: 350px !important;
        }
        div[data-testid="stPopoverBody"] * { color: #1D1D1F !important; }
        div[data-testid="stPopoverBody"] input {
            background-color: #F5F5F7 !important;
            -webkit-text-fill-color: #1D1D1F !important;
            border-radius: 10px !important;
            padding: 6px 10px !important;
        }

        /* 黑色主按钮 */
        button[kind="primary"] {
            background-color: #1D1D1F !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 14px !important;
            min-height: 40px !important;
            padding: 6px 14px !important;
            box-shadow: none !important;
        }
        button[kind="primary"] *,
        button[kind="primary"] p,
        button[kind="primary"] span {
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
            font-weight: 500 !important;
            font-size: 13.5px !important;
        }

        /* 下载备份按钮美化 */
        div[data-testid="stDownloadButton"] button {
            background-color: #F2F2F7 !important;
            color: #1D1D1F !important;
            border: none !important;
            border-radius: 14px !important;
            min-height: 38px !important;
            width: 100% !important;
        }
        div[data-testid="stDownloadButton"] button * {
            color: #1D1D1F !important;
            -webkit-text-fill-color: #1D1D1F !important;
            font-weight: 500 !important;
            font-size: 13px !important;
        }

        /* 流水单条右侧极简减号按钮 */
        div[data-testid="stPopoverBody"] button[kind="secondary"] {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            outline: none !important;
            padding: 0 !important;
            width: 28px !important;
            height: 28px !important;
            min-height: 28px !important;
            border-radius: 50% !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        div[data-testid="stPopoverBody"] button[kind="secondary"] *,
        div[data-testid="stPopoverBody"] button[kind="secondary"] p,
        div[data-testid="stPopoverBody"] button[kind="secondary"] span {
            color: #8E8E93 !important;
            -webkit-text-fill-color: #8E8E93 !important;
            font-size: 18px !important;
            font-weight: 400 !important;
            line-height: 1 !important;
        }
        div[data-testid="stPopoverBody"] button[kind="secondary"]:hover,
        div[data-testid="stPopoverBody"] button[kind="secondary"]:active {
            background-color: rgba(255, 59, 48, 0.1) !important;
        }
        div[data-testid="stPopoverBody"] button[kind="secondary"]:hover *,
        div[data-testid="stPopoverBody"] button[kind="secondary"]:active * {
            color: #FF3B30 !important;
            -webkit-text-fill-color: #FF3B30 !important;
        }

        div[data-testid="stPopoverBody"] div[data-testid="stHorizontalBlock"] {
            background: transparent !important;
            border: none !important;
            border-bottom: 1px solid #F2F2F7 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            padding: 7px 0 !important;
            margin: 0 !important;
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
            justify-content: space-between !important;
            gap: 8px !important;
        }
        div[data-testid="stPopoverBody"] div[data-testid="stHorizontalBlock"] > div:first-child {
            flex: 1 1 auto !important;
            width: auto !important;
            min-width: 0 !important;
        }
        div[data-testid="stPopoverBody"] div[data-testid="stHorizontalBlock"] > div:last-child {
            flex: 0 0 28px !important;
            width: 28px !important;
            min-width: 28px !important;
            display: flex !important;
            justify-content: flex-end !important;
        }

        /* 5. Apple 原生感日期抬头、主白卡与心愿胶囊 */
        .apple-date-header {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            padding: 0 8px;
            margin-bottom: 10px;
        }
        .apple-date-main {
            font-size: 15px;
            font-weight: 600;
            color: #1D1D1F;
            letter-spacing: -0.2px;
        }
        .apple-date-sub {
            font-size: 11px;
            font-weight: 600;
            color: #86868B;
            letter-spacing: 0.8px;
            text-transform: uppercase;
        }
        .apple-white-card {
            background: #FFFFFF !important;
            color: #1D1D1F !important;
            border-radius: 26px;
            padding: 26px 24px;
            box-shadow: 0 6px 24px rgba(0, 0, 0, 0.04), 0 1px 3px rgba(0, 0, 0, 0.02);
            border: 1px solid rgba(0, 0, 0, 0.03);
            margin-bottom: 14px;
        }
        .metric-title {
            font-size: 12px;
            font-weight: 500;
            color: #86868B !important;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 40px;
            font-weight: 700;
            color: #1D1D1F !important;
            letter-spacing: -1px;
        }
        .ai-comment-row {
            margin-top: 15px;
            padding-top: 13px;
            border-top: 1px solid #F2F2F7;
            font-size: 12.5px;
            color: #63686E;
            display: flex;
            align-items: center;
            gap: 7px;
            line-height: 1.4;
        }
        .apple-wish-card {
            background: rgba(255, 255, 255, 0.78) !important;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-radius: 20px;
            padding: 14px 20px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.025);
            border: 1px solid rgba(0, 0, 0, 0.03);
            margin-bottom: 16px;
        }
    </style>
""",
    unsafe_allow_html=True,
)


# 3. 本地精准分类器与高级低饱和莫兰迪色盘
def infer_precise_category(text, ai_cat=None):
    t = str(text)
    if any(
        k in t
        for k in [
            "打车", "滴滴", "地铁", "公交", "高铁", "火车", "机票",
            "车费", "加油", "停车", "骑车", "单车", "出行", "交通",
        ]
    ):
        return "交通"
    if any(
        k in t
        for k in [
            "水", "饭", "餐", "面", "粉", "火锅", "咖啡", "奶茶",
            "可乐", "饮料", "吃", "早", "午", "晚", "夜宵", "烧烤",
            "水果", "零食", "面包", "蛋糕", "菜", "外卖", "食堂",
        ]
    ):
        return "餐饮"
    if any(
        k in t
        for k in [
            "显示器", "电脑", "手机", "键盘", "鼠标", "耳机",
            "iPad", "Mac", "充电", "数码", "相机", "硬盘",
        ]
    ):
        return "数码"
    if any(
        k in t
        for k in [
            "电影", "游戏", "门票", "KTV", "演出", "展览",
            "会员", "网吧", "桌游", "娱乐", "旅游",
        ]
    ):
        return "娱乐"
    if any(
        k in t
        for k in [
            "房租", "水电", "电费", "水费", "燃气", "物业",
            "纸巾", "洗衣", "日用", "居家", "话费", "网费",
        ]
    ):
        return "居家"
    if any(k in t for k in ["药", "医院", "看病", "挂号", "体检", "牙", "医疗"]):
        return "医疗"
    if any(
        k in t
        for k in [
            "买", "购", "衣", "裤", "鞋", "包", "淘宝",
            "京东", "拼多多", "超市", "商场", "护肤", "洗发",
        ]
    ):
        return "购物"

    valid_cats = {"餐饮", "交通", "购物", "娱乐", "居家", "数码", "医疗"}
    if ai_cat in valid_cats:
        return ai_cat
    return "其他"


CATEGORY_STYLES = {
    "餐饮": ("#EDF3F0", "#4F6F61"),
    "交通": ("#EDF2F7", "#4A6B82"),
    "购物": ("#F3EFF5", "#6E5A7F"),
    "娱乐": ("#F9EFEF", "#9E5B5B"),
    "数码": ("#EBF3F5", "#3D6B78"),
    "居家": ("#F7F3EB", "#8C704C"),
    "医疗": ("#F7EFF2", "#8C566B"),
    "其他": ("#F2F3F5", "#63686E"),
}

PLOTLY_COLOR_MAP = {
    "餐饮": "#84A59D",
    "交通": "#7C98B3",
    "购物": "#9D8CA7",
    "娱乐": "#D49A9A",
    "数码": "#6B909E",
    "居家": "#C9B396",
    "医疗": "#B88B9C",
    "其他": "#A3A8B0",
}


def render_category_badge(cat, pool):
    bg, fg = CATEGORY_STYLES.get(cat, ("#F2F3F5", "#63686E"))
    html = (
        f"<span style='background-color:{bg}; color:{fg}; padding:2px 7px;"
        " border-radius:6px; font-size:11px; font-weight:600;"
        f" display:inline-block;'>{cat}</span>"
    )
    if pool == "vault":
        html += (
            " <span style='background-color:#F5EFE6; color:#8C6239; padding:2px"
            " 7px; border-radius:6px; font-size:11px; font-weight:600;"
            " display:inline-block;'>小金库</span>"
        )
    return html


# 4. 数据库初始化（平滑升级支持 user_id 多人独立分舱）
def init_db():
    conn = sqlite3.connect("ledger.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
    c.execute(
        """CREATE TABLE IF NOT EXISTS transactions 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, title TEXT, amount REAL, pool TEXT, note TEXT, category TEXT DEFAULT '其他', user_id TEXT DEFAULT 'default')"""
    )
    try:
        c.execute("ALTER TABLE transactions ADD COLUMN category TEXT DEFAULT '其他'")
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE transactions ADD COLUMN user_id TEXT DEFAULT 'default'")
    except Exception:
        pass

    c.execute(
        "SELECT id, title, note, category FROM transactions WHERE category IN"
        " ('日常', '其他') OR category IS NULL"
    )
    for row_id, title, note, old_cat in c.fetchall():
        new_cat = infer_precise_category(f"{title} {note}")
        if new_cat != old_cat:
            c.execute(
                "UPDATE transactions SET category=? WHERE id=?", (new_cat, row_id)
            )

    conn.commit()
    return conn


conn = init_db()

# 5. 极简暗号分舱识别引擎（支持 ?u=暗号 或首次弹窗进入）
query_dict = dict(st.query_params)
url_user = None
q_val = None

for k, v in query_dict.items():
    k_clean = k.strip().lower()
    if k_clean in ("u", "user") and v:
        url_user = str(v).strip()
    elif k_clean == "q" and v:
        q_val = str(v).strip()

if url_user:
    st.session_state.current_user = url_user

if "current_user" not in st.session_state or not st.session_state.current_user:
    st.markdown("<div style='height: 36px;'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="apple-white-card" style="text-align: center; padding: 36px 26px;">
            <div style="font-size: 34px; margin-bottom: 10px;">⚪</div>
            <div style="font-size: 20px; font-weight: 700; color: #1D1D1F; margin-bottom: 8px;">极简私人账本</div>
            <div style="font-size: 13px; color: #86868B; margin-bottom: 24px; line-height: 1.5;">
                请输入你的专属暗号（如姓名缩写或昵称）<br>每位用户的账本、小金库与分析图完全独立隔离
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    u_input = st.text_input(
        "专属暗号",
        placeholder="在此输入你的专属暗号（例如：kai）...",
        label_visibility="collapsed",
    )
    if st.button("进入我的私人账本 →", type="primary", use_container_width=True):
        if u_input and u_input.strip():
            clean_u = u_input.strip()
            st.session_state.current_user = clean_u
            st.query_params["u"] = clean_u
            st.rerun()
    st.stop()

CURRENT_USER = st.session_state.current_user
if st.query_params.get("u") != CURRENT_USER:
    st.query_params["u"] = CURRENT_USER


# 6. 按用户隔离的参数配置读取与保存
def get_user_config(key, default):
    c = conn.cursor()
    user_key = f"{CURRENT_USER}_{key}"
    c.execute("SELECT value FROM config WHERE key=?", (user_key,))
    row = c.fetchone()
    if row is not None:
        return row[0]
    if CURRENT_USER == "default":
        c.execute("SELECT value FROM config WHERE key=?", (key,))
        row_old = c.fetchone()
        if row_old is not None:
            return row_old[0]
    return default


def set_user_config(key, value):
    c = conn.cursor()
    user_key = f"{CURRENT_USER}_{key}"
    c.execute(
        "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
        (user_key, str(value)),
    )
    conn.commit()


SHARED_SECRET_KEY = ""
try:
    SHARED_SECRET_KEY = st.secrets.get("DEEPSEEK_API_KEY", "")
except Exception:
    SHARED_SECRET_KEY = ""

USER_CUSTOM_KEY = get_user_config("deepseek_api_key", "")
ACTIVE_API_KEY = USER_CUSTOM_KEY.strip() if USER_CUSTOM_KEY.strip() else SHARED_SECRET_KEY

BUDGET_LIMIT = float(get_user_config("monthly_budget", 2000.0))
VAULT_INIT = float(get_user_config("vault_init", 1000.0))
THRESHOLD = float(get_user_config("threshold", 300.0))

AI_PERSONA = get_user_config("ai_persona", "温柔治愈")
WISH_NAME = get_user_config("wish_name", "").strip()
try:
    WISH_TARGET = float(get_user_config("wish_target", 0.0))
except Exception:
    WISH_TARGET = 0.0
LAST_AI_COMMENT = get_user_config("last_ai_comment", "").strip()


# 7. DeepSeek 智能语义解析 + 个性化微评语生成
def fallback_comment(title, amount, category, persona):
    if persona == "极简高冷":
        return ""
    if persona == "毒舌损友":
        if amount >= 200:
            return f"这一笔 ¥{amount:.0f} 下去，小金库正在角落瑟瑟发抖。"
        if category == "餐饮":
            return f"又吃「{title}」？嘴巴享福了，钱包瘦身了。"
        return f"「{title}」已记下，省着点花，月底别吃土。"
    else:
        if amount >= 200:
            return f"努力生活的日子，偶尔犒劳自己「{title}」也很值得 ✨"
        if category == "餐饮":
            return f"好好吃饭是头等大事，「{title}」为你补充今日元气 ☕"
        return f"每一笔记录都是对生活的掌控，今天也辛苦啦 🌱"


def parse_with_deepseek(text):
    if not ACTIVE_API_KEY:
        return fallback_parse(text)
    try:
        client = OpenAI(api_key=ACTIVE_API_KEY, base_url="https://api.deepseek.com")
        persona_rule = ""
        if AI_PERSONA == "温柔治愈":
            persona_rule = "请用温柔、治愈、暖心夸奖的语气写一句18字以内的简短微评语（如鼓励好好吃饭、夸奖理性消费等）。"
        elif AI_PERSONA == "毒舌损友":
            persona_rule = "请用幽默、傲娇、损友吐槽的语气写一句18字以内的简短微评语（如调侃乱花钱、深夜放毒等，好玩但不伤人）。"
        else:
            persona_rule = "直接返回空字符串 \"\"。"

        prompt = f"""
        你是一个专业的分类记账助手。请解析用户的消费输入，提取以下5个字段并严格以 JSON 格式输出：
        - title: 消费项目精简名称（string，不要包含金额数字）
        - amount: 消费金额（float）
        - category: 消费分类，必须严格从 ["餐饮", "交通", "购物", "娱乐", "居家", "数码", "医疗", "其他"] 这8个词中选一个！
        - is_vault: 是否属于数码硬件、大件或不应占用日常2000元生活费的大额支出（boolean）
        - comment: {persona_rule}（string）
        
        用户输入：{text}
        """
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            stream=False,
        )
        result = json.loads(response.choices[0].message.content)
        raw_title = result.get("title", text)
        amount = float(result.get("amount", 0.0))
        ai_cat = result.get("category", "")
        final_cat = infer_precise_category(f"{text} {raw_title}", ai_cat)
        is_vault = bool(result.get("is_vault", False)) or (final_cat == "数码")
        comment = str(result.get("comment", "")).strip()
        if AI_PERSONA == "极简高冷":
            comment = ""
        elif not comment:
            comment = fallback_comment(raw_title, amount, final_cat, AI_PERSONA)
        return raw_title, amount, final_cat, is_vault, comment
    except Exception:
        return fallback_parse(text)


def fallback_parse(text):
    nums = re.findall(r"\d+\.?\d*", text)
    amount = float(nums[0]) if nums else 0.0
    clean_title = (
        re.sub(r"\d+\.?\d*", "", text).replace("元", "").replace("块", "").strip()
        or text
    )
    category = infer_precise_category(text)
    is_vault = (
        True
        if (category == "数码" or "大件" in text or amount >= THRESHOLD)
        else False
    )
    comment = fallback_comment(clean_title, amount, category, AI_PERSONA)
    return clean_title, amount, category, is_vault, comment


# 8. 入账处理、回车回调与 URL 快捷指令传参支持
def add_transaction(user_text):
    user_text = str(user_text).strip()
    if user_text:
        title, amount, category, is_vault, comment = parse_with_deepseek(user_text)
        if amount >= THRESHOLD:
            is_vault = True
        pool_type = "vault" if is_vault else "monthly"
        date_str = get_china_now().strftime("%Y-%m-%d %H:%M")

        c = conn.cursor()
        c.execute(
            "INSERT INTO transactions (date, title, amount, pool, note, category, user_id)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (date_str, title, amount, pool_type, user_text, category, CURRENT_USER),
        )
        conn.commit()
        if comment:
            set_user_config("last_ai_comment", comment)
        pool_name = "🥇小金库" if pool_type == "vault" else "本月生活费"
        st.session_state.last_toast = (
            f"✅ 已入账：[{category}] {title} ¥{amount:.2f} （{pool_name}）"
        )


def handle_capsule_submit():
    add_transaction(st.session_state.capsule_input_key)
    st.session_state.capsule_input_key = ""


if q_val:
    if st.session_state.get("last_processed_q") != q_val:
        st.session_state.last_processed_q = q_val
        add_transaction(q_val)
    st.query_params.clear()
    st.query_params["u"] = CURRENT_USER
    LAST_AI_COMMENT = get_user_config("last_ai_comment", "").strip()

if "last_toast" in st.session_state and st.session_state.last_toast:
    st.toast(st.session_state.last_toast)
    st.session_state.last_toast = ""

# 9. 中国时区（UTC+8）当前用户的财务数据计算
now_cn = get_china_now()
current_month_str = now_cn.strftime("%Y-%m")
weekdays_cn = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
formatted_date_cn = f"{now_cn.month}月{now_cn.day}日 {weekdays_cn[now_cn.weekday()]}"
formatted_month_en = now_cn.strftime("%b %Y").upper()

c = conn.cursor()
c.execute(
    "SELECT SUM(amount) FROM transactions WHERE user_id=? AND pool='monthly' AND substr(date, 1, 7) = ?",
    (CURRENT_USER, current_month_str),
)
total_monthly_spent = c.fetchone()[0] or 0.0
remaining_budget = BUDGET_LIMIT - total_monthly_spent

c.execute(
    """
    SELECT substr(date, 1, 7) as m, SUM(amount) 
    FROM transactions 
    WHERE user_id=? AND pool='monthly' AND substr(date, 1, 7) < ? 
    GROUP BY m
""",
    (CURRENT_USER, current_month_str),
)
past_months_rows = c.fetchall()
accumulated_rollover = sum(
    (BUDGET_LIMIT - (row[1] or 0.0)) for row in past_months_rows
)

c.execute(
    "SELECT SUM(amount) FROM transactions WHERE user_id=? AND pool='vault'",
    (CURRENT_USER,),
)
vault_spent = c.fetchone()[0] or 0.0
current_vault = VAULT_INIT + accumulated_rollover - vault_spent

# 10. 顶部纯白胶囊栏
col_plus, col_input_area = st.columns([1.1, 8.9])

with col_plus:
    with st.popover(" "):
        tab_ledger, tab_analytics, tab_settings = st.tabs(
            ["🛡️ 小金库与流水", "📊 消费分析", "⚙️ 参数设置"]
        )

        with tab_ledger:
            st.markdown(f"#### 🛡️ 隐藏小金库: ¥{current_vault:.2f}")
            st.caption(
                f"专属舱位：{CURRENT_USER}  ·  初始 ¥{VAULT_INIT:.0f}  ·  历月累加"
                f" {'+' if accumulated_rollover>=0 else ''}¥{accumulated_rollover:.1f}"
                f"  ·  大件 -¥{vault_spent:.1f}"
            )
            st.markdown("---")
            st.markdown(f"**📜 近期账单流水（{current_month_str}）**")
            c.execute(
                "SELECT id, date, title, amount, pool, category FROM transactions"
                " WHERE user_id=? ORDER BY id DESC LIMIT 20",
                (CURRENT_USER,),
            )
            rows = c.fetchall()
            if not rows:
                st.caption("暂无记录")
            for row in rows:
                tx_id, tx_date, tx_title, tx_amount, tx_pool, tx_cat = row
                tx_cat = tx_cat or "其他"
                badge_html = render_category_badge(tx_cat, tx_pool)

                r_col1, r_col2 = st.columns([8.8, 1.2])
                with r_col1:
                    st.markdown(
                        "<div style='font-size:13.5px; color:#1D1D1F; white-space:nowrap;"
                        " overflow:hidden; text-overflow:ellipsis; display:flex;"
                        " align-items:center; gap:6px;'>"
                        f"<span style='color:#8E8E93; font-size:12px;'>{tx_date[5:]}</span>"
                        f"<b>{tx_title}</b><span>¥{tx_amount:.1f}</span>{badge_html}"
                        "</div>",
                        unsafe_allow_html=True,
                    )
                with r_col2:
                    if st.button(
                        "－", key=f"del_{tx_id}", type="secondary", help="删除此笔记录"
                    ):
                        c.execute(
                            "DELETE FROM transactions WHERE id=? AND user_id=?",
                            (tx_id, CURRENT_USER),
                        )
                        conn.commit()
                        st.session_state.last_toast = (
                            f"🗑️ 已撤销：{tx_title} (¥{tx_amount:.1f} 已退回)"
                        )
                        st.rerun()

            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            if st.button(
                "🗑️ 清空我的账单数据", type="primary", use_container_width=True
            ):
                c.execute("DELETE FROM transactions WHERE user_id=?", (CURRENT_USER,))
                conn.commit()
                st.session_state.last_toast = "🗑️ 你的个人账单已清空重置"
                st.rerun()

        with tab_analytics:
            st.markdown("#### 📊 本月消费构成")
            st.caption(f"统计周期：{current_month_str}（低饱和莫兰迪色系）")

            c.execute(
                """
                SELECT category, SUM(amount) 
                FROM transactions 
                WHERE user_id=? AND substr(date, 1, 7) = ? 
                GROUP BY category 
                ORDER BY SUM(amount) DESC
            """,
                (CURRENT_USER, current_month_str),
            )
            cat_rows = c.fetchall()

            if not cat_rows:
                st.info("本月暂无消费记录，快记一笔来看看分析图吧！")
            else:
                import pandas as pd
                import plotly.express as px

                df_cat = pd.DataFrame(cat_rows, columns=["类别", "金额"])
                total_all_pools = sum(r[1] for r in cat_rows)
                color_discrete_map = {
                    row[0]: PLOTLY_COLOR_MAP.get(row[0], "#A3A8B0") for row in cat_rows
                }

                fig = px.pie(
                    df_cat,
                    names="类别",
                    values="金额",
                    hole=0.62,
                    color="类别",
                    color_discrete_map=color_discrete_map,
                )
                fig.update_traces(
                    textposition="inside",
                    textinfo="percent",
                    insidetextorientation="horizontal",
                    textfont=dict(size=12, color="#FFFFFF", family="-apple-system, sans-serif"),
                    marker=dict(line=dict(color="#FFFFFF", width=3)),
                    hovertemplate="<b>%{label}</b><br>¥%{value:.2f} (%{percent})<extra></extra>",
                )
                fig.update_layout(
                    height=240,
                    margin=dict(t=10, b=10, l=10, r=10),
                    showlegend=False,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    annotations=[
                        dict(
                            text=(
                                "<span style='color:#86868B; font-size:11px;'>总支出</span>"
                                f"<br><b style='color:#1D1D1F; font-size:18px;'>¥{total_all_pools:.0f}</b>"
                            ),
                            x=0.5,
                            y=0.5,
                            font_size=14,
                            showarrow=False,
                        )
                    ],
                )
                st.plotly_chart(
                    fig, use_container_width=True, config={"displayModeBar": False}
                )

                st.markdown("<div style='margin-top: 4px;'></div>", unsafe_allow_html=True)
                for cat_name, cat_amt in cat_rows:
                    pct = (cat_amt / total_all_pools * 100) if total_all_pools > 0 else 0
                    dot_color = PLOTLY_COLOR_MAP.get(cat_name, "#A3A8B0")
                    st.markdown(
                        "<div style='display:flex; justify-content:space-between;"
                        " align-items:center; padding:6px 4px; border-bottom:1px"
                        " solid #F5F5F7; font-size:13px;'>"
                        "<div style='display:flex; align-items:center; gap:8px;'>"
                        f"<span style='width:10px; height:10px; border-radius:50%; background:{dot_color}; display:inline-block;'></span>"
                        f"<span style='font-weight:500; color:#1D1D1F;'>{cat_name}</span>"
                        "</div>"
                        "<div style='color:#1D1D1F; font-weight:600;'>"
                        f"¥{cat_amt:.1f} <span style='color:#8E8E93; font-weight:400; font-size:12px; margin-left:4px;'>({pct:.1f}%)</span>"
                        "</div></div>",
                        unsafe_allow_html=True,
                    )

        with tab_settings:
            st.caption(f"👤 当前独立暗号舱位：**{CURRENT_USER}**")
            new_budget = st.number_input(
                "月度生活费 (元)", value=BUDGET_LIMIT, step=100.0
            )
            new_vault = st.number_input(
                "小金库初始资金 (元)", value=VAULT_INIT, step=100.0
            )
            new_threshold = st.number_input(
                "大额分流阈值 (元)", value=THRESHOLD, step=50.0
            )

            st.markdown("---")
            st.markdown("**🎭 AI 伴侣与小金库心愿单**")
            persona_options = ["温柔治愈", "毒舌损友", "极简高冷"]
            p_idx = persona_options.index(AI_PERSONA) if AI_PERSONA in persona_options else 0
            new_persona = st.selectbox("AI 评语性格", options=persona_options, index=p_idx)
            new_wish_name = st.text_input(
                "心愿物品名称 (留空则主页面不显示)",
                value=WISH_NAME,
                placeholder="例如：AirPods Pro 2 / 演唱会门票",
            )
            new_wish_target = st.number_input(
                "心愿目标金额 (元)", value=WISH_TARGET, min_value=0.0, step=100.0
            )

            st.markdown("---")
            key_placeholder = "已启用云端共享 AI 算力 (选填私人Key)" if SHARED_SECRET_KEY else "请输入 DeepSeek Key"
            new_key = st.text_input(
                "私人 DeepSeek Key (选填)",
                value=USER_CUSTOM_KEY,
                placeholder=key_placeholder,
                type="password",
            )
            if st.button("💾 保存参数", type="primary", use_container_width=True):
                set_user_config("monthly_budget", new_budget)
                set_user_config("vault_init", new_vault)
                set_user_config("threshold", new_threshold)
                set_user_config("ai_persona", new_persona)
                set_user_config("wish_name", new_wish_name.strip())
                set_user_config("wish_target", new_wish_target)
                set_user_config("deepseek_api_key", new_key)
                if new_persona == "极简高冷":
                    set_user_config("last_ai_comment", "")
                elif not LAST_AI_COMMENT:
                    set_user_config(
                        "last_ai_comment",
                        "今天也请好好吃饭、理性消费，小金库正在稳稳长大 🌱"
                        if new_persona == "温柔治愈"
                        else "管住双手，你的小金库可经不起几次深夜冲动消费 👀",
                    )
                st.session_state.last_toast = "✅ 参数与心愿设置已保存"
                st.rerun()

            st.markdown("---")
            st.markdown("**🛡️ 账单备份与恢复（防云端重置）**")
            c.execute(
                "SELECT date, title, amount, pool, note, category FROM transactions WHERE user_id=?",
                (CURRENT_USER,),
            )
            backup_data = {
                "user": CURRENT_USER,
                "budget": BUDGET_LIMIT,
                "vault_init": VAULT_INIT,
                "threshold": THRESHOLD,
                "ai_persona": AI_PERSONA,
                "wish_name": WISH_NAME,
                "wish_target": WISH_TARGET,
                "records": [
                    {
                        "date": r[0],
                        "title": r[1],
                        "amount": r[2],
                        "pool": r[3],
                        "note": r[4],
                        "category": r[5],
                    }
                    for r in c.fetchall()
                ],
            }
            st.download_button(
                "📤 导出本舱备份 (.json)",
                data=json.dumps(backup_data, ensure_ascii=False, indent=2),
                file_name=f"ledger_{CURRENT_USER}_{current_month_str}.json",
                mime="application/json",
                use_container_width=True,
            )

            uploaded_file = st.file_uploader(
                "📥 上传备份文件恢复", type=["json"], label_visibility="collapsed"
            )
            if uploaded_file is not None:
                if st.button("⚡ 确认恢复账单", type="primary", use_container_width=True):
                    try:
                        data = json.loads(uploaded_file.getvalue().decode("utf-8"))
                        set_user_config("monthly_budget", data.get("budget", BUDGET_LIMIT))
                        set_user_config("vault_init", data.get("vault_init", VAULT_INIT))
                        set_user_config("threshold", data.get("threshold", THRESHOLD))
                        if "ai_persona" in data:
                            set_user_config("ai_persona", data["ai_persona"])
                        if "wish_name" in data:
                            set_user_config("wish_name", data["wish_name"])
                        if "wish_target" in data:
                            set_user_config("wish_target", data["wish_target"])
                        c.execute("DELETE FROM transactions WHERE user_id=?", (CURRENT_USER,))
                        for rec in data.get("records", []):
                            c.execute(
                                "INSERT INTO transactions (date, title, amount, pool, note, category, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                (
                                    rec["date"],
                                    rec["title"],
                                    rec["amount"],
                                    rec["pool"],
                                    rec.get("note", ""),
                                    rec.get("category", "其他"),
                                    CURRENT_USER,
                                ),
                            )
                        conn.commit()
                        st.session_state.last_toast = "🎉 备份恢复成功！"
                        st.rerun()
                    except Exception:
                        st.error("备份文件格式有误")

            st.markdown("---")
            if st.button("🚪 切换其他暗号账户", type="primary", use_container_width=True):
                st.session_state.current_user = ""
                st.query_params.clear()
                st.rerun()

with col_input_area:
    st.text_input(
        "记一笔",
        placeholder="记一笔...",
        label_visibility="collapsed",
        key="capsule_input_key",
        on_change=handle_capsule_submit,
    )

# 11. Apple 原生感日期抬头、主白卡（内嵌 AI 微评语）与心愿单动态进度
progress_pct = min(max((total_monthly_spent / BUDGET_LIMIT) * 100, 0), 100)
bar_color = "#D49A9A" if remaining_budget < 0 else "#1D1D1F"
status_text = (
    "⚠️ 额度已透支 · 小金库兜底中"
    if remaining_budget < 0
    else f"AI 护航中 · {CURRENT_USER} 🟢"
)

# 构造 AI 评语 HTML（极简高冷模式下完全隐藏）
ai_comment_html = ""
if AI_PERSONA != "极简高冷":
    display_comment = LAST_AI_COMMENT
    if not display_comment:
        display_comment = (
            "随手记下一笔，让生活费与小金库井井有条 ✨"
            if AI_PERSONA == "温柔治愈"
            else "还没开张？今天居然一分钱都没花，值得表扬 👀"
        )
    dot_c = "#84A59D" if AI_PERSONA == "温柔治愈" else "#D49A9A"
    ai_comment_html = (
        f'<div class="ai-comment-row">'
        f'<span style="width:7px; height:7px; border-radius:50%; background:{dot_c}; display:inline-block; flex-shrink:0;"></span>'
        f'<span>{display_comment}</span>'
        f'</div>'
    )

st.markdown(
    f"""
    <div class="apple-date-header">
        <span class="apple-date-main">{formatted_date_cn}</span>
        <span class="apple-date-sub">{formatted_month_en}</span>
    </div>
    <div class="apple-white-card">
        <div class="metric-title">本月生活费余额 · DEEPSEEK 托管</div>
        <div class="metric-value">¥{remaining_budget:.2f} <span style="font-size: 15px; font-weight: 400; color: #86868B;">/ {BUDGET_LIMIT:.0f}</span></div>
        <div style="margin-top: 20px; background: #F2F2F7; border-radius: 99px; height: 7px; overflow: hidden;">
            <div style="width: {progress_pct}%; background: {bar_color}; height: 100%; border-radius: 99px; transition: width 0.4s ease;"></div>
        </div>
        <div style="margin-top: 14px; font-size: 12px; color: #86868B; display: flex; justify-content: space-between; align-items: center;">
            <span>本月已消费 ¥{total_monthly_spent:.2f}</span>
            <span>{status_text}</span>
        </div>
        {ai_comment_html}
    </div>
""",
    unsafe_allow_html=True,
)

# 构造心愿单动态展示（严格遵循3条规则：未填不渲染；小于目标显示差额；大于等于目标切换满额文案）
if WISH_NAME and WISH_TARGET > 0:
    wish_pct = min(max((current_vault / WISH_TARGET) * 100, 0.0), 100.0)
    if current_vault < WISH_TARGET:
        diff_amt = WISH_TARGET - current_vault
        wish_text = f"🎯 距离拿下「<b>{WISH_NAME}</b>」还差 <b>¥{diff_amt:.2f}</b>"
        wish_sub = f"{wish_pct:.0f}%"
        wish_bar_color = "#7C98B3"
    else:
        wish_text = f"✨ 小金库已攒够 <b>¥{current_vault:.2f}</b>，随时可全款拿下「<b>{WISH_NAME}</b>」！"
        wish_sub = "100% 达成"
        wish_bar_color = "#84A59D"

    st.markdown(
        f"""
        <div class="apple-wish-card">
            <div style="display:flex; justify-content:space-between; align-items:center; font-size:12.5px; color:#1D1D1F; margin-bottom:8px;">
                <span>{wish_text}</span>
                <span style="color:#86868B; font-size:11.5px; font-weight:600;">{wish_sub}</span>
            </div>
            <div style="background:#EAEAEA; border-radius:99px; height:4px; overflow:hidden;">
                <div style="width:{wish_pct}%; background:{wish_bar_color}; height:100%; border-radius:99px; transition:width 0.4s ease;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# 12. 注入原生 JS 监听器：在输入框最右侧动态浮现 Gemini 原版蓝底向上箭头 (#A8C7FA)
components.html(
    """
    <script>
    (function() {
        const doc = window.parent.document;
        function mountGeminiArrow() {
            const input = doc.querySelector('input[placeholder="记一笔..."]');
            if (!input) return;
            const container = input.parentElement;
            container.style.position = 'relative';
            container.style.display = 'flex';
            container.style.alignItems = 'center';

            let btn = doc.getElementById('gemini-send-circle-btn');
            if (!btn) {
                btn = doc.createElement('button');
                btn.id = 'gemini-send-circle-btn';
                btn.type = 'button';
                btn.title = '发送记账';
                btn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1F1F1F" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"></line><polyline points="5 12 12 5 19 12"></polyline></svg>';
                btn.style.cssText = 'position:absolute; right:2px; width:34px; height:34px; border-radius:50%; background-color:#A8C7FA; border:none; outline:none; display:flex; align-items:center; justify-content:center; cursor:pointer; opacity:0; transform:scale(0.5); pointer-events:none; transition:opacity 0.16s ease, transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1); z-index:999; padding:0; box-shadow: 0 1px 3px rgba(0,0,0,0.06);';
                container.appendChild(btn);

                const triggerSubmit = function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    btn.style.transform = 'scale(0.88)';
                    setTimeout(() => {
                        input.dispatchEvent(new KeyboardEvent('keydown', {
                            key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true
                        }));
                        input.blur();
                    }, 60);
                };
                btn.addEventListener('mousedown', triggerSubmit);
                btn.addEventListener('touchstart', triggerSubmit, {passive: false});
            }

            function syncVisibility() {
                if (input.value && input.value.trim().length > 0) {
                    btn.style.opacity = '1';
                    btn.style.transform = 'scale(1)';
                    btn.style.pointerEvents = 'auto';
                } else {
                    btn.style.opacity = '0';
                    btn.style.transform = 'scale(0.5)';
                    btn.style.pointerEvents = 'none';
                }
            }

            if (!input.dataset.geminiArrowBound) {
                input.dataset.geminiArrowBound = 'true';
                input.addEventListener('input', syncVisibility);
                input.addEventListener('keyup', syncVisibility);
                input.addEventListener('change', syncVisibility);
            }
            syncVisibility();
        }
        mountGeminiArrow();
        setInterval(mountGeminiArrow, 250);
    })();
    </script>
    """,
    height=0,
)
