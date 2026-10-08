import streamlit as st
from datetime import datetime
import json
import os
import requests
import streamlit.components.v1 as components

# 頁面基本設定
st.set_page_config(page_title="小學數學科校本 AI 輔助平台", layout="wide", page_icon="📐")

# 讀取 Secrets
cf_account_id = st.secrets.get("CF_ACCOUNT_ID", "")
cf_api_token = st.secrets.get("CF_API_TOKEN", "")

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
# Tab 1: 集體備課紀錄生成
# ==========================================
with tab1:
    st.header("🎙️ 集體備課會議錄音轉寫與紀錄生成")
    audio_file = st.file_uploader("上傳會議錄音/影片檔", type=["mp3", "m4a", "wav", "webm", "mp4"])

    if audio_file and cf_account_id and cf_api_token:
        if st.button("🚀 開始分析錄音並生成紀錄", type="primary"):
            with st.spinner("1/2 語音轉寫中..."):
                file_bytes = audio_file.getvalue()
                whisper_headers = {"Authorization": f"Bearer {cf_api_token}", "Content-Type": "application/octet-stream"}
                
                models = ["@cf/openai/whisper", "@cf/openai/whisper-large-v3-turbo"]
                res = None
                for m in models:
                    res = run_cf_ai(m, whisper_headers, payload=file_bytes, is_binary=True)
                    if res.get("success"): break
                
                if res and res.get("success"):
                    st.session_state["transcript_text"] = res.get("result", {}).get("text", "")
                    st.success("✅ 語音轉寫完成！")
                else:
                    st.error("語音轉寫失敗，請重試。")

            if "transcript_text" in st.session_state:
                with st.spinner("2/2 AI 生成校本格式紀錄..."):
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    clean_transcript = st.session_state["transcript_text"][:4000].replace("{", "(").replace("}", ")")
                    
                    prompt = (
                        "你是一位香港小學資深數學科科主席。請根據以下會議逐字稿整理「小學數學科集體備課紀錄」。\n"
                        "格式要求：Markdown 表格包含【教學重點/難點】、【教學程序】、【資料來源】、【檢討建議】與【備註】。\n"
                        "日期：" + today_str + "\n\n逐字稿：\n" + clean_transcript
                    )
                    llm_res = run_cf_ai("@cf/meta/llama-3.1-8b-instruct", {"Authorization": f"Bearer {cf_api_token}"}, 
                                        payload={"messages": [{"role": "user", "content": prompt}]})
                    if llm_res.get("success"):
                        st.session_state["current_note"] = llm_res.get("result", {}).get("response", "")
                        st.success("✅ 生成成功！")

    if "current_note" in st.session_state and st.session_state["current_note"]:
        st.divider()
        st.subheader("📋 集體備課紀錄預覽與編輯")
        edited_note = st.text_area("編輯內容", value=st.session_state["current_note"], height=300)
        st.session_state["current_note"] = edited_note
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("📥 下載備課紀錄 (.md)", data=st.session_state["current_note"], file_name="備課紀錄.md")
        with col2:
            if st.button("💾 儲存至紀錄庫"):
                history = load_data(HISTORY_FILE)
                history.append({
                    "id": len(history) + 1,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "title": f"數學備課紀錄 ({datetime.now().strftime('%Y-%m-%d')})",
                    "content": st.session_state["current_note"]
                })
                save_data(HISTORY_FILE, history)
                st.success("✅ 已儲存！")

# ==========================================
# Tab 2: 歷年備課紀錄庫
# ==========================================
with tab2:
    st.header("📚 歷年備課紀錄庫")
    history = load_data(HISTORY_FILE)
    if not history:
        st.info("目前尚無儲存的備課紀錄。")
    else:
        titles = [f"{item['date']} - {item['title']}" for item in reversed(history)]
        selected = st.selectbox("選擇備課紀錄", titles)
        idx = titles.index(selected)
        item = list(reversed(history))[idx]
        
        st.markdown(item["content"])
        st.download_button("📥 下載此紀錄 (.md)", data=item["content"], file_name=f"{item['title']}.md")

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
    
    # 展示教材選單與遊玩視窗
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
        
        # 使用 Streamlit HTML 組件即時渲染 HTML/JS 遊戲
        components.html(current_game["code"], height=600, scrolling=True)
        
        st.download_button("📥 下載此 HTML 教材原始碼", data=current_game["code"], file_name=f"{current_game['title']}.html", mime="text/html")
