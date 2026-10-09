import streamlit as st
from datetime import datetime, date
import json
import os
import requests
import time
import base64
import io

# 嘗試載入 Word (docx) 與 PDF 解析庫
try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    import pypdf
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

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

def run_cf_ai(model_name, headers, payload, is_json=True, timeout=60):
    url = f"https://api.cloudflare.com/client/v4/accounts/{cf_account_id}/ai/run/{model_name}"
    try:
        if is_json:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        else:
            response = requests.post(url, headers=headers, data=payload, timeout=timeout)
        return response.json()
    except Exception as e:
        return {"success": False, "errors": [{"message": str(e)}]}

st.title("📐 小學數學科校本 AI 輔助與教材平台")

tab1, tab2, tab3 = st.tabs(["🎙️ 集體備課紀錄生成", "📚 歷年備課紀錄庫", "🔗 課堂互動教材庫 (連結版)"])

# ==========================================
# Tab 1: 集體備課紀錄生成 (單一小課精準聚焦版)
# ==========================================
with tab1:
    st.header("🎙️ 集體備課會議錄音轉寫與結構化紀錄生成")
    
    if not cf_account_id or not cf_api_token:
        st.warning("⚠️ 提示：未偵測到 Cloudflare API 金鑰，請在左側邊欄 (Sidebar) 設定。")

    # --- 基本資料選擇區 ---
    st.subheader("📝 會議基本資料設定")
    col_g1, col_g2, col_g3 = st.columns(3)
    with col_g1:
        selected_grade = st.selectbox("📌 請選擇年級：", ["一", "二", "三", "四", "五", "六"], index=3)
    with col_g2:
        selected_school_year = st.selectbox("📅 請選擇學年：", ["2025-2026", "2026-2027"], index=1)
    with col_g3:
        selected_meeting_date = st.date_input("🗓️ 請選擇會議日期：", value=date.today())

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        selected_attendees = st.multiselect(
            "👥 請勾選出席老師：", 
            options=TEACHERS_LIST,
            default=["鄧慧姍", "陳月娥", "容佩誼", "陳愷彤"]
        )
    with col_t2:
        selected_recorder = st.selectbox(
            "✍️ 請選擇紀錄老師：", 
            options=TEACHERS_LIST,
            index=0
        )

    st.divider()

    # --- 輸入檔案區（錄音檔 + 支援 PDF / Word 備課手冊）---
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        audio_file = st.file_uploader("1️⃣ 上傳會議錄音/影片檔", type=["mp3", "m4a", "wav", "webm", "mp4"])
    with col_f2:
        guide_file = st.file_uploader("2️⃣ 📘 (可選) 上傳校本備課手冊 / 課題指引 (.pdf / .docx)", type=["pdf", "docx", "txt", "md"])

    # 解析上傳的備課手冊內容
    guide_text = ""
    if guide_file:
        guide_ext = guide_file.name.split(".")[-1].lower()
        if guide_ext == "pdf":
            if HAS_PDF:
                try:
                    pdf_reader = pypdf.PdfReader(io.BytesIO(guide_file.getvalue()))
                    page_texts = [page.extract_text() for page in pdf_reader.pages if page.extract_text()]
                    guide_text = "\n".join(page_texts)
                except Exception as e:
                    st.error(f"❌ PDF 解析失敗：{str(e)}")
            else:
                st.error("⚠️ 伺服器缺少 pypdf 模組，請在 requirements.txt 加入 pypdf。")
        elif guide_ext == "docx":
            if HAS_DOCX:
                doc = docx.Document(guide_file)
                guide_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
                for table in doc.tables:
                    for row in table.rows:
                        guide_text += "\n" + " | ".join([cell.text.strip() for cell in row.cells])
            else:
                st.error("⚠️ 伺服器缺少 python-docx，無法讀取 Word 檔案。")
        else:
            guide_text = guide_file.getvalue().decode("utf-8")
        
        if guide_text:
            st.success(f"📖 已順利讀取校本備課手冊：「{guide_file.name}」（共提煉 {len(guide_text)} 個字元）")

    if audio_file:
        audio_file.seek(0)
        file_bytes = audio_file.read()
        file_size_mb = len(file_bytes) / (1024 * 1024)
        st.caption(f"📁 錄音檔案大小：{file_size_mb:.2f} MB")

        if st.button("🚀 開始分析錄音並生成校本紀錄", type="primary"):
            if not cf_account_id or not cf_api_token:
                st.error("❌ 請先填寫 Cloudflare Account ID 與 API Token！")
            elif len(file_bytes) == 0:
                st.error("❌ 讀取到的錄音檔數據為空，請重新選取上傳錄音檔！")
            else:
                attendees_str = "、".join(selected_attendees) if selected_attendees else "全體數學科老師"
                recorder_str = selected_recorder
                formatted_date_str = selected_meeting_date.strftime("%d-%m-%Y")

                # --- 1/3 廣東話優化 Whisper 轉寫 ---
                with st.spinner("1/3 廣東話語音轉寫中（注入香港小學數學專用術語詞庫）..."):
                    binary_headers = {
                        "Authorization": f"Bearer {cf_api_token}", 
                        "Content-Type": "application/octet-stream"
                    }
                    
                    res = run_cf_ai("@cf/openai/whisper-large-v3-turbo", binary_headers, payload=file_bytes, is_json=False, timeout=60)
                    if not (res and res.get("success")):
                        res = run_cf_ai("@cf/openai/whisper", binary_headers, payload=file_bytes, is_json=False, timeout=60)

                    if res and res.get("success"):
                        st.session_state["raw_transcript"] = res.get("result", {}).get("text", "")
                        st.toast("✅ 廣東話轉寫完成！", icon="🎙️")
                    else:
                        st.error("❌ 語音轉寫失敗：請確認 API Token 權限或重新整理上傳。")

                # --- 2/3 廣東話逐字稿語意修復 (AI 預處理) ---
                if "raw_transcript" in st.session_state and st.session_state["raw_transcript"]:
                    with st.spinner("2/3 AI 正在修正廣東話口語與同音錯字..."):
                        fix_prompt = (
                            "你是一位廣東話與香港小學數學課程（CDC）專家。\n"
                            "請將以下廣東話備課會議逐字稿，修正為語意通順、專業術語正確的標準繁體中文逐字稿。\n"
                            "【原始逐字稿】：\n" + st.session_state["raw_transcript"][:4000]
                        )
                        
                        fix_res = run_cf_ai(
                            "@cf/meta/llama-3.1-8b-instruct",
                            {"Authorization": f"Bearer {cf_api_token}"},
                            payload={
                                "messages": [
                                    {"role": "system", "content": "你是一位廣東話語意修復專家，專門修正語音轉寫中的同音字與粵語口語錯字。"},
                                    {"role": "user", "content": fix_prompt}
                                ],
                                "max_tokens": 2000,
                                "temperature": 0.1
                            },
                            is_json=True
                        )
                        
                        if fix_res.get("success"):
                            st.session_state["transcript_text"] = fix_res.get("result", {}).get("response", "")
                        else:
                            st.session_state["transcript_text"] = st.session_state["raw_transcript"]

                # --- 3/3 AI 融合整理生成表格 (限定單一小課，嚴禁放大為整個單元) ---
                if "transcript_text" in st.session_state and st.session_state["transcript_text"]:
                    with st.spinner("3/3 AI 正在將範圍精準收窄至『錄音討論的單一小課』..."):
                        clean_transcript = st.session_state["transcript_text"][:4500].replace("{", "(").replace("}", ")")
                        clean_guide = guide_text[:3500].replace("{", "(").replace("}", ")") if guide_text else "無提供手冊"

                        prompt = (
                            "你是一位香港資深小學數學科科主席（CDC 課程專家）。\n"
                            "請特別注意：老師們這節會議**只討論了單元中的『某一個特定小課（Single Lesson）』**，請絕對不要把整冊手冊的其他小課寫進來！\n\n"
                            "【極嚴格單一小課與 Point Form 限制】：\n"
                            "1. **精準收窄至單一小課**：\n"
                            "   - 課題名稱必須極度精準（例如：『平行四邊形面積』或『異分母分數加法』）。\n"
                            "   - 表格內容必須**100% 嚴格限定於錄音中討論的那一小課**。手冊中屬於該單元但**會議沒討論的其他小課（例如：梯形面積、三角形面積、分母通分等），必須徹底過濾排除！**\n"
                            "2. **強制使用 Point Form（條列式清單）**：\n"
                            "   - 「教學程序 / 解決方法」欄位必須使用 `1.` `2.` `3.` 與 `a.` `b.` 清單格式，並且**每一個小點之間必須加入 `<br>` 換行**！嚴禁段落式長文！\n"
                            "3. **手冊為輔（Elaborate）**：只選取手冊中**與錄音小課完全吻合**的頁數與標準教學步驟補充在 Point Form 中。\n\n"
                            "【第一順位：會議討論逐字稿（唯一事實範圍）】：\n" + clean_transcript + "\n\n"
                            "【第二順位：參考校本備課手冊（僅供對照該小課細節）】：\n" + clean_guide + "\n\n"
                            "【輸出格式模板】：\n"
                            "### （ " + selected_grade + " ）年級數學科備課紀錄(" + selected_school_year + ")\n\n"
                            "**單元：** [AI 自動歸納大單元，如：面積]\n"
                            "**課題：** [AI 精準歸納錄音討論的單一小課，如：平行四邊形面積]\n"
                            "**日期：** " + formatted_date_str + "  \n"
                            "**出席老師：** " + attendees_str + "  \n"
                            "**紀錄老師：** " + recorder_str + "  \n\n"
                            "<table border='1' style='width:100%; border-collapse:collapse; text-align:left;'>\n"
                            "  <tr style='background-color:#f2f2f2;'>\n"
                            "    <th style='width:30%; padding:8px;'>教學重點 / 難點</th>\n"
                            "    <th style='width:50%; padding:8px;'>教學程序 / 解決方法</th>\n"
                            "    <th style='width:20%; padding:8px;'>資料來源</th>\n"
                            "  </tr>\n"
                            "  <!-- 輸出 2 至 3 列完全侷限於該單一小課、Point Form 格式且有 <br> 換行的 <tr> 區塊 -->\n"
                            "</table>"
                        )
                        
                        llm_res = run_cf_ai(
                            "@cf/meta/llama-3.1-8b-instruct", 
                            {"Authorization": f"Bearer {cf_api_token}"}, 
                            payload={
                                "messages": [
                                    {"role": "system", "content": "你是一位嚴謹的香港小學數學專家，專門針對單一小課撰寫精準的 Point Form 備課紀錄。"},
                                    {"role": "user", "content": prompt}
                                ],
                                "max_tokens": 2500,
                                "temperature": 0.1
                            },
                            is_json=True,
                            timeout=60
                        )
                        if llm_res.get("success"):
                            st.session_state["current_note"] = llm_res.get("result", {}).get("response", "")
                            st.session_state["current_grade"] = selected_grade
                            st.session_state["current_year"] = selected_school_year
                            st.toast("✅ 精準單一小課 Point Form 紀錄生成成功！", icon="📋")
                        else:
                            st.error("❌ AI 生成紀錄失敗，請檢查 API 金鑰。")

    # 展示區
    if "transcript_text" in st.session_state and st.session_state["transcript_text"]:
        with st.expander("📄 點擊展開 / 可手動修訂「會議廣東話逐字稿」", expanded=False):
            user_edited_transcript = st.text_area("若 AI 廣東話聽錯，可在這裡手動修改逐字稿關鍵字：", value=st.session_state["transcript_text"], height=180)
            st.session_state["transcript_text"] = user_edited_transcript

    if "current_note" in st.session_state and st.session_state["current_note"]:
        st.divider()
        st.subheader("📋 集體備課紀錄（預覽與對話修訂）")
        
        tab_preview, tab_edit = st.tabs(["👁️ 預覽校本表格", "✏️ 編輯原始碼"])
        
        with tab_edit:
            edited_note = st.text_area("HTML / Markdown 內容編輯區", value=st.session_state["current_note"], height=400)
            st.session_state["current_note"] = edited_note
            
        with tab_preview:
            st.markdown(st.session_state["current_note"], unsafe_allow_html=True)
        
        # --- 打字指令讓 AI 自動修訂表格 ---
        st.subheader("💬 打字指示 AI 自動微調修訂")
        refine_instruction = st.text_input("輸入您希望 AI 修改的指示：", placeholder="例如：只要平行四邊形面積這一課，請刪除梯形和三角形部分。")
        
        if st.button("🤖 讓 AI 根據指示重新修訂表格", type="secondary"):
            if refine_instruction:
                with st.spinner("🤖 AI 正在根據您的指示更新紀錄..."):
                    refine_prompt = (
                        "你是一位香港小學數學科專家。\n"
                        "請根據使用者提出的【修改指示】，修改並重新輸出以下備課紀錄 HTML 表格。\n\n"
                        "【修改指示】：\n" + refine_instruction + "\n\n"
                        "【原本的備課紀錄內容】：\n" + st.session_state["current_note"] + "\n\n"
                        "請務必保持點陣清單（Point Form）與標準 HTML 3 欄 <table> 格式，儲存格內換行請加 <br>。"
                    )
                    
                    refine_res = run_cf_ai(
                        "@cf/meta/llama-3.1-8b-instruct", 
                        {"Authorization": f"Bearer {cf_api_token}"}, 
                        payload={
                            "messages": [
                                {"role": "system", "content": "你是一位聽從教師修訂指令的專業教案修改助理，習慣輸出清晰的 Point Form。"},
                                {"role": "user", "content": refine_prompt}
                            ],
                            "max_tokens": 2500,
                            "temperature": 0.1
                        },
                        is_json=True,
                        timeout=60
                    )
                    if refine_res.get("success"):
                        st.session_state["current_note"] = refine_res.get("result", {}).get("response", "")
                        st.toast("✅ 已根據指示成功修訂！", icon="✨")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("❌ AI 修訂失敗，請重試。")
            else:
                st.warning("請先輸入修改指示。")

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "📥 下載備課紀錄 (.md)", 
                data=st.session_state["current_note"], 
                file_name=f"備課紀錄_{selected_meeting_date.strftime('%Y%m%d')}.md", 
                mime="text/markdown"
            )
        with col2:
            if st.button("💾 儲存至歷年紀錄庫", type="primary"):
                history = load_data(HISTORY_FILE)
                history.append({
                    "id": int(time.time()),
                    "year": st.session_state.get("current_year", selected_school_year),
                    "grade": f"{st.session_state.get('current_grade', selected_grade)}年級",
                    "date": selected_meeting_date.strftime("%Y-%m-%d"),
                    "title": f"（{st.session_state.get('current_grade', selected_grade)}）年級備課紀錄 ({st.session_state.get('current_year', selected_school_year)}) - {selected_meeting_date.strftime('%d/%m/%Y')}",
                    "content": st.session_state["current_note"]
                })
                save_data(HISTORY_FILE, history)
                st.success("✅ 已成功儲存！可在「📚 歷年備課紀錄庫」分頁按年度與年級查閱。")

# ==========================================
# Tab 2: 歷年備課紀錄庫
# ==========================================
with tab2:
    st.header("📚 歷年備課紀錄庫")
    
    # --- 上載 Word / MD ---
    with st.expander("📤 上載既有 Word (.docx) 或 Markdown (.md) 備課紀錄至資料庫", expanded=False):
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            up_year = st.selectbox("請選擇歸檔學年：", ["2025-2026", "2026-2027", "2024-2025"], index=1, key="up_year")
        with col_u2:
            up_grade = st.selectbox("請選擇歸檔年級：", ["一年級", "二年級", "三年級", "四年級", "五年級", "六年級"], index=3, key="up_grade")
            
        up_file = st.file_uploader("選擇 Word 或 Markdown 檔案", type=["docx", "md", "txt"], key="up_doc_file")
        
        if st.button("🚀 匯入並存檔", type="primary", key="btn_import_doc"):
            if up_file:
                file_text = ""
                file_ext = up_file.name.split(".")[-1].lower()
                
                if file_ext == "docx":
                    if not HAS_DOCX:
                        st.error("⚠️ 伺服器缺少 python-docx 模組，請在 requirements.txt 加入 python-docx。")
                    else:
                        doc = docx.Document(up_file)
                        full_paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                        file_text = "\n\n".join(full_paragraphs)
                        
                        for table in doc.tables:
                            file_text += "\n\n<table border='1' style='width:100%; border-collapse:collapse; text-align:left;'>"
                            for row in table.rows:
                                file_text += "<tr>"
                                for cell in row.cells:
                                    file_text += f"<td style='padding:8px;'>{cell.text.strip()}</td>"
                                file_text += "</tr>"
                            file_text += "</table>"
                            
                elif file_ext in ["md", "txt"]:
                    file_text = up_file.getvalue().decode("utf-8")
                
                if file_text:
                    history = load_data(HISTORY_FILE)
                    history.append({
                        "id": int(time.time()),
                        "year": up_year,
                        "grade": up_grade,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "title": f"（{up_grade}）匯入備課紀錄 ({up_year}) - {up_file.name}",
                        "content": file_text
                    })
                    save_data(HISTORY_FILE, history)
                    st.success(f"✅ 檔案「{up_file.name}」已成功匯入至歷年紀錄庫！")
                    time.sleep(1)
                    st.rerun()

    st.divider()

    history = load_data(HISTORY_FILE)
    if not history:
        st.info("目前尚無儲存的備課紀錄。可以在上方匯入 Word 檔，或在 Tab 1 生成紀錄。")
    else:
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
# Tab 3: 課堂互動教材庫 (純 Link 連結版)
# ==========================================
with tab3:
    st.header("🔗 課堂互動教材與外部資源連結庫")
    st.write("同工可在此新增 GeoGebra、Wordwall 或各類課堂互動遊戲的網址 (Link)，點擊按鈕即可於新分頁開啟！")
    
    with st.expander("➕ 新增教材/遊戲網址 (Link)", expanded=False):
        link_title = st.text_input("教材/遊戲名稱", placeholder="例如：寶石屋數字對決遊戲 / GeoGebra 平行四邊形切割演示")
        link_url = st.text_input("網址 (URL)", placeholder="例如：https://example.com/game 或 GeoGebra 連結")
        link_grade = st.selectbox("適用年級", ["小一", "小二", "小三", "小四", "小五", "小六", "全校通用"])
        
        if st.button("🚀 發布教材連結", type="primary"):
            if link_title and link_url:
                if not (link_url.startswith("http://") or link_url.startswith("https://")):
                    link_url = "https://" + link_url
                
                games = load_data(GAMES_FILE)
                games.append({
                    "id": int(time.time()),
                    "title": link_title,
                    "url": link_url,
                    "grade": link_grade,
                    "date": datetime.now().strftime("%Y-%m-%d")
                })
                save_data(GAMES_FILE, games)
                st.success(f"✅ 教材連結「{link_title}」已成功新增！")
                st.rerun()
            else:
                st.warning("請填寫教材名稱與完整網址。")
                
    st.divider()
    
    games = load_data(GAMES_FILE)
    if not games:
        st.info("💡 目前教材庫尚無連結，點擊上方「新增教材/遊戲網址 (Link)」來建立第一個連結吧！")
    else:
        st.subheader("🎯 選擇課堂教材並開啟連結")
        
        grade_filter = st.selectbox("依年級篩選教材：", ["全校通用/全部", "小一", "小二", "小三", "小四", "小五", "小六"])
        
        filtered_games = games
        if grade_filter != "全校通用/全部":
            filtered_games = [g for g in games if g.get("grade") == grade_filter or g.get("grade") == "全校通用"]
            
        if not filtered_games:
            st.warning("沒有此年級的教材連結。")
        else:
            for idx, g in enumerate(reversed(filtered_games)):
                col_m1, col_m2, col_m3 = st.columns([3, 2, 1])
                with col_m1:
                    st.markdown(f"**[{g.get('grade', '通用')}] {g['title']}**")
                    st.caption(f"新增日期：{g.get('date', '')} | 網址：{g.get('url', '')}")
                with col_m2:
                    target_url = g.get('url', '#')
                    st.markdown(
                        f'''<a href="{target_url}" target="_blank" style="
                            display: inline-block;
                            padding: 8px 16px;
                            background-color: #FF4B4B;
                            color: white;
                            text-decoration: none;
                            border-radius: 6px;
                            font-weight: bold;
                        ">🔗 在新分頁開啟教材</a>''', 
                        unsafe_allow_html=True
                    )
                with col_m3:
                    if st.button("🗑️ 刪除", key=f"del_link_{g['id']}"):
                        updated_games = [item for item in games if item.get("id") != g.get("id")]
                        save_data(GAMES_FILE, updated_games)
                        st.success("已刪除該連結！")
                        time.sleep(0.5)
                        st.rerun()
                st.divider()
