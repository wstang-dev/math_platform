import streamlit as st
from datetime import datetime
import json
import os
import requests
import time
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
# Tab 1: 集體備課紀錄生成（黃金高質量內容版）
# ==========================================
with tab1:
    st.header("🎙️ 集體備課會議錄音轉寫與結構化紀錄生成")
    
    if not cf_account_id or not cf_api_token:
        st.warning("⚠️ 提示：未偵測到 Cloudflare API 金鑰，請在左側邊欄 (Sidebar) 設定。")

    # --- 基本資料選擇區 ---
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
        if st.button("🚀 開始分析錄音並生成紀錄", type="primary"):
            if not cf_account_id or not cf_api_token:
                st.error("❌ 請先填寫 Cloudflare Account ID 與 API Token！")
            else:
                attendees_str = "、".join(selected_attendees) if selected_attendees else "全體數學科老師"
                recorder_str = selected_recorder

                # --- 1/2 語音轉寫 (含自動重試機制) ---
                with st.spinner("1/2 語音轉寫中（正在連線 Cloudflare Whisper 節點）..."):
                    file_bytes = audio_file.getvalue()
                    whisper_headers = {"Authorization": f"Bearer {cf_api_token}", "Content-Type": "application/octet-stream"}
                    
                    models = [
                        "@cf/openai/whisper-large-v3-turbo", 
                        "@cf/openai/whisper",
                        "@cf/openai/whisper-large-v3-turbo"
                    ]
                    
                    res = None
                    for attempt, m in enumerate(models):
                        res = run_cf_ai(m, whisper_headers, payload=file_bytes, is_binary=True)
                        if res and res.get("success"):
                            break
                        time.sleep(1.5)
                    
                    if res and res.get("success"):
                        st.session_state["transcript_text"] = res.get("result", {}).get("text", "")
                        st.toast("✅ 語音轉寫完成！", icon="🎙️")
                    else:
                        err_msg = res.get("errors", [{}])[0].get("message", "Cloudflare 語音服務繁忙") if res else "連線失敗"
                        st.error(f"❌ 語音轉寫失敗：{err_msg}。請稍等 5 秒後重新點擊「🚀 開始分析錄音」。")

                # --- 2/2 AI 整理校本表格（黃金品質內容）---
                if "transcript_text" in st.session_state and st.session_state["transcript_text"]:
                    with st.spinner("2/2 AI 正在分析會議內容，精緻化整理校本教學程序..."):
                        today_str = datetime.now().strftime("%d-%m-%Y")
                        clean_transcript = st.session_state["transcript_text"][:4000].replace("{", "(").replace("}", ")")
                        
                        prompt = (
                            "你是一位香港資深小學數學科科主席與課程發展專家（CDC）。\n"
                            "請根據以下會議逐字稿，撰寫一份極具專業深度、條理分明且符合香港小學數學課程指引的「集體備課紀錄」。\n\n"
                            "【高質量寫作原則】：\n"
                            "1. **專業語言校正與提煉**：修正廣東話口語及轉寫錯字（如「體型」改為「梯形」、「周界」若指邊長則修正語境），轉換為專業數學教學用語。\n"
                            "2. **豐富且層次分明的教學程序（1. 搭配 a. b. c.）**：\n"
                            "   - 每個教學程序必須包含具體操作步驟，例如：\n"
                            "     `1. 介紹平行四邊形面積公式與對應底高`\n"
                            "     `   a. 使用教具：指導學生運用三角尺與直角尺，準確量度並繪出對應的高`\n"
                            "     `   b. 幾何探究：利用 GeoGebra 或幾何紙，示範將平行四邊形沿高剪開並割補拼砌成長方形`\n"
                            "     `   c. 鞏固應用：提供具體實例計算，強調面積 = 底 × 高`\n"
                            "3. **澄清學生常見迷思**：針對「混淆斜邊與高」、「找不到對應底高」等難點，設計具體的澄清策略（如進展工作紙、對線練習）。\n"
                            "4. **嚴格 HTML <table> 輸出**：絕對不輸出校名，輸出 3 個 Column（教學重點 / 難點、教學程序 / 解決方法、資料來源），儲存格內換行統一使用 `<br>`。\n\n"
                            "【輸出格式模板】：\n"
                            "### （ " + selected_grade + " ）年級數學科備課紀錄(" + selected_school_year + ")\n\n"
                            "**單元：** [單元名稱]  \n"
                            "**課題：** [課題名稱]  \n"
                            "**日期：** " + today_str + "  \n"
                            "**出席老師：** " + attendees_str + "  \n"
                            "**紀錄老師：** " + recorder_str + "  \n\n"
                            "<table border='1' style='width:100%; border-collapse:collapse; text-align:left;'>\n"
                            "  <tr style='background-color:#f2f2f2;'>\n"
                            "    <th style='width:30%; padding:8px;'>教學重點 / 難點</th>\n"
                            "    <th style='width:50%; padding:8px;'>教學程序 / 解決方法</th>\n"
                            "    <th style='width:20%; padding:8px;'>資料來源</th>\n"
                            "  </tr>\n"
                            "  <!-- 請整理 2 至 3 列極具層次與充實內容的 <tr> 區塊 -->\n"
                            "</table>\n\n"
                            "會議逐字稿內容：\n" + clean_transcript
                        )
                        
                        llm_res = run_cf_ai(
                            "@cf/meta/llama-3.1-8b-instruct", 
                            {"Authorization": f"Bearer {cf_api_token}"}, 
                            payload={
                                "messages": [
                                    {"role": "system", "content": "你是一位專業的香港小學數學教學專家，文字優美充實，善於設計嚴謹且具操作性的教學程序。"},
                                    {"role": "user", "content": prompt}
                                ],
                                "max_tokens": 2800,
                                "temperature": 0.3
                            }
                        )
                        if llm_res.get("success"):
                            st.session_state["current_note"] = llm_res.get("result", {}).get("response", "")
                            st.session_state["current_grade"] = selected_grade
                            st.session_state["current_year"] = selected_school_year
                            st.toast("✅ 高質量校本紀錄生成成功！", icon="📋")
                        else:
                            st.error("❌ AI 生成紀錄失敗，請檢查 API 金鑰。")

    # 展示區
    if "transcript_text" in st.session_state and st.session_state["transcript_text"]:
        with st.expander("📄 點擊展開 / 隱藏「會議完整逐字稿」", expanded=False):
            st.text_area("逐字稿內容", value=st.session_state["transcript_text"], height=180)

    if "current_note" in st.session_state and st.session_state["current_note"]:
        st.divider()
        st.subheader("📋 集體備課紀錄（預覽與手動修訂）")
        
        tab_preview, tab_edit = st.tabs(["👁️ 預覽校本表格", "✏️ 編輯與修正錯字"])
        
        with tab_edit:
            edited_note = st.text_area("HTML / Markdown 內容編輯區", value=st.session_state["current_note"], height=400)
            st.session_state["current_note"] = edited_note
            
        with tab_preview:
            st.markdown(st.session_state["current_note"], unsafe_allow_html=True)
        
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
                    "id": int(time.time()),
                    "year": st.session_state.get("current_year", selected_school_year),
                    "grade": f"{st.session_state.get('current_grade', selected_grade)}年級",
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "title": f"（{st.session_state.get('current_grade', selected_grade)}）年級備課紀錄 ({st.session_state.get('current_year', selected_school_year)})",
                    "content": st.session_state["current_note"]
                })
                save_data(HISTORY_FILE, history)
                st.success("✅ 已成功儲存！可在「📚 歷年備課紀錄庫」分頁按年度與年級查閱。")

# ==========================================
# Tab 2: 歷年備課紀錄庫（按年度/年級篩選 + 刪除功能）
# ==========================================
with tab2:
    st.header("📚 歷年備課紀錄庫")
    history = load_data(HISTORY_FILE)
    
    if not history:
        st.info("目前尚無儲存的備課紀錄。可以在 Tab 1 生成或修訂後點擊「💾 儲存至歷年紀錄庫」。")
    else:
        # 篩選工具列
        st.subheader("🔍 篩選與檢索")
        col_f1, col_f2 = st.columns(2)
        
        available_years = ["全部學年"] + sorted(list(set([item.get("year", "未知學年") for item in history])), reverse=True)
        available_grades = ["全部年級"] + sorted(list(set([item.get("grade", "未知年級") for item in history])))
        
        with col_f1:
            filter_year = st.selectbox("📅 依學年篩選：", available_years)
        with col_f2:
            filter_grade = st.selectbox("📌 依年級篩選：", available_grades)
            
        filtered_history = history
        if filter_year != "全部學年":
            filtered_history = [item for item in filtered_history if item.get("year") == filter_year]
        if filter_grade != "全部年級":
            filtered_history = [item for item in filtered_history if item.get("grade") == filter_grade]
            
        st.divider()
        
        if not filtered_history:
            st.warning("⚠️ 沒有符合條件的備課紀錄。")
        else:
            titles_map = {
                f"[{item.get('year', '')}][{item.get('grade', '')}] {item['date']} - {item['title']}": item
                for item in reversed(filtered_history)
            }
            
            selected_title = st.selectbox("請選擇要查閱或管理的備課紀錄：", list(titles_map.keys()))
            selected_item = titles_map[selected_title]
            
            st.markdown(selected_item["content"], unsafe_allow_html=True)
            
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.download_button(
                    "📥 下載此紀錄 (.md)", 
                    data=selected_item["content"], 
                    file_name=f"{selected_item['title']}.md", 
                    mime="text/markdown"
                )
            with col_d2:
                if st.button(f"🗑️ 刪除這筆紀錄 ({selected_item['date']})", type="secondary"):
                    updated_history = [h for h in history if h.get("id") != selected_item.get("id")]
                    save_data(HISTORY_FILE, updated_history)
                    st.success("🗑️ 該紀錄已成功刪除！")
                    time.sleep(1)
                    st.rerun()

# ==========================================
# Tab 3: 課堂互動教材庫 (HTML5 / AI 遊戲)
# ==========================================
with tab3:
    st.header("🎮 課堂互動教材與 AI 程式庫")
    st.write("上載同工製作或 AI 生成的 HTML5 互動教具/遊戲，老師可在課堂上即時開啟給學生遊玩。")
    
    with st.expander("➕ 上載新互動教材 (.html 檔)", expanded=False):
        game_title = st.text_input("教材/遊戲名稱", placeholder="例如：小三分數大小比較遊戲")
        game_grade = st.selectbox("適用年級", ["小一", "小二", "小三", "小四", "小五", "小六", "全校通用"])
        html_file = st.file_uploader("上傳單頁 HTML 檔", type=["html", "htm"])
        
        if st.button("🚀 發布教材至教材庫", type="primary"):
            if game_title and html_file:
                html_code = html_file.getvalue().decode("utf-8")
                games = load_data(GAMES_FILE)
                games.append({
                    "id": int(time.time()),
                    "title": game_title,
                    "grade": game_grade,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "code": html_code
                })
                save_data(GAMES_FILE, games)
                st.success(f"✅ 教材「{game_title}」發布成功！")
                st.rerun()
            else:
                st.warning("請填寫名稱並上傳 HTML 檔案。")
                
    st.divider()
    
    games = load_data(GAMES_FILE)
    if not games:
        st.info("💡 目前教材庫尚未有互動教具，點擊上方「上載新互動教材」來建立第一個課堂遊戲吧！")
    else:
        st.subheader("🎯 選擇課堂教材與開始互動")
        game_options = [f"[{g['grade']}] {g['title']} ({g['date']})" for g in reversed(games)]
        selected_game_str = st.selectbox("選擇要播放的教材", game_options)
        
        selected_idx = game_options.index(selected_game_str)
        current_game = list(reversed(games))[selected_idx]
        
        st.markdown(f"### 🎮 當前播放：{current_game['title']}")
        components.html(current_game["code"], height=600, scrolling=True)
        st.download_button("📥 下載此 HTML 教材原始碼", data=current_game["code"], file_name=f"{current_game['title']}.html", mime="text/html")
