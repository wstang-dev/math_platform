import streamlit as st
import os
from groq import Groq

st.set_page_config(page_title="數學科教師專業交流平台", page_icon="📐", layout="wide")

api_key = os.getenv("GROQ_API_KEY") or st.sidebar.text_input("輸入 Groq API Key (免費)", type="password")

if not api_key:
    st.info("👈 請先在左側邊欄輸入免費的 Groq API Key 以啟用 AI 功能。")
    client = None
else:
    try:
        client = Groq(api_key=api_key)
    except Exception as e:
        st.error(f"API Key 設定失敗：{e}")
        client = None

st.title("📐 數學科教師專業交流與 AI 備課平台 (Groq 免費版)")
st.caption("專為數學科組設計：語音轉備課紀錄 | 校本題庫共享 | AI 輔助擬題")

tab1, tab2, tab3 = st.tabs(["🎙️ 語音生成備課紀錄", "📝 數學教案與題庫共享", "🤖 AI 數學擬題助手"])

# ==========================================
# Tab 1: 語音生成備課紀錄
# ==========================================
with tab1:
    st.header("🎙️ 備課會議錄音轉寫與結構化紀錄")
    st.write("上傳備課會議錄音檔（MP3, M4A, WAV 等），Groq 將自動進行超高速語音轉寫與紀錄整理。")

    audio_file = st.file_uploader("上傳會議錄音/影片檔", type=["mp3", "m4a", "wav", "webm", "mp4"])

    if audio_file and client:
        if st.button("🚀 開始分析錄音並生成紀錄", type="primary"):
            with st.spinner("1/2 使用 Whisper 進行極速語音轉寫..."):
                try:
                   # 1. 呼叫 Groq Whisper 進行轉寫 (檔名統一寫 "audio.mp3" 避開中文檔名編碼錯誤)
            transcription = client.audio.transcriptions.create(
                file=("audio.mp3", audio_file.getvalue()),
                model="whisper-large-v3",
                response_format="text"
            )
                    transcript_text = transcription
                    st.success("✅ 語音轉寫完成！")
                except Exception as e:
                    st.error(f"語音轉寫失敗：{e}")
                    transcript_text = None

            if transcript_text:
                with st.spinner("2/2 整理數學科結構化備課紀錄..."):
                    prompt = f"""
你是一位資深的中學數學科科主席。請根據以下備課會議的逐字稿，整理出一份結構化的「數學科集體備課紀錄」。

【輸出格式要求】：
1. **會議基本資訊**：日期、主題、參與年級與章節（例如：中四 - 一元二次方程）。
2. **教學重點與難點**：列出本單元學生最容易混淆的觀念（Misconceptions）。
3. **教學策略與課堂活動**：同工討論出的教學法、視覺化工具（如 GeoGebra）應用建議。
4. **擬題與評估建議**：提供 2-3 題符合本單元重點的範例題目，所有數學公式必須使用標準 LaTeX 格式（例如：$x^2 + bx + c = 0$ 或 block 格式 $$x = \\frac{{-b \\pm \\sqrt{{b^2-4ac}}}}{{2a}}$$）。
5. **待辦事項（Action Items）**：分工與負責老師。

以下是會議逐字稿：
{transcript_text}
"""
                    try:
                        response = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.3
                        )
                        result_md = response.choices[0].message.content
                        st.markdown(result_md)
                        st.download_button(
                            label="📥 下載備課紀錄 (Markdown)",
                            data=result_md,
                            file_name="數學科備課紀錄.md",
                            mime="text/markdown"
                        )
                    except Exception as e:
                        st.error(f"AI 生成紀錄失敗：{e}")

# ==========================================
# Tab 2: 數學教案與題庫共享
# ==========================================
with tab2:
    st.header("📝 校本數學資源庫")
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        st.selectbox("選擇年級", ["全部", "中一", "中二", "中三", "中四", "中五", "中六"])
    with col_filter2:
        st.selectbox("選擇主題", ["全部", "代數 (Algebra)", "幾何 (Geometry)", "微積分 (Calculus)", "概率與統計 (Statistics)"])

    st.subheader("📚 共享資源清單")
    with st.expander("📌 [中四] 一元二次方程：求根公式與判別式工作紙"):
        st.write("**提供者：** 張老師 | **更新日期：** 2026-10-01")
        st.write("**教學重點：** 判別式 $\\Delta = b^2 - 4ac$ 對根的性質之影響。")
        st.markdown("""
        **範例題目：**
        解方程 $$3x^2 - 5x + 2 = 0$$
        
        **解答思路：**
        使用求根公式 $x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$，其中 $a=3, b=-5, c=2$。
        """)

# ==========================================
# Tab 3: AI 數學擬題助手
# ==========================================
with tab3:
    st.header("🤖 AI 數學命題助手")
    st.write("輸入教學主題，Groq 會自動生成帶有 LaTeX 算式的試題與步驟。")

    col1, col2 = st.columns(2)
    with col1:
        input_topic = st.text_input("題目主題 / 章節", value="二次函數的最大值與最小值")
        difficulty = st.select_slider("題目難度", options=["基礎", "中等", "進階 (DSE 乙部範例)"])
    with col2:
        num_questions = st.number_input("生成題目數量", min_value=1, max_value=5, value=2)

    if st.button("✨ 生成題目", type="primary") and client:
        with st.spinner("Groq 正在擬題中..."):
            prompt = f"""
請為香港中學數學科設計 {num_questions} 道題目。
- 主題：{input_topic}
- 難度：{difficulty}

【格式要求】：
1. 題目必須符合 DSE / 中學數學課程標準，並包含詳細解題步驟。
2. 所有數學符號與算式**必須使用標準 LaTeX 格式**（如 $f(x) = ax^2 + bx + c$）。
"""
            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5
                )
                st.markdown(response.choices[0].message.content)
            except Exception as e:
                st.error(f"擬題失敗：{e}")
