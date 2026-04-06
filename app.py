import streamlit as st
import json, os, urllib.parse
from datetime import date, datetime, timedelta
import streamlit.components.v1 as components

# ══════════════════════════════════════════════════════════════════
#  頁面設定
# ══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="行程報到單產生器",
    page_icon="📋",
    layout="centered",
)

# ══════════════════════════════════════════════════════════════════
#  常數
# ══════════════════════════════════════════════════════════════════
DATA_FILE = "quote_data.json"
WEEKDAY_ZH = ["一", "二", "三", "四", "五", "六", "日"]
NOTICE_TEXT = (
    "注意事項：限定為當天航班使用。不得退改期。"
    "當日當班未到視同放棄。恕無法退款。"
    "請在開船前 20 分鐘至報到地點。"
    "請遵守行程安全指示講解。違規者自行負責。"
)
FIXED_ITINERARIES = [
    "七美+東吉嶼、藍洞、南方四島一日遊",
    "七美一日遊",
    "​加購浮潛",
    "加購獨木舟",
    "薰衣草森林浮潛+七美一日遊",
    "不浮潛方案(東嶼坪登島自由行+七美",
    "七美+望安",
    "金色雙島跳島 - 虎井嶼 (貓島) ＆ 桶盤",
    "北海1日遊",
    "員貝耍廢島一日遊",
    "東海星空之旅+龍蝦海鮮泡麵",
    "悠游員貝一日遊（含水上活動）",
    "戀夏超值B東海一日",
    "驚豔吉貝",
    "夜釣小管",
    "夜釣小管+煙火船",
    "煙火船",
    "海鮮燒烤吃到飽",
    "海洋牧場",
    "夕遊海洋牧場",
]
FIXED_COUNTERS = [
    "海安",
    "金八達",
    "得意快艇",
    "和慶半潛艇",
    "海上皇宮",
    "新揚快艇",
    "戀夏育樂",
    "大姐燒烤",
    "南碼燒烤",
]
FIXED_LOCATIONS = [
    "南海遊客中心",
    "北海遊客中心",
    "岐頭遊客中心",
]
FIXED_TRAVEL_AGENCIES = [
    "丞欣旅行社",
    "香妹旅行社",
]

# ══════════════════════════════════════════════════════════════════
#  資料 IO
# ══════════════════════════════════════════════════════════════════
def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"itineraries": [], "locations": {}, "agencies": [], "counters": []}


def save_data(d: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════
#  Session State
# ══════════════════════════════════════════════════════════════════
if "data" not in st.session_state:
    st.session_state.data = load_data()
if "copied" not in st.session_state:
    st.session_state.copied = False
if "list_dirty" not in st.session_state:
    st.session_state.list_dirty = False
if "last_valid_depart" not in st.session_state:
    st.session_state.last_valid_depart = ""

data = st.session_state.data
data.setdefault("itineraries", [])
data.setdefault("locations", {})
data.setdefault("agencies", [])
data.setdefault("counters", [])

page = st.sidebar.radio("功能選單", ["前台（產生行程報到單）", "後台管理"])


# ══════════════════════════════════════════════════════════════════
#  工具函式
# ══════════════════════════════════════════════════════════════════
def map_url(place: str) -> str:
    # NOTE: 直接用「地點名稱」當查詢字串
    return f"https://www.google.com/maps/search/{urllib.parse.quote(place)}"


def merge_fixed_items(d: dict) -> None:
    d.setdefault("itineraries", [])
    d.setdefault("locations", {})
    d.setdefault("agencies", [])
    d.setdefault("counters", [])

    for name in FIXED_ITINERARIES:
        if name and name not in d["itineraries"]:
            d["itineraries"].append(name)

    for name in FIXED_COUNTERS:
        if name and name not in d["counters"]:
            d["counters"].append(name)

    for name in FIXED_TRAVEL_AGENCIES:
        if name and name not in d["agencies"]:
            d["agencies"].append(name)

    for loc in FIXED_LOCATIONS:
        if loc and loc not in d["locations"]:
            d["locations"][loc] = map_url(loc)


merge_fixed_items(data)


def day_type(d: date) -> str:
    # 星期五到日算「假日」，其餘「平日」
    return "假日" if d.weekday() >= 4 else "平日"


def parse_hhmm(s: str) -> tuple[bool, int, int]:
    raw = (s or "").strip()
    if not raw:
        return False, 0, 0
    # 支援 "19:00" 或 "1900"
    if ":" in raw:
        parts = raw.split(":")
        if len(parts) != 2:
            return False, 0, 0
        hh, mm = parts[0].strip(), parts[1].strip()
    else:
        if len(raw) != 4 or not raw.isdigit():
            return False, 0, 0
        hh, mm = raw[:2], raw[2:]
    if not (hh.isdigit() and mm.isdigit()):
        return False, 0, 0
    h, m = int(hh), int(mm)
    if h < 0 or h > 23 or m < 0 or m > 59:
        return False, 0, 0
    return True, h, m


def minus_30_minutes_hhmm(depart_hhmm: str) -> str:
    ok, h, m = parse_hhmm(depart_hhmm)
    if not ok:
        return ""
    base = datetime(2000, 1, 1, h, m)
    checkin = base - timedelta(minutes=30)
    return checkin.strftime("%H:%M")


def checkin_display_from_depart(depart_hhmm: str) -> str:
    hhmm = minus_30_minutes_hhmm(depart_hhmm)
    return f"{hhmm}抵達" if hhmm else ""


def build_message(
    sel_date,
    checkin_t,
    depart_t,
    counter,
    itinerary,
    adults,
    children,
    infants,
    note,
    loc_name,
    loc_url,
    agency,
    passenger_name,
    island_transport,
    scooter_count,
) -> str:
    dtype = day_type(sel_date)
    # 依需求：星期刪除，只留日期（假日/平日不顯示在文字中）
    date_str = sel_date.strftime("%Y/%m/%d")

    people_parts = []
    if adults:
        people_parts.append(f"成人 {adults} 位")
    if children:
        people_parts.append(f"兒童 {children} 位")
    if infants:
        people_parts.append(f"幼兒 {infants} 位")
    people_str = "　".join(people_parts) if people_parts else "－"

    lines = [
        "📋 行程報到單",
        f"📅 日期：{date_str}",
        f"🙍 旅客姓名：{passenger_name if str(passenger_name).strip() else '－'}",
        f"🕐 報到時間：{checkin_t if str(checkin_t).strip() else '－'}",
        f"🚢 出發時間：{depart_t if str(depart_t).strip() else '－'}",
        f"🗺️ 行程：{itinerary if itinerary else ''}",
        f"📍 報到地點：{loc_name if loc_name else ''}",
        f"🏢 報到櫃台：{counter if counter else '－'}",
    ]

    if loc_url:
        # A：讓 LINE 更容易點擊，做成「一行完整 URL」
        lines.append("🔗 地圖網址：")
        lines.append(loc_url)

    if island_transport == "機車":
        transport_text = f"機車 {scooter_count} 台" if scooter_count > 0 else "機車"
    else:
        transport_text = island_transport if island_transport else "－"
    lines.append(f"🛵 島上交通：{transport_text}")

    # 減少空白：讓人數在同一行呈現
    lines.append(f"👥 人數：成人 {adults} 位　兒童 {children} 位　幼兒 {infants} 位")
    if note:
        lines.append(f"📝 備註：{note}")
    if agency:
        lines.append(f"🏢 旅行社：{agency}")

    lines += [
        "",
        f"⚠️ {NOTICE_TEXT}",
    ]
    return "\n".join(lines)


def render_admin_panel() -> None:
    st.markdown("## 後台管理")
    st.caption("在這裡可隨時更改/增加/刪除行程、報到地點、報到櫃台、旅行社清單。")

    if st.session_state.list_dirty:
        st.warning("目前有變更尚未保存，請按下「保存鍵」。")

    # 清楚鍵：清空未保存的新增/刪除操作（避免使用者寫錯）
    if st.button("清楚鍵（清空未保存變更）", use_container_width=True):
        st.session_state.data = load_data()
        st.session_state.list_dirty = False
        for k in [
            "new_itinerary",
            "del_itinerary",
            "new_location_name",
            "new_location_url",
            "del_location",
            "new_counter",
            "del_counter",
            "new_agency",
            "del_agency",
        ]:
            st.session_state[k] = ""
        st.rerun()

    st.divider()
    st.subheader("寫錯資料清除鍵（重置 quote_data.json）")
    st.caption("會把已保存的行程/報到地點/旅行社清單全部清空。")
    confirm_clear = st.checkbox("我確定要清除所有已保存資料", value=False)
    if confirm_clear:
        if st.button("寫錯資料清除鍵（清空已保存資料）", type="primary", use_container_width=True):
            if os.path.exists(DATA_FILE):
                os.remove(DATA_FILE)
            st.session_state.data = load_data()
            st.session_state.list_dirty = False
            st.rerun()

    st.divider()

    # 行程清單
    st.markdown("### 行程（itineraries）")
    new_itinerary = st.text_input("新增行程", key="new_itinerary")
    col_it_add, col_it_del = st.columns([1, 1])
    with col_it_add:
        if st.button("增加", key="add_itinerary_btn", use_container_width=True):
            v = (new_itinerary or "").strip()
            if v:
                if v not in data["itineraries"]:
                    data["itineraries"].append(v)
                    st.session_state.list_dirty = True
                    st.success("已加入行程清單（尚未保存）。")
                else:
                    st.info("此行程已存在。")
                st.session_state["new_itinerary"] = ""
            else:
                st.warning("請輸入行程名稱。")
    with col_it_del:
        del_it = st.selectbox(
            "刪除行程（選擇後按刪除）",
            options=[""] + list(data["itineraries"]),
            key="del_itinerary",
        )
        if st.button("刪除", key="del_itinerary_btn", use_container_width=True):
            v = (del_it or "").strip()
            if v:
                if v in data["itineraries"]:
                    data["itineraries"] = [x for x in data["itineraries"] if x != v]
                    st.session_state.list_dirty = True
                    st.success("已刪除行程（尚未保存）。")
                else:
                    st.info("此行程不存在。")
            else:
                st.warning("請先選擇要刪除的行程。")

    st.divider()

    # 報到地點清單
    st.markdown("### 報到地點（locations）")
    new_location_name = st.text_input("新增報到地點名稱", key="new_location_name")
    new_location_url = st.text_input(
        "新增地圖網址（可留空，留空則自動生成）",
        key="new_location_url",
        placeholder="例如：https://www.google.com/maps/...",
    )
    col_loc_add, col_loc_del = st.columns([1, 1])
    with col_loc_add:
        if st.button("增加", key="add_location_btn", use_container_width=True):
            name = (new_location_name or "").strip()
            if name:
                url = (new_location_url or "").strip()
                if not url:
                    url = map_url(name)
                data["locations"][name] = url
                st.session_state.list_dirty = True
                st.success("已加入/更新報到地點（尚未保存）。")
                st.session_state["new_location_name"] = ""
                st.session_state["new_location_url"] = ""
            else:
                st.warning("請輸入報到地點名稱。")
    with col_loc_del:
        del_loc = st.selectbox(
            "刪除報到地點（選擇後按刪除）",
            options=[""] + list(data["locations"].keys()),
            key="del_location",
        )
        if st.button("刪除", key="del_location_btn", use_container_width=True):
            v = (del_loc or "").strip()
            if v:
                data["locations"].pop(v, None)
                st.session_state.list_dirty = True
                st.success("已刪除報到地點（尚未保存）。")
            else:
                st.warning("請先選擇要刪除的報到地點。")

    st.divider()

    # 旅行社清單
    st.markdown("### 旅行社（agencies）")
    new_agency = st.text_input("新增旅行社", key="new_agency")
    del_agency = st.selectbox(
        "刪除旅行社（選擇後按刪除）",
        options=[""] + list(data["agencies"]),
        key="del_agency",
    )
    col_ag_add, col_ag_del = st.columns([1, 1])
    with col_ag_add:
        if st.button("增加", key="add_agency_btn", use_container_width=True):
            v = (new_agency or "").strip()
            if v:
                if v not in data["agencies"]:
                    data["agencies"].append(v)
                    st.session_state.list_dirty = True
                    st.success("已加入旅行社（尚未保存）。")
                else:
                    st.info("此旅行社已存在。")
                st.session_state["new_agency"] = ""
            else:
                st.warning("請輸入旅行社名稱。")
    with col_ag_del:
        if st.button("刪除", key="del_agency_btn", use_container_width=True):
            v = (del_agency or "").strip()
            if v:
                if v in data["agencies"]:
                    data["agencies"] = [x for x in data["agencies"] if x != v]
                    st.session_state.list_dirty = True
                    st.success("已刪除旅行社（尚未保存）。")
                else:
                    st.info("此旅行社不存在。")
            else:
                st.warning("請先選擇要刪除的旅行社。")

    st.divider()

    # 報到櫃台清單
    st.markdown("### 報到櫃台（counters）")
    new_counter = st.text_input("新增報到櫃台", key="new_counter", placeholder="例：櫃台A / 第3櫃台 / 報到中心")
    del_counter = st.selectbox(
        "刪除報到櫃台（選擇後按刪除）",
        options=[""] + list(data["counters"]),
        key="del_counter",
    )
    col_ct_add, col_ct_del = st.columns([1, 1])
    with col_ct_add:
        if st.button("增加", key="add_counter_btn", use_container_width=True):
            v = (new_counter or "").strip()
            if v:
                if v not in data["counters"]:
                    data["counters"].append(v)
                    st.session_state.list_dirty = True
                    st.success("已加入報到櫃台（尚未保存）。")
                else:
                    st.info("此報到櫃台已存在。")
                st.session_state["new_counter"] = ""
            else:
                st.warning("請輸入報到櫃台名稱。")
    with col_ct_del:
        if st.button("刪除", key="del_counter_btn", use_container_width=True):
            v = (del_counter or "").strip()
            if v:
                if v in data["counters"]:
                    data["counters"] = [x for x in data["counters"] if x != v]
                    st.session_state.list_dirty = True
                    st.success("已刪除報到櫃台（尚未保存）。")
                else:
                    st.info("此報到櫃台不存在。")
            else:
                st.warning("請先選擇要刪除的報到櫃台。")

    st.divider()

    if st.button("保存鍵", type="primary", use_container_width=True):
        if st.session_state.list_dirty:
            save_data(data)
            st.session_state.list_dirty = False
            st.success("✅ 已保存清單變更。")
        else:
            st.info("目前沒有待保存的變更。")


# ══════════════════════════════════════════════════════════════════
#  CSS 美化
# ══════════════════════════════════════════════════════════════════
if page == "後台管理":
    render_admin_panel()
    st.stop()

st.markdown(
    """
<style>
  [data-testid="stAppViewContainer"] { background: #f9fbff; }
  /* 手機上避免文字消失：強制表單區文字顏色 */
  [data-testid="stAppViewContainer"] p,
  [data-testid="stAppViewContainer"] label,
  [data-testid="stAppViewContainer"] li,
  [data-testid="stAppViewContainer"] span,
  [data-testid="stAppViewContainer"] div {
    color: #111827;
  }
  /* Caption / 說明文字用深灰 */
  [data-testid="stAppViewContainer"] .stCaption,
  [data-testid="stAppViewContainer"] [data-testid="stCaptionContainer"] {
    color: #374151 !important;
  }
  /* 讓輸入區有明顯底色區分（可編輯 vs 不可編輯） */
  div[data-testid="stTextInput"] input,
  div[data-testid="stTextArea"] textarea,
  div[data-testid="stSelectbox"] div[role="combobox"],
  div[data-testid="stNumberInput"] input {
    background: #fffaf0 !important;   /* 更亮的淺米：可輸入 */
    border: 1px solid rgba(0, 184, 212, .35) !important;
    border-radius: 10px !important;
    color: #111 !important;          /* 文字改黑色，清楚可讀 */
  }
  /* disabled（例如自動生成的報到時間） */
  div[data-testid="stTextInput"] input:disabled,
  div[data-testid="stTextArea"] textarea:disabled,
  div[data-testid="stNumberInput"] input:disabled {
    background: #f1f6ff !important;   /* 更亮的淺藍：不可編輯/自動 */
    color: #111827 !important;
    -webkit-text-fill-color: #111827 !important; /* iOS/LINE 內建瀏覽器 */
    opacity: 1 !important;                        /* 避免 disabled 自動降透明 */
  }
  /* 下拉選單展開的選項列表底色 */
  div[role="listbox"] { background: #fff !important; }
  .card {
    background: white;
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
    border: 1px solid rgba(0, 0, 0, .04);
    box-shadow: 0 6px 18px rgba(16, 24, 40, .06);
  }
  .section-title {
    font-size: 1rem;
    font-weight: 700;
    color: #0077ff;
    margin-bottom: .6rem;
    letter-spacing: .03em;
  }
  .notice-bar {
    background: #fff7cc;
    border-left: 6px solid #ffb300;
    border-radius: 8px;
    padding: .8rem 1.2rem;
    font-size: .9rem;
    color: #7a5c00;
    margin-bottom: 1rem;
  }
  .preview-box {
    background: #effdfc;
    border: 1.5px solid #00b8d4;
    border-radius: 12px;
    padding: .75rem 1rem;
    font-family: 'Courier New', monospace;
    font-size: .9rem;
    white-space: pre-wrap;
    line-height: 1.45;
    color: #083344;
  }
  .copy-btn {
    display: inline-flex; align-items: center; justify-content: center; gap: .5rem;
    background: linear-gradient(135deg,#25d366,#128c7e);
    color: white; border: none; border-radius: 10px;
    padding: .65rem 1.6rem; font-size: 1rem; font-weight: 700;
    cursor: pointer; width: 100%; justify-content: center;
    transition: opacity .2s;
  }
  .copy-btn:hover { opacity: .88; }
  .copy-btn:active { opacity: .7; }
</style>
""",
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════
#  頁首
# ══════════════════════════════════════════════════════════════════
st.markdown(
    """
<div style='background:linear-gradient(90deg,#0077ff,#00b8d4);
            padding:1.1rem 1.8rem;border-radius:14px;margin-bottom:1rem'>
  <h1 style='color:white;margin:0;font-size:1.8rem'>📋 行程報到單產生器</h1>
  <p style='color:rgba(255,255,255,.85);margin:.25rem 0 0;font-size:.9rem'>
    填寫資訊 → 一鍵複製 → 傳送 LINE 給客人
  </p>
</div>
""",
    unsafe_allow_html=True,
)

# 頂部注意事項
st.markdown(f"<div class='notice-bar'>⚠️ {NOTICE_TEXT}</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  表單區
# ══════════════════════════════════════════════════════════════════

# ── ① 日期 & 時間 ─────────────────────────────────────────────────
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">📅 日期 ＆ 時間</div>', unsafe_allow_html=True)

col_d, col_ci, col_dep = st.columns([2, 1, 1])
with col_d:
    sel_date = st.date_input("日期", value=date.today(), label_visibility="visible", key="sel_date")
    dt = day_type(sel_date)
    st.markdown(
        f"<span style='font-size:1rem;font-weight:700'>📆 {sel_date.strftime('%Y/%m/%d')}</span>",
        unsafe_allow_html=True,
    )
with col_ci:
    st.markdown("🕐 **報到時間**")
    st.caption("自動生成：出發時間 - 30 分（例如 19:30 → 19:00抵達）")
    # 依需求：報到時間 = 出發時間 - 30 分（自動生成）
    st.text_input(
        "報到時間（自動：出發時間 - 30 分）",
        value=st.session_state.get("checkin_auto", ""),
        disabled=True,
        label_visibility="visible",
    )
with col_dep:
    st.markdown("🚢 **出發時間**")
    st.caption("手動輸入：19:30 或 1930")
    depart_t = st.text_input(
        "出發時間（手動輸入，例如 19:00 或 1900）",
        value="09:00",
        label_visibility="visible",
        key="depart_manual",
    )
    ok, _, _ = parse_hhmm(depart_t)
    if (depart_t or "").strip() and not ok:
        st.session_state["checkin_auto"] = ""
        st.error("出發時間格式錯誤：請輸入 19:30 或 1930。")
        if st.session_state.last_valid_depart:
            if st.button("返回上一次正確的出發時間", use_container_width=True):
                st.session_state["depart_manual"] = st.session_state.last_valid_depart
                st.rerun()
    else:
        st.session_state.last_valid_depart = (depart_t or "").strip()
        checkin_auto = checkin_display_from_depart(depart_t)
        st.session_state["checkin_auto"] = checkin_auto
        if checkin_auto:
            st.caption(f"報到時間（自動）：{checkin_auto}")
st.markdown("</div>", unsafe_allow_html=True)

# 報到櫃台
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">🏢 報到櫃台</div>', unsafe_allow_html=True)
counter_options = ["（輸入新櫃台）"] + list(data.get("counters", []))
counter_choice = st.selectbox(
    "選擇或新增報到櫃台",
    counter_options,
    label_visibility="visible",
    key="counter_choice",
)
if counter_choice == "（輸入新櫃台）":
    counter = st.text_input(
        "報到櫃台名稱",
        placeholder="例：櫃台A / 第3櫃台 / 報到中心",
        label_visibility="visible",
        key="counter_new",
    )
else:
    counter = counter_choice
    st.info(f"已選歷史報到櫃台：**{counter}**")
st.markdown("</div>", unsafe_allow_html=True)

# ── ② 行程 ────────────────────────────────────────────────────────
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">🗺️ 行程</div>', unsafe_allow_html=True)

iti_options = ["（輸入新行程）"] + data["itineraries"]
iti_choice = st.selectbox("選擇或新增行程", iti_options, label_visibility="collapsed", key="iti_choice")
if iti_choice == "（輸入新行程）":
    itinerary = st.text_input(
        "行程名稱",
        placeholder="例：小琉球半日浮潛",
        label_visibility="collapsed",
        key="itinerary_new",
    )
else:
    itinerary = iti_choice
    st.info(f"已選歷史行程：**{itinerary}**")
st.markdown("</div>", unsafe_allow_html=True)

# ── ③ 旅客姓名 ───────────────────────────────────────────────────
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">🙍 旅客姓名</div>', unsafe_allow_html=True)

passenger_name = st.text_input(
    "旅客姓名",
    placeholder="例：王小明",
    label_visibility="visible",
    key="passenger_name",
)
st.markdown("</div>", unsafe_allow_html=True)

# ── ③ 人數 ────────────────────────────────────────────────────────
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">👥 人數</div>', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
adults = c1.number_input("成人 👨", min_value=0, max_value=99, value=1, step=1, key="adults")
children = c2.number_input("兒童 🧒", min_value=0, max_value=99, value=0, step=1, key="children")
infants = c3.number_input("幼兒 👶", min_value=0, max_value=99, value=0, step=1, key="infants")
total = adults + children + infants
st.caption(f"合計：**{total} 人**（成人 {adults}、兒童 {children}、幼兒 {infants}）")
st.markdown("</div>", unsafe_allow_html=True)

# ── ④ 島上交通 ────────────────────────────────────────────────────
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">🛵 島上交通</div>', unsafe_allow_html=True)

island_transport = st.selectbox(
    "島上交通",
    ["機車", "導覽車", "無"],
    key="island_transport",
)
scooter_count = 0
if island_transport == "機車":
    scooter_count = st.number_input(
        "機車台數",
        min_value=1,
        max_value=99,
        value=1,
        step=1,
        key="scooter_count",
    )

st.markdown("</div>", unsafe_allow_html=True)

# ── ⑤ 地點 ────────────────────────────────────────────────────────
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">📍 報到地點</div>', unsafe_allow_html=True)

loc_options = ["（輸入新地點）"] + list(data["locations"].keys())
loc_choice = st.selectbox("選擇或新增報到地點", loc_options, label_visibility="collapsed", key="loc_choice")

# 修正：避免在「選擇歷史地點」時 custom_url 未定義
custom_url = ""

if loc_choice == "（輸入新地點）":
    loc_name = st.text_input(
        "報到地點名稱",
        placeholder="例：小琉球花瓶岩碼頭",
        label_visibility="collapsed",
        key="loc_name_new",
    )
    auto_url = map_url(loc_name) if loc_name else ""
    custom_url = st.text_input(
        "自訂地圖網址（選填，留空自動產生）",
        value="",
        placeholder="https://maps.google.com/...",
        key="loc_custom_url",
    )
    loc_url = custom_url if custom_url else auto_url
    if loc_name and loc_url:
        st.markdown(
            f"🗺️ <a href='{loc_url}' target='_blank' style='color:#1a6cf5'>{loc_url}</a>",
            unsafe_allow_html=True,
        )
else:
    loc_name = loc_choice
    st.info(f"已選歷史報到地點：**{loc_name}**")
    loc_url = data["locations"].get(loc_name, "") or map_url(loc_name)
    if loc_name and loc_url:
        st.markdown(
            f"🗺️ <a href='{loc_url}' target='_blank' style='color:#1a6cf5'>{loc_url}</a>",
            unsafe_allow_html=True,
        )
st.markdown("</div>", unsafe_allow_html=True)

# ── ⑥ 備註 & 旅行社 ──────────────────────────────────────────────
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">📝 備註 ＆ 旅行社</div>', unsafe_allow_html=True)

note = st.text_area(
    "備註（可不填）",
    placeholder="例：請攜帶毛巾、防曬乳……",
    height=90,
    label_visibility="collapsed",
    key="note",
)

agency_options = ["（輸入旅行社名稱）"] + data["agencies"]
agency_choice = st.selectbox("旅行社", agency_options, label_visibility="collapsed", key="agency_choice")
if agency_choice == "（輸入旅行社名稱）":
    agency = st.text_input(
        "旅行社名稱",
        placeholder="例：陽光旅遊",
        label_visibility="collapsed",
        key="agency_new",
    )
else:
    agency = agency_choice
    st.info(f"已選歷史旅行社：**{agency}**")

st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  產生行程報到單預覽 ＋ 複製
# ══════════════════════════════════════════════════════════════════
st.markdown("---")

depart_ok, _, _ = parse_hhmm(depart_t)
if (depart_t or "").strip() and not depart_ok:
    st.info("請先修正出發時間格式，或按「返回上一次正確的出發時間」。")
    st.stop()

msg = build_message(
    sel_date,
    st.session_state.get("checkin_auto", ""),
    depart_t,
    counter,
    itinerary,
    adults,
    children,
    infants,
    note,
    loc_name,
    loc_url,
    agency,
    passenger_name,
    island_transport,
    int(scooter_count) if island_transport == "機車" else 0,
)

st.markdown("### 📄 行程報到單預覽")
st.markdown(f'<div class="preview-box">{msg}</div>', unsafe_allow_html=True)

# ── 儲存 + 複製 按鈕列 ──────────────────────────────────────────
btn_save, btn_space = st.columns([1, 2])

with btn_save:
    if st.button("💾 儲存此行程資料", use_container_width=True):
        changed = False
        if itinerary and itinerary not in data["itineraries"]:
            data["itineraries"].append(itinerary)
            changed = True
        if counter and counter not in data.get("counters", []):
            data["counters"].append(counter)
            changed = True
        if loc_name:
            if loc_name not in data["locations"]:
                data["locations"][loc_name] = loc_url
                changed = True
            elif custom_url:
                data["locations"][loc_name] = custom_url
                changed = True
        if agency and agency not in data["agencies"]:
            data["agencies"].append(agency)
            changed = True
        if changed:
            save_data(data)
            st.success("✅ 資料已儲存，下次使用時可從下拉選單選取！")
        else:
            st.info("資料已存在，無需重複儲存。")

# ── JavaScript 一鍵複製按鈕（LINE 貼上用）─────────────────────────
escaped = msg.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")

components.html(
    f"""
<style>
  .copy-btn {{
    display: flex; align-items: center; justify-content: center; gap: .5rem;
    background: linear-gradient(135deg,#25d366,#128c7e);
    color: white; border: none; border-radius: 12px;
    padding: .75rem 0; font-size: 1.05rem; font-weight: 700;
    cursor: pointer; width: 100%;
    box-shadow: 0 4px 12px rgba(37,211,102,.35);
    transition: transform .15s, opacity .15s;
  }}
  .copy-btn:hover  {{ opacity:.9; transform:translateY(-1px); }}
  .copy-btn:active {{ opacity:.7; transform:translateY(0); }}
  .done-msg {{
    text-align:center; color:#128c7e;
    font-size:.95rem; font-weight:600; margin-top:.5rem; display:none;
  }}
</style>

<button class="copy-btn" onclick="copyMsg()">
  📲 &nbsp; 複製行程報到單（貼到 LINE 傳給客人）
</button>
<div class="done-msg" id="doneMsg">✅ 已複製！請開啟 LINE 貼上傳送 🙌</div>

<script>
function copyMsg() {{
  const text = `{escaped}`;
  if (navigator.clipboard && navigator.clipboard.writeText) {{
    navigator.clipboard.writeText(text).then(() => showDone());
  }} else {{
    // fallback
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity  = '0';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    showDone();
  }}
}}
function showDone() {{
  const el = document.getElementById('doneMsg');
  el.style.display = 'block';
  setTimeout(() => {{ el.style.display = 'none'; }}, 3000);
}}
</script>
""",
    height=100,
)

# ══════════════════════════════════════════════════════════════════
#  底部固定注意事項
# ══════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown(
    f"""
<div style='background:#fff8e1;border:1.5px solid #ffc107;border-radius:12px;
            padding:1rem 1.5rem;font-size:.92rem;color:#7a5c00;text-align:center'>
  <b>📢 注意事項</b><br><br>
  {NOTICE_TEXT}
</div>
""",
    unsafe_allow_html=True,
)
