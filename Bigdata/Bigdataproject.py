# main/Bigdata/Bigdataproject.py
import streamlit as st
from bs4 import BeautifulSoup
from urllib.parse import unquote
from pathlib import Path
from PIL import Image
from io import BytesIO
import tempfile
import base64, zipfile, io, os, re, numpy as np
import csv

# ================== CONFIG ==================
st.set_page_config(page_title="Profile + Notion + Spam + Waste", layout="wide")

# ---------- FIXED PATHS ----------
ROOT = Path("main/Bigdata").resolve()
IMG_PROFILE_PATH = ROOT / "image" / "FUJI0041.jpg"
SPAM_MODEL_PATH = ROOT / "spam_model.pkl"
SPAM_VECT_PATH = ROOT / "vectorizer.pkl"
SPAM_DATA_PATH = ROOT / "SMSSpamCollection.csv"
WASTE_MODEL_PATH = ROOT / "waste_model.keras"

# ================== CSS ==================
st.markdown(
    """
    <style>
    :root { --brand:#4CAF50; --radius:16px; --shadow:0 4px 14px rgba(0,0,0,0.08); }
    [data-testid="stSidebar"]{
      background:#f6f8f7; border-right:4px solid var(--brand);
      box-shadow:0 2px 12px rgba(0,0,0,0.06); padding:12px 14px;
    }
    .sidebar-label{font-weight:700;color:#2c3e50;margin-bottom:10px;font-size:18px;}
    .card{background:#fff;border:1px solid #eaeaea;border-radius:16px;
          box-shadow:0 4px 14px rgba(0,0,0,0.08);padding:22px;margin-bottom:18px;}
    .subtle{color:#607d8b;font-size:13px;margin-top:-4px;}
    </style>
    """,
    unsafe_allow_html=True
)

# ================== SESSION ==================
if "page" not in st.session_state:
    st.session_state.page = "profile"

def nav_click(target: str):
    st.session_state.page = target

# ================== Helper ==================
def _img(img, caption=None):
    try:
        st.image(img, caption=caption, use_container_width=True)
    except TypeError:
        st.image(img, caption=caption, use_column_width=True)

# ================== Sidebar ==================
with st.sidebar:
    st.markdown("<div class='sidebar-label'>📌 เลือกหน้า</div>", unsafe_allow_html=True)
    st.button("👤 Profile", key="profile_btn", use_container_width=True, on_click=nav_click, args=("profile",))
    st.button("🗒️ Notion", key="notion_btn", use_container_width=True, on_click=nav_click, args=("notion",))
    st.button("📧 Spam", key="spam_btn", use_container_width=True, on_click=nav_click, args=("spam",))
    st.button("🗑️ Waste", key="waste_btn", use_container_width=True, on_click=nav_click, args=("waste",))
    st.caption(f"📂 ROOT: {ROOT}")

page = st.session_state.page

# ================== PAGE 1: Profile ==================
def show_profile(name, student_id, major, interest, experience, skills, img_url=None):
    st.title("👤 Profile Page")
    img_html = f'<img src="{img_url}" width="120" style="border-radius:50%; border:3px solid #4CAF50;">' if img_url else ""
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:20px; padding:20px;
                    border-radius:15px; background-color:#f9f9f9; box-shadow:2px 2px 10px #ddd;">
            {img_html}
            <div>
                <h2 style="margin-bottom:5px;">{name}</h2>
                <p><b>รหัสนักศึกษา:</b> {student_id}<br>
                <b>สาขา:</b> {major}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.subheader("💡 ความสนใจด้าน Data Science / Data Mining")
    st.info(interest)
    st.subheader("🚀 ประสบการณ์")
    st.write(experience)
    st.subheader("🛠️ Skillset")
    cols = st.columns(2)
    for i, skill in enumerate(skills):
        with cols[i % 2]:
            st.success(skill)
    st.markdown("---")
    st.success("🎉 ขอบคุณที่เข้ามาชมโปรไฟล์ครับ")

# ================== PAGE 2: Notion ==================
def render_notion():
    st.markdown("<h2>🗒️ Notion</h2><div class='subtle'>แนบไฟล์จาก Notion Export (ZIP/HTML)</div>", unsafe_allow_html=True)
    up = st.file_uploader("อัปโหลด Notion HTML หรือ ZIP", type=["html","htm","zip"])
    if not up:
        st.info("คำแนะนำ: ให้อัปโหลดไฟล์ ZIP จาก Notion Export เพื่อให้รูป/สไตล์แสดงครบ")
        return

    suffix = Path(up.name).suffix.lower()
    if suffix in [".html", ".htm"]:
        html = up.read().decode("utf-8", errors="ignore")
        st.components.v1.html(html, height=820, scrolling=True)
        return

    if suffix == ".zip":
        try:
            with tempfile.TemporaryDirectory() as td:
                tmpdir = Path(td)
                with zipfile.ZipFile(io.BytesIO(up.read())) as z:
                    z.extractall(tmpdir)
                html_files = list(tmpdir.rglob("*.html"))
                if not html_files:
                    st.error("ไม่พบไฟล์ HTML ภายใน ZIP")
                    return
                candidate = next((p for p in html_files if p.name.lower()=="index.html"), html_files[0])
                html = candidate.read_text(encoding="utf-8", errors="ignore")
                st.components.v1.html(html, height=820, scrolling=True)
        except Exception as e:
            st.error(f"อ่าน ZIP ไม่สำเร็จ: {e}")

# ================== PAGE 3: Spam ==================
def load_sms_dataset_safely(path_str: str):
    import pandas as pd
    for sep in ["\t", ","]:
        for enc in ("utf-8", "latin1", "utf-8-sig"):
            try:
                df = pd.read_csv(path_str, sep=sep, header=None, encoding=enc, engine="python", on_bad_lines="warn")
                if df.shape[1] >= 2:
                    first = df.iloc[:, 0].astype(str)
                    rest = df.iloc[:, 1:].astype(str).agg(" ".join, axis=1)
                    return pd.DataFrame({"label": first, "message": rest})
            except Exception:
                continue
    raise RuntimeError("ไม่สามารถอ่านไฟล์ได้")

def render_spam():
    import pandas as pd
    import joblib
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import LinearSVC
    from sklearn.naive_bayes import MultinomialNB, ComplementNB
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, roc_auc_score, roc_curve, classification_report

    st.markdown("<h2>📧 SMS/Email Spam</h2>", unsafe_allow_html=True)
    txt = st.text_area("ข้อความที่ต้องการทำนาย", height=100, placeholder="เช่น: Win a FREE iPhone now!")

    if st.button("ทำนาย", use_container_width=True):
        if not txt.strip():
            st.warning("กรุณาใส่ข้อความก่อนทำนาย")
        elif not (SPAM_MODEL_PATH.exists() and SPAM_VECT_PATH.exists()):
            st.error(f"ไม่พบไฟล์โมเดลที่ {SPAM_MODEL_PATH} หรือ {SPAM_VECT_PATH}")
        else:
            model = joblib.load(SPAM_MODEL_PATH)
            vectorizer = joblib.load(SPAM_VECT_PATH)
            X = vectorizer.transform([txt])
            y = model.predict(X)[0]
            st.success(f"ผลทำนาย: **{'Spam' if y==1 else 'Ham'}**")

    st.markdown("---")
    if st.button("🚀 Run report (ใช้ไฟล์คงที่ใน main/Bigdata/)"):
        if not SPAM_DATA_PATH.exists():
            st.error(f"ไม่พบไฟล์ข้อมูลที่ {SPAM_DATA_PATH}")
            return
        df = load_sms_dataset_safely(str(SPAM_DATA_PATH))
        df["label"] = df["label"].astype(str).str.lower().map({"ham":0,"spam":1})
        df = df[df["label"].isin([0,1])].dropna(subset=["message"]).drop_duplicates()

        X_train, X_test, y_train, y_test = train_test_split(df["message"], df["label"], test_size=0.2, random_state=42)
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1,2), max_features=5000)
        models = {
            "LogisticRegression": LogisticRegression(max_iter=2000),
            "LinearSVC": LinearSVC(),
            "MultinomialNB": MultinomialNB(),
            "ComplementNB": ComplementNB(),
            "RandomForest": RandomForestClassifier(n_estimators=100, random_state=42),
        }

        rows = []
        for name, clf in models.items():
            pipe = Pipeline([("vec", vectorizer), ("clf", clf)])
            pipe.fit(X_train, y_train)
            y_pred = pipe.predict(X_test)
            y_prob = pipe.predict_proba(X_test)[:,1] if hasattr(clf,"predict_proba") else None
            rows.append({
                "Model": name,
                "Accuracy": accuracy_score(y_test,y_pred),
                "Precision": precision_score(y_test,y_pred),
                "Recall": recall_score(y_test,y_pred),
                "F1": f1_score(y_test,y_pred),
                "ROC-AUC": roc_auc_score(y_test,y_prob) if y_prob is not None else None
            })
        st.dataframe(pd.DataFrame(rows))

# ================== PAGE 4: Waste ==================
@st.cache_resource
def load_keras_model(path: str):
    import tensorflow as tf
    return tf.keras.models.load_model(path)

def render_waste():
    st.markdown("<h2>🗑️ Waste Classification</h2>", unsafe_allow_html=True)

    class_names_str = st.text_input("ชื่อคลาส (คั่นด้วยจุลภาค)", value="organic,reuse")
    class_names = [c.strip() for c in class_names_str.split(",") if c.strip()]
    src = st.radio("เลือกแหล่งภาพ", ["อัปโหลดไฟล์", "ถ่ายจากกล้อง"], horizontal=True)

    uploaded_img = None
    if src == "อัปโหลดไฟล์":
        up_img = st.file_uploader("อัปโหลดรูป", type=["jpg","jpeg","png"])
        if up_img: uploaded_img = Image.open(up_img).convert("RGB")
    else:
        cam_img = st.camera_input("ถ่ายภาพ")
        if cam_img: uploaded_img = Image.open(cam_img).convert("RGB")

    if st.button("Predict"):
        if not WASTE_MODEL_PATH.exists():
            st.error(f"ไม่พบไฟล์โมเดลที่ {WASTE_MODEL_PATH}")
            return
        if uploaded_img is None:
            st.warning("กรุณาอัปโหลด/ถ่ายภาพก่อน")
            return

        import tensorflow as tf
        model = load_keras_model(str(WASTE_MODEL_PATH))
        H, W = 224, 224
        img_resized = uploaded_img.resize((W, H))
        arr = np.asarray(img_resized, dtype="float32")/255.0
        arr = np.expand_dims(arr, axis=0)
        pred = model.predict(arr)[0]
        idx = int(np.argmax(pred))
        conf = float(pred[idx])
        label = class_names[idx] if idx < len(class_names) else f"Class {idx}"
        st.success(f"ผลทำนาย: **{label}** | ความมั่นใจ {conf:.2%}")
        _img(img_resized, caption=f"ภาพที่ใช้ทำนาย ({W}x{H})")

    # ---- สรุปการประยุกต์ใช้งานจริง ----
    st.markdown("---")
    st.subheader("📌 สรุปการประยุกต์ใช้งานจริง & ประโยชน์")
    st.markdown("""
คัดแยกขยะอัจฉริยะ (Smart Bins / MRF): ติดกล้องที่ถังขยะหรือสายพานลำเลียงให้ระบบจำแนกประเภทอัตโนมัติ ลดภาระคนงาน และเพิ่มความแม่นยำการรีไซเคิล  
IoT + กล้อง ณ จุดทิ้งขยะ: แจ้งเตือนเมื่อพบการทิ้งผิดประเภท (เช่น ขยะอันตรายปะปน) หรือคัดแยกเบื้องต้นก่อนเข้าระบบหลัก  
งานเทศบาล/มหาวิทยาลัย/ห้างฯ: สื่อสาร “ทิ้งให้ถูกที่” แบบเรียลไทม์ผ่านจอ/แอป ช่วยปรับพฤติกรรมประชาชนและเพิ่มอัตรารีไซเคิล  
ธุรกิจรีไซเคิล/โลจิสติกส์: ตรวจคุณภาพวัสดุเข้าโรงรีไซเคิล ออกใบรับรองหรือคำนวณมูลค่าจากประเภทวัสดุได้รวดเร็ว  
ประโยชน์ทางเศรษฐกิจ & สิ่งแวดล้อม: ลดต้นทุนแรงงานและความผิดพลาด เพิ่มอัตรารีไซเคิล ลดของเสียฝังกลบและการปล่อยก๊าซเรือนกระจก  
ต่อยอดโมเดล: เก็บภาพจริงหน้างานมาปรับปรุงชุดข้อมูล, ทำ active learning, เพิ่มคลาส/ย่อยคลาส (เช่น พลาสติกใส/ทึบ), และติดตามผลแบบ dashboard
    """)

# ================== ROUTING ==================
if page == "profile":
    if IMG_PROFILE_PATH.exists():
        img = Image.open(IMG_PROFILE_PATH)
        buf = BytesIO(); img.convert("RGB").save(buf, format="JPEG")
        img_b64 = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"
    else:
        img_b64 = None
        st.caption(f"ไม่พบรูปโปรไฟล์ที่ {IMG_PROFILE_PATH}")

    show_profile(
        name="นาย ศิรวัช ปัญญาสวรรค์",
        student_id="2313110526",
        major="Information Technology",
        interest="ผมสนใจด้าน Data Science เพราะข้อมูลช่วยตัดสินใจได้อย่างมีเหตุผลและท้าทายในการค้นหารูปแบบซ่อนอยู่ในข้อมูล",
        experience="- 📌Mini Project วิชา ITE-436: Big Data & Data Mining — Spam Email Classification\n"
                  "- ☁️ วิเคราะห์ข้อมูล YouTube ยอดวิวกับความยาววิดีโอด้วย Pandas และ Seaborn\n"
                  "- 🧑‍💼Staff Event Maruya, Cosnatsu, TIGS, TGS\n"
                  "- 📸 ถ่ายภาพในมหาวิทยาลัย งาน ReshTech & ตั้งตัว",
        skills=["🐍 Python", "⚙️ SQL", "☁️ Streamlit", "🗄️ BigQuery", "✅ Excel", "📊 HTML"],
        img_url=img_b64
    )
elif page == "notion":
    render_notion()
elif page == "spam":
    render_spam()
elif page == "waste":
    render_waste()
