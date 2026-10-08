import streamlit as st
import os
from openai import OpenAI

# 頁面配置
st.set_page_config(
    page_title="數學科教師專業交流平台",
    page_icon="📐",
    layout="wide"
)

# 初始化 OpenAI API Client (請確保設定了環境變數或直接在此輸入 Key)
# 建議設定環境變數: export OPENAI_API_KEY="your-api-key"
api_key = os.getenv("OPENAI_API_KEY") or st.sidebar.text_input("輸入 OpenAI API Key", type="password")

if not api_key:
    st.info("👈 請先在左側邊欄輸入 OpenAI API Key 以啟用 AI 功能。")
    client = None
else:
    client = OpenAI(api_key=api_key)

# 標題與簡介
st.title("📐 數學科教師專業交流與 AI 備課平台")
st.caption("專為數學科組設計：語音轉備課紀錄 | 校本題庫共享 | AI 輔助擬題")

# 建立分頁
tab1, tab2, tab3 = st.tabs(["🎙️ 語音生成備課紀錄", "📝 數學教案與題庫共享", "🤖 AI 數學擬題助手"])

# ==========================================
# Tab 1: 語音生成備課紀錄
# ==========================================
with tab1:
    st.header("🎙️ 備課會議錄音轉寫與結構化紀錄")
    st.write("上傳備課會議的音訊檔案（MP3, M4A, WAV 等），AI 將自動轉寫並整理成數學科專用備課紀錄。")

    audio_file = st.file_uploader("上傳會議錄音檔", type=["mp3", "m4a", "wav", "webm"])

    if audio_file and client:
        if st.button("🚀 開始分析錄音並生成紀錄", type="primary"):
            with st.spinner("1/2 正在使用 Whisper 轉寫語音..."):
                try:
                    # 呼叫 Whisper API 轉寫語音
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=audio_file
                    )
                    transcript_text = transcription.text
                    
                    with st.expander("📄 查看原始逐字稿"):
                        st.write(transcript_text)

                except Exception as e:
                    st.error(f"語音轉寫失敗：{e}")
                    transcript_text = None

            if transcript_text:
                with st.spinner("2/2 正在整理數學科結構化備課紀錄..."):
                    prompt = f"""
你是一位資深的中學數學科科主席。請根據以下備課會議的逐字稿，整理出一份結構化的「數學科集體備課紀錄」。

【輸出格式要求】：
1. **會議基本資訊**：日期、主題、參與年級與章節（例如：中四 - 一元二次方程）。
2. **教學重點與難點**：列出本單元學生最容易混淆的觀念（Misconception）。
3. **教學策略與課堂活動**：同工討論出的教學法、視覺化工具（如 GeoGebra）應用建議。
4. **擬題與評估建議**：提供 2-3 題符合本單元重點的範例題目，所有數學公式必須使用標準 LaTeX 格式（例如：Inline 使用 $x^2 + bX + c = 0$，Block 使用 $$x = \\frac{{-b \\pm \\sqrt{{b^2-4ac}}}}{{2a}}$$）。
5. **待辦事項（Action Items）**：分工與負責老師。

以下是會議逐字稿：
{transcript_text}
"""
                    try:
                        response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.3
                        )
                        result_md = response.choices[0].message.content
                        st.success("✅ 備課紀錄生成成功！")
                        st.markdown(result_md)
                        
                        # 提供下載功能
                        st.download_button(
                            label="📥 下載備課紀錄 (Markdown)",
                            data=result_md,
                            file_name="數學科備課紀錄.md",
                            mime="text/markdown"
                        )
                    except Exception as e:
                        st.error(f"AI 生成紀錄失敗：{e}")

# ==========================================
# Tab 2: 數學教案與題庫共享 (模擬數據)
# ==========================================
with tab2:
    st.header("📝 校本數學資源庫")
    
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        grade = st.selectbox("選擇年級", ["全部", "中一", "中二", "中三", "中四", "中五", "中六"])
    with col_filter2:
        topic = st.selectbox("選擇主題", ["全部", "代數 (Algebra)", "幾何 (Geometry)", "微積分 (Calculus)", "概率與統計 (Statistics)"])

    st.subheader("📚 共享資源清單")
    
    # 範例數學卡片，展示 LaTeX 渲染效果
    with st.expander("📌 [中四] 一元二次方程：求根公式與判別式工作紙"):
        st.write("**提供者：** 張老師 | **更新日期：** 2026-10-01")
        st.write("**教學重點：** 判別式 $\\Delta = b^2 - 4ac$ 對根的性質之影響。")
        st.markdown("""
        **範例題目：**
        解方程 $$3x^2 - 5x + 2 = 0$$
        
        **解答思路：**
        使用求根公式 $x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$，其中 $a=3, b=-5, c=2$。
        """)
        st.button("📥 下載完整 PDF/Word 檔", key="btn1")

    with st.expander("📌 [中二] 全等與相似三角形課堂活動指南"):
        st.write("**提供者：** 李老師 | **更新日期：** 2026-09-25")
        st.write("**教學重點：** 利用 SAS, SSS, ASA, AAS, RHS 判定全等三角形。")
        st.write("配合 GeoGebra 動態幾何軟件進行分組探索。")
        st.button("📥 下載完整 PDF/Word 檔", key="btn2")

# ==========================================
# Tab 3: AI 數學擬題助手
# ==========================================
with tab3:
    st.header("🤖 AI 數學命題與診斷助手")
    st.write("輸入你的教學主題與難度，AI 會自動生成包含答案與解題步驟的 LaTeX 題目。")

    col1, col2 = st.columns(2)
    with col1:
        input_topic = st.text_input("題目主題 / 章節", value="二次函數的最大值與最小值")
        difficulty = st.select_slider("題目難度", options=["基礎", "中等", "進階 (DSE 乙部範例)"])
    with col2:
        num_questions = st.number_input("生成題目數量", min_value=1, max_value=5, value=2)
        include_steps = st.checkbox("包含詳細解題步驟", value=True)

    if st.button("✨ 生成題目", type="primary") and client:
        with st.spinner("AI 正在擬題中..."):
            prompt = f"""
請為香港中學數學科設計 {num_questions} 道題目。
- 主題：{input_topic}
- 難度：{difficulty}
- 是否包含詳細解題步驟：{include_steps}

【格式要求】：
1. 題目必須符合 DSE / 中學數學課程標準。
2. 所有數學符號與算式**必須使用 LaTeX 格式**，例如 $f(x) = ax^2 + bx + c$ 或 block 格式 $$f(x) = a(x-h)^2 + k$$。
3. 標註題目考核的數學概念。
"""
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5
                )
                st.markdown(response.choices[0].message.content)
            except Exception as e:
                st.error(f"擬題失敗：{e}")