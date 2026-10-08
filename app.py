from google import genai

# 初始化 Gemini
client = genai.Client(api_key=api_key)

# 1. 語音轉寫與整理備課紀錄（Gemini 可以直接讀取音訊檔！）
uploaded_file = client.files.upload(file=audio_file)
response = client.models.generate_content(
    model='gemini-1.5-flash',
    contents=[uploaded_file, "請根據這段數學科備課錄音，整理出結構化備課紀錄..."]
)
st.markdown(response.text)

# 2. AI 出題
response = client.models.generate_content(
    model='gemini-1.5-flash',
    contents=f"請設計 {num_questions} 道關於 {input_topic} 的數學題，使用 LaTeX 格式。"
)
st.markdown(response.text)
