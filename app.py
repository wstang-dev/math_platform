import streamlit as st
import os
import requests
import json
from datetime import datetime

st.set_page_config(page_title="小學數學科教師專業交流平台", page_icon="📐", layout="wide")

# 讀取 Cloudflare 金鑰
cf_account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID") or st.sidebar.text_input("Cloudflare Account ID", type="password")
cf_api_token = os.getenv("CLOUDFLARE_API_TOKEN") or st.sidebar.text_input("Cloudflare API Token", type="password")

st.title("📐 小學數學科集體備課與 AI 輔助平台")
st.caption("專為香港小學數學科組設計：小學校本備課紀錄格式 | 線上即時修訂 | 歷史紀錄庫")

HISTORY_FILE = "meeting_notes_history.json"

# 載入歷史紀錄
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

# 儲存歷史紀錄
def save_history(records):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

# Helper function: 呼叫 Cloudflare Workers AI REST API
def run_cf_ai(model_name, headers, payload=None, is_binary=False):
    url = f"https://api.cloudflare.com/client/v4/accounts/{cf_account_id}/ai/run/{model_name}"
    try:
        if is_binary:
            response = requests.post(url, headers=headers, data=payload)
        else:
            response = requests.post(url, headers=headers, json=payload)
        return response.json()
    except Exception as e:
        return {"success": False, "errors": [str(e)]}

tab1, tab2, tab3 = st.tabs(["🎙️ 語音生成校本備課紀錄", "📚 歷年備課紀錄庫", "🤖 AI 小學數學擬題助手"])

# ==========================================
# Tab 1: 語音生成校本備課紀錄（支援即時編輯與自動儲存）
# ==========================================
with tab1:
    st.header("🎙️ 集體備課會議錄音轉寫與紀錄生成")
    st.write("上傳備課會議錄音檔，系統將自動套用小學數學科校本表格格式生成紀錄，並支援即時修改文字。")

    audio_file = st.file_uploader("上傳會議錄音/影片檔", type=["mp3", "m4a", "wav", "webm", "mp4"])

    if audio_file and cf_account_id and cf_api_token:
        if st.button("🚀 開始分析錄音並生成紀錄", type="primary"):
            transcript_text = None
            
            # --- 第一階段：語音轉寫 ---
            with st.spinner("1/2 使用 Cloudflare Whisper 進行語音轉寫..."):
                file_bytes = audio_file.getvalue()
                whisper_headers = {
                    "Authorization": f"Bearer {cf_api_token}",
                    "Content-Type": "application/octet-stream"
                }
                
                models_to_try = ["@cf/openai/whisper", "@cf/openai/whisper-large-v3-turbo"]
                res = None
                for model in models_to_try:
                    res = run_cf_ai(model, whisper_headers, payload=file_bytes, is_binary=True)
                    if res.get("success"):
                        break
                
                if res and res.get("success"):
                    transcript_text = res.get("result", {}).get("text", "")
                    st.session_state["transcript_text"] = transcript_text
                    st.success("✅ 語音轉寫完成！")
                else:
                    err_msg = res.get("errors", [{}])[0].get("message", "Cloudflare 轉寫服務繁忙")
                    st.error(f"語音轉寫失敗：{err_msg}")

            # --- 第二階段：AI 整理結構化紀錄 ---
            if transcript_text:
                with st.spinner("2/2 套用小學數學科校本格式整理紀錄..."):
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    clean_transcript = transcript_text[:4000].replace("{", "(").replace("}", ")")
                    
                    prompt = (
                        "你是一位香港小學資深數學科科主席。請根據以下備課會議逐字稿，嚴格按照學校標準格式整理一份「小學數學科集體備課紀錄」。\n\n"
                        "【輸出格式與結構要求】：\n"
                        "請直接輸出 Markdown 格式，結構如下：\n\n"
                        "### （  ）年級數學科備課紀錄 (2025-2026)\n\n"
                        "**單元：** [填寫單元名稱]  \n"
                        "**課題：** [填寫課題名稱]  \n"
                        "**日期：** " + today_str + "  \n"
                        "**出席老師：** [根據逐字稿列出出席老師]  \n"
                        "**紀錄老師：** [列出紀錄老師]  \n\n"
                        "| 教學重點 / 難點 | 教學程序 / 解決方法 | 資料來源 | 檢討及建議 | 備註 |\n"
                        "| :--- | :--- | :--- | :--- | :--- |\n"
                        "| 1. [重點1]<br><br>2. [重點2] | 1. [程序1]<br>&nbsp;&nbsp;a. [子點a]<br>&nbsp;&nbsp;b. [子點b]<br>2. [程序2] | [如教科書/工作紙/GeoGebra] | 1. [建議1]<br>2. [建議2] | [備註事項] |\n\n"
                        "【注意事項】：\n"
                        "1. 修正逐字稿中明顯的語音轉寫錯別字。\n"
                        "2. 內容必須符合香港小學數學課程（小一至小六）。\n"
                        "3. 所有數學算式與符號請使用標準 LaTeX 格式（例如 $12 \\times 5 = 60$）。\n"
                        "4. 請使用繁體中文。\n\n"
                        "以下是會議逐字稿：\n" + clean_transcript
                    )

                    llm_headers = {"Authorization": f"Bearer {cf_api_token}"}
                    payload = {
                        "messages": [
                            {"role": "system", "content": "你是一位專業的香港小學數學教學助理，熟悉香港小學數學課程與常用語。"},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 2048
                    }
                    
                    llm_res = run_cf_ai("@cf/meta/llama-3.1-8b-instruct", llm_headers, payload=payload)
                    
                    if llm_res.get("success"):
                        result_md = llm_res.get("result", {}).get("response", "")
                        st.session_state["current_note"] = result_md
                        st.success("✅ 校本備課紀錄生成成功！")
                    else:
                        err_msg = llm_res.get("errors", [{}])[0].get("message", repr(llm_res))
                        st.error(f"❌ AI 生成紀錄失敗，原因：{err_msg}")

    # --- 展示逐字稿 ---
    if "transcript_text" in st.session_state and st.session_state["transcript_text"]:
        with st.expander("📄 點擊展開 / 隱藏「會議完整逐字稿」", expanded=False):
            st.text_area("逐字稿內容", value=st.session_state["transcript_text"], height=200)
            st.download_button(
                label="📥 下載完整逐字稿 (.txt)",
                data=st.session_state["transcript_text"],
                file_name="meeting_transcript.txt",
                mime="text/plain"
            )

    # --- 顯示生成結果與修訂區域 ---
    if "current_note" in st.session_state and st.session_state["current_note"]:
        st.divider()
        st.subheader("📋 集體備課紀錄（可預覽與即時修訂）")
        
        tab_preview, tab_edit = st.tabs(["👁️ 預覽視圖", "✏️ 手動編輯與修訂錯字"])
        
        with tab_edit:
            st.info("💡 可以在下方框內直接修改任何錯字或調整內容：")
            edited_note = st.text_area("Markdown 編輯器", value=st.session_state["current_note"], height=400)
            st.session_state["current_note"] = edited_note
            
        with tab_preview:
            st.markdown(st.session_state["current_note"])
        
        col_dl, col_sv = st.columns(2)
        with col_dl:
            st.download_button(
                label="📥 下載修訂後的備課紀錄 (.md)",
                data=st.session_state["current_note"],
                file_name=f"備課紀錄_{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown"
            )
        with col_sv:
            if st.button("💾 儲存至校本紀錄庫", type="primary"):
                history = load_history()
                new_record = {
                    "id": len(history) + 1,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "title": f"小學數學備課紀錄 ({datetime.now().strftime('%Y-%m-%d')})",
                    "content": st.session_state["current_note"]
                }
                history.append(new_record)
                save_history(history)
                st.success("✅ 已成功儲存至校本資料庫！請切換至「📚 歷年備課紀錄庫」查看。")
