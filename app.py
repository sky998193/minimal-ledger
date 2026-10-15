import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import json
import re
from datetime import datetime, timedelta, timezone
from openai import OpenAI
import streamlit.components.v1 as components

# 1. 页面极简配置
st.set_page_config(
    page_title="极简记账",
    page_icon="⚪",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. 全局纯净 CSS 样式（单块无空行，彻底杜绝源码外泄乱码，并消除手机端 Tab 黑边）
GLOBAL_CSS = """
<style>
#MainMenu, header, footer, [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"], .viewerBadge_container__1QSob, .styles_viewerBadge__1yB5_, [data-testid="manage-app-button"] { display: none !important; visibility: hidden !important; }
html, body, [data-testid="stAppViewContainer"], .stApp { background-color: #F5F5F7 !important; color: #1D1D1F !important; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", sans-serif !important; }
.block-container { max-width: 460px !important; padding-top: 1.8rem !important; padding-bottom: 4rem !important; padding-left: 1.1rem !important; padding-right: 1.1rem !important; }
[data-testid="stTabs"] [data-baseweb="tab-list"]::before, [data-testid="stTabs"] [data-baseweb="tab-list"]::after { display: none !important; background: none !important; box-shadow: none !important; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 8px !important; scrollbar-width: none !important; -ms-overflow-style: none !important; border-bottom: 1px solid #E5E5EA !important; }
[data-testid="stTabs"] [data-baseweb="tab-list"]::-webkit-scrollbar { display: none !important; }
[data-testid="stTabs"] button[role="tab"] { padding: 8px 6px !important; font-size: 13px !important; font-weight: 500 !important; color: #86868B !important; }
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] { color: #1D1D1F !important; font-weight: 600 !important; }
div[data-testid="stHorizontalBlock"] { align-items: center !important; }
div[data-testid="stPopover"] > div > button { border-radius: 50% !important; width: 40px !important; height: 40px !important; min-height: 40px !important; padding: 0 !important; background: #FFFFFF !important; border: 1px solid rgba(0,0,0,0.06) !important; box-shadow: 0 2px 10px rgba(0,0,0,0.03) !important; color: #1D1D1F !important; display: flex !important; align-items: center !important; justify-content: center !important; }
div[data-testid="stPopover"] > div > button span { font-size: 18px !important; font-weight: 400 !important; line-height: 1 !important; }
div[data-testid="stPopover"] > div > button svg { display: none !important; }
div[data-testid="stTextInput"] input { border-radius: 22px !important; background: #FFFFFF !important; border: 1px solid rgba(0,0,0,0.06) !important; padding: 10px 18px !important; font-size: 14.5px !important; color: #1D1D1F !important; box-shadow: 0 2px 10px rgba(0,0,0,0.03) !important; height: 42px !important; }
div[data-testid="stTextInput"] input:focus { border-color: #1D1D1F !important; box-shadow: 0 2px 12px rgba(0,0,0,0.06) !important; }
div[data-testid="stPopoverBody"] { border-radius: 22px !important; border: 1px solid rgba(0,0,0,0.06) !important; box-shadow: 0 12px 36px rgba(0,0,0,0.1) !important; padding: 14px 16px !important; width: min(92vw, 420px) !important; max-width: 92vw !important; background: #FFFFFF !important; }
div[data-testid="stPopoverBody"] div[data-testid="stButton"] button[kind="secondary"] { border: none !important; background: transparent !important; color: #86868B !important; padding: 2px 6px !important; min-height: 26px !important; height: 26px !important; border-radius: 8px !important; box-shadow: none !important; }
div[data-testid="stPopoverBody"] div[data-testid="stButton"] button[kind="secondary"]:hover { background-color: rgba(255,59,48,0.1) !important; color: #FF3B30 !important; }
div[data-testid="stPopoverBody"] div[data-testid="stHorizontalBlock"] { background: transparent !important; border: none !important; border-bottom: 1px solid #F2F2F7 !important; padding: 7px 0 !important; margin: 0 !important; display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; align-items: center !important; justify-content: space-between !important; gap: 8px !important; }
div[data-testid="stPopoverBody"] div[data-testid="stHorizontalBlock"] > div:first-child { flex: 1 1 auto !important; min-width: 0 !important; }
div[data-testid="stPopoverBody"] div[data-testid="stHorizontalBlock"] > div:last-child { flex: 0 0 28px !important; width: 28px !important; display: flex !important; justify-content: flex-end !important; }
.apple-date-header { display: flex; justify-content: space-between; align-items: baseline; padding: 0 8px; margin-bottom: 10px; }
.apple-date-main { font-size: 15px; font-weight: 600; color: #1D1D1F; letter-spacing: -0.2px; }
.apple-date-sub { font-size: 11px; font-weight: 600; color: #86868B; letter-spacing: 0.8px; text-transform: uppercase; }
.apple-white-card { background: #FFFFFF !important; color: #1D1D1F !important; border-radius: 26px; padding: 26px 24px; box-shadow: 0 6px 24px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.02); border: 1px solid rgba(0,0,0,0.03); margin-bottom: 14px; }
.metric-title { font-size: 12px; font-weight: 500; color: #86868B !important; letter-spacing: 0.5px; margin-bottom: 8px; }
.metric-value { font-size: 40px; font-weight: 700; color: #1D1D1F !important; letter-spacing: -1px; }
.ai-comment-row { margin-top: 15px; padding-top: 13px; border-top: 1px solid #F2F2F7; font-size: 12.5px; color: #636366; display: flex; align-items: center; gap: 7px; line-height: 1.4; }
.apple-wish-card { background: rgba(255,255,255,0.78) !important; backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border-radius: 20px; padding: 14px 20px; box-shadow: 0 4px 16px rgba(0,0,0,0.025); border: 1px solid rgba(0,0,0,0.03); margin-bottom: 16px; }
</style>
"""
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# 跨层 JS 隐藏右下角残留徽章
components.html(
    """
    <script>
    const cleanBadges = () => {
        try {
            const doc = window.parent.document;
            const selectors = [
                '.viewerBadge_container__1QSob',
                '.styles_viewerBadge__1yB5_',
                '[data-testid="manage-app-button"]',
                'a[href*="streamlit.io/cloud"]'
            ];
            selectors.forEach(sel => {
                doc.querySelectorAll(sel).forEach(el => { el.style.display = 'none'; });
            });
        } catch (e) {}
    };
    cleanBadges();
    setInterval(cleanBadges, 1200);
    </script>
    """,
    height=0,
)

# 3. 数据库初始化与缓存
def get_china_now():
    return datetime.now(timezone(timedelta(hours=8)))

@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect("expenses.db", check_same_thread=False)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            title TEXT,
            amount REAL,
            pool TEXT,
            note TEXT,
            category TEXT DEFAULT '其他',
            user_id TEXT DEFAULT 'default'
        )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS user_config (
            user_id TEXT,
            key TEXT,
            value TEXT,
            PRIMARY KEY (user_id, key)
        )"""
    )
    conn.commit()
    return conn

conn = get_db_connection()

# 4. 暗号分舱与静默参数拦截
query_params = st.query_params
url_user = query_params.get("u", "").strip()

if "current_user" not in st.session_state:
    st.session_state.current_user = url_user if url_user else ""

if url_user and st.session_state.current_user != url_user:
    st.session_state.current_user = url_user

if not st.session_state.current_user:
    st.markdown(
        """
        <div style="text-align:center; padding-top: 60px; padding-bottom: 20px;">
            <div style="font-size: 38px; margin-bottom: 12px;">⚪</div>
            <div style="font-size: 20px; font-weight: 600; color: #1D1D1F; margin-bottom: 8px;">极简私人账本</div>
            <div style="font-size: 13px; color: #86868B; line-height: 1.6;">
                请输入你的专属暗号（如姓名缩写或昵称）<br>每位用户的账本、小金库与分析图完全独立隔离
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    user_input = st.text_input("专属暗号", placeholder="输入暗号后按回车进入...", label_visibility="collapsed")
    if user_input.strip():
        clean_u = user_input.strip()
        st.session_state.current_user = clean_u
        st.query_params["u"] = clean_u
        st.rerun()
    st.stop()

CURRENT_USER = st.session_state.current_user

# 5. 用户独立配置读写
def get_user_config(key, default_val):
    c = conn.cursor()
    c.execute("SELECT value FROM user_config WHERE user_id=? AND key=?", (CURRENT_USER, key))
    row = c.fetchone()
    return row[0] if row else default_val

def set_user_config(key, val):
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO user_config (user_id, key, value) VALUES (?, ?, ?)",
        (CURRENT_USER, key, str(val)),
    )
    conn.commit()

MONTHLY_BUDGET = float(get_user_config("monthly_budget", "2500.0"))
THRESHOLD = float(get_user_config("threshold", "300.0"))
AI_PERSONA = get_user_config("ai_persona", "温柔治愈")
WISH_NAME = get_user_config("wish_name", "AirPods Pro 2")
WISH_TARGET = float(get_user_config("wish_target", "1899.0"))
USER_API_KEY = get_user_config("api_key", "")
DEFAULT_SECRET_KEY = st.secrets.get("DEEPSEEK_API_KEY", "") if hasattr(st, "secrets") else ""
ACTIVE_API_KEY = USER_API_KEY if USER_API_KEY else DEFAULT_SECRET_KEY

# 6. 精准分类兜底与 AI 评语生成
CATEGORY_KEYWORDS = {
    "餐饮": ["饭", "餐", "水", "奶茶", "咖啡", "面", "粉", "肉", "菜", "水果", "零食", "烧烤", "火锅", "外卖", "早餐", "午饭", "晚饭", "宵夜", "瑞幸", "星巴克", "麦当劳", "肯德基", "吃", "喝"],
    "交通": ["打车", "滴滴", "地铁", "公交", "高铁", "火车", "机票", "加油", "停车", "单车", "骑车", "路费"],
    "购物": ["买", "衣服", "裤", "鞋", "包", "护肤", "化妆", "日用", "超市", "淘宝", "京东", "拼多多", "快递"],
    "娱乐": ["电影", "游戏", "会员", "充值", "KTV", "剧本杀", "演出", "门票", "旅游", "网吧", "麻将"],
    "居家": ["房租", "水费", "电费", "燃气", "网费", "话费", "物业", "维修", "纸巾", "洗衣"],
    "数码": ["手机", "电脑", "耳机", "键盘", "鼠标", "显示器", "iPad", "苹果", "相机", "镜头", "充电器", "数据线", "硬盘"],
    "医疗": ["药", "医院", "看病", "挂号", "体检", "牙", "医保", "诊所"],
}

def infer_precise_category(text, ai_cat=""):
    valid_cats = ["餐饮", "交通", "购物", "娱乐", "居家", "数码", "医疗", "其他"]
    for cat, kw_list in CATEGORY_KEYWORDS.items():
        for kw in kw_list:
            if kw in text:
                return cat
    if ai_cat in valid_cats and ai_cat != "其他":
        return ai_cat
    return "其他"

def fallback_comment(title, amount, category, persona):
    if persona == "极简高冷":
        return ""
    if persona == "毒舌损友":
        if amount >= 200:
            return f"又花了 ¥{amount:.0f}，钱包在滴血！"
        return f"{title} ¥{amount:.1f}，记下了，省着点花吧。"
    return f"已温柔记下 {title}，每一分钱都算数 ✨"

def fallback_parse(text):
    matches = re.findall(r"\d+(?:\.\d+)?", text)
    amount = float(matches[-1]) if matches else 0.0
    title = re.sub(r"\d+(?:\.\d+)?", "", text).replace("元", "").replace("块", "").strip()
    if not title:
        title = "日常消费"
    cat = infer_precise_category(text)
    is_vault = (amount >= THRESHOLD) or (cat == "数码")
    comment = fallback_comment(title, amount, cat, AI_PERSONA)
    return title, amount, cat, is_vault, comment

# 7. 支持“一句话拆分多笔账单”的 DeepSeek 解析函数
def parse_with_deepseek(text):
    if not ACTIVE_API_KEY:
        t, a, cat, iv, cm = fallback_parse(text)
        return [(t, a, cat, iv)], cm
    try:
        client = OpenAI(api_key=ACTIVE_API_KEY, base_url="https://api.deepseek.com")
        persona_rule = ""
        if AI_PERSONA == "温柔治愈":
            persona_rule = "请用温柔、治愈、暖心夸奖的语气写一句18字以内的简短微评语。"
        elif AI_PERSONA == "毒舌损友":
            persona_rule = "请用幽默、傲娇、损友吐槽的语气写一句18字以内的简短微评语。"
        else:
            persona_rule = '留空字符串 ""。'

        prompt = f"""
        你是一个专业的分类记账助手。用户可能会在一句话中输入多笔消费（例如：“买水5元吃饭15元”）。请将它们拆分为独立的消费记录，并严格以包含 items 数组的 JSON 对象格式输出：
        {{
          "items": [
            {{
              "title": "消费项目精简名称（string，不含数字和金额）",
              "amount": 消费金额（float）,
              "category": "必须从 ['餐饮', '交通', '购物', '娱乐', '居家', '数码', '医疗', '其他'] 中选一个",
              "is_vault": 是否属于数码大件或大额支出（boolean）
            }}
          ],
          "comment": "{persona_rule}"
        }}
        
        用户输入：{text}
        """
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            stream=False,
        )
        res_data = json.loads(response.choices[0].message.content)
        items = res_data.get("items", [])
        comment = str(res_data.get("comment", "")).strip()

        parsed_results = []
        for item in items:
            raw_title = item.get("title", text)
            amount = float(item.get("amount", 0.0))
            ai_cat = item.get("category", "")
            final_cat = infer_precise_category(f"{text} {raw_title}", ai_cat)
            is_vault = bool(item.get("is_vault", False)) or (final_cat == "数码")
            parsed_results.append((raw_title, amount, final_cat, is_vault))

        if not parsed_results:
            t, a, cat, iv, _ = fallback_parse(text)
            parsed_results.append((t, a, cat, iv))

        if AI_PERSONA == "极简高冷":
            comment = ""
        elif not comment and parsed_results:
            comment = fallback_comment(parsed_results[0][0], parsed_results[0][1], parsed_results[0][2], AI_PERSONA)

        return parsed_results, comment
    except Exception:
        t, a, cat, iv, cm = fallback_parse(text)
        return [(t, a, cat, iv)], cm

# 8. 批量循环入账逻辑
def add_transaction(user_text):
    user_text = str(user_text).strip()
    if user_text:
        items_list, comment = parse_with_deepseek(user_text)
        date_str = get_china_now().strftime("%Y-%m-%d %H:%M")
        c = conn.cursor()
        count = 0

        for title, amount, category, is_vault in items_list:
            if amount <= 0:
                continue
            if amount >= THRESHOLD:
                is_vault = True
            pool_type = "vault" if is_vault else "monthly"

            c.execute(
                "INSERT INTO transactions (date, title, amount, pool, note, category, user_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (date_str, title, amount, pool_type, user_text, category, CURRENT_USER),
            )
            count += 1

        conn.commit()
        if comment:
            set_user_config("last_ai_comment", comment)

        if count > 1:
            st.session_state.last_toast = f"✅ 已成功批量入账 {count} 笔交易"
        elif count == 1:
            item = items_list[0]
            pool_name = "🥇小金库" if (item[3] or item[1] >= THRESHOLD) else "本月生活费"
            st.session_state.last_toast = f"✅ 已入账：[{item[2]}] {item[0]} ¥{item[1]:.2f} （{pool_name}）"
        else:
            st.session_state.last_toast = "⚠️ 未识别到有效金额"

# 拦截快捷指令 URL 参数 ?q=xxx 自动记账
if "q" in query_params and query_params["q"].strip():
    q_text = query_params["q"].strip()
    add_transaction(q_text)
    del st.query_params["q"]
    st.rerun()

if "last_toast" in st.session_state and st.session_state.last_toast:
    st.toast(st.session_state.last_toast)
    st.session_state.last_toast = ""

# 9. 数据查询与双资金池计算
now_dt = get_china_now()
current_month_prefix = now_dt.strftime("%Y-%m")

df_all = pd.read_sql_query(
    "SELECT * FROM transactions WHERE user_id=? ORDER BY id DESC",
    conn,
    params=(CURRENT_USER,),
)

if not df_all.empty:
    df_all["month"] = df_all["date"].str.slice(0, 7)
    df_curr_month = df_all[df_all["month"] == current_month_prefix]
    monthly_spent = df_curr_month[df_curr_month["pool"] == "monthly"]["amount"].sum()

    past_months = [m for m in df_all["month"].unique() if m < current_month_prefix]
    accumulated_surplus = 0.0
    for m in past_months:
        m_spent = df_all[(df_all["month"] == m) & (df_all["pool"] == "monthly")]["amount"].sum()
        accumulated_surplus += (MONTHLY_BUDGET - m_spent)

    vault_spent_total = df_all[df_all["pool"] == "vault"]["amount"].sum()
    manual_vault_init = float(get_user_config("vault_init", "2000.0"))
    vault_balance = manual_vault_init + accumulated_surplus - vault_spent_total
else:
    monthly_spent = 0.0
    manual_vault_init = float(get_user_config("vault_init", "2000.0"))
    vault_balance = manual_vault_init

monthly_remaining = MONTHLY_BUDGET - monthly_spent

# 10. 顶部极简输入栏与 4 标签页弹出菜单
col_menu, col_input = st.columns([1.2, 8.8])

with col_menu:
    with st.popover("＋"):
        tab_ledger, tab_analytics, tab_settings, tab_guide = st.tabs(
            ["🛡️ 小金库与流水", "📊 消费分析", "⚙️ 参数设置", "📖 使用说明"]
        )

        with tab_ledger:
            st.markdown(
                f"""
                <div style="background:#F5F5F7; border-radius:16px; padding:14px 16px; margin-bottom:12px;">
                    <div style="font-size:11.5px; color:#86868B;">🥇 隐藏小金库可用余额</div>
                    <div style="font-size:24px; font-weight:700; color:#1D1D1F; margin-top:2px;">¥ {vault_balance:,.2f}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.caption("最近账单流水（点击右侧 × 可删除）")
            if df_all.empty:
                st.info("暂无记账记录")
            else:
                for _, row in df_all.head(20).iterrows():
                    r_col1, r_col2 = st.columns([8.8, 1.2])
                    pool_tag = "🥇" if row["pool"] == "vault" else "⚪"
                    with r_col1:
                        st.markdown(
                            f"<div style='font-size:13px; color:#1D1D1F; font-weight:500; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>"
                            f"{pool_tag} [{row['category']}] {row['title']} <span style='color:#1D1D1F; font-weight:600;'>¥{row['amount']:.2f}</span> "
                            f"<span style='font-size:11px; color:#86868B;'>({row['date'][5:]})</span></div>",
                            unsafe_allow_html=True,
                        )
                    with r_col2:
                        if st.button("×", key=f"del_{row['id']}"):
                            c = conn.cursor()
                            c.execute("DELETE FROM transactions WHERE id=? AND user_id=?", (row["id"], CURRENT_USER))
                            conn.commit()
                            st.rerun()

        with tab_analytics:
            if df_all.empty:
                st.info("记几笔账后即可查看莫兰迪消费分布图")
            else:
                cat_sum = df_all.groupby("category")["amount"].sum().reset_index()
                morandi_colors = ["#8E9BAE", "#A3B19B", "#D6A29A", "#C9B79C", "#B4A6AB", "#94A7AE", "#D0C4B2", "#B5B5B5"]
                fig = px.pie(
                    cat_sum,
                    values="amount",
                    names="category",
                    hole=0.58,
                    color_discrete_sequence=morandi_colors,
                )
                fig.update_layout(
                    margin=dict(t=10, b=10, l=10, r=10),
                    height=240,
                    showlegend=True,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with tab_settings:
            st.caption(f"当前独立舱位暗号：`{CURRENT_USER}`")
            new_budget = st.number_input("月度生活费预算 (¥)", value=MONTHLY_BUDGET, step=100.0)
            new_init_vault = st.number_input("小金库初始底金 (¥)", value=manual_vault_init, step=100.0)
            new_threshold = st.number_input("单笔大额自动分流阈值 (¥)", value=THRESHOLD, step=50.0)
            persona_options = ["温柔治愈", "毒舌损友", "极简高冷"]
            p_idx = persona_options.index(AI_PERSONA) if AI_PERSONA in persona_options else 0
            new_persona = st.selectbox("AI 记账伴侣性格", persona_options, index=p_idx)
            new_wish_name = st.text_input("心愿单目标名称", value=WISH_NAME)
            new_wish_target = st.number_input("心愿单目标金额 (¥)", value=WISH_TARGET, step=100.0)
            new_api_key = st.text_input("自定义 DeepSeek API Key (选填)", value=USER_API_KEY, type="password")

            if st.button("保存参数设置", use_container_width=True):
                set_user_config("monthly_budget", new_budget)
                set_user_config("vault_init", new_init_vault)
                set_user_config("threshold", new_threshold)
                set_user_config("ai_persona", new_persona)
                set_user_config("wish_name", new_wish_name)
                set_user_config("wish_target", new_wish_target)
                set_user_config("api_key", new_api_key.strip())
                st.success("✅ 设置已保存")
                st.rerun()

            st.markdown("---")
            if not df_all.empty:
                backup_json = df_all.to_json(orient="records", force_ascii=False)
                st.download_button(
                    "📤 导出本舱备份 (.json)",
                    data=backup_json,
                    file_name=f"ledger_{CURRENT_USER}_{now_dt.strftime('%Y%m%d')}.json",
                    mime="application/json",
                    use_container_width=True,
                )

        with tab_guide:
            st.markdown("#### 📖 帮助与文档手册")
            st.caption("查看图文配置教程与使用指南")
            st.markdown("---")

            st.markdown("**1. 极简账本用户使用手册**")
            st.markdown(
                '<a href="https://你的账本使用手册链接" target="_blank" style="display:block; text-align:center; background:#F2F2F7; color:#1D1D1F; padding:10px 14px; border-radius:12px; text-decoration:none; font-weight:500; font-size:13px; margin-bottom:14px;">📖 查看账本使用手册 →</a>',
                unsafe_allow_html=True,
            )

            st.markdown("**2. iOS 快捷指令配置教程**")
            st.markdown(
                '<a href="https://你的快捷指令教程链接" target="_blank" style="display:block; text-align:center; background:#F2F2F7; color:#1D1D1F; padding:10px 14px; border-radius:12px; text-decoration:none; font-weight:500; font-size:13px;">⚡ 查看敲背面快捷指令教程 →</a>',
                unsafe_allow_html=True,
            )

with col_input:
    def on_Quick_Submit():
        val = st.session_state.quick_input_box
        if val.strip():
            add_transaction(val.strip())
            st.session_state.quick_input_box = ""

    st.text_input(
        "快速记账",
        placeholder="记一笔账吧（支持连记：买水5元吃饭15元）...",
        key="quick_input_box",
        on_change=on_Quick_Submit,
        label_visibility="collapsed",
    )

# 11. 主界面：日期抬头 + 月度生活费白色卡片 + 心愿单进度条
weekdays_cn = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
date_main_str = f"{now_dt.month}月{now_dt.day}日 {weekdays_cn[now_dt.weekday()]}"
last_comment = get_user_config("last_ai_comment", "今天也要好好生活，理智消费 ✨")

comment_html = ""
if AI_PERSONA != "极简高冷" and last_comment:
    comment_html = f'<div class="ai-comment-row"><span>💬</span><span>{last_comment}</span></div>'

st.markdown(
    f"""
    <div class="apple-date-header">
        <div class="apple-date-main">{date_main_str}</div>
        <div class="apple-date-sub">MONTHLY POOL · {CURRENT_USER}</div>
    </div>
    <div class="apple-white-card">
        <div class="metric-title">本月剩余可用生活费</div>
        <div class="metric-value">¥ {monthly_remaining:,.2f}</div>
        <div style="font-size:12px; color:#86868B; margin-top:6px;">
            本月已用 ¥{monthly_spent:,.2f} / 预算 ¥{MONTHLY_BUDGET:,.0f}
        </div>
        {comment_html}
    </div>
    """,
    unsafe_allow_html=True,
)

if WISH_NAME and WISH_TARGET > 0:
    progress_pct = max(0.0, min(100.0, (vault_balance / WISH_TARGET) * 100.0))
    diff_amt = max(0.0, WISH_TARGET - vault_balance)
    status_text = "🎉 小金库已攒够，随时可以全款拿下！" if diff_amt == 0 else f"距离拿下还差 ¥{diff_amt:,.0f} ({progress_pct:.1f}%)"
    st.markdown(
        f"""
        <div class="apple-wish-card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-size:13px; font-weight:600; color:#1D1D1F;">🎯 心愿单：{WISH_NAME}</span>
                <span style="font-size:11.5px; color:#86868B;">{status_text}</span>
            </div>
            <div style="width:100%; height:7px; background:#E5E5EA; border-radius:99px; overflow:hidden;">
                <div style="width:{progress_pct:.1f}%; height:100%; background:#8E9BAE; border-radius:99px;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
