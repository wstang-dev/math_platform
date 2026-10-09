import streamlit as st
from datetime import datetime
import json
import os
import requests
import streamlit.components.v1 as components

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

def run_cf_ai(model_name, headers, payload, is_binary=False):
    url = f"https://api.cloudflare.com/client/v4/accounts/{cf_account_id}/ai/run/{model_name}"
    try:
        if is_binary:
            response = requests.post(url, headers=headers, data=payload, timeout=120)
        else:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
        return response.json()
    except Exception as e:
        return {"success": False, "errors": [{"message": str(e)}]}

st.title("📐 小學數學科校本 AI 輔助與教材平台")

tab1, tab2, tab3 = st.tabs(["🎙️ 集體備課紀錄生成", "📚 歷年備課紀錄庫", "🎮 課堂互動教材庫"])

# ==========================================
# Tab 1: 集體備課紀錄生成（高品質校本內容版）
# ==========================================
with tab1:
    st.header("🎙️ 集體備課會議錄音轉寫與結構化紀錄生成")
    
    if not cf_account_id or not cf_api_token:
        st.warning("⚠️ 提示：未偵測到 Cloudflare API 金鑰，請在左側邊欄 (Sidebar) 設定。")

    # --- 校本資訊選擇區 ---
    st.subheader("📝 會議基本資料設定")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        selected_grade = st.selectbox("📌 請選擇年級：", ["一", "二", "三", "四", "五", "六"], index=3)
    with col_g2:
        selected_school_year = st.selectbox("📅 請選擇學年：", ["2025-2026", "2026-2027"], index=1)

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        selected_attendees = st.multiselect(
            "👥 請勾選出席老師：", 
            options=TEACHERS_LIST,
            default=["鄧慧姍", "陳月娥", "容佩誼"]
        )
    with col_t2:
        selected_recorder = st.selectbox(
            "✍️ 請選擇紀錄老師：", 
            options=TEACHERS_LIST,
            index=0
        )

    st.divider()

    audio_file = st.file_uploader("上傳會議錄音/影片檔", type=["mp3", "m4a", "wav", "webm", "mp4"])

    if audio_file:
        if st.button("🚀 開始分析錄音並生成校本紀錄", type="primary"):
            if not cf_account_id or not cf_api_token:
                st.error("❌ 請先填寫 Cloudflare Account ID 與 API Token！")
            else:
                attendees_str = "、".join(selected_attendees) if selected_attendees else "全體數學科老師"
                recorder_str = selected_recorder

                # --- 1/2 語音轉寫 ---
                with st.spinner("1/2 語音轉寫中（使用 Whisper 模型）..."):
                    file_bytes = audio_file.getvalue()
                    whisper_headers = {"Authorization": f"Bearer {cf_api_token}", "Content-Type": "application/octet-stream"}
                    
                    models = ["@cf/openai/whisper-large-v3-turbo", "@cf/openai/whisper"]
                    res = None
                    for m in models:
                        res = run_cf_ai(m, whisper_headers, payload=file_bytes, is_binary=True)
                        if res and res.get("success"): break
                    
                    if res and res.get("success"):
                        st.session_state["transcript_text"] = res.get("result", {}).get("text", "")
                        st.toast("✅ 語音轉寫完成！", icon="🎙️")
                    else:
                        err_msg = res.get("errors", [{}])[0].get("message", "轉寫失敗") if res else "連線失敗"
                        st.error(f"❌ 語音轉寫失敗：{err_msg}")

                # --- 2/2 AI 整理校本表格（強化高質量內容生成）---
                if "transcript_text" in st.session_state and st.session_state["transcript_text"]:
                    with st.spinner("2/2 AI 正在分析會議內容，整理高質感校本備課內容..."):
                        today_str = datetime.now().strftime("%d-%m-%Y")
                        clean_transcript = st.session_state["transcript_text"][:4000].replace("{", "(").replace("}", ")")
                        
                        prompt = (
                            "你是一位香港資深小學數學科科主席及課程專家。\n"
                            "請根據以下備課會議逐字稿，撰寫一份內容極其扎實、條理清晰且完全符合「嘉諾撒撒心學校（九龍塘）」質素要求的「集體備課紀錄」。\n\n"
                            "【內容與寫作質量要求】：\n"
                            "1. **實事求是與深度擴充**：精準歸納會議討論的數學課題（例如平行四邊形面積）。教學程序必須寫出具體的課堂活動（如：使用三角尺與直角尺找出對應底高、以 GeoGebra 進行分割拼砌長方形演示、運用工作紙進行進展性評估等）。\n"
                            "2. **結構化層次（1. 配合 a. b. c.）**：\n"
                            "   - 「教學重點/難點」請列出 1. 2.\n"
                            "   - 「教學程序/解決方法」請使用清晰主次編號，例如：\n"
                            "     1. 介紹平行四邊形面積公式\n"
                            "        a. 使用教具：三角尺、直角尺找出對應的底和高\n"
                            "        b. 老師示範範用 GeoGebra 將平行四邊形分割再拼成長方形\n"
                            "        c. 提供實例計算\n"
                            "3. **格式規範禁令**：絕對禁止在輸出內容中出現 `<br>`、`<p>` 等 HTML 標籤！表格內換行請使用 Markdown 標準換行。\n"
                            "4. **專業語彙校正**：將逐字稿中的口語及轉寫錯別字（如「貨題長方」改為「課題：長方體」）修正為香港小學數學科專業術語。\n\n"
                            "【輸出格式模板】：\n"
                            "# 嘉諾撒撒心學校（九龍塘）\n"
                            "### （ " + selected_grade + " ）年級數學科備課紀錄(" + selected_school_year + ")\n\n"
                            "**單元：** [單元名稱]  \n"
                            "**課題：** [課題名稱]  \n"
                            "**日期：** " + today_str + "  \n"
                            "**出席老師：** " + attendees_str + "  \n"
                            "**紀錄老師：** " + recorder_str + "  \n\n"
                            "| 教學重點 / 難點 | 教學程序 / 解決方法 | 資料來源 | 檢討及建議 | 備註 |\n"
                            "| :--- | :--- | :--- | :--- | :--- |\n"
                            "| 1. [核心教學重點]\n\n2. [學生主要難點/迷思] | 1. [主程序 1]\n   a. [具體教學操作步驟]\n   b. [教具/軟件使用細節]\n   c. [課堂鞏固與計算]\n2. [解決方法/針對難點之策略]\n   a. [強化理解的具體做法] | 教科書\nGeoGebra\n工作紙 | 1. [課堂檢討建議 1]\n2. [課堂檢討建議 2] | [備註與注意事項] |\n\n"
                            "會議逐字稿內容：\n" + clean_transcript
                        )
                        
                        llm_res = run_cf_ai(
                            "@cf/meta/llama-3.1-8b-instruct", 
                            {"Authorization": f"Bearer {cf_api_token}"}, 
                            payload={
                                "messages": [
                                    {"role": "system", "content": "你是一位專業的香港小學數學教學專家，文字精煉流暢，排版嚴謹無 HTML 雜訊。"},
                                    {"role": "user", "content": prompt}
                                ],
                                "max_tokens": 2500,
                                "temperature": 0.2
                            }
                        )
                        if llm_res.get("success"):
                            st.session_state["current_note"] = llm_res.get("result", {}).get("response", "")
                            st.toast("✅ 高質量校本紀錄生成成功！", icon="📋")
                        else:
                            st.error("❌ AI 生成紀錄失敗，請檢查 API 金鑰。")

    # 2. 展示區
    if "transcript_text" in st.session_state and st.session_state["transcript_text"]:
        with st.expander("📄 點擊展開 / 隱藏「會議完整逐字稿」", expanded=False):
            st.text_area("逐字稿內容", value=st.session_state["transcript_text"], height=180)

    if "current_note" in st.session_state and st.session_state["current_note"]:
        st.divider()
        st.subheader("📋 集體備課紀錄（預覽與手動修訂）")
        
        tab_preview, tab_edit = st.tabs(["👁️ 預覽校本表格", "✏️ 編輯與修正錯字"])
        
        with tab_edit:
            edited_note = st.text_area("Markdown 內容編輯區", value=st.session_state["current_note"], height=400)
            st.session_state["current_note"] = edited_note
            
        with tab_preview:
            st.markdown(st.session_state["current_note"])
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "📥 下載備課紀錄 (.md)", 
                data=st.session_state["current_note"], 
                file_name=f"備課紀錄_{datetime.now().strftime('%Y%m%d')}.md", 
                mime="text/markdown"
            )
        with col2:
            if st.button("💾 儲存至歷年紀錄庫", type="primary"):
                history = load_data(HISTORY_FILE)
                history.append({
                    "id": len(history) + 1,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "title": f"嘉諾撒撒心學校_{selected_grade}年級備課紀錄_({datetime.now().strftime('%Y-%m-%d')})",
                    "content": st.session_state["current_note"]
                })
                save_data(HISTORY_FILE, history)
                st.success("✅ 已成功儲存！可在「📚 歷年備課紀錄庫」查閱。")

# ==========================================
# Tab 2: 歷年備課紀錄庫
# ==========================================
with tab2:
    st.header("📚 歷年備課紀錄庫")
    history = load_data(HISTORY_FILE)
    if not history:
        st.info("目前尚無儲存的備課紀錄。可以在 Tab 1 生成或修訂後點擊「💾 儲存至歷年紀錄庫」。")
