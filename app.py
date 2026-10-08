import streamlit as st
import os
import requests
import io

st.set_page_config(page_title="數學科教師專業交流平台", page_icon="📐", layout="wide")

# 從 Secrets 或 Sidebar 讀取 Cloudflare 金鑰
cf_account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID") or st.sidebar.text_input("Cloudflare Account ID", type="password")
cf_api_token = os.getenv("CLOUDFLARE_API_TOKEN") or st.sidebar.text_input("Cloudflare API Token", type="password")

st.title("📐 數學科教師專業交流與 AI 備課平台 (Cloudflare 免費版)")
st.caption("專為香港中學數學科組設計：語音轉備課紀錄 | 校本題庫共享 | AI 輔助擬題")

tab1, tab2, tab3 = st.tabs(["🎙️ 語音生成備課紀錄", "📝 數學教案與題庫共享", "🤖 AI 數學擬題助手"])

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

# ==========================================
# Tab 1: 語音生成備課紀錄
# ==========================================
with tab1:
    st.header("🎙️ 備課會議錄音轉寫與結構化紀錄")
    st.write("上傳備課會議錄音/影片檔（MP3, M4A, WAV, MP4 等），Cloudflare 將自動進行語音轉寫與紀錄整理。")

    audio_file = st.file_uploader("上傳會議錄音/影片檔", type=["mp3", "m4a", "wav", "webm", "mp4"])

    if audio_file and cf_account_id and cf_api_token:
        if st.button("🚀 開始分析錄音並生成紀錄", type="primary"):
            transcript_text = None
            headers = {"Authorization": f"Bearer {cf_api_token}"}
            
            with st.spinner("1/2 使用 Cloudflare Whisper 進行語音轉寫..."):
                file_bytes = audio_file.getvalue()
                # 呼叫 Cloudflare Whisper 模型
                # 修正後的寫法：加入 Content-Type 標頭
                whisper_headers = {
                    "Authorization": f"Bearer {cf_api_token}",
                    "Content-Type": "application/octet-stream"
                }
                res = run_cf_ai("@cf/openai/whisper", whisper_headers, payload=file_bytes, is_binary=True)
                
                if res.get("success"):
                    transcript_text = res.get("result", {}).get("text", "")
                    st.success("✅ 語音轉寫完成！")
                else:
                    err_msg = res.get("errors", [{}])[0].get("message", "未知錯誤")
                    st.error(f"語音轉寫失敗：{err_msg}")

            if transcript_text:
                with st.spinner("2/2 整理數學科結構化備課紀錄..."):
                    prompt = f"""你是一位資深的中學數學科科主席。請根據以下備課會議的逐字稿，整理出一份結構化的「數學科集體備課紀錄」。

【輸出格式要求】：
1. **會議基本資訊**：日期、主題、參與年級與章節（例如：中四 - 一元二次方程）。
2. **教學重點與難點**：列出本單元學生最容易混淆的觀念（Misconceptions）。
3. **教學策略與課堂活動**：同工討論出的教學法、視覺化工具（如 GeoGebra）應用建議。
4. **擬題與評估建議**：提供 2-3 題符合本單元重點的範例題目，所有數學公式必須使用標準 LaTeX 格式（例如：$x^2 + bx + c = 0$）。
5. **待辦事項（Action Items）**：分工與負責老師。

以下是會議逐字稿：
{transcript_text}"""
                    
                    payload = {
                        "messages": [
                            {"role": "system", "content": "你是一位專業的數學教學助理。"},
                            {"role": "user", "content": prompt}
                        ]
                    }
                    # 呼叫 Cloudflare Llama-3 70B / 8B 模型
                    llm_res = run_cf_ai("@cf/meta/llama-3-8b-instruct", headers, payload=payload)
                    
                    if llm_res.get("success"):
                        result_md = llm_res.get("result", {}).get("response", "")
                        st.markdown(result_md)
                        st.download_button(
                            label="📥 下載備課紀錄 (Markdown)",
                            data=result_md,
                            file_name="meeting_notes.md",
                            mime="text/markdown"
                        )
                    else:
                        st.error("AI 生成紀錄失敗。")

# ==========================================
# Tab 2: 數學教案與題庫共享
# ==========================================
with tab2:
    st.header("📝 校本數學資源庫")
    col1, col2 = st.columns(2)
    with col1:
        st.selectbox("選擇年級", ["全部", "中一", "中二", "中三", "中四", "中五", "中六"])
    with col2:
        st.selectbox("選擇主題", ["全部", "代數", "幾何", "微積分", "概率與統計"])

    st.subheader("📚 共享資源清單")
    with st.expander("📌 [中四] 一元二次方程：求根公式與判別式工作紙"):
        st.write("**提供者：** 張老師 | **更新日期：** 2026-10-01")
        st.markdown("""
        **範例題目：**
        解方程 $$3x^2 - 5x + 2 = 0$$
        
        **解答思路：**
        使用求根公式 $x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$
        """)

# ==========================================
# Tab 3: AI 數學擬題助手
# ==========================================
with tab3:
    st.header("🤖 AI 數學命題助手")
    st.write("輸入教學主題，Cloudflare AI 會自動生成帶有 LaTeX 算式的試題與步驟。")

    col1, col2 = st.columns(2)
    with col1:
        input_topic = st.text_input("題目主題 / 章節", value="二次函數的最大值與最小值")
        difficulty = st.select_slider("題目難度", options=["基礎", "中等", "進階 (DSE 乙部範例)"])
    with col2:
        num_questions = st.number_input("生成題目數量", min_value=1, max_value=5, value=2)

    if st.button("✨ 生成題目", type="primary") and cf_account_id and cf_api_token:
        headers = {"Authorization": f"Bearer {cf_api_token}"}
        with st.spinner("AI 正在擬題中..."):
            prompt = f"""請為香港中學數學科設計 {num_questions} 道題目。
- 主題：{input_topic}
- 難度：{difficulty}

【格式要求】：
1. 題目必須符合 DSE / 中學數學課程標準，並包含詳細解題步驟。
2. 所有數學符號與算式必須使用標準 LaTeX 格式（如 $f(x) = ax^2 + bx + c$）。"""

            payload = {
                "messages": [
                    {"role": "system", "content": "你是一位香港中學數學科資深教師。"},
                    {"role": "user", "content": prompt}
                ]
            }
            llm_res = run_cf_ai("@cf/meta/llama-3-8b-instruct", headers, payload=payload)
            if llm_res.get("success"):
                st.markdown(llm_res.get("result", {}).get("response", ""))
            else:
                st.error("擬題失敗。")
