import streamlit as st
import json, os, urllib.parse
import uuid
import re
from datetime import date, datetime, timedelta
from io import BytesIO
import streamlit.components.v1 as components
import pandas as pd
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    HAS_REPORTLAB = True
except ImportError:
    canvas = None  # type: ignore
    A4 = None  # type: ignore
    HAS_REPORTLAB = False
try:
    import holidays
except Exception:
    holidays = None

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
QUOTE_HISTORY_FILE = "quote_history.json"
WEEKDAY_ZH = ["一", "二", "三", "四", "五", "六", "日"]
NOTICE_TEXT = (
    "注意事項：限定為當天航班使用。不得退改期。"
    "當日當班未到視同放棄。恕無法退款。"
    "請在開船前 20 分鐘至報到地點。"
    "請遵守行程安全指示講解。違規者自行負責。"
)

THEME_PRESETS = {
    "溫柔奶茶粉": {
        "app_bg": "#fff7fb",
        "input_bg": "#fff9fc",
        "input_border": "#fbcfe8",
        "disabled_bg": "#fdf2f8",
        "disabled_text": "#831843",
        "card_border": "#fbcfe8",
        "card_shadow": "rgba(236, 72, 153, .08)",
        "section_title": "#be185d",
        "notice_bg": "#fff1f2",
        "notice_border": "#fb7185",
        "notice_text": "#9f1239",
        "preview_bg": "#fff1f8",
        "preview_border": "#f9a8d4",
        "preview_text": "#831843",
        "hero_from": "#ec4899",
        "hero_to": "#fb7185",
        "link": "#db2777",
        "copy_from": "#f472b6",
        "copy_to": "#fb7185",
        "copy_shadow": "rgba(236,72,153,.35)",
        "copy_done": "#be185d",
    },
    "薰衣草紫": {
        "app_bg": "#faf7ff",
        "input_bg": "#fcfbff",
        "input_border": "#ddd6fe",
        "disabled_bg": "#f5f3ff",
        "disabled_text": "#4c1d95",
        "card_border": "#ddd6fe",
        "card_shadow": "rgba(124, 58, 237, .10)",
        "section_title": "#6d28d9",
        "notice_bg": "#f5f3ff",
        "notice_border": "#a78bfa",
        "notice_text": "#5b21b6",
        "preview_bg": "#f5f3ff",
        "preview_border": "#c4b5fd",
        "preview_text": "#4c1d95",
        "hero_from": "#8b5cf6",
        "hero_to": "#a78bfa",
        "link": "#7c3aed",
        "copy_from": "#a78bfa",
        "copy_to": "#8b5cf6",
        "copy_shadow": "rgba(124,58,237,.35)",
        "copy_done": "#6d28d9",
    },
    "薄荷綠": {
        "app_bg": "#f3fffb",
        "input_bg": "#f8fffd",
        "input_border": "#a7f3d0",
        "disabled_bg": "#ecfdf5",
        "disabled_text": "#065f46",
        "card_border": "#a7f3d0",
        "card_shadow": "rgba(16, 185, 129, .12)",
        "section_title": "#047857",
        "notice_bg": "#ecfeff",
        "notice_border": "#5eead4",
        "notice_text": "#0f766e",
        "preview_bg": "#ecfdf5",
        "preview_border": "#6ee7b7",
        "preview_text": "#065f46",
        "hero_from": "#10b981",
        "hero_to": "#14b8a6",
        "link": "#0f766e",
        "copy_from": "#34d399",
        "copy_to": "#14b8a6",
        "copy_shadow": "rgba(16,185,129,.35)",
        "copy_done": "#047857",
    },
    "蜜桃橘": {
        "app_bg": "#fff9f5",
        "input_bg": "#fffdfb",
        "input_border": "#fed7aa",
        "disabled_bg": "#fff7ed",
        "disabled_text": "#9a3412",
        "card_border": "#fdba74",
        "card_shadow": "rgba(249, 115, 22, .12)",
        "section_title": "#c2410c",
        "notice_bg": "#fff7ed",
        "notice_border": "#fb923c",
        "notice_text": "#9a3412",
        "preview_bg": "#fff7ed",
        "preview_border": "#fdba74",
        "preview_text": "#9a3412",
        "hero_from": "#fb923c",
        "hero_to": "#f97316",
        "link": "#c2410c",
        "copy_from": "#fb923c",
        "copy_to": "#f97316",
        "copy_shadow": "rgba(249,115,22,.35)",
        "copy_done": "#c2410c",
    },
    "天空藍": {
        "app_bg": "#f4faff",
        "input_bg": "#f8fcff",
        "input_border": "#bae6fd",
        "disabled_bg": "#eef8ff",
        "disabled_text": "#0c4a6e",
        "card_border": "#7dd3fc",
        "card_shadow": "rgba(14, 165, 233, .12)",
        "section_title": "#0369a1",
        "notice_bg": "#f0f9ff",
        "notice_border": "#38bdf8",
        "notice_text": "#075985",
        "preview_bg": "#eef8ff",
        "preview_border": "#7dd3fc",
        "preview_text": "#0c4a6e",
        "hero_from": "#38bdf8",
        "hero_to": "#0ea5e9",
        "link": "#0284c7",
        "copy_from": "#38bdf8",
        "copy_to": "#0ea5e9",
        "copy_shadow": "rgba(14,165,233,.35)",
        "copy_done": "#0369a1",
    },
    "奶油黃": {
        "app_bg": "#fffdf2",
        "input_bg": "#fffef7",
        "input_border": "#fde68a",
        "disabled_bg": "#fefce8",
        "disabled_text": "#854d0e",
        "card_border": "#fcd34d",
        "card_shadow": "rgba(234, 179, 8, .12)",
        "section_title": "#a16207",
        "notice_bg": "#fefce8",
        "notice_border": "#facc15",
        "notice_text": "#854d0e",
        "preview_bg": "#fefce8",
        "preview_border": "#fcd34d",
        "preview_text": "#713f12",
        "hero_from": "#facc15",
        "hero_to": "#eab308",
        "link": "#a16207",
        "copy_from": "#facc15",
        "copy_to": "#eab308",
        "copy_shadow": "rgba(234,179,8,.35)",
        "copy_done": "#a16207",
    },
}

FIXED_ITINERARIES = [
    "南方4島+東吉.七美登島.藍洞",
    "七美單程",
    "望安單程",
    "薰衣草浮潛+七美",
    "東嶼坪登島+七美",
    "吉貝來回",
    "驚豔吉貝",
    "吉貝+目斗嶼",
    "吉貝小玩",
    "吉貝輕旅行",
    "北海1日遊",
    "北海跳島1日遊-市區出航",
    "黃昏之旅-市區出航",
    "吉貝8合1水上加購",
    "精選東海",
    "超值東海",
    "東海半日遊",
    "星空之旅",
    "與龍共舞-夕陽之約",
    "員貝耍廢1日遊",
    "悠遊員貝1日遊",
    "員貝海牧之旅",
    "員貝海牧+玩水之旅",
    "海底漫步",
    "浮潛",
    "競速SUP",
    "漁人潮間帶",
    "海漫+浮潛",
    "海洋牧場",
    "夕遊海皇海牧+夜釣",
    "夕遊海皇海牧+夜釣+煙火",
    "夜釣小管",
    "夜釣小管+煙火",
    "煙火船",
    "七美煙火",
    "望安煙火",
    "吉貝煙火",
    "金色雙島",
    "風帆三合1",
    "獨木舟跨島",
    "石斑豐魚季半日遊",
    "忘憂島1日遊",
    "鉅航龍蝦島1日遊",
    "鉅航1日遊A",
    "鉅航半日遊B",
    "鉅航半日遊B1",
    "鉅航樂活遊C行程",
    "銀海超值1日遊",
    "銀海遨遊東海B行程",
    "銀海海田夢幻C行程",
    "銀海浪漫之旅",
    "銀海龍蝦島",
    "盛夏育樂",
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
FIXED_COUNTERS = [
    "海安育樂",
    "金八達育樂",
    "得意育樂",
    "和慶海洋牧場",
    "海上皇宮",
    "小丑魚",
    "新揚育樂",
    "戀夏育樂",
    "鉅航育樂",
    "銀海育樂",
    "大姐燒烤",
    "夏日燒烤",
    "瘋燒烤",
    "南碼燒烤",
    "南海燒烤",
    "369燒烤",
]

AIRPORT_OPTIONS = ["台北", "高雄", "台中", "台南", "嘉義", "花蓮", "台東", "金門", "澎湖"]
AIRLINE_OPTIONS = ["華信航空", "立榮航空"]

# 票價表：各出發地 × 票種 → (單程, 回程, 總計)。單位：元。可手動改下方輸入欄覆寫。
FARE_HUAXIN = {
    "台北": {
        "成人": (2234, 2128, 4362),
        "兒童": (1676, 1596, 3272),
        "敬老": (1117, 1064, 2181),
    },
    "高雄": {
        "成人": (1911, 1820, 3731),
        "兒童": (1433, 1365, 2798),
        "敬老": (956, 910, 1866),
    },
    "台中": {
        "成人": (1668, 1589, 3257),
        "兒童": (1251, 1192, 2443),
        "敬老": (834, 795, 1629),
    },
}

FARE_UNI = {
    "台北": {
        "成人": (2197, 2092, 4289),
        "兒童": (1868, 1779, 3647),
        "敬老": (1099, 1046, 2145),
    },
    "高雄": {
        "成人": (1812, 1726, 3538),
        "兒童": (1541, 1468, 3009),
        "敬老": (906, 863, 1769),
    },
    "台中": {
        "成人": (1705, 1624, 3329),
        "兒童": (1450, 1381, 2831),
        "敬老": (853, 812, 1665),
    },
    "台南": {
        "成人": (1643, 1565, 3208),
        "兒童": (1397, 1331, 2728),
        "敬老": (822, 783, 1605),
    },
    "嘉義": {
        "成人": (1671, 1591, 3262),
        "兒童": (1421, 1353, 2774),
        "敬老": (836, 796, 1632),
    },
}

HOLIDAY_TABLE_ROWS = [
    {"連假": "清明", "日期": "4/2 - 4/6"},
    {"連假": "端午", "日期": "6/19 - 6/21"},
    {"連假": "中秋", "日期": "9/25 - 9/28"},
    {"連假": "國慶", "日期": "10/9 - 10/11"},
]

# 船票表列：全票 成/兒/敬；半票（敬·兒·愛）
BOAT_FARE_ADULT = 1300
BOAT_FARE_CHILD = 1500
BOAT_FARE_SENIOR = 1700
BOAT_FARE_HALF = 975

# ══════════════════════════════════════════════════════════════════
#  後台維護用：票價/費用預設資料（可由「後台管理」覆寫）
# ══════════════════════════════════════════════════════════════════
def convert_city_table_to_backend_flight_fares(city_table: dict) -> dict:
    """
    將既有的「出發地 -> 票種 -> (單程, 回程, 總計)」轉成後台可編輯格式：
    出發地 -> 票種 -> {out, back}
    """
    out: dict = {}
    for airport, kinds in city_table.items():
        out[airport] = {}
        for label in ("成人", "兒童", "敬老"):
            if label not in kinds:
                continue
            s, r, _tot = kinds[label]
            out[airport][label] = {"out": int(s), "back": int(r)}
    return out


def default_flight_fares() -> dict:
    return {
        "華信航空": convert_city_table_to_backend_flight_fares(FARE_HUAXIN),
        "立榮航空": convert_city_table_to_backend_flight_fares(FARE_UNI),
    }


def default_boat_fares() -> dict:
    # 舊版「半票」按鈕：兒/敬 = 975，成人 = 1300（仍維持成人全票）
    return {
        "full": {"adult": BOAT_FARE_ADULT, "child": BOAT_FARE_CHILD, "senior": BOAT_FARE_SENIOR},
        "half": {"adult": BOAT_FARE_ADULT, "child": BOAT_FARE_HALF, "senior": BOAT_FARE_HALF},
    }


def default_moto_car_fares() -> dict:
    # 1~6 人方案：對應「機車/汽車手動費用」輸入欄的預設總價
    return {"moto_by_people": [0] * 7, "car_by_people": [0] * 7}


def ensure_data_price_defaults(d: dict) -> None:
    if not d.get("flight_fares"):
        d["flight_fares"] = default_flight_fares()
    if not d.get("boat_fares"):
        d["boat_fares"] = default_boat_fares()
    if not d.get("moto_car_fares"):
        d["moto_car_fares"] = default_moto_car_fares()

    # 容錯：確保陣列長度正確
    moto = d.get("moto_car_fares", {}).get("moto_by_people")
    car = d.get("moto_car_fares", {}).get("car_by_people")
    if not isinstance(moto, list) or len(moto) < 7:
        current = moto if isinstance(moto, list) else []
        d["moto_car_fares"]["moto_by_people"] = (current + [0] * 7)[:7]
    if not isinstance(car, list) or len(car) < 7:
        current = car if isinstance(car, list) else []
        d["moto_car_fares"]["car_by_people"] = (current + [0] * 7)[:7]


def _default_data() -> dict:
    return {"itineraries": [], "locations": {}, "agencies": [], "counters": []}


# ══════════════════════════════════════════════════════════════════
#  資料 IO
# ══════════════════════════════════════════════════════════════════
def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return _default_data()


def save_data(d: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def load_quote_history() -> list:
    if os.path.exists(QUOTE_HISTORY_FILE):
        with open(QUOTE_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_quote_history(rows: list):
    with open(QUOTE_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


QUOTE_SNAPSHOT_KEYS = (
    "quote_go_date",
    "quote_back_date",
    "q_airline",
    "q_airport",
    "q_travel_people",
    "f_count_adult",
    "f_count_child",
    "f_count_senior",
    "f_out_adult",
    "f_out_child",
    "f_out_senior",
    "f_back_adult",
    "f_back_child",
    "f_back_senior",
    "b_count_adult",
    "b_count_child",
    "b_count_senior",
    "b_price_adult",
    "b_price_child",
    "b_price_senior",
    "share_manual_n",
    "divide_by",
    "q_customer_name",
    "q_customer_phone",
    "q_customer_note",
    "q_customer_source",
    "sum_hotel_nights",
    "sum_hotel_people",
    "sum_moto_days",
    "sum_moto_people",
    "sum_moto_units",
    "sum_line_hotel_custom",
    "sum_hotel_booking_text",
    "sum_line_moto_custom",
    "q_discount_amount",
) + tuple(f"hotel_{i}" for i in range(1, 7)) + tuple(f"moto_{i}" for i in range(1, 7)) + tuple(f"car_{i}" for i in range(1, 7))


def snapshot_quote_form_from_session() -> dict:
    snap = {}
    for k in QUOTE_SNAPSHOT_KEYS:
        if k not in st.session_state:
            continue
        v = st.session_state[k]
        if isinstance(v, date):
            snap[k] = v.isoformat()
        elif isinstance(v, (int, float, str, bool)) or v is None:
            snap[k] = v
        else:
            snap[k] = str(v)
    return snap


def apply_quote_snapshot(snap: dict) -> None:
    if not snap:
        return
    for k, v in snap.items():
        if k not in QUOTE_SNAPSHOT_KEYS:
            continue
        if k in ("quote_go_date", "quote_back_date") and isinstance(v, str):
            try:
                v = date.fromisoformat(v)
            except ValueError:
                continue
        st.session_state[k] = v


def history_item_label(h: dict) -> str:
    sid = h.get("quote_id", "—")
    name = h.get("customer_name", "") or "未命名"
    ts = (h.get("saved_at") or h.get("created_at") or "")[:16]
    return f"{ts or '—'}｜{name}｜{sid}"


def flatten_history_for_df(rows: list) -> list:
    out = []
    for h in rows:
        row = {k: v for k, v in h.items() if k != "snapshot"}
        out.append(row)
    return out


FLAT_TO_SNAPSHOT = {
    "go_date": "quote_go_date",
    "back_date": "quote_back_date",
    "airline": "q_airline",
    "depart_airport": "q_airport",
    "travel_people": "q_travel_people",
    "divide_by": "divide_by",
    "customer_name": "q_customer_name",
    "customer_phone": "q_customer_phone",
    "customer_note": "q_customer_note",
    "customer_source": "q_customer_source",
    "flight_out_total": None,
}


def history_item_to_snapshot(h: dict) -> dict:
    snap = dict(h.get("snapshot") or {})
    for flat_k, snap_k in FLAT_TO_SNAPSHOT.items():
        if snap_k is None:
            continue
        if snap_k not in snap and flat_k in h and h[flat_k] is not None:
            snap[snap_k] = h[flat_k]
    return snap


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
if "_moto_units_default_migrated" not in st.session_state:
    # 舊版本「機車臺數」預設是 1，首次載入時自動改成 0
    if st.session_state.get("sum_moto_units", None) == 1:
        st.session_state["sum_moto_units"] = 0
    st.session_state["_moto_units_default_migrated"] = True

data = st.session_state.data
data.setdefault("itineraries", [])
data.setdefault("locations", {})
data.setdefault("agencies", [])
data.setdefault("counters", [])
for _it in FIXED_ITINERARIES:
    if _it and _it not in data["itineraries"]:
        data["itineraries"].append(_it)
for _loc in FIXED_LOCATIONS:
    if _loc and _loc not in data["locations"]:
        data["locations"][_loc] = f"https://www.google.com/maps/search/{urllib.parse.quote(_loc)}"
for _ag in FIXED_TRAVEL_AGENCIES:
    if _ag and _ag not in data["agencies"]:
        data["agencies"].append(_ag)
for _ct in FIXED_COUNTERS:
    if _ct and _ct not in data["counters"]:
        data["counters"].append(_ct)
ensure_data_price_defaults(data)
data.setdefault("customer_sources", ["FB", "Instagram", "Google", "LINE", "轉介", "舊客回購"])
data.setdefault("customers", [])

page = st.sidebar.radio("功能選單", ["前台（產生行程報到單）", "後台管理"])
theme_names = list(THEME_PRESETS.keys())
if "ui_theme" not in st.session_state:
    st.session_state["ui_theme"] = "溫柔奶茶粉"
if "pinned_themes" not in st.session_state:
    st.session_state["pinned_themes"] = ["溫柔奶茶粉", "薰衣草紫", "薄荷綠"]
if "admin_authed" not in st.session_state:
    st.session_state["admin_authed"] = False


def _admin_password_from_secrets() -> str:
    try:
        return str(st.secrets.get("ADMIN_PASSWORD", "")).strip()
    except Exception:
        return ""


def _admin_gate() -> bool:
    pwd = _admin_password_from_secrets()
    if not pwd:
        st.warning("尚未設定後台密碼。請在 Streamlit secrets 設定 `ADMIN_PASSWORD`。")
        st.stop()
    entered = st.sidebar.text_input("後台密碼", type="password", key="admin_pwd_input")
    if st.sidebar.button("登入後台", key="admin_login_btn"):
        st.session_state["admin_authed"] = entered == pwd
        if st.session_state["admin_authed"]:
            st.sidebar.success("後台登入成功")
            st.rerun()
        st.sidebar.error("密碼錯誤")
    if st.session_state.get("admin_authed"):
        if st.sidebar.button("登出後台", key="admin_logout_btn"):
            st.session_state["admin_authed"] = False
            st.rerun()
        return True
    st.info("此區為管理後台，請先輸入密碼登入。")
    st.stop()
if page == "前台（產生行程報到單）":
    current_theme = st.session_state.get("ui_theme", "溫柔奶茶粉")
    if current_theme not in theme_names:
        current_theme = "溫柔奶茶粉"
    sidebar_theme = st.sidebar.selectbox(
        "前台色系",
        theme_names,
        index=theme_names.index(current_theme),
    )
    st.session_state["ui_theme"] = sidebar_theme
    pinned = st.sidebar.multiselect(
        "固定色系（快捷按鈕）",
        options=theme_names,
        default=[x for x in st.session_state.get("pinned_themes", []) if x in theme_names],
        max_selections=5,
        key="pinned_themes_selector",
    )
    st.session_state["pinned_themes"] = pinned or ["溫柔奶茶粉", "薰衣草紫", "薄荷綠"]
active_theme = THEME_PRESETS.get(st.session_state.get("ui_theme", "溫柔奶茶粉"), THEME_PRESETS["溫柔奶茶粉"])


# ══════════════════════════════════════════════════════════════════
#  工具函式
# ══════════════════════════════════════════════════════════════════
def map_url(place: str) -> str:
    # NOTE: 直接用「地點名稱」當查詢字串
    return f"https://www.google.com/maps/search/{urllib.parse.quote(place)}"


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


def parse_lodging_booking_text(raw_text: str) -> dict:
    text = (raw_text or "").strip()
    if not text:
        return {}

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    date_range = ""
    package_rooms = None
    double_rooms = 0
    quad_rooms = 0
    people = None
    contact_phone = ""
    contact_name = ""

    for ln in lines:
        if not date_range:
            m_date = re.search(r"(\d{1,2}\s*/\s*\d{1,2}\s*[-~～至]\s*\d{1,2}\s*/\s*\d{1,2})", ln)
            if m_date:
                date_range = re.sub(r"\s+", "", m_date.group(1))

        m_pkg = re.search(r"(\d+)\s*間\s*包棟", ln)
        if m_pkg:
            package_rooms = int(m_pkg.group(1))

        m_double = re.search(r"雙人\s*[*xX×]\s*(\d+)", ln)
        if m_double:
            double_rooms += int(m_double.group(1))

        m_quad = re.search(r"四人\s*[*xX×]\s*(\d+)", ln)
        if m_quad:
            quad_rooms += int(m_quad.group(1))

        if people is None:
            m_people = re.search(r"(\d+)\s*(?:位|人)", ln)
            if m_people:
                people = int(m_people.group(1))

        if not contact_phone:
            m_phone = re.search(r"(09\d{2}[-\s]?\d{3}[-\s]?\d{3})", ln)
            if m_phone:
                contact_phone = re.sub(r"[-\s]", "", m_phone.group(1))
                left = ln[: m_phone.start()].strip("：:，,　 ")
                if left:
                    contact_name = left

    room_parts = []
    if package_rooms is not None:
        room_parts.append(f"{package_rooms}間包棟")
    if double_rooms > 0:
        room_parts.append(f"雙人*{double_rooms}")
    if quad_rooms > 0:
        room_parts.append(f"四人*{quad_rooms}")

    out = {}
    if date_range:
        out["date_range"] = date_range
    if room_parts:
        out["room_desc"] = "＋".join(room_parts)
    if people is not None:
        out["people"] = int(people)
    if contact_name:
        out["contact_name"] = contact_name
    if contact_phone:
        out["contact_phone"] = contact_phone
    return out


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
    passenger_phone,
    island_transport,
    scooter_count,
) -> str:
    date_str = sel_date.strftime("%Y/%m/%d")
    lines = ["📋 行程報到單"]

    if date_str:
        lines.append(f"📅 日期：{date_str}")
    if str(passenger_name).strip():
        lines.append(f"🙍 旅客姓名：{passenger_name}")
    if str(passenger_phone).strip():
        lines.append(f"📞 旅客電話：{passenger_phone}")
    if str(checkin_t).strip():
        lines.append(f"🕐 報到時間：{checkin_t}")
    if str(depart_t).strip():
        lines.append(f"🚢 出發時間：{depart_t}")
    if str(itinerary).strip():
        lines.append(f"🗺️ 行程：{itinerary}")
    if str(loc_name).strip():
        lines.append(f"📍 報到地點：{loc_name}")
    if str(counter).strip():
        lines.append(f"🏢 報到櫃台：{counter}")

    if str(loc_url).strip():
        lines.append("🔗 地圖網址：")
        lines.append(loc_url)

    if island_transport == "機車":
        if int(scooter_count or 0) > 0:
            lines.append(f"🛵 島上交通：機車 {int(scooter_count)} 台")
    elif str(island_transport).strip() and island_transport != "無":
        lines.append(f"🛵 島上交通：{island_transport}")

    people_parts = []
    if int(adults or 0) > 0:
        people_parts.append(f"成人 {int(adults)} 位")
    if int(children or 0) > 0:
        people_parts.append(f"兒童 {int(children)} 位")
    if int(infants or 0) > 0:
        people_parts.append(f"幼兒 {int(infants)} 位")
    if people_parts:
        lines.append("👥 人數：" + "　".join(people_parts))

    if str(note).strip():
        lines.append(f"📝 備註：{note}")
    if str(agency).strip():
        lines.append(f"🏢 旅行社：{agency}")

    lines += ["", f"⚠️ {NOTICE_TEXT}"]
    return "\n".join(lines)


def render_admin_panel() -> None:
    st.markdown("## 後台管理")
    st.caption("在這裡可隨時更改/增加/刪除行程、報到地點、報到櫃台、旅行社清單。")

    # 備份/還原：避免重部署後資料遺失
    st.markdown("### 備份與還原")
    backup_json = json.dumps(data, ensure_ascii=False, indent=2)
    st.download_button(
        "下載目前清單備份（JSON）",
        data=backup_json.encode("utf-8"),
        file_name=f"quote_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        use_container_width=True,
    )
    uploaded = st.file_uploader("匯入備份 JSON（覆蓋目前清單）", type=["json"], key="import_quote_data")
    if uploaded is not None:
        try:
            obj = json.loads(uploaded.getvalue().decode("utf-8"))
            obj.setdefault("itineraries", [])
            obj.setdefault("locations", {})
            obj.setdefault("agencies", [])
            obj.setdefault("counters", [])
            merge_fixed_items(obj)
            st.session_state.data = obj
            save_data(st.session_state.data)
            st.session_state.list_dirty = False
            st.success("已匯入並保存備份資料。")
            st.rerun()
        except Exception as e:
            st.error(f"匯入失敗：{e}")

    st.caption("可在下方調整行程順序（前台下拉選單會依此順序顯示）。")
    if data["itineraries"]:
        move_it = st.selectbox(
            "排序行程（選一筆後按按鈕）",
            options=data["itineraries"],
            key="move_itinerary",
        )
        idx = data["itineraries"].index(move_it)
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            if st.button("置頂", key="it_move_top", use_container_width=True) and idx > 0:
                item = data["itineraries"].pop(idx)
                data["itineraries"].insert(0, item)
                st.session_state.list_dirty = True
                st.rerun()
        with s2:
            if st.button("上移", key="it_move_up", use_container_width=True) and idx > 0:
                data["itineraries"][idx - 1], data["itineraries"][idx] = (
                    data["itineraries"][idx],
                    data["itineraries"][idx - 1],
                )
                st.session_state.list_dirty = True
                st.rerun()
        with s3:
            if st.button("下移", key="it_move_down", use_container_width=True) and idx < len(data["itineraries"]) - 1:
                data["itineraries"][idx + 1], data["itineraries"][idx] = (
                    data["itineraries"][idx],
                    data["itineraries"][idx + 1],
                )
                st.session_state.list_dirty = True
                st.rerun()
        with s4:
            if st.button("置底", key="it_move_bottom", use_container_width=True) and idx < len(data["itineraries"]) - 1:
                item = data["itineraries"].pop(idx)
                data["itineraries"].append(item)
                st.session_state.list_dirty = True
                st.rerun()

        if st.button("一鍵恢復預設排序", key="it_restore_default_order", use_container_width=True):
            fixed = [x for x in FIXED_ITINERARIES if x in data["itineraries"]]
            custom = [x for x in data["itineraries"] if x not in FIXED_ITINERARIES]
            data["itineraries"] = fixed + custom
            st.session_state.list_dirty = True
            st.success("已恢復預設排序（自訂行程保留在後方）。")
            st.rerun()

    st.divider()

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


def is_rest_day(d: date, tw_holidays) -> bool:
    # 需求：平日=週一到週四；假日=週五到週日；連假含國定假日
    return d.weekday() >= 4 or (tw_holidays is not None and d in tw_holidays)


def count_day_types(start_date: date, end_date: date) -> dict:
    years = [start_date.year, end_date.year]
    tw_holidays = None
    if holidays is not None:
        try:
            tw_holidays = holidays.country_holidays("TW", years=years)
        except Exception:
            tw_holidays = None

    current = start_date
    weekday_count = 0
    holiday_count = 0
    rest_days = []
    while current <= end_date:
        if is_rest_day(current, tw_holidays):
            holiday_count += 1
            rest_days.append(current)
        else:
            weekday_count += 1
        current += timedelta(days=1)

    segments = []
    if rest_days:
        seg_start = rest_days[0]
        prev = rest_days[0]
        for d in rest_days[1:]:
            if (d - prev).days == 1:
                prev = d
            else:
                segments.append((seg_start, prev))
                seg_start = d
                prev = d
        segments.append((seg_start, prev))

    long_holidays = [x for x in segments if (x[1] - x[0]).days + 1 >= 3]
    return {
        "weekday_count": weekday_count,
        "holiday_count": holiday_count,
        "long_holidays": long_holidays,
    }


def fare_city_table_to_df(table: dict) -> pd.DataFrame:
    rows = []
    for city in sorted(table.keys()):
        kinds = table[city]
        for label in ("成人", "兒童", "敬老"):
            if label not in kinds:
                continue
            s, r, tot = kinds[label]
            rows.append(
                {
                    "出發地": city,
                    "票種": label,
                    "單程": s,
                    "回程": r,
                    "總計": tot,
                    "單/回/總": f"{s}/{r}/{tot}",
                }
            )
    return pd.DataFrame(rows)


def get_airline_city_table_for_preview(airline: str) -> dict:
    """
    轉成給 `fare_city_table_to_df()` 用的格式：
    出發地 -> 票種 -> (單程, 回程, 總計)
    """
    d = st.session_state.get("data") or {}
    flight_fares = d.get("flight_fares") or {}
    airline_tbl = flight_fares.get(airline) or {}
    if not airline_tbl:
        return FARE_HUAXIN if airline == "華信航空" else FARE_UNI

    out: dict = {}
    for airport, kinds in airline_tbl.items():
        out[airport] = {}
        for label in ("成人", "兒童", "敬老"):
            kind = (kinds or {}).get(label) or {}
            if "out" in kind and "back" in kind:
                s = int(kind.get("out", 0) or 0)
                r = int(kind.get("back", 0) or 0)
                out[airport][label] = (s, r, s + r)
    return out


def get_boat_fares_from_data() -> dict:
    d = st.session_state.get("data") or {}
    bf = d.get("boat_fares") or {}
    full = bf.get("full") or {}
    half = bf.get("half") or {}
    # 舊版：半票成人價仍為全票成人價
    return {
        "adult_full": int(full.get("adult", BOAT_FARE_ADULT) or 0),
        "child_full": int(full.get("child", BOAT_FARE_CHILD) or 0),
        "senior_full": int(full.get("senior", BOAT_FARE_SENIOR) or 0),
        "adult_half": int(half.get("adult", BOAT_FARE_ADULT) or 0),
        "child_half": int(half.get("child", BOAT_FARE_HALF) or 0),
        "senior_half": int(half.get("senior", BOAT_FARE_HALF) or 0),
    }


def get_ref_fare(airline: str, airport: str) -> dict | None:
    ap = (airport or "").replace("松山", "台北")
    d = st.session_state.get("data") or {}
    flight_fares = d.get("flight_fares") or {}
    airline_tbl = flight_fares.get(airline) or {}
    airport_tbl = airline_tbl.get(ap) or {}
    a = airport_tbl.get("成人") or {}
    c = airport_tbl.get("兒童") or {}
    sen = airport_tbl.get("敬老") or {}

    if all(k in a for k in ("out", "back")) and all(k in c for k in ("out", "back")) and all(k in sen for k in ("out", "back")):
        return {
            "f_out_adult": int(a.get("out", 0) or 0),
            "f_back_adult": int(a.get("back", 0) or 0),
            "f_out_child": int(c.get("out", 0) or 0),
            "f_back_child": int(c.get("back", 0) or 0),
            "f_out_senior": int(sen.get("out", 0) or 0),
            "f_back_senior": int(sen.get("back", 0) or 0),
        }

    # fallback：使用舊版硬編表
    tbl = FARE_HUAXIN if airline == "華信航空" else FARE_UNI
    row = tbl.get(ap)
    if not row:
        return None
    a2, c2, sen2 = row["成人"], row["兒童"], row["敬老"]
    return {
        "f_out_adult": a2[0],
        "f_back_adult": a2[1],
        "f_out_child": c2[0],
        "f_back_child": c2[1],
        "f_out_senior": sen2[0],
        "f_back_senior": sen2[1],
    }


def build_quote_record(payload: dict) -> dict:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {"created_at": now_str, **payload}


def build_quote_customer_summary(record: dict) -> str:
    """給客戶與 LINE：只顯示摘要（每人價格、折扣、總計），不含試算過程。"""

    def fmt_price(v):
        if v is None:
            return "—"
        if isinstance(v, float):
            return f"{round(v):,.0f}".replace(",", "，")
        if isinstance(v, int):
            return f"{v:,}".replace(",", "，")
        return str(v)

    nm = (record.get("customer_name") or "").strip()
    lines = [
        "📋 報價摘要（複製貼到 LINE）",
        f"客戶：{nm}" if nm else None,
        f"日期：{record.get('go_date', '')} ～ {record.get('back_date', '')}",
        "",
        record.get("summary_line_flight") or "機票來回",
    ]
    sh = (record.get("summary_line_hotel") or "").strip()
    if sh:
        lines.append(sh)
    sm = (record.get("summary_line_moto") or "").strip()
    if sm:
        lines.append(sm)
    lines.append("──────────")
    fa = int(record.get("fly_adult", 0) or 0)
    fc = int(record.get("fly_child", 0) or 0)
    fs = int(record.get("fly_senior", 0) or 0)
    lines.append(f"成人多少？　{fmt_price(record.get('net_adult')) if fa else '—'}")
    lines.append(f"兒童多少？　{fmt_price(record.get('net_child')) if fc else '—'}")
    lines.append(f"敬老多少？　{fmt_price(record.get('net_senior')) if fs else '—'}")
    disc = int(record.get("discount_amount", 0) or 0)
    lines.append(f"折扣　　-{fmt_price(disc)}" if disc else "折扣　　0")
    g_after = record.get("grand_after_discount")
    if g_after is None:
        g_after = record.get("grand_total")
    lines.append(f"總計　　{fmt_price(g_after)}")
    lines += ["", "※ 參考報價，以實際訂位／付款為準。"]
    return "\n".join(x for x in lines if x is not None)


def quote_to_pdf_bytes(record: dict) -> bytes:
    if not HAS_REPORTLAB or canvas is None or A4 is None:
        raise RuntimeError("reportlab 未安裝，無法產生 PDF")
    buf = BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 50
    lines = [
        f"Trip Quote - {record.get('created_at', '')}",
        f"Customer: {record.get('customer_name', '')} / {record.get('customer_phone', '')} / src:{record.get('customer_source', '')}",
        f"Date: {record.get('go_date', '')} -> {record.get('back_date', '')}",
        f"Airline: {record.get('airline', '')} / Airport: {record.get('depart_airport', '')}",
        f"Travel people: {record.get('travel_people', 0)}",
        f"Flight adult out/back/tot: {record.get('flight_adult_out', 0)}/{record.get('flight_adult_back', 0)}/{record.get('flight_adult_total', 0)}",
        f"Flight child out/back/tot: {record.get('flight_child_out', 0)}/{record.get('flight_child_back', 0)}/{record.get('flight_child_total', 0)}",
        f"Flight senior out/back/tot: {record.get('flight_senior_out', 0)}/{record.get('flight_senior_back', 0)}/{record.get('flight_senior_total', 0)}",
        f"Flight out/back/all: {record.get('flight_out_total', 0)}/{record.get('flight_back_total', 0)}/{record.get('flight_total', 0)}",
        f"Boat total: {record.get('boat_total', 0)}",
        f"Hotel total: {record.get('hotel_total', 0)}",
        f"Moto total: {record.get('moto_total', 0)}",
        f"Car total: {record.get('car_total', 0)}",
        f"Manual total: {record.get('manual_total', 0)}",
        f"Per adult personal: {record.get('personal_adult', 0):.2f}",
        f"Per child personal: {record.get('personal_child', 0):.2f}",
        f"Per senior personal: {record.get('personal_senior', 0):.2f}",
        f"Grand total: {record.get('grand_total', 0)}",
        f"Avg per person: {record.get('avg_total', 0):.2f}",
        f"Summary flight: {record.get('summary_line_flight', '')}",
        f"Summary hotel: {record.get('summary_line_hotel', '')}",
        f"Summary moto: {record.get('summary_line_moto', '')}",
        f"Discount: {record.get('discount_amount', 0)} / After: {record.get('grand_after_discount', 0)}",
        f"Net per adult/child/senior: {record.get('net_adult')}/{record.get('net_child')}/{record.get('net_senior')}",
    ]
    for line in lines:
        pdf.drawString(40, y, line)
        y -= 20
        if y < 50:
            pdf.showPage()
            y = height - 50
    pdf.save()
    data = buf.getvalue()
    buf.close()
    return data


def render_quote_app() -> None:
    pending_snap = st.session_state.pop("_pending_quote_snapshot", None)
    if pending_snap:
        apply_quote_snapshot(pending_snap)

    st.title("報價單 APP")
    st.caption("日期來回、平假日/連假判斷、機票依成人/兒童/敬老分開合計、分攤、儲存每一組客人、匯出")

    st.subheader("0) 已儲存報價組")
    _hist = load_quote_history()
    if not _hist:
        st.caption("尚無儲存紀錄。報價完成後可用下方「儲存此一組報價」。")
    else:
        rev = list(reversed(_hist))
        labels = [history_item_label(h) for h in rev]
        pick_i = st.selectbox("選擇一筆", range(len(labels)), format_func=lambda i: labels[i], key="saved_quote_pick")
        chosen = rev[pick_i] if _hist else None
        b0, b1, b2 = st.columns(3)
        with b0:
            if st.button("載入此組", use_container_width=True, key="btn_quote_load") and chosen:
                st.session_state["_pending_quote_snapshot"] = history_item_to_snapshot(chosen)
                st.rerun()
        with b1:
            if st.button("刪除此組", use_container_width=True, key="btn_quote_del") and chosen and _hist:
                del_idx = len(_hist) - 1 - pick_i
                if 0 <= del_idx < len(_hist):
                    _hist.pop(del_idx)
                    save_quote_history(_hist)
                st.success("已刪除。")
                st.rerun()
        with b2:
            if st.button("返回／清空表單", use_container_width=True, key="btn_quote_reset"):
                for k in QUOTE_SNAPSHOT_KEYS:
                    st.session_state.pop(k, None)
                st.rerun()

    st.subheader("1) 旅遊日期（來回）")
    c1, c2 = st.columns(2)
    with c1:
        go_date = st.date_input("出發日期", value=date.today(), key="quote_go_date")
    with c2:
        back_date = st.date_input("回程日期", value=date.today() + timedelta(days=1), key="quote_back_date")
    if back_date < go_date:
        st.error("回程日期不能早於出發日期。")
        st.stop()

    day_info = count_day_types(go_date, back_date)
    st.info(f"平日(一~四)：{day_info['weekday_count']} 天｜假日(五~日+國定假日)：{day_info['holiday_count']} 天")
    if day_info["long_holidays"]:
        for start_d, end_d in day_info["long_holidays"]:
            days = (end_d - start_d).days + 1
            st.warning(f"偵測到連續假期：{start_d.strftime('%Y/%m/%d')} ~ {end_d.strftime('%Y/%m/%d')}（{days}天）")
    else:
        st.caption("未偵測到 3 天以上連假。")

    st.subheader("1b) 客戶資料")
    cust_rows = data.get("customers", [])
    cust_labels = ["（不帶入）"] + [
        f"{c.get('name', '')}／{c.get('source', '')}／{c.get('departure', '')}" for c in cust_rows
    ]
    ci = st.selectbox("後台客人範本（於後台建立）", range(len(cust_labels)), format_func=lambda i: cust_labels[i], key="q_cust_pick")
    if st.button("帶入此客人（名稱·來源·出發地）", key="q_cust_apply"):
        if ci > 0 and cust_rows:
            c = cust_rows[ci - 1]
            st.session_state["q_customer_name"] = c.get("name", "")
            st.session_state["q_customer_source"] = c.get("source", "")
            dep = c.get("departure", "")
            if dep in AIRPORT_OPTIONS:
                st.session_state["q_airport"] = dep
            st.rerun()
    cnx1, cnx2 = st.columns(2)
    with cnx1:
        customer_name = st.text_input("客人姓名", key="q_customer_name")
    with cnx2:
        customer_phone = st.text_input("客人電話", key="q_customer_phone")
    src_opts = data.get("customer_sources", []) + ["其他（自填）"]
    src_sel = st.selectbox("客人來源", src_opts, key="q_customer_source_sel")
    if src_sel == "其他（自填）":
        customer_source = st.text_input("來源自填", key="q_customer_source")
    else:
        customer_source = src_sel
    customer_note = st.text_area("客戶備註", key="q_customer_note", height=70)

    with st.expander("📊 票價／連假報表（對應報表價錢，選看）", expanded=False):
        st.subheader("票價總表（單程／回程／總計）— 機票費用對應此報表")
        st.caption(
            "報價計算之機票，以下方報表數字為準；按「依票價表帶入」可自動對應航空公司、出發地之成／兒／敬單程與回程。"
            "若表上無您的航點，請自行輸入。實際售價仍以航空公司公告為準。"
        )
        bf = get_boat_fares_from_data()
        t1, t2 = st.tabs(["華信航空", "立榮航空"])
        with t1:
            st.markdown("**華信（單／回／總）** — 台北、高雄、台中")
            st.dataframe(
                fare_city_table_to_df(get_airline_city_table_for_preview("華信航空")),
                use_container_width=True,
                hide_index=True,
            )
        with t2:
            st.markdown("**立榮（單／回／總）** — 台北、高雄、台中、台南、嘉義")
            st.dataframe(
                fare_city_table_to_df(get_airline_city_table_for_preview("立榮航空")),
                use_container_width=True,
                hide_index=True,
            )

        st.subheader("連假與雜項")
        hc1, hc2 = st.columns(2)
        with hc1:
            st.markdown("**連假參考**")
            st.dataframe(pd.DataFrame(HOLIDAY_TABLE_ROWS), use_container_width=True, hide_index=True)
        with hc2:
            st.markdown("**船票參考**")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "項目": "船票（表列）",
                            "成人": bf["adult_full"],
                            "兒童": bf["child_full"],
                            "敬老": bf["senior_full"],
                        },
                        {
                            "項目": "半票（敬·兒·愛）",
                            "成人": "—",
                            "兒童": bf["child_half"],
                            "敬老": bf["senior_half"],
                        },
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )

    with st.expander("✏️ 費用試算（過程不顯示於下方摘要／LINE）", expanded=False):
        st.subheader("2) 航空票價（華信/立榮，來回分開計算）")
        a1, a2, a3 = st.columns(3)
        with a1:
            airline = st.selectbox("航空公司", AIRLINE_OPTIONS, key="q_airline")
        with a2:
            depart_airport = st.selectbox("出發地點", AIRPORT_OPTIONS, key="q_airport")
        with a3:
            travel_people = st.number_input("旅遊人數(1-6)", min_value=1, max_value=6, value=2, step=1, key="q_travel_people")

        st.markdown("**摘要用（LINE 抬頭；不影響試算數字）**")
        sh1, sh2, sh3 = st.columns(3)
        with sh1:
            sum_hotel_people = st.number_input(
                "住宿人數(摘要)",
                min_value=1,
                max_value=99,
                value=int(travel_people),
                step=1,
                key="sum_hotel_people",
            )
        with sh2:
            sum_hotel_nights = st.number_input("住宿晚數", min_value=1, max_value=99, value=2, step=1, key="sum_hotel_nights")
        with sh3:
            sum_line_hotel_custom = st.text_input("自訂住宿一行（可留空）", "", key="sum_line_hotel_custom")
        sum_hotel_booking_text = st.text_area(
            "住宿預定文字（可貼上多行，自動解析）",
            value=st.session_state.get("sum_hotel_booking_text", ""),
            key="sum_hotel_booking_text",
            height=100,
            placeholder="5/21-5/23\n8間包棟\n顏義國 0953871627\n24位\n或\n雙人*6\n四人*3",
        )
        st.caption("可解析：日期區間、包棟、雙人*幾、四人*幾、聯絡人電話、人數。")
        _preview_booking = parse_lodging_booking_text(sum_hotel_booking_text)
        if _preview_booking:
            preview_parts = []
            if _preview_booking.get("date_range"):
                preview_parts.append(f"日期：{_preview_booking.get('date_range')}")
            if _preview_booking.get("room_desc"):
                preview_parts.append(f"房型：{_preview_booking.get('room_desc')}")
            if _preview_booking.get("people") is not None:
                preview_parts.append(f"人數：{_preview_booking.get('people')}位")
            _name = str(_preview_booking.get("contact_name", "")).strip()
            _phone = str(_preview_booking.get("contact_phone", "")).strip()
            if _name or _phone:
                preview_parts.append(f"聯絡：{' '.join(x for x in [_name, _phone] if x)}")
            if preview_parts:
                st.info("住宿預定解析結果：" + "｜".join(preview_parts))
        sm1, sm2, sm3, sm4 = st.columns(4)
        with sm1:
            sum_moto_days = st.number_input("機車天數(摘要)", min_value=0, max_value=99, value=3, step=1, key="sum_moto_days")
        with sm2:
            sum_moto_people = st.number_input("機車幾人一臺", min_value=1, max_value=99, value=2, step=1, key="sum_moto_people")
        with sm3:
            sum_moto_units = st.number_input("機車臺數", min_value=0, max_value=99, value=0, step=1, key="sum_moto_units")
        with sm4:
            sum_line_moto_custom = st.text_input("自訂機車一行（可留空）", "", key="sum_line_moto_custom")

        st.caption("機票費用以「票價總表」報表為準：可一鍵帶入表價到計算欄位，或依報表手動輸入／微調。")
        if st.button("依票價表帶入（對應航空公司＋出發地）", use_container_width=True):
            ref = get_ref_fare(airline, depart_airport)
            if ref:
                for k, v in ref.items():
                    st.session_state[k] = v
                st.success("已依上方報表票價帶入單程／回程。")
            else:
                st.warning(
                    f"「{airline}」報表無「{depart_airport}」列（例如華信無台南／嘉義），請對照報表手動輸入。"
                )

        p1, p2, p3 = st.columns(3)
        with p1:
            fly_adult = st.number_input("搭機 成人(12歲以上) 人數", min_value=0, max_value=99, value=1, key="f_count_adult")
        with p2:
            fly_child = st.number_input("搭機 兒童(2-12歲) 人數", min_value=0, max_value=99, value=0, key="f_count_child")
        with p3:
            fly_senior = st.number_input("搭機 敬老(65歲以上) 人數", min_value=0, max_value=99, value=0, key="f_count_senior")

        st.markdown("**去程票價（每人）**")
        fo1, fo2, fo3 = st.columns(3)
        with fo1:
            f_out_adult = st.number_input("去程 成人票", min_value=0, value=st.session_state.get("f_out_adult", 0), key="f_out_adult")
        with fo2:
            f_out_child = st.number_input("去程 兒童票", min_value=0, value=st.session_state.get("f_out_child", 0), key="f_out_child")
        with fo3:
            f_out_senior = st.number_input("去程 敬老票", min_value=0, value=st.session_state.get("f_out_senior", 0), key="f_out_senior")

        st.markdown("**回程票價（每人）**")
        fb1, fb2, fb3 = st.columns(3)
        with fb1:
            f_back_adult = st.number_input("回程 成人票", min_value=0, value=st.session_state.get("f_back_adult", 0), key="f_back_adult")
        with fb2:
            f_back_child = st.number_input("回程 兒童票", min_value=0, value=st.session_state.get("f_back_child", 0), key="f_back_child")
        with fb3:
            f_back_senior = st.number_input("回程 敬老票", min_value=0, value=st.session_state.get("f_back_senior", 0), key="f_back_senior")

        flight_adult_out = fly_adult * f_out_adult
        flight_adult_back = fly_adult * f_back_adult
        flight_adult_total = flight_adult_out + flight_adult_back
        flight_child_out = fly_child * f_out_child
        flight_child_back = fly_child * f_back_child
        flight_child_total = flight_child_out + flight_child_back
        flight_senior_out = fly_senior * f_out_senior
        flight_senior_back = fly_senior * f_back_senior
        flight_senior_total = flight_senior_out + flight_senior_back

        flight_out_total = flight_adult_out + flight_child_out + flight_senior_out
        flight_back_total = flight_adult_back + flight_child_back + flight_senior_back
        flight_total = flight_out_total + flight_back_total

        st.subheader("3) 搭船費用")
        b1, b2, b3 = st.columns(3)
        with b1:
            boat_adult = st.number_input("搭船 成人(12歲以上) 人數", min_value=0, max_value=99, value=0, key="b_count_adult")
        with b2:
            boat_child = st.number_input("搭船 兒童(3-12歲) 人數", min_value=0, max_value=99, value=0, key="b_count_child")
        with b3:
            boat_senior = st.number_input("搭船 敬老(65歲以上) 人數", min_value=0, max_value=99, value=0, key="b_count_senior")

        bp1, bp2, bp3 = st.columns(3)
        with bp1:
            boat_adult_price = st.number_input(
                "搭船 成人票價(每人)", min_value=0, value=st.session_state.get("b_price_adult", 0), key="b_price_adult"
            )
        with bp2:
            boat_child_price = st.number_input(
                "搭船 兒童票價(每人)", min_value=0, value=st.session_state.get("b_price_child", 0), key="b_price_child"
            )
        with bp3:
            boat_senior_price = st.number_input(
                "搭船 敬老票價(每人)", min_value=0, value=st.session_state.get("b_price_senior", 0), key="b_price_senior"
            )
        boat_total = boat_adult * boat_adult_price + boat_child * boat_child_price + boat_senior * boat_senior_price

        bboat1, bboat2 = st.columns(2)
        with bboat1:
            if st.button("帶入船票表列（全票）", use_container_width=True, key="boat_fill_full"):
                bf = get_boat_fares_from_data()
                st.session_state["b_price_adult"] = bf["adult_full"]
                st.session_state["b_price_child"] = bf["child_full"]
                st.session_state["b_price_senior"] = bf["senior_full"]
        with bboat2:
            if st.button("帶入船票表列（半票）", use_container_width=True, key="boat_fill_half"):
                bf = get_boat_fares_from_data()
                st.session_state["b_price_adult"] = bf["adult_half"]
                st.session_state["b_price_child"] = bf["child_half"]
                st.session_state["b_price_senior"] = bf["senior_half"]

        st.subheader("4) 住宿/機車/汽車手動費用")
        hotel_mode = st.radio(
            "住宿計算方式",
            ("依房型分配", "手動輸入 1~6 人方案"),
            index=0,
            horizontal=True,
            key="hotel_mode",
        )

        # 住宿：房型分配
        if hotel_mode == "依房型分配":
            st.caption("輸入各房型「間數 × 每間總價 × 每間入住人數」，系統自動加總住宿總額；分攤人數可再用下方按鈕調整。")
            room_labels = [
                ("單人房", 1),
                ("雙人房", 2),
                ("三人房", 3),
                ("四人房", 4),
                ("五人房", 5),
                ("六人房", 6),
                ("加床", 1),
                ("包棟3間", 6),
                ("包棟4間", 8),
                ("包棟5間", 10),
                ("包棟6間以上", 12),
            ]
            hotel_total = 0
            hotel_people_from_rooms = 0
            for idx_room, (label, default_cap) in enumerate(room_labels):
                r1, r2, r3 = st.columns(3)
                with r1:
                    cnt = st.number_input(
                        f"{label} 間數",
                        min_value=0,
                        max_value=99,
                        value=0,
                        step=1,
                        key=f"room_cnt_{idx_room}",
                    )
                with r2:
                    price = st.number_input(
                        f"{label} 每間總價(含所有晚)",
                        min_value=0,
                        value=0,
                        step=100,
                        key=f"room_price_{idx_room}",
                    )
                with r3:
                    cap = st.number_input(
                        f"{label} 每間入住人數",
                        min_value=0,
                        max_value=99,
                        value=default_cap,
                        step=1,
                        key=f"room_cap_{idx_room}",
                    )
                hotel_total += int(cnt) * int(price)
                hotel_people_from_rooms += int(cnt) * int(cap)
            st.caption(
                f"房型小計：共 {hotel_people_from_rooms} 人入住；住宿總額 = {hotel_total}。"
                "（實際分攤人數仍以下方「住宿／機車／汽車 分攤人數」與按鈕為準）"
            )
        else:
            # 舊版：依 1~6 人方案直接輸入
            st.caption("先輸入各人數對應費用，再用「總結手動除幾」平均分配")
            cols = st.columns(6)
            hotel_costs, moto_costs, car_costs = [], [], []
            moto_defaults = data.get("moto_car_fares", {}).get("moto_by_people", [0] * 7)
            car_defaults = data.get("moto_car_fares", {}).get("car_by_people", [0] * 7)
            for i in range(1, 7):
                with cols[i - 1]:
                    st.markdown(f"**{i}人**")
                    hotel_costs.append(st.number_input(f"住宿{i}人", min_value=0, value=0, key=f"hotel_{i}"))
                    moto_costs.append(
                        st.number_input(
                            f"機車{i}人",
                            min_value=0,
                            value=int(st.session_state.get(f"moto_{i}", moto_defaults[i] if i < len(moto_defaults) else 0)),
                            key=f"moto_{i}",
                        )
                    )
                    car_costs.append(
                        st.number_input(
                            f"汽車{i}人",
                            min_value=0,
                            value=int(st.session_state.get(f"car_{i}", car_defaults[i] if i < len(car_defaults) else 0)),
                            key=f"car_{i}",
                        )
                    )

            idx = travel_people - 1
            hotel_total = hotel_costs[idx]
            moto_total = moto_costs[idx]
            car_total = car_costs[idx]

        # 機車／汽車若使用房型模式仍沿用原 1~6 人欄位
        if hotel_mode == "依房型分配":
            cols = st.columns(6)
            moto_costs, car_costs = [], []
            moto_defaults = data.get("moto_car_fares", {}).get("moto_by_people", [0] * 7)
            car_defaults = data.get("moto_car_fares", {}).get("car_by_people", [0] * 7)
            for i in range(1, 7):
                with cols[i - 1]:
                    st.markdown(f"**{i}人**（僅機車/汽車）")
                    moto_costs.append(
                        st.number_input(
                            f"機車{i}人",
                            min_value=0,
                            value=int(st.session_state.get(f"moto_{i}", moto_defaults[i] if i < len(moto_defaults) else 0)),
                            key=f"moto_{i}",
                        )
                    )
                    car_costs.append(
                        st.number_input(
                            f"汽車{i}人",
                            min_value=0,
                            value=int(st.session_state.get(f"car_{i}", car_defaults[i] if i < len(car_defaults) else 0)),
                            key=f"car_{i}",
                        )
                    )
            idx = travel_people - 1
            moto_total = moto_costs[idx]
            car_total = car_costs[idx]

        # 汽車車型計價（覆蓋 1~6 人方案的 car_total）
        # 用你提供的座位區間：1-5 五人座、5-7 七人座、7-9 九人座
        #（此處用 <=5 判為五人座；6-7 判為七人座；>=8 判為九人座）
        car_auto_enabled = st.checkbox("使用車型計價（覆蓋汽車總價）", value=False, key="car_auto_enabled")
        if car_auto_enabled:
            car_people_count_default = int(travel_people)
            car_people_count_default = max(1, min(9, car_people_count_default))
            car_people_count = st.number_input(
                "汽車計價人數(1-9)",
                min_value=1,
                max_value=9,
                value=car_people_count_default,
                step=1,
                key="car_people_count",
            )
            car_days = st.number_input(
                "租車天數（24小時；1天=1筆）",
                min_value=1,
                max_value=30,
                value=int(sum_hotel_nights) if "sum_hotel_nights" in locals() else 1,
                step=1,
                key="car_days",
            )

            if car_people_count <= 5:
                seats = 5
                price_options = {"1600/24h": 1600, "1800/24h": 1800}
            elif car_people_count <= 7:
                seats = 7
                price_options = {"2300/24h": 2300, "2500/24h": 2500}
            else:
                seats = 9
                price_options = {"2800/24h": 2800, "3500/24h": 3500}

            option_labels = list(price_options.keys())
            default_idx = 0
            try:
                default_idx = sorted(range(len(option_labels)), key=lambda i: price_options[option_labels[i]])[0]
            except Exception:
                default_idx = 0

            picked_label = st.selectbox("車型價格選擇（依你資料挑）", option_labels, index=default_idx, key="car_price_pick")
            price_per_day = int(price_options.get(picked_label, 0) or 0)
            units = (int(car_people_count) + seats - 1) // seats

            st.caption(f"依 {car_people_count} 人 / {seats}人座，需 {units} 台；汽車總額 = {price_per_day} × {int(car_days)} × {units}")
            car_total = price_per_day * int(car_days) * int(units)

        manual_total = hotel_total + moto_total + car_total

        share_manual_n = st.number_input(
            "住宿／機車／汽車 分攤人數（可與旅遊人數不同）",
            min_value=1,
            max_value=99,
            value=int(travel_people),
            step=1,
            key="share_manual_n",
        )

        c_share1, c_share2, c_share3 = st.columns(3)
        with c_share1:
            if st.button("全部人分攤", use_container_width=True, key="btn_share_all"):
                base_n = fly_adult + fly_child + fly_senior
                if base_n <= 0:
                    base_n = int(travel_people)
                st.session_state["share_manual_n"] = max(1, int(base_n))
        with c_share2:
            if st.button("只成人分攤", use_container_width=True, key="btn_share_adult"):
                base_n = fly_adult
                if base_n <= 0:
                    base_n = 1
                st.session_state["share_manual_n"] = max(1, int(base_n))
        with c_share3:
            if st.button("只兒童分攤", use_container_width=True, key="btn_share_child"):
                base_n = fly_child
                if base_n <= 0:
                    base_n = 1
                st.session_state["share_manual_n"] = max(1, int(base_n))

        manual_avg_share = manual_total / share_manual_n if share_manual_n else 0

        # 一人份：機票(去+回/人) + 有搭船則船票每人 + 住宿／機車／汽車分攤每人
        pp_flight_adult = f_out_adult + f_back_adult
        pp_flight_child = f_out_child + f_back_child
        pp_flight_senior = f_out_senior + f_back_senior
        pp_boat_adult = boat_adult_price if boat_adult else 0
        pp_boat_child = boat_child_price if boat_child else 0
        pp_boat_senior = boat_senior_price if boat_senior else 0

        personal_adult = float(pp_flight_adult + pp_boat_adult + manual_avg_share) if fly_adult else 0.0
        personal_child = float(pp_flight_child + pp_boat_child + manual_avg_share) if fly_child else 0.0
        personal_senior = float(pp_flight_senior + pp_boat_senior + manual_avg_share) if fly_senior else 0.0

        st.markdown("**機票／船票／分攤 — 依票種分開；並算出各票種一人份合計**")
        per_rows = []
        if fly_adult:
            per_rows.append(
                {
                    "票種": "成人(12↑)",
                    "人數": fly_adult,
                    "機票去程小計": flight_adult_out,
                    "機票回程小計": flight_adult_back,
                    "機票合計": flight_adult_total,
                    "機票每人(去+回)": pp_flight_adult,
                    "船票每人": boat_adult_price if boat_adult else "—",
                    "船票小計": boat_adult * boat_adult_price if boat_adult else "—",
                    "住宿等每人分攤": round(manual_avg_share, 2),
                    "一人份合計": round(personal_adult, 2),
                }
            )
        if fly_child:
            per_rows.append(
                {
                    "票種": "兒童(2-12)",
                    "人數": fly_child,
                    "機票去程小計": flight_child_out,
                    "機票回程小計": flight_child_back,
                    "機票合計": flight_child_total,
                    "機票每人(去+回)": pp_flight_child,
                    "船票每人": boat_child_price if boat_child else "—",
                    "船票小計": boat_child * boat_child_price if boat_child else "—",
                    "住宿等每人分攤": round(manual_avg_share, 2),
                    "一人份合計": round(personal_child, 2),
                }
            )
        if fly_senior:
            per_rows.append(
                {
                    "票種": "敬老(65↑)",
                    "人數": fly_senior,
                    "機票去程小計": flight_senior_out,
                    "機票回程小計": flight_senior_back,
                    "機票合計": flight_senior_total,
                    "機票每人(去+回)": pp_flight_senior,
                    "船票每人": boat_senior_price if boat_senior else "—",
                    "船票小計": boat_senior * boat_senior_price if boat_senior else "—",
                    "住宿等每人分攤": round(manual_avg_share, 2),
                    "一人份合計": round(personal_senior, 2),
                }
            )
        if not per_rows:
            per_rows.append(
                {
                    "票種": "—",
                    "人數": 0,
                    "機票去程小計": "—",
                    "機票回程小計": "—",
                    "機票合計": "—",
                    "機票每人(去+回)": "—",
                    "船票每人": "—",
                    "船票小計": "—",
                    "住宿等每人分攤": round(manual_avg_share, 2),
                    "一人份合計": "—",
                }
            )
        st.caption("一人份合計 ＝ 機票每人(去+回) ＋（有搭船則加船票每人）＋ 住宿／機車／汽車分攤每人")
        st.dataframe(pd.DataFrame(per_rows), use_container_width=True, hide_index=True)

        divide_by = st.number_input(
            "總報價平均分配（除幾人）",
            min_value=1,
            max_value=99,
            value=travel_people,
            step=1,
            key="divide_by",
        )

        grand_total = flight_total + boat_total + manual_total
        avg_total = grand_total / divide_by if divide_by else 0
        st.number_input(
            "折扣金額（由總報價扣除；每人金額會依比例遞減）",
            min_value=0,
            step=100,
            key="q_discount_amount",
        )

    q_disc_raw = int(st.session_state.get("q_discount_amount", 0) or 0)
    discount_amount = min(q_disc_raw, int(grand_total)) if grand_total else 0
    grand_after_discount = max(0, int(grand_total) - discount_amount)
    ratio = (grand_after_discount / grand_total) if grand_total else 0.0
    net_adult = round(personal_adult * ratio, 2) if fly_adult else None
    net_child = round(personal_child * ratio, 2) if fly_child else None
    net_senior = round(personal_senior * ratio, 2) if fly_senior else None

    summary_line_flight = f"機票來回｜{airline}｜{depart_airport}"
    _hc = (sum_line_hotel_custom or "").strip()
    _hb = parse_lodging_booking_text(st.session_state.get("sum_hotel_booking_text", ""))
    if _hc:
        summary_line_hotel = _hc
    elif _hb:
        parts = []
        if _hb.get("date_range"):
            parts.append(str(_hb["date_range"]))
        if _hb.get("room_desc"):
            parts.append(str(_hb["room_desc"]))
        if _hb.get("people") is not None:
            parts.append(f"{int(_hb['people'])}位")
        contact = " ".join(x for x in [str(_hb.get("contact_name", "")).strip(), str(_hb.get("contact_phone", "")).strip()] if x)
        if contact:
            parts.append(contact)
        summary_line_hotel = "｜".join(parts) if parts else f"住宿{sum_hotel_people}人{sum_hotel_nights}晚"
    else:
        summary_line_hotel = f"住宿{sum_hotel_people}人{sum_hotel_nights}晚"
    _mc = (sum_line_moto_custom or "").strip()
    if _mc:
        summary_line_moto = _mc
    elif sum_moto_days > 0 and sum_moto_units > 0:
        summary_line_moto = f"機車{sum_moto_days}天｜{sum_moto_people}人一臺×{sum_moto_units}臺"
    else:
        summary_line_moto = ""

    st.subheader("📋 報價摘要（給客戶／LINE）")
    st.caption("試算過程請展開上方「費用試算」；此區只顯示摘要。")
    st.markdown(f"- {summary_line_flight}")
    st.markdown(f"- {summary_line_hotel}")
    if summary_line_moto:
        st.markdown(f"- {summary_line_moto}")
    st.markdown("──────────")
    if fly_adult and net_adult is not None:
        st.markdown(f"- **成人多少？**　**{(net_adult):,.0f}**　（每人，含機票／船／住宿等分攤，已依折扣比例）".replace(",", "，"))
    if fly_child and net_child is not None:
        st.markdown(f"- **兒童多少？**　**{(net_child):,.0f}**　（每人，同上）".replace(",", "，"))
    if fly_senior and net_senior is not None:
        st.markdown(f"- **敬老多少？**　**{(net_senior):,.0f}**　（每人，同上）".replace(",", "，"))
    st.markdown(f"- **折扣**　-{discount_amount:,}".replace(",", "，"))
    st.markdown(f"- **總計**　**{grand_after_discount:,}**".replace(",", "，"))

    # 家庭分組：依每人價格計算各家庭金額（不影響總價，只是輔助試算）
    st.subheader("👨‍👩‍👧‍👦 家庭分組試算（選填）")
    st.caption("若同一團有不同家庭，可在此輸入每組家庭的 成人／兒童／敬老 人數，系統會依上方每人價格計算各家庭應付金額。")
    max_groups = 5
    family_count = st.number_input(
        "家庭組數（1～5 組）",
        min_value=1,
        max_value=max_groups,
        value=1,
        step=1,
        key="family_group_count",
    )
    family_rows = []
    for i in range(1, int(family_count) + 1):
        c1, c2, c3, c4 = st.columns((2, 1, 1, 1))
        with c1:
            name = st.text_input(f"第{i}組家庭名稱", value=f"第{i}組家庭", key=f"family_name_{i}")
        with c2:
            fa = st.number_input("成人", min_value=0, max_value=99, value=0, step=1, key=f"family_adult_{i}")
        with c3:
            fc = st.number_input("兒童", min_value=0, max_value=99, value=0, step=1, key=f"family_child_{i}")
        with c4:
            fs = st.number_input("敬老", min_value=0, max_value=99, value=0, step=1, key=f"family_senior_{i}")
        total = (fa * (net_adult or 0)) + (fc * (net_child or 0)) + (fs * (net_senior or 0))
        family_rows.append(
            {
                "家庭": name or f"第{i}組",
                "成人": fa,
                "兒童": fc,
                "敬老": fs,
                "家庭應付小計": round(total, 2),
            }
        )
    if family_rows:
        st.dataframe(pd.DataFrame(family_rows), use_container_width=True, hide_index=True)

    record = build_quote_record(
        {
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "customer_note": customer_note,
            "customer_source": customer_source,
            "go_date": go_date.strftime("%Y-%m-%d"),
            "back_date": back_date.strftime("%Y-%m-%d"),
            "weekday_count": day_info["weekday_count"],
            "holiday_count": day_info["holiday_count"],
            "airline": airline,
            "depart_airport": depart_airport,
            "travel_people": int(travel_people),
            "flight_out_total": int(flight_out_total),
            "flight_back_total": int(flight_back_total),
            "flight_total": int(flight_total),
            "flight_adult_out": int(flight_adult_out),
            "flight_adult_back": int(flight_adult_back),
            "flight_adult_total": int(flight_adult_total),
            "flight_child_out": int(flight_child_out),
            "flight_child_back": int(flight_child_back),
            "flight_child_total": int(flight_child_total),
            "flight_senior_out": int(flight_senior_out),
            "flight_senior_back": int(flight_senior_back),
            "flight_senior_total": int(flight_senior_total),
            "boat_total": int(boat_total),
            "hotel_total": int(hotel_total),
            "moto_total": int(moto_total),
            "car_total": int(car_total),
            "manual_total": int(manual_total),
            "share_manual_n": int(share_manual_n),
            "manual_avg_share": float(manual_avg_share),
            "divide_by": int(divide_by),
            "grand_total": int(grand_total),
            "avg_total": float(avg_total),
            "pp_flight_adult": int(pp_flight_adult),
            "pp_flight_child": int(pp_flight_child),
            "pp_flight_senior": int(pp_flight_senior),
            "pp_boat_adult": int(pp_boat_adult),
            "pp_boat_child": int(pp_boat_child),
            "pp_boat_senior": int(pp_boat_senior),
            "personal_adult": float(personal_adult),
            "personal_child": float(personal_child),
            "personal_senior": float(personal_senior),
            "fly_adult": int(fly_adult),
            "fly_child": int(fly_child),
            "fly_senior": int(fly_senior),
            "summary_line_flight": summary_line_flight,
            "summary_line_hotel": summary_line_hotel,
            "summary_line_moto": summary_line_moto,
            "discount_amount": int(discount_amount),
            "grand_after_discount": int(grand_after_discount),
            "net_adult": net_adult,
            "net_child": net_child,
            "net_senior": net_senior,
        }
    )

    line_msg = build_quote_customer_summary(record)
    st.subheader("複製到 LINE")
    st.caption(
        "避免瀏覽器 iframe 造成畫面錯誤，改以下載文字檔：下載後開啟 → 全選複製 → 到 LINE 貼上；"
        "手機也可在檔案選單選「分享」傳到 LINE。"
    )
    st.caption("報價內容預覽")
    st.code(line_msg, language=None)
    st.download_button(
        "下載報價文字檔（貼到 LINE）",
        data=("\ufeff" + line_msg).encode("utf-8"),
        file_name=f"報價_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain; charset=utf-8",
        use_container_width=True,
        key="quote_line_txt_download",
    )

    st.subheader("6) 儲存此組客人報價")
    snap = snapshot_quote_form_from_session()
    snap["q_customer_source"] = customer_source
    history = load_quote_history()
    s1, s2 = st.columns(2)
    with s1:
        if st.button("儲存此一組報價（含表單可載回）", use_container_width=True, key="btn_save_quote_group"):
            entry = {
                "quote_id": uuid.uuid4().hex[:10],
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "snapshot": snap,
            }
            entry.update(record)
            history.append(entry)
            save_quote_history(history)
            st.success("已儲存。可到上方「0) 已儲存報價組」載入或刪除。")
    with s2:
        if st.button("清空全部歷史報價", use_container_width=True, key="btn_clear_all_quotes"):
            save_quote_history([])
            st.warning("歷史報價已清空。")

    st.subheader("8) 匯出（Excel / PDF）")
    current_df = pd.DataFrame([record])
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        current_df.to_excel(writer, sheet_name="current_quote", index=False)
        qh = flatten_history_for_df(load_quote_history())
        pd.DataFrame(qh if qh else [{}]).to_excel(writer, sheet_name="quote_history", index=False)
    excel_bytes = excel_buffer.getvalue()

    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "下載當前報價 Excel",
            data=excel_bytes,
            file_name=f"quote_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with d2:
        if HAS_REPORTLAB:
            pdf_bytes = quote_to_pdf_bytes(record)
            st.download_button(
                "下載當前報價 PDF",
                data=pdf_bytes,
                file_name=f"quote_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.caption(
                "PDF 需安裝 `reportlab`。請在 **GitHub 專案根目錄** 的 `requirements.txt` 加入一行 "
                "`reportlab>=4.0.0`，推送後到 Streamlit Cloud 按 **Redeploy**。"
            )

    st.subheader("9) 歷史報價查詢")
    history = load_quote_history()
    if not history:
        st.caption("目前沒有歷史資料。")
    else:
        keyword = st.text_input("依姓名/電話搜尋", key="history_keyword")
        filtered = history
        if keyword.strip():
            kw = keyword.strip()
            filtered = [
                x
                for x in history
                if kw in str(x.get("customer_name", ""))
                or kw in str(x.get("customer_phone", ""))
                or kw in str(x.get("customer_source", ""))
            ]
        st.dataframe(
            pd.DataFrame(flatten_history_for_df(filtered)),
            use_container_width=True,
            hide_index=True,
        )


# ══════════════════════════════════════════════════════════════════
#  CSS 美化
# ══════════════════════════════════════════════════════════════════
if page == "後台管理":
    _admin_gate()
    render_admin_panel()
    st.stop()

# 手機版側欄常收起，前台再提供一個頁內色系切換
if page == "前台（產生行程報到單）":
    pinned_themes = [x for x in st.session_state.get("pinned_themes", []) if x in theme_names]
    if pinned_themes:
        st.caption("固定色系（快速切換）")
        quick_cols = st.columns(len(pinned_themes))
        for i, name in enumerate(pinned_themes):
            with quick_cols[i]:
                if st.button(name, key=f"quick_theme_{i}", use_container_width=True):
                    if st.session_state.get("ui_theme") != name:
                        st.session_state["ui_theme"] = name
                        st.rerun()

    current_theme = st.session_state.get("ui_theme", "溫柔奶茶粉")
    if current_theme not in theme_names:
        current_theme = "溫柔奶茶粉"
    front_theme = st.selectbox(
        "前台色系（手機可在這裡切換）",
        theme_names,
        index=theme_names.index(current_theme),
    )
    if front_theme != st.session_state.get("ui_theme"):
        st.session_state["ui_theme"] = front_theme
        st.rerun()

st.markdown(
    """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700;800&display=swap');
  :root { color-scheme: light; }
  html, body, [class*="css"]  {
    font-family: 'Noto Sans TC', 'Microsoft JhengHei', sans-serif;
    color: #111827 !important;
  }
  [data-testid="stAppViewContainer"] { background: #fff7fb; }
  /* 手機上避免文字消失：強制表單區文字顏色 */
  [data-testid="stAppViewContainer"] p,
  [data-testid="stAppViewContainer"] label,
  [data-testid="stAppViewContainer"] li,
  [data-testid="stAppViewContainer"] span,
  [data-testid="stAppViewContainer"] div {
    color: #111827;
  }
  [data-testid="stSidebar"] * {
    color: #111827 !important;
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
    background: #fff9fc !important;   /* 奶茶粉：可輸入 */
    border: 1px solid #fbcfe8 !important;
    border-radius: 14px !important;
    color: #111 !important;          /* 文字改黑色，清楚可讀 */
  }
  div[data-baseweb="select"] * {
    color: #111827 !important;
  }
  div[data-baseweb="select"] > div {
    background: #fff9fc !important;
    border-radius: 14px !important;
  }
  div[role="listbox"] *,
  ul[role="listbox"] * {
    color: #111827 !important;
  }
  /* disabled（例如自動生成的報到時間） */
  div[data-testid="stTextInput"] input:disabled,
  div[data-testid="stTextArea"] textarea:disabled,
  div[data-testid="stNumberInput"] input:disabled {
    background: #fdf2f8 !important;   /* 淡粉：不可編輯/自動 */
    color: #831843 !important;
    -webkit-text-fill-color: #831843 !important; /* iOS/LINE 內建瀏覽器 */
    opacity: 1 !important;                        /* 避免 disabled 自動降透明 */
  }
  /* 下拉選單展開的選項列表底色 */
  div[role="listbox"] { background: #fff !important; }
  .card {
    background: white;
    border-radius: 22px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
    border: 1px solid #fbcfe8;
    box-shadow: 0 8px 20px rgba(236, 72, 153, .08);
  }
  .section-title {
    font-size: 1rem;
    font-weight: 700;
    color: #be185d;
    margin-bottom: .6rem;
    letter-spacing: .03em;
  }
  .notice-bar {
    background: #fff1f2;
    border-left: 6px solid #fb7185;
    border-radius: 14px;
    padding: .8rem 1.2rem;
    font-size: .9rem;
    color: #9f1239;
    margin-bottom: 1rem;
  }
  .preview-box {
    background: #fff1f8;
    border: 1.5px solid #f9a8d4;
    border-radius: 18px;
    padding: .75rem 1rem;
    font-family: 'Courier New', monospace;
    font-size: .9rem;
    white-space: pre-wrap;
    line-height: 1.45;
    color: #831843;
  }
  .copy-btn {
    display: inline-flex; align-items: center; justify-content: center; gap: .5rem;
    background: linear-gradient(135deg,#f472b6,#fb7185);
    color: white; border: none; border-radius: 18px;
    padding: .8rem 1.6rem; font-size: 1rem; font-weight: 800;
    cursor: pointer; width: 100%; justify-content: center;
    transition: opacity .2s, transform .15s;
  }
  .copy-btn:hover { opacity: .9; transform: translateY(-1px); }
  .copy-btn:active { opacity: .7; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    f"""
<style>
  :root {{ color-scheme: light; }}
  html, body {{
    color: #111827 !important;
  }}
  [data-testid="stAppViewContainer"] {{ background: {active_theme['app_bg']} !important; }}
  div[data-testid="stTextInput"] input,
  div[data-testid="stTextArea"] textarea,
  div[data-testid="stSelectbox"] div[role="combobox"],
  div[data-testid="stNumberInput"] input {{
    background: {active_theme['input_bg']} !important;
    border: 1px solid {active_theme['input_border']} !important;
  }}
  div[data-testid="stTextInput"] input:disabled,
  div[data-testid="stTextArea"] textarea:disabled,
  div[data-testid="stNumberInput"] input:disabled {{
    background: {active_theme['disabled_bg']} !important;
    color: {active_theme['disabled_text']} !important;
    -webkit-text-fill-color: {active_theme['disabled_text']} !important;
  }}
  div[data-baseweb="select"] * {{
    color: #111827 !important;
  }}
  div[data-baseweb="select"] > div {{
    background: {active_theme['input_bg']} !important;
    border-radius: 14px !important;
  }}
  div[role="listbox"] *,
  ul[role="listbox"] * {{
    color: #111827 !important;
  }}
  .card {{
    border: 1px solid {active_theme['card_border']} !important;
    border-radius: 22px !important;
    box-shadow: 0 8px 20px {active_theme['card_shadow']} !important;
  }}
  .section-title {{ color: {active_theme['section_title']} !important; }}
  .notice-bar {{
    background: {active_theme['notice_bg']} !important;
    border-left-color: {active_theme['notice_border']} !important;
    color: {active_theme['notice_text']} !important;
  }}
  .preview-box {{
    background: {active_theme['preview_bg']} !important;
    border-color: {active_theme['preview_border']} !important;
    color: {active_theme['preview_text']} !important;
  }}
  .hero-box {{
    background: linear-gradient(90deg, {active_theme['hero_from']}, {active_theme['hero_to']}) !important;
    border-radius: 22px !important;
  }}
  .location-link {{ color: {active_theme['link']} !important; }}
  .bottom-notice {{
    background: {active_theme['notice_bg']} !important;
    border: 1.5px solid {active_theme['notice_border']} !important;
    color: {active_theme['notice_text']} !important;
    border-radius: 16px !important;
  }}
  div[data-testid="stButton"] > button {{
    border-radius: 16px !important;
    border: 0 !important;
    font-weight: 700 !important;
    padding-top: 0.55rem !important;
    padding-bottom: 0.55rem !important;
    background: linear-gradient(135deg, {active_theme['copy_from']}, {active_theme['copy_to']}) !important;
    color: #fff !important;
    box-shadow: 0 5px 14px {active_theme['copy_shadow']} !important;
    transition: transform .15s ease, opacity .2s ease !important;
  }}
  div[data-testid="stButton"] > button:hover {{
    opacity: .92 !important;
    transform: translateY(-1px) !important;
  }}
  div[data-testid="stDownloadButton"] > button {{
    border-radius: 16px !important;
  }}
</style>
""",
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════
#  頁首
# ══════════════════════════════════════════════════════════════════
st.markdown(
    """
<div class='hero-box' style='padding:1.1rem 1.8rem;border-radius:14px;margin-bottom:1rem'>
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
pn1, pn2 = st.columns(2)
with pn1:
    passenger_name = st.text_input(
        "旅客姓名",
        placeholder="例：王小明",
        label_visibility="visible",
        key="passenger_name",
    )
with pn2:
    passenger_phone = st.text_input(
        "旅客電話",
        placeholder="例：0912345678",
        label_visibility="visible",
        key="passenger_phone",
    )
st.markdown("</div>", unsafe_allow_html=True)

# ── ④ 人數 ────────────────────────────────────────────────────────
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">👥 人數</div>', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
adults = c1.number_input("成人 👨", min_value=0, max_value=99, value=1, step=1, key="adults")
children = c2.number_input("兒童 🧒", min_value=0, max_value=99, value=0, step=1, key="children")
infants = c3.number_input("幼兒 👶", min_value=0, max_value=99, value=0, step=1, key="infants")
total = adults + children + infants
st.caption(f"合計：**{total} 人**（成人 {adults}、兒童 {children}、幼兒 {infants}）")
st.markdown("</div>", unsafe_allow_html=True)

# ── ⑤ 島上交通 ────────────────────────────────────────────────────
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
        min_value=0,
        max_value=99,
        value=0,
        step=1,
        key="scooter_count",
    )
st.markdown("</div>", unsafe_allow_html=True)

# ── ⑥ 地點 ────────────────────────────────────────────────────────
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
            f"🗺️ <a class='location-link' href='{loc_url}' target='_blank'>{loc_url}</a>",
            unsafe_allow_html=True,
        )
else:
    loc_name = loc_choice
    st.info(f"已選歷史報到地點：**{loc_name}**")
    loc_url = data["locations"].get(loc_name, "") or map_url(loc_name)
    if loc_name and loc_url:
        st.markdown(
            f"🗺️ <a class='location-link' href='{loc_url}' target='_blank'>{loc_url}</a>",
            unsafe_allow_html=True,
        )
st.markdown("</div>", unsafe_allow_html=True)

# ── ⑦ 備註 & 旅行社 ──────────────────────────────────────────────
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
    passenger_phone,
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
    background: linear-gradient(135deg,{active_theme['copy_from']},{active_theme['copy_to']});
    color: white; border: none; border-radius: 12px;
    padding: .75rem 0; font-size: 1.05rem; font-weight: 700;
    cursor: pointer; width: 100%;
    box-shadow: 0 4px 12px {active_theme['copy_shadow']};
    transition: transform .15s, opacity .15s;
  }}
  .copy-btn:hover  {{ opacity:.9; transform:translateY(-1px); }}
  .copy-btn:active {{ opacity:.7; transform:translateY(0); }}
  .done-msg {{
    text-align:center; color:{active_theme['copy_done']};
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
<div class='bottom-notice' style='border-radius:12px;
            padding:1rem 1.5rem;font-size:.92rem;text-align:center'>
  <b>📢 注意事項</b><br><br>
  {NOTICE_TEXT}
</div>
""",
    unsafe_allow_html=True,
)

