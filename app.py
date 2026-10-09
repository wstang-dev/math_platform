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
# Tab 1: 集體備課紀錄生成（HTML 100% 穩定表格 + Whisper 多重重試版）
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
                        "@cf/openai/whisper-large-v3-turbo" # 再次重試
                    ]
                    
                    res = None
                    for attempt, m in enumerate(models):
                        res = run_cf_ai(m, whisper_headers, payload=file_bytes, is_binary=True)
                        if res and res.get("success"):
                            break
                        time.sleep(1.5) # 稍微等待後進行重試
                    
                    if res and res.get("success"):
                        st.session_state["transcript_text"] = res.get("result", {}).get("text", "")
                        st.toast("✅ 語音轉寫完成！", icon="🎙️")
                    else:
                        err_msg = res.get("errors", [{}])[0].get("message", "Cloudflare 語音服務繁忙") if res else "連線失敗"
                        st.error(f"❌ 語音轉寫失敗：{err_msg}。請稍等 5 秒後重新點擊「🚀 開始分析錄音」。")

                # --- 2/2 AI 整理校本表格 ---
                if "transcript_text" in st.session_state and st.session_state["transcript_text"]:
                    with st.spinner("2/2 AI 正在分析會議內容，生成 3 欄 HTML 完美表格..."):
                        today_str = datetime.now().strftime("%d-%m-%Y")
                        clean_transcript = st.session_state["transcript_text"][:4000].replace("{", "(").replace("}", ")")
                        
                        prompt = (
                            "你是一位香港資深小學數學科科主席。\n"
                            "請【嚴格根據以下會議逐字稿的真實討論內容】，整理出一份結構清晰的「小學數學科集體備課紀錄」。\n\n"
                            "【極嚴格輸出格式指示】：\n"
                            "1. **絕對不輸出校名**。\n"
                            "2. **表格必須使用 HTML <table> 語法**，結構如下：\n"
                            "   <table border='1' style='width:100%; border-collapse:collapse;'>\n"
                            "     <tr style='background-color:#f2f2f2;'>\n"
                            "       <th style='width:30%; padding:8px;'>教學重點 / 難點</th>\n"
                            "       <th style='width:50%; padding:8px;'>教學程序 / 解決方法</th>\n"
                            "       <th style='width:20%; padding:8px;'>資料來源</th>\n"
                            "     </tr>\n"
                            "     <tr>\n"
                            "       <td style='padding:8px; vertical-align:top;'>[教學重點1與學生迷思]</td>\n"
                            "       <td style='padding:8px; vertical-align:top;'>[教學程序1，包含 1. a. b. c.]</td>\n"
                            "       <td style='padding:8px; vertical-align:top;'>[資料來源]</td>\n"
                            "     </tr>\n"
                            "   </table>\n"
                            "3. 儲存格內部換行請直接使用 `<br>`，內容必須層次分明（使用 1. 2. 與 a. b. c.）。\n\n"
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
                            "  <tr>\n"
                            "    <td style='padding:8px; vertical-align:top;'>\n"
                            "      1. 平行四邊形面積計算<br><br>\n"
                            "      2. 學生未能找出底和對應的高\n"
                            "    </td>\n"
                            "    <td style='padding:8px; vertical-align:top;'>\n"
                            "      1. 介紹平行四邊形面積公式<br>\n"
                            "      &nbsp;&nbsp;a. 使用教具：三角尺、直角尺找出對應的底和高<br>\n"
                            "      &nbsp;&nbsp;b. 老師示範用 GeoGebra 將平行四邊形分割再拼成長方形<br>\n"
                            "      &nbsp;&nbsp;c. 提供實例計算<br><br>\n"
                            "      2. 強調找到對應的底和高<br>\n"
                            "      &nbsp;&nbsp;a. 使用進展工作紙找底部和高的關係，強化學生對底部和高的理解\n"
                            "    </td>\n"
                            "    <td style='padding:8px; vertical-align:top;'>\n"
                            "      教科書<br>GeoGebra<br>工作紙\n"
                            "    </td>\n"
                            "  </tr>\n"
                            "</table>\n\n"
                            "會議逐字稿內容：\n" + clean_transcript
                        )
                        
                        llm_res = run_cf_ai(
                            "@cf/meta/llama-3.1-8b-instruct", 
                            {"Authorization": f"Bearer {cf_api_token}"}, 
                            payload={
                                "messages": [
                                    {"role": "system", "content": "你是一位專業的香港小學數學教學助理，輸出完美的 HTML Table，格式 100% 穩定無懈可擊。"},
                                    {"role": "user", "content": prompt}
                                ],
                                "max_tokens": 2500,
                                "temperature": 0.1
                            }
                        )
                        if llm_res.get("success"):
                            st.session_state["current_note"] = llm_res.get("result", {}).get("response", "")
                            st.toast("✅ 備課紀錄生成成功！", icon="📋")
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
                    "id": len(history) + 1,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "title": f"{selected_grade}年級備課紀錄_({datetime.now().strftime('%Y-%m-%d')})",
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
    else:
        titles = [f"{item['date']} - {item['title']}" for item in reversed(history)]
        selected = st.selectbox("選擇要查閱的備課紀錄", titles)
        idx = titles.index(selected)
        item = list(reversed(history))[idx]
        
        st.markdown(item["content"], unsafe_allow_html=True)
        st.download_button("📥 下載此紀錄 (.md)", data=item["content"], file_name=f"{item['title']}.md", mime="text/markdown")

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
                    "id": len(games) + 1,
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
