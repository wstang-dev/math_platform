import streamlit as st
from datetime import datetime
import json
import os
import requests
import streamlit.components.v1 as components

# 頁面基本設定
st.set_page_config(page_title="小學數學科校本 AI 輔助平台", layout="wide", page_icon="📐")

# 相容讀取不同命名格式的 Secrets 或 側邊欄輸入
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
# Tab 1: 集體備課紀錄生成
# ==========================================
with tab1:
    st.header("🎙️ 集體備課會議錄音轉寫與紀錄生成")
    
    if not cf_account_id or not cf_api_token:
        st.warning("⚠️ 提示：未偵測到 Cloudflare API 金鑰，請在左側邊欄 (Sidebar) 輸入 Account ID 與 Token，或於 Streamlit Secrets 設定。")

    audio_file = st.file_uploader("上傳會議錄音/影片檔", type=["mp3", "m4a", "wav", "webm", "mp4"])

    # 1. 處理按鈕點擊與 AI 呼叫
    if audio_file:
        if st.button("🚀 開始分析錄音並生成紀錄", type="primary"):
            if not cf_account_id or not cf_api_token:
                st.error("❌ 請先填寫 Cloudflare Account ID 與 API Token！")
            else:
                # --- 1/2 語音轉寫 ---
                with st.spinner("1/2 語音轉寫中（使用 Whisper 模型）..."):
                    file_bytes = audio_file.getvalue()
                    whisper_headers = {"Authorization": f"Bearer {cf_api_token}", "Content-Type": "application/octet-stream"}
                    
                    models = ["@cf/openai/whisper", "@cf/openai/whisper-large-v3-turbo"]
                    res = None
                    for m in models:
                        res = run_cf_ai(m, whisper_headers, payload=file_bytes, is_binary=True)
                        if res and res.get("success"):
                            break
                    
                    if res and res.get("success"):
                        st.session_state["transcript_text"] = res.get("result", {}).get("text", "")
                        st.toast("✅ 語音轉寫完成！", icon="🎙️")
                    else:
                        err_msg = res.get("errors", [{}])[0].get("message", "語音轉寫服務繁忙") if res else "連線失敗"
                        st.error(f"❌ 語音轉寫失敗：{err_msg}")

               # --- 2/2 AI 整理校本表格（加入深度擴充指令）---
                if "transcript_text" in st.session_state and st.session_state["transcript_text"]:
                    with st.spinner("2/2 AI 正在分析語音並詳細擴充校本備課紀錄..."):
                        today_str = datetime.now().strftime("%Y-%m-%d")
                        clean_transcript = st.session_state["transcript_text"][:4000].replace("{", "(").replace("}", ")")
                        
                        prompt = (
                            "你是一位香港資深小學數學科主席與課程專家。請根據以下備課會議逐字稿，整理出一份極為詳細、結構嚴謹的「小學數學科集體備課紀錄」。\n\n"
                            "【生成與擴充（Elaborate）原則】：\n"
                            "1. **保留原意並豐富細節**：以同工討論內容為核心，根據香港小學數學課程指引（小一至小六），將對話內容補充擴充為完整、專業的教學紀錄。\n"
                            "2. **自動修正錯別字**：將廣東話轉寫錯字修正為數學專業術語（如「貨題長方」修正為「課題：長方體」、「避距」修正為「教具/小白板」等）。\n"
                            "3. **詳細條列教學程序**：教學程序不可簡略，需分層次寫出（1., 2., 3. 以及 a., b., c.），包含動手操作、分組討論及提問技巧。\n"
                            "4. **補充學生迷思與檢討**：針對該課題，主動補充學生常見的觀念混淆（Misconceptions）與相對應的澄清策略。\n"
                            "5. **數學公式**：所有數學算式與符號請統一使用標準 LaTeX 格式（例如 $L \\times W \\times H$ 或 $12 \\times 5 = 60$）。\n\n"
                            "【輸出格式要求（Markdown 表格）】：\n"
                            "### （  ）年級數學科備課紀錄 (2025-2026)\n\n"
                            "**單元：** [根據內容填寫單元名稱]  \n"
                            "**課題：** [根據內容填寫課題名稱]  \n"
                            "**日期：** " + today_str + "  \n"
                            "**出席老師：** [根據逐字稿列出]  \n"
                            "**紀錄老師：** [紀錄老師]  \n\n"
                            "| 教學重點 / 難點 | 教學程序 / 解決方法 | 資料來源 | 檢討及建議 | 備註 |\n"
                            "| :--- | :--- | :--- | :--- | :--- |\n"
                            "| 1. **[重點1]**<br>• 詳細說明<br><br>2. **[學生迷思]**<br>• 觀念澄清點 | 1. **[引動動機/複習]**<br>&nbsp;&nbsp;a. [具體提問與步驟]<br>&nbsp;&nbsp;b. [教具操作說明]<br>2. **[核心建構]**<br>&nbsp;&nbsp;a. [解題策略]<br>&nbsp;&nbsp;b. [分組討論/匯報] | [如教科書第X冊、工作紙、GeoGebra、小白板] | 1. **[課堂回饋]**<br>• 評估重點<br><br>2. **[鞏固與延伸]**<br>• 提優補差建議 | [備註與待辦事項] |\n\n"
                            "以下是會議逐字稿：\n" + clean_transcript
                        )
                        llm_res = run_cf_ai(
                            "@cf/meta/llama-3.1-8b-instruct", 
                            {"Authorization": f"Bearer {cf_api_token}"}, 
                            payload={
                                "messages": [
                                    {"role": "system", "content": "你是一位專業的香港小學數學課程專家與資深科主席，善於寫出內容詳盡、條理分明的教案與備課紀錄。"},
                                    {"role": "user", "content": prompt}
                                ],
                                "max_tokens": 3000
                            }
                        )
                        if llm_res.get("success"):
                            st.session_state["current_note"] = llm_res.get("result", {}).get("response", "")
                            st.toast("✅ 校本紀錄詳細生成成功！", icon="📋")
                        else:
                            st.error("❌ AI 生成紀錄失敗，請稍後重試。")

    # 2. 獨立展示區：只要 Session State 裡有資料就必定繪製渲染到畫面上
    if "transcript_text" in st.session_state and st.session_state["transcript_text"]:
        with st.expander("📄 點擊展開 / 隱藏「會議完整逐字稿」", expanded=False):
            st.text_area("逐字稿內容", value=st.session_state["transcript_text"], height=180)

    if "current_note" in st.session_state and st.session_state["current_note"]:
        st.divider()
        st.subheader("📋 集體備課紀錄預覽與手動修訂")
        
        # 預覽與編輯雙 Tab 頁面
        tab_preview, tab_edit = st.tabs(["👁️ 預覽校本表格", "✏️ 編輯與修正錯字"])
        
        with tab_edit:
            edited_note = st.text_area("Markdown 內容編輯區", value=st.session_state["current_note"], height=350)
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
