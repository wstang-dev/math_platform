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
# Tab 1: 集體備課紀錄生成（深度校本版）
# ==========================================
with tab1:
    st.header("🎙️ 集體備課會議錄音轉寫與結構化紀錄生成")
    
    if not cf_account_id or not cf_api_token:
        st.warning("⚠️ 提示：未偵測到 Cloudflare API 金鑰，請在左側邊欄 (Sidebar) 設定。")

    audio_file = st.file_uploader("上傳會議錄音/影片檔", type=["mp3", "m4a", "wav", "webm", "mp4"])

    if audio_file:
        if st.button("🚀 開始分析錄音並生成高品質紀錄", type="primary"):
            if not cf_account_id or not cf_api_token:
                st.error("❌ 請先填寫 Cloudflare Account ID 與 API Token！")
            else:
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

                # --- 2/2 使用 Llama 3.3 70B 模型進行深度推理與專業紀錄生成 ---
                if "transcript_text" in st.session_state and st.session_state["transcript_text"]:
                    with st.spinner("2/2 AI 正在運用 Llama 3.3 70B 模型進行深度數學教學分析與紀錄寫作..."):
                        today_str = datetime.now().strftime("%Y-%m-%d")
                        clean_transcript = st.session_state["transcript_text"][:4000].replace("{", "(").replace("}", ")")
                        
                        prompt = (
                            "你是一位香港資深小學數學科科主席、課程發展主任（CDC）及小學數學教學法專家。\n"
                            "請根據以下備課會議逐字稿，撰寫一份極具專業深度、細節豐富且符合香港小學數學課程標準（P1-P6）的「集體備課紀錄」。\n\n"
                            "【極重要撰寫規範】：\n"
                            "1. **拒絕空洞套話**：請勿撰寫如「進行教學活動」、「使用教具」等籠統字眼。必須寫出**具體數學操作**（例如：以剪刀將平行四邊形沿高剪開，拼砌成等面積的長方形）、**具體提問**及**數學公式**（以 LaTeX 呈現，如 $A = b \\times h$）。\n"
                            "2. **剖析學生迷思（Misconceptions）**：明確列出該課題學生最常見的認知誤區（例如：混淆斜邊與高、忽視垂直符號、忘記除以 2 等）及具體澄清策略。\n"
                            "3. **格式純淨無 HTML**：絕對禁止出現 `<br>`、`<p>` 等 HTML 標籤。單元格內分點請直接換行，使用標準 Markdown 數字列表（1. 2. 3.）或符號（-）。\n"
                            "4. **專業術語校正**：將逐字稿中的廣東話口語及轉寫錯字（如「貨題長方」改為「課題：長方體」、「避距」改為「教具/幾何板」）自動修正為香港數學科專業術語。\n\n"
                            "【輸出格式】：\n"
                            "### （  ）年級數學科備課紀錄 (2025-2026)\n\n"
                            "**單元：** [單元名稱]  \n"
                            "**課題：** [課題名稱]  \n"
                            "**日期：** " + today_str + "  \n"
                            "**出席老師：** [根據逐字稿列出]  \n"
                            "**紀錄老師：** [紀錄老師]  \n\n"
                            "| 教學重點 / 難點 | 教學程序 / 解決方法 | 資料來源 | 檢討及建議 | 備註 |\n"
                            "| :--- | :--- | :--- | :--- | :--- |\n"
                            "| 1. **核心概念與公式**\n詳細說明此課題的核心概念與公式導出邏輯。\n\n2. **學生迷思剖析**\n列出學生最易犯錯的認知誤區與澄清點。 | 1. **導入與複習**\n具體情境與複習舊知提問。\n\n2. **探究與操作**\n一步步寫出學生操作教具、分組討論及公式推導過程。\n\n3. **鞏固與應用**\n課堂範例演練與提示點。 | 具體列出教科書冊數、工作紙編號、實物教具（如三角尺、幾何板）、GeoGebra 課件等。 | 1. **課堂形成性評估**\n具體的觀察點與提問設計。\n\n2. **分層教學策略**\n針對能力較弱及資優學生的具體抽離/延伸建議。 | 具體教學資源準備、特別注意事項及分工。 |\n\n"
                            "會議逐字稿內容：\n" + clean_transcript
                        )
                        
                        # 採用 Llama 3.3 70B 大模型
                        llm_res = run_cf_ai(
                            "@cf/meta/llama-3.3-70b-instruct-fp8-fast", 
                            {"Authorization": f"Bearer {cf_api_token}"}, 
                            payload={
                                "messages": [
                                    {"role": "system", "content": "你是一位香港頂尖的小學數學科教學專家，專門寫作高水準、無 HTML 雜訊、具體扎實的教案與備課紀錄。"},
                                    {"role": "user", "content": prompt}
                                ],
                                "max_tokens": 3000,
                                "temperature": 0.2
                            }
                        )
                        if llm_res.get("success"):
                            st.session_state["current_note"] = llm_res.get("result", {}).get("response", "")
                            st.toast("✅ 高品質校本紀錄生成成功！", icon="📋")
                        else:
                            # 備用機制：若 70B 繁忙則自動切換至 3.1 8B
                            llm_res = run_cf_ai(
                                "@cf/meta/llama-3.1-8b-instruct", 
                                {"Authorization": f"Bearer {cf_api_token}"}, 
                                payload={"messages": [{"role": "user", "content": prompt}], "max_tokens": 2500}
                            )
                            if llm_res.get("success"):
                                st.session_state["current_note"] = llm_res.get("result", {}).get("response", "")
                                st.toast("✅ 校本紀錄生成成功！", icon="📋")
                            else:
                                st.error("❌ AI 生成紀錄失敗，請檢查 API 金鑰。")

    # 2. 展示區
    if "transcript_text" in st.session_state and st.session_state["transcript_text"]:
        with st.expander("📄 點擊展開 / 隱藏「會議完整逐字稿」", expanded=False):
            st.text_area("逐字稿內容", value=st.session_state["transcript_text"], height=180)

    if "current_note" in st.session_state and st.session_state["current_note"]:
        st.divider()
        st.subheader("📋 高品質集體備課紀錄（預覽與即時修訂）")
        
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
                    "title": f"數學備課紀錄 ({datetime.now().strftime('%Y-%m-%d')})",
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
        
        st.markdown(item["content"])
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
        st.subheader("🎯 選擇課堂教材並開始互動")
        game_options = [f"[{g['grade']}] {g['title']} ({g['date']})" for g in reversed(games)]
        selected_game_str = st.selectbox("選擇要播放的教材", game_options)
        
        selected_idx = game_options.index(selected_game_str)
        current_game = list(reversed(games))[selected_idx]
        
        st.markdown(f"### 🎮 當前播放：{current_game['title']}")
        components.html(current_game["code"], height=600, scrolling=True)
        st.download_button("📥 下載此 HTML 教材原始碼", data=current_game["code"], file_name=f"{current_game['title']}.html", mime="text/html")
