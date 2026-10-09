import streamlit as st
from datetime import datetime, date
import json
import os
import requests
import time
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
# Tab 1: 集體備課紀錄生成 (高深度、防機械式重複版)
# ==========================================
with tab1:
    st.header("🎙️ 集體備課會議紀錄生成 (貼上逐字稿 + 備課手冊)")
    
    if not cf_account_id or not cf_api_token:
        st.warning("⚠️ 提示：未偵測到 Cloudflare API 金鑰，請在左側邊欄 (Sidebar) 設定。")

    # --- 基本資料選擇區 ---
    st.subheader("📝 會議基本資料設定")
    col_g1, col_g2, col_g3 = st.columns(3)
    with col_g1:
        selected_grade = st.selectbox("📌 請選擇年級：", ["一", "二", "三", "四", "五", "六"], index=4)
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
            index=2
        )

    st.divider()

    # --- 輸入區：貼上 Gemini 逐字稿 + 上傳 PDF 備課手冊 ---
    st.subheader("📥 輸入會議資料與備課手冊")
    
    col_input1, col_input2 = st.columns([3, 2])
    
    with col_input1:
        transcript_input = st.text_area(
            "1️⃣ 請貼上 Gemini 轉寫好的廣東話/中文逐字稿：", 
            placeholder="請在此處貼上從 Gemini 複製過來的逐字稿內容...", 
            height=250
        )
        
    with col_input2:
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
                st.error("⚠️ 伺服器缺少 pypdf 模組。")
        elif guide_ext == "docx":
            if HAS_DOCX:
                doc = docx.Document(guide_file)
                guide_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
                for table in doc.tables:
                    for row in table.rows:
                        guide_text += "\n" + " | ".join([cell.text.strip() for cell in row.cells])
            else:
                st.error("⚠️ 伺服器缺少 python-docx。")
        else:
            guide_text = guide_text = guide_file.getvalue().decode("utf-8")
        
        if guide_text:
            st.success(f"📖 已讀取校本備課手冊：「{guide_file.name}」（共 {len(guide_text)} 字元）")

    st.divider()

    if st.button("🚀 開始結合逐字稿與手冊生成校本紀錄", type="primary"):
        if not cf_account_id or not cf_api_token:
            st.error("❌ 請先填寫 Cloudflare Account ID 與 API Token！")
        elif not transcript_input.strip():
            st.error("❌ 請先在左側框貼上逐字稿內容！")
        else:
            attendees_str = "、".join(selected_attendees) if selected_attendees else "全體數學科老師"
            recorder_str = selected_recorder
            formatted_date_str = selected_meeting_date.strftime("%d-%m-%Y")

            with st.spinner("🤖 AI 正在精準整理高質量、極具具體步驟的 Point Form 表格..."):
                clean_transcript = transcript_input[:5000].replace("{", "(").replace("}", ")")
                clean_guide = guide_text[:3500].replace("{", "(").replace("}", ")") if guide_text else "無提供額外手冊，請純粹根據逐字稿詳細內容展開教學程序。"

                prompt = (
                    "你是一位香港資深小學數學科科主席（CDC 課程專家）。\n"
                    "請閱讀【會議逐字稿】，精準提煉老師們討論的**單一特定課題（例如：三角形的面積）**，撰寫一份高品質、條理分明且極具教導性的「集體備課紀錄」。\n\n"
                    "【絕對禁止機械式重複！嚴格寫作限制規則】：\n"
                    "1. **結構歸納（最多 3 至 4 行 <tr>）**：\n"
                    "   - 切勿將每個小迷思都單獨拆成一行！請把全篇逐字稿歸納為 2 至 3 個綜合教學重點（例如：1. 觀念與底高對應、2. 面積公式與分割探究、3. 已知面積倒推計算）。\n"
                    "2. **具體且紮實的教學程序（Point Form）**：\n"
                    "   - **絕對禁止每一行都複製貼上相同的『提醒學生... 使用動畫... 嘗試計算』套話**！\n"
                    "   - 每一列的教學程序必須**完全針對該欄位的教學難點**寫出具體解決策略。必須包含逐字稿中的具體細節（如：圈出直角符號、使用 iPad 平行四邊形分割探究、倒推計算時先乘以 2 再除以底/高、圖像化展示）。\n"
                    "   - 步驟必須使用 `1.` `2.` `3.` 及 `a.` `b.`，且每一個小點之間必須加 `<br>` 換行！\n"
                    "3. **資料來源**：結合備課手冊及逐字稿，寫出具體參考（如：校本備課手冊、進展工作紙、課本動畫及 iPad 探究）。\n\n"
                    "【第一順位：會議逐字稿】：\n" + clean_transcript + "\n\n"
                    "【第二順位：參考校本備課手冊】：\n" + clean_guide + "\n\n"
                    "【請輸出以下 HTML 表格格式】：\n"
                    "### （ " + selected_grade + " ）年級數學科備課紀錄(" + selected_school_year + ")\n\n"
                    "**單元：** [AI 自動歸納，如：面積]\n"
                    "**課題：** [AI 自動歸納，如：三角形的面積]\n"
                    "**日期：** " + formatted_date_str + "  \n"
                    "**出席老師：** " + attendees_str + "  \n"
                    "**紀錄老師：** " + recorder_str + "  \n\n"
                    "<table border='1' style='width:100%; border-collapse:collapse; text-align:left;'>\n"
                    "  <tr style='background-color:#f2f2f2;'>\n"
                    "    <th style='width:30%; padding:8px;'>教學重點 / 難點</th>\n"
                    "    <th style='width:50%; padding:8px;'>教學程序 / 解決方法</th>\n"
                    "    <th style='width:20%; padding:8px;'>資料來源</th>\n"
                    "  </tr>\n"
                    "  <!-- 輸出 2 至 3 列極具針對性、內容充實、含 <br> 換行的 Point Form <tr> 區塊 -->\n"
                    "</table>"
                )
                
                llm_res = run_cf_ai(
                    "@cf/meta/llama-3.1-8b-instruct", 
                    {"Authorization": f"Bearer {cf_api_token}"}, 
                    payload={
                        "messages": [
                            {"role": "system", "content": "你是一位專業的小學數學教案專家，擅長根據會議逐字稿整理高質量、具體紮實的條列式教案，絕不輸出重複套話。"},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 2800,
                        "temperature": 0.1
                    },
                    is_json=True,
                    timeout=60
                )
                if llm_res.get("success"):
                    st.session_state["current_note"] = llm_res.get("result", {}).get("response", "")
                    st.session_state["current_grade"] = selected_grade
                    st.session_state["current_year"] = selected_school_year
                    st.toast("✅ 高質量備課紀錄生成成功！", icon="📋")
                else:
                    st.error("❌ AI 生成紀錄失敗，請檢查 API 金鑰。")

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
        refine_instruction = st.text_input("輸入您希望 AI 修改的指示：", placeholder="例如：請將資料來源改為工作紙 P.12，或增加倒推計算的具體提示。")
        
        if st.button("🤖 讓 AI 根據指示重新修訂表格", type="secondary"):
            if refine_instruction:
                with st.spinner("🤖 AI 正在修訂紀錄..."):
                    refine_prompt = (
                        "請根據以下【修改指示】，修改並重新輸出備課紀錄 HTML 表格。\n\n"
                        "【修改指示】：\n" + refine_instruction + "\n\n"
                        "【原本內容】：\n" + st.session_state["current_note"] + "\n\n"
                        "請保持點陣清單（Point Form）與標準 HTML 3 欄 <table> 格式，換行使用 <br>。"
                    )
                    
                    refine_res = run_cf_ai(
                        "@cf/meta/llama-3.1-8b-instruct", 
                        {"Authorization": f"Bearer {cf_api_token}"}, 
                        payload={
                            "messages": [
                                {"role": "system", "content": "你是一位聽從指令的專業教案修改助理。"},
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
                        st.toast("✅ 已成功修訂！", icon="✨")
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
            up_grade = st.selectbox("請選擇歸檔年級：", ["一年級", "二年級", "三年級", "四年級", "五年級", "六年級"], index=4, key="up_grade")
            
        up_file = st.file_uploader("選擇 Word 或 Markdown 檔案", type=["docx", "md", "txt"], key="up_doc_file")
        
        if st.button("🚀 匯入並存檔", type="primary", key="btn_import_doc"):
            if up_file:
                file_text = ""
                file_ext = up_file.name.split(".")[-1].lower()
                
                if file_ext == "docx":
                    if not HAS_DOCX:
                        st.error("⚠️ 伺服器缺少 python-docx 模組。")
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
                    st.success(f"✅ 檔案「{up_file.name}」已成功匯入！")
