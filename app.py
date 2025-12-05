# app.py — Streamlit Dashboard สำหรับ Environmental & Water Quality Monitoring
# รันใน Colab: https://colab.research.google.com แล้วเลือก "Open in Streamlit" หรือ deploy ฟรีที่ https://share.streamlit.io

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import google.generativeai as genai
import os

# === ตั้งค่า Gemini API (ได้ฟรีจาก Google AI Studio) ===
# วิธีได้ API Key: ไป https://aistudio.google.com → ได้ key ฟรี → วางด้านล่าง
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else st.text_input("ใส่ Gemini API Key", type="password")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')  # หรือ gemini-2.0-exp ถ้ามี

st.set_page_config(page_title="Environmental & Water Quality Dashboard", layout="wide")
st.title("Environmental & Water Quality Monitoring Dashboard")
st.markdown("โดยวิศวกรสิ่งแวดล้อมที่ผันตัวมาทำ IoT")

# === Sidebar ===
with st.sidebar:
    st.header("อัปเดตข้อมูลล่าสุด")
    pm25 = st.number_input("PM2.5 (µg/m³)", 0.0, 500.0, 45.0)
    hardness = st.number_input("Total Hardness (mg/L as CaCO₃)", 0.0, 1000.0, 268.0)
    temp = st.number_input("อุณหภูมิน้ำ (°C)", 0.0, 50.0, 28.0)
    ph = st.number_input("pH", 0.0, 14.0, 7.8)
    location = st.text_input("สถานที่", "กรุงเทพฯ")

    if st.button("ทำนาย + บันทึกข้อมูล"):
        new_data = pd.DataFrame([{
            "เวลาที่บันทึก": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "สถานที่": location,
            "PM2.5": pm25,
            "Hardness": hardness,
            "Temp": temp,
            "pH": ph
        }])
        if "data" not in st.session_state:
            st.session_state.data = new_data
        else:
            st.session_state.data = pd.concat([st.session_state.data, new_data], ignore_index=True)
        st.success("บันทึกแล้ว!")

# === เริ่มต้นข้อมูลตัวอย่าง ===
if "data" not in st.session_state or st.session_state.data.empty:
    st.session_state.data = pd.DataFrame({
        "เวลาที่บันทึก": pd.date_range(end=datetime.now(), periods=24, freq='H')[::-1].strftime("%Y-%m-%d %H:%M"),
        "สถานที่": ["กรุงเทพฯ"]*24,
        "PM2.5": [35,38,42,48,55,62,68,75,82,88,92,85,78,72,65,58,52,48,45,42,40,38,36,35],
        "Hardness": [220,225,235,245,255,268,275,282,290,295,292,285,278,270,265,268,265,260,255,250,245,240,235,230],
        "Temp": [28,28.5,29,30,31,32,32.5,32,31.5,30.5,30,29.5,29,28.8,28.5,28.3,28.2,28.1,28,28,28,28,28,28],
        "pH": [7.6,7.7,7.8,7.9,8.0,8.1,8.1,8.0,7.9,7.8,7.8,7.8,7.8,7.7,7.7,7.8,7.8,7.8,7.8,7.7,7.7,7.7,7.6,7.6]
    })

df = st.session_state.data
df["เวลาที่บันทึก"] = pd.to_datetime(df["เวลาที่บันทึก"])

# === แสดงกราฟ ===
col1, col2 = st.columns(2)
with col1:
    fig1 = px.line(df, x="เวลาที่บันทึก", y="PM2.5", title="PM2.5 Trend (24 ชม.)", color_discrete_sequence=["#FF4444"])
    fig1.add_hline(y=50, line_dash="dash", line_color="orange", annotation_text="เกินมาตรฐานไทย")
    fig1.add_hline(y=75, line_dash="dash", line_color="red", annotation_text="อันตราย")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    fig2 = px.line(df, x="เวลาที่บันทึก", y="Hardness", title="Total Hardness Trend", color_discrete_sequence=["#4488FF"])
    fig2.add_hline(y=300, line_dash="dash", line_color="orange", annotation_text="น้ำกระด้าง")
    fig2.add_hline(y=500, line_dash="dash", line_color="red", annotation_text="น้ำกระด้างมาก")
    st.plotly_chart(fig2, use_container_width=True)

# === สรุปสถานการณ์ปัจจุบัน + แจ้งเตือน ===
latest = df.iloc[-1]
st.subheader("สถานการณ์ล่าสุด")
col_a, col_b, col_c, col_d = st.columns(4)
with col_a:
    color = "red" if latest["PM2.5"] > 75 else "orange" if latest["PM2.5"] > 50 else "green"
    st.metric("PM2.5", f"{latest['PM2.5']:.1f} µg/m³", delta=f"{latest['PM2.5']-df['PM2.5'].iloc[-2]:+.1f}")
with col_b:
    hard_text = "น้ำกระด้างมาก" if latest["Hardness"] > 300 else "น้ำกระด้างปานกลาง" if latest["Hardness"] > 150 else "น้ำอ่อน"
    st.metric("Hardness", f"{latest['Hardness']:.0f} mg/L", delta=hard_text)
with col_c:
    st.metric("อุณหภูมิ", f"{latest['Temp']:.1f}°C")
with col_d:
    st.metric("pH", f"{latest['pH']:.1f}")

# === Gemini Prediction (สำคัญสุด!) ===
if GEMINI_API_KEY and st.button("Gemini ทำนาย 24 ชม. ข้างหน้า"):
    with st.spinner("Gemini กำลังวิเคราะห์..."):
        prompt = f"""
        ข้อมูลล่าสุด: PM2.5 = {latest['PM2.5']} µg/m³, Hardness = {latest['Hardness']} mg/L, Temp = {latest['Temp']}°C, pH = {latest['pH']}, สถานที่: {location}
        ทำนายค่า PM2.5 และ Hardness ในอีก 6, 12, 24 ชั่วโมงข้างหน้า
        และบอกคำแนะนำสั้น ๆ ภาษาไทย
        ตอบเป็น JSON เท่านั้น:
        {{
          "forecast": [{{"hours":6,"pm25":...,"hardness":...}}, ...],
          "alert": "ข้อความแจ้งเตือน",
          "recommend": "คำแนะนำ"
        }}
        """
        response = model.generate_content(prompt)
        try:
            import json
            result = json.loads(response.text)
            st.success("Gemini ทำนายเสร็จแล้ว!")
            st.json(result)
            if "alert" in result:
                st.error(result["alert"])
            if "recommend" in result:
                st.info(result["recommend"])
        except:
            st.write(response.text)

# === Chat กับ Gemini ===
st.subheader("ถาม Gemini ได้เลย!")
user_question = st.text_input("เช่น พรุ่งนี้ฝุ่นจะเยอะไหม?, น้ำแข็งนี้ดื่มได้หรือเปล่า?")
if user_question and GEMINI_API_KEY:
    with st.spinner("กำลังถาม Gemini..."):
        prompt_chat = f"คุณคือผู้เชี่ยวชาญสิ่งแวดล้อมในไทย ตอบสั้นกระชับและเป็นกันเอง: {user_question}\nข้อมูลล่าสุด: PM2.5={latest['PM2.5']}, Hardness={latest['Hardness']} mg/L, สถานที่: {location}"
        resp = model.generate_content(prompt_chat)
        st.write(resp.text)

# === ดาวน์โหลดข้อมูล ===
csv = df.to_csv(index=False).encode()
st.download_button("ดาวน์โหลดข้อมูล CSV", csv, "environmental_data.csv", "text/csv")
