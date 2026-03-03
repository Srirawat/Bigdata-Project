import streamlit as st
import os
from PIL import Image

# นำเข้าฟังก์ชันจากไฟล์ในโฟลเดอร์ต่างๆ
from Profile.Profile import show_profile
from Notion.Notion import render_notion
from Spam.Spam import render_spam
from Waste.Waste import render_waste

# ================== CONFIG & CSS ==================
st.set_page_config(page_title="Sirawat's Bigdata", page_icon="👤", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    /* ... (ใส่ CSS จากโค้ดเดิมทั้งหมด) ... */
    </style>
""", unsafe_allow_html=True)

# ================== SESSION ==================
if "page" not in st.session_state:
    st.session_state.page = "profile"

def nav_click(target: str):
    st.session_state.page = target

# ================== Sidebar ==================
with st.sidebar:
    st.markdown("<div class='sidebar-label'>📌 เลือกหน้า</div>", unsafe_allow_html=True)
    st.button("👤 Profile", key="profile_btn", use_container_width=True, on_click=nav_click, args=("profile",))
    st.button("📊 YouTube Data", key="notion_btn", use_container_width=True, on_click=nav_click, args=("notion",))
    st.button("📧 Spam", key="spam_btn", use_container_width=True, on_click=nav_click, args=("spam",))
    st.button("🗑️ Waste", key="waste_btn", use_container_width=True, on_click=nav_click, args=("waste",))
    st.markdown('<hr style="border:none;border-top:1px solid #e8e8e8;margin:10px 0 8px;">', unsafe_allow_html=True)

page = st.session_state.page

# ================== ROUTING ==================
if page == "profile":
    # จัดการรูปภาพหน้า Profile ตรงนี้ หรือย้ายไปในฟังก์ชัน show_profile ก็ได้ครับ
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(CURRENT_DIR, "Bigdata", "image", "FUJI0041.jpg")
    profile_image = None
    if os.path.exists(image_path):
        profile_image = Image.open(image_path)
    
    show_profile(
        name="นาย ศิรวัช ปัญญาสวรรค์",
        student_id="2313110526",
        major="Information Technology (IT)",
        interest="ผมเชื่อว่าข้อมูลมีอยู่ในทุกจุดและเป็นประโยชน์มหาศาลหากเรารู้วิธีการนำมาใช้ ผมจึงมีความสนใจในด้าน Data Science เพื่อฝึกฝนทักษะการวิเคราะห์และพยากรณ์แนวโน้ม ซึ่งจะช่วยให้การตัดสินใจในเรื่องที่ซับซ้อนมีความแม่นยำและมีประสิทธิภาพมากขึ้น",
        experience="- 📌Mini Project วิชา ITE-436: Big Data & Data Mining — ทำโปรเจ็กต์ Spam Email Classification ด้วย SMSSpamCollection Dataset\n"
                   "- ☁️ โปรเจ็กต์วิเคราะห์ข้อมูล YouTube ศึกษาความสัมพันธ์ระหว่างความยาววิดีโอและยอดวิวโดยใช้ Pandas และ seaborn\n"
                   " - 🧑‍💼Staff Event Maruya,Cosnatsu,TIGS,TGS\n"
                   " - 📸 ตากล้อง ถ่ายภาพในมหาวิทยาลัย,งานReshTech&ตั้งตัว,งานคอสเพลย์\n"
                   " - 💻 พัฒนาเซ็นเซอร์ตรวจนับจำนวนคนเข้า-ออกห้องสุขาโดยใช้ Arduino Board\n• ออกแบบและต่อวงจรเซ็นเซอร์อินฟราเรดเพื่อตรวจจับการเคลื่อนไหว\n• เขียนโปรแกรมควบคุมด้วย Arduino IDE\n• บันทึกและวิเคราะห์ข้อมูลจำนวนผู้ใช้งาน\n• จัดทำสื่อการนำเสนอผลงาน\n🔗 [ดูผลงานบน Canva](https://www.canva.com/design/DAF-udj88wI/md3_ETPfTtixlI_xnaffpA/edit?utm_content=DAF-udj88wI&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton)\n\n - 💻 โครงงานพัฒนาสื่อการเรียนรู้ดนตรี: การประยุกต์คาลิมบาร่วมกับ Arduino และจอ LCD\n• พัฒนาระบบแสดงผลโน้ตดนตรีแบบเรียลไทม์ผ่านจอ LCD\n• ออกแบบและเขียนโปรแกรมควบคุมไมโครคอนโทรลเลอร์\n• บูรณาการเทคโนโลยี IoT และดนตรีเพื่อสร้างสื่อการเรียนรู้เชิงโต้ตอบ\n• ทดสอบการใช้งานจริงกับผู้เริ่มต้นเรียนดนตรี\n🔗 [ดูผลงานบน Canva](https://www.canva.com/design/DAFJYF1JZcE/IsyUWigo5lqtQ_WqM9V4JQ/edit?utm_content=DAFJYF1JZcE&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton)"
,
        skills=["🐍 Python (Pandas, NumPy)", 
    "🤖 Machine Learning (Scikit-Learn)", 
    "🧠 Deep Learning (TensorFlow/Keras)", 
    "👁️ Computer Vision & NLP",
    "☁️ Streamlit Web Development", 
    "🕸️ Web Scraping (BeautifulSoup)", 
    "📊 Data Visualization (Altair)", 
    "⚙️ SQL & Big Data Concepts",
    "🛠️ Soft Skill: Problem Solving & Debugging",
            "📊 Soft Skill: Analytical Thinking",
            "🌱 Soft Skill: Fast Learning & Adaptability"],
        profile_image=profile_image
    )

elif page == "notion":
    render_notion()

elif page == "spam":
    render_spam()

elif page == "waste":
    render_waste()