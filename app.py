import streamlit as st
from datetime import datetime
import json
import os
import requests
import time
import base64
import io

# 嘗試載入 Word (docx) 與 PDF 解析庫
try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    import pypdf
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

# 頁面基本設定
st.set_page_config(page_title="小學數學科校本 AI 輔助平台", layout="wide", page_icon="📐")

# 相容讀取 Secrets 或 側邊欄輸入
st.sidebar.header("🔑 系統設定")
cf_account_id = (
    st.secrets.get("CLOUDFLARE_ACCOUNT_ID") 
    or st.secrets.get("CF_ACCOUNT_ID") 
    or st.sidebar.text_input("Cloudflare Account ID", type="password")
)
cf_api_token = (
    st.secrets.get("CLOUDFLARE_API_TOKEN") 
    or st.secrets.get("CF_API_TOKEN") 
    or st.sidebar.text_input("Cloudflare API Token", type="password")
)

# 科組老師名單
TEACHERS_LIST = [
    "鄧慧姍", "陳月娥", "朱嘉欣", "韓斐", "黃群英", 
    "梁倩玉", "容佩誼", "鄭棋昌", "李嘉琪", "林莉雅", 
    "陳詩雅", "陳岍柔", "陳愷彤", "廖心妍"
]

# 歷史紀錄檔案路徑
HISTORY_FILE = "meeting_notes_history.json"
GAMES_FILE = "interactive_games.json"

def load_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_data(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def run_cf_ai(model_name, headers, payload, is_json=True, timeout=180):
    url = f"https://api.cloudflare.com/client/v4/accounts/{cf_account_id}/ai/run/{model_name}"
    try:
        if is_json:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        else:
            response = requests.post(url, headers=headers, data=payload, timeout=timeout)
        return response.json()
    except Exception as e:
        return {"success": False, "errors": [{"message": str(e)}]}

st.title("📐 小學數學科校本 AI 輔助與教材平台")

tab1, tab2, tab3 = st.tabs(["🎙️ 集體備課紀錄生成", "📚 歷年備課紀錄庫", "🔗 課堂互動教材庫 (連結版)"])

# ==========================================
# Tab 1: 集體備課紀錄生成（防幻想 + 文字對話修訂功能）
# ==========================================
with tab1:
    st.header("🎙️ 集體備課會議錄音轉寫與結構化紀錄生成")
    
    if not cf_account_id or not cf_api_token:
        st.warning("⚠️ 提示：未偵測到 Cloudflare API 金鑰，請在左側邊欄 (Sidebar) 設定。")

    # --- 基本資料選擇區 ---
    st.subheader("📝 會議基本資料設定")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        selected_grade = st.selectbox("📌 請選擇年級：", ["一", "二", "三", "四", "五", "六"],
