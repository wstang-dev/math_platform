# --- 2/2 AI 整理校本表格（解決表格跑版與內文掉出問題）---
                if "transcript_text" in st.session_state and st.session_state["transcript_text"]:
                    with st.spinner("2/2 AI 正在分析會議內容，生成精準對齊 Word 表格的校本紀錄..."):
                        today_str = datetime.now().strftime("%d-%m-%Y")
                        clean_transcript = st.session_state["transcript_text"][:4000].replace("{", "(").replace("}", ")")
                        
                        prompt = (
                            "你是一位香港資深小學數學科科主席。\n"
                            "請【嚴格根據以下會議逐字稿的真實討論內容】，整理出一份完全符合嘉諾撒撒心學校（九龍塘）格式的「集體備課紀錄」。\n\n"
                            "【極重要表格排版規範】：\n"
                            "1. **儲存格內換行**：Markdown 表格內部【絕對禁止直接按 Enter 換行】！儲存格內若有多個點或縮排，必須使用 `<br>` 標籤連貫成同一行寫完，否則表格會破裂跑版。\n"
                            "2. **層次結構**：\n"
                            "   - 教學程序請寫成：`1. 介紹平行四邊形面積公式<br>&nbsp;&nbsp;a. 使用教具：三角尺，直角尺找出對應的底和高<br>&nbsp;&nbsp;b. 老師示範範用 GeoGebra 將平行四邊形分割再拼成長方形<br>&nbsp;&nbsp;c. 提供實例計算`\n"
                            "   - 教學重點請寫成：`1. 學生理解平行四邊形面積公式的核心教學重點<br><br>2. 學生找不到對應的高，忽略周界關係`\n"
                            "3. **嚴格欄位對齊**：每一行表格必須包含完整的 5 個欄位（用 `|` 隔開）：`| 教學重點/難點 | 教學程序/解決方法 | 資料來源 | 檢討及建議 | 備註 |`。\n\n"
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
                            "| 1. 平行四邊形面積計算<br><br>2. 學生未能找出底和對應的高 | 1. 介紹平行四邊形面積公式<br>&nbsp;&nbsp;a. 使用教具：三角尺，直角尺找出對應的底和高<br>&nbsp;&nbsp;b. 老師示範範用 GeoGebra 將平行四邊形分割再拼成長方形<br>&nbsp;&nbsp;c. 提供實例計算<br><br>2. 強調找到對應的底和高<br>&nbsp;&nbsp;a. 使用進展工作紙找底部和高的關係，強化學生對底部和高的理解 | 教科書<br>GeoGebra<br>工作紙 | 1. 在課堂上進行多次練習，以幫助學生鞏固理解 | [備註事項] |\n\n"
                            "會議逐字稿內容：\n" + clean_transcript
                        )
                        
                        llm_res = run_cf_ai(
                            "@cf/meta/llama-3.1-8b-instruct", 
                            {"Authorization": f"Bearer {cf_api_token}"}, 
                            payload={
                                "messages": [
                                    {"role": "system", "content": "你是一位專業的香港小學數學教學助理，表格排版無懈可擊，內容完全符合校本要求。"},
                                    {"role": "user", "content": prompt}
                                ],
                                "max_tokens": 2500,
                                "temperature": 0.1
                            }
                        )
                        if llm_res.get("success"):
                            st.session_state["current_note"] = llm_res.get("result", {}).get("response", "")
                            st.toast("✅ 校本紀錄生成成功！", icon="📋")
                        else:
                            st.error("❌ AI 生成紀錄失敗，請檢查 API 金鑰。")
