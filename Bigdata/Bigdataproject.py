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

# ---------- FIXED PATHS (ตามที่ต้องการ) ----------
ROOT = Path("main/Bigdata").resolve()
IMG_PROFILE_PATH   = ROOT / "image" / "FUJI0041.jpg"
SPAM_MODEL_PATH    = ROOT / "spam_model.pkl"
SPAM_VECT_PATH     = ROOT / "vectorizer.pkl"
SPAM_DATA_PATH     = ROOT / "SMSSpamCollection.csv"   # ถ้าเป็น .tsv หรือ .txt เปลี่ยนชื่อไฟล์ให้ตรง
WASTE_MODEL_PATH   = ROOT / "waste_model.keras"       # หรือ .h5

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

# ================== Helpers ==================
def _img(img, caption=None):
    try:
        st.image(img, caption=caption, use_container_width=True)
    except TypeError:
        st.image(img, caption=caption, use_column_width=True)

def img_path_to_b64(path: Path) -> str | None:
    try:
        img = Image.open(path).convert("RGB")
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=90)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"
    except Exception:
        return None

# ===== Notion inline helpers =====
def data_uri_from_file(path: Path):
    try:
        mime = "image/png"
        if path.suffix.lower() in [".jpg", ".jpeg"]: mime = "image/jpeg"
        elif path.suffix.lower() == ".gif": mime = "image/gif"
        elif path.suffix.lower() == ".svg": mime = "image/svg+xml"
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return None

def _resolve_local_path(base_dir: Path, url: str):
    if not url or url.startswith(("http://", "https://", "data:")):
        return None
    url = url.split("?")[0].split("#")[0]
    url = unquote(url)
    candidate = (base_dir / url).resolve()
    if candidate.exists():
        return candidate
    try:
        candidate = (base_dir / Path(url)).resolve()
        if candidate.exists():
            return candidate
    except Exception:
        pass
    return None

def _inline_css_urls(css_text: str, base_dir: Path) -> str:
    def repl(m):
        raw = m.group(1).strip().strip('"').strip("'")
        p = _resolve_local_path(base_dir, raw)
        if p:
            uri = data_uri_from_file(p)
            if uri:
                return f"url('{uri}')"
        return f"url('{raw}')"
    return re.sub(r"url\((.*?)\)", repl, css_text, flags=re.IGNORECASE)

def inline_assets(html_text: str, base_dir: Path):
    soup = BeautifulSoup(html_text, "html.parser")
    # inline images
    for img in soup.find_all("img"):
        if not img.get("src"):
            for k in ("data-src","data-original","data-lazy-src"):
                if img.get(k): img["src"] = img.get(k); break
        src = img.get("src")
        p = _resolve_local_path(base_dir, src)
        if p:
            uri = data_uri_from_file(p)
            if uri: img["src"] = uri
    # inline CSS files
    for link in soup.find_all("link", rel="stylesheet"):
        href = link.get("href")
        p = _resolve_local_path(base_dir, href)
        if p and p.exists():
            try:
                css_text = p.read_text(encoding="utf-8", errors="ignore")
                css_text = _inline_css_urls(css_text, p.parent)
                style_tag = soup.new_tag("style")
                style_tag.string = css_text
                link.replace_with(style_tag)
            except Exception:
                pass
    return str(soup)

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
    # ไม่เปิดให้อัปโหลด/เลือก — ใช้ไฟล์คงที่ตามที่กำหนด
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
    with st.container():
        st.subheader("💡 ความสนใจด้าน Data Science / Data Mining")
        st.info(interest)
    with st.container():
        st.subheader("🚀 ประสบการณ์")
        st.write(experience)
    with st.container():
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

    # หน้านี้ยังคงต้องอัปโหลดไฟล์ (ไม่เกี่ยวกับพาธคงที่ของโปรเจกต์)
    up = st.file_uploader("อัปโหลด Notion HTML หรือ ZIP", type=["html","htm","zip"])
    if not up:
        st.info("คำแนะนำ: ให้อัปโหลดไฟล์ **ZIP** จาก Notion Export เพื่อให้รูป/สไตล์แสดงครบ")
        return

    suffix = Path(up.name).suffix.lower()
    if suffix in [".html", ".htm"]:
        st.warning("อัปโหลด HTML เดี่ยวอาจไม่เห็นรูป (relative path). แนะนำ ZIP")
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
                raw_html = candidate.read_text(encoding="utf-8", errors="ignore")
                inlined_html = inline_assets(raw_html, candidate.parent)
                st.components.v1.html(inlined_html, height=820, scrolling=True)
                num_imgs = sum(1 for _ in candidate.parent.rglob("*") if _.suffix.lower() in [".png",".jpg",".jpeg",".gif",".svg"])
                st.caption(f"✅ Inline assets เสร็จสิ้น ~{num_imgs} รูป")
        except Exception as e:
            st.error(f"อ่าน ZIP ไม่สำเร็จ: {e}")

# ================== PAGE 3: Spam ==================
def load_sms_dataset_safely(path_str: str):
    """
    คืนค่า DataFrame สองคอลัมน์: label, message
    รองรับไฟล์ TSV/CSV/TXT ที่มีตัวคั่นไม่สม่ำเสมอ โดยพยายามหลายวิธี
    """
    import pandas as pd
    p = Path(path_str)

    # 1) พยายามแบบ TSV (มาตรฐาน UCI)
    for enc in ("utf-8", "latin1", "utf-8-sig"):
        try:
            df = pd.read_csv(
                path_str,
                sep="\t",
                header=None,
                names=["label", "message"],
                encoding=enc,
                quoting=csv.QUOTE_NONE,
                engine="python",
                on_bad_lines="warn",
            )
            if df.shape[1] >= 2:
                return df[["label", "message"]]
        except Exception:
            pass

    # 2) ลอง CSV: ถ้ามากกว่า 2 คอลัมน์ ให้รวมคอลัมน์ที่เหลือกลับเป็นข้อความเดียว
    for enc in ("utf-8", "latin1", "utf-8-sig"):
        try:
            df = pd.read_csv(
                path_str,
                sep=",",
                header=None,
                encoding=enc,
                engine="python",
                on_bad_lines="warn",
            )
            if df.shape[1] >= 2:
                first = df.iloc[:, 0].astype(str)
                rest  = df.iloc[:, 1:].astype(str).agg(",".join, axis=1)
                return pd.DataFrame({"label": first, "message": rest})
        except Exception as e:
            last_err = e
            continue

    # ถ้าไม่สำเร็จจริง ๆ ให้โยน error สุดท้าย
    raise last_err if 'last_err' in locals() else RuntimeError("ไม่สามารถอ่านไฟล์ได้")

def render_spam():
    import pandas as pd
    # รองรับกรณีไม่มี matplotlib
    try:
        import matplotlib.pyplot as plt
        _HAS_MPL = True
    except ModuleNotFoundError:
        plt = None
        _HAS_MPL = False

    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import LinearSVC
    from sklearn.naive_bayes import MultinomialNB, ComplementNB
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score,
        confusion_matrix, roc_auc_score, roc_curve, classification_report
    )
    import joblib

    st.markdown("<h2>📧 SMS/Email Spam</h2><div class='subtle'>ทดสอบข้อความว่าเป็น Ham หรือ Spam</div>", unsafe_allow_html=True)

    # ----- กล่องทำนายข้อความเดี่ยว (ไม่ต้องเลือกไฟล์) -----
    st.markdown("### 🔎 ทำนายข้อความเดี่ยว")
    txt = st.text_area("ข้อความที่ต้องการทำนาย", height=100, placeholder="เช่น: Win a FREE iPhone now! Click link…")

    if st.button("ทำนาย", use_container_width=True):
        if not txt.strip():
            st.warning("กรุณาใส่ข้อความก่อนทำนาย")
        else:
            if not (SPAM_MODEL_PATH.exists() and SPAM_VECT_PATH.exists()):
                st.error(f"ไม่พบไฟล์โมเดล/เวกเตอร์ที่ต้องใช้:\n- {SPAM_MODEL_PATH}\n- {SPAM_VECT_PATH}\nกรุณาวางไฟล์ที่ตำแหน่งดังกล่าว")
            else:
                try:
                    model = joblib.load(str(SPAM_MODEL_PATH))
                    vectorizer = joblib.load(str(SPAM_VECT_PATH))
                    X = vectorizer.transform([txt])
                    if hasattr(model, "predict_proba"):
                        p = model.predict_proba(X)[0]
                        spam_idx = np.where(model.classes_ == 1)[0][0]
                        ham_idx  = np.where(model.classes_ == 0)[0][0]
                        st.success(f"ผลทำนาย: **{'Spam' if p[spam_idx] > p[ham_idx] else 'Ham'}** | Ham={p[ham_idx]:.4f}  Spam={p[spam_idx]:.4f}")
                    else:
                        y = model.predict(X)[0]
                        st.success(f"ผลทำนาย: **{'Spam' if y==1 else 'Ham'}**")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")

    st.markdown("---")

    # ----- ส่วนรายงานเทรน/เทียบโมเดล (ใช้พาธตายตัว ไม่ต้องเลือกไฟล์) -----
    st.header("รายงานเทรนและเปรียบเทียบโมเดล")
    if st.button("🚀 Run report (อ่านจากไฟล์คงที่ใน main/Bigdata/)"):
        if not SPAM_DATA_PATH.exists():
            st.error(f"ไม่พบไฟล์ข้อมูลที่ {SPAM_DATA_PATH}")
            st.stop()
        try:
            df = load_sms_dataset_safely(str(SPAM_DATA_PATH))
        except Exception as e:
            st.error(f"อ่านไฟล์ไม่สำเร็จ: {e}")
            st.stop()

        st.markdown("""
- แปลง **label**: `ham→0`, `spam→1`
- ลบข้อความว่าง (`NaN`) และซ้ำ
- แปลงข้อความด้วย **TfidfVectorizer(1,2)**
        """)

        df["label"] = df["label"].astype(str).str.strip().str.lower().map({"ham":0,"spam":1})
        before = len(df)
        df = df[df["label"].isin([0,1])]
        df = df.dropna(subset=["message"]).drop_duplicates(subset=["message"]).reset_index(drop=True)
        after = len(df)

        c1, c2 = st.columns(2)
        with c1:
            st.write("ตัวอย่าง 5 แถวแรก:", df.head())
        with c2:
            st.write(f"จำนวนตัวอย่างหลังทำความสะอาด: **{after}** (เดิม {before})")
            st.write("สัดส่วนคลาส:", df["label"].value_counts().rename({0:"ham(0)",1:"spam(1)"}))

        # เทรน/เทียบ
        X_train, X_test, y_train, y_test = train_test_split(
            df["message"].astype(str), df["label"].astype(int),
            test_size=0.2, random_state=42, stratify=df["label"].astype(int)
        )

        vectorizer = TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1,2), max_features=5000)
        models = {
            "LogisticRegression": LogisticRegression(max_iter=2000),
            "LinearSVC": LinearSVC(dual=True),
            "MultinomialNB": MultinomialNB(),
            "ComplementNB": ComplementNB(),
            "RandomForest": RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
        }

        rows, trained = [], {}
        with st.spinner("กำลังเทรนและเปรียบเทียบโมเดล..."):
            for name, clf in models.items():
                pipe = Pipeline([("vec", vectorizer), ("clf", clf)])
                pipe.fit(X_train, y_train)
                y_pred = pipe.predict(X_test)

                y_proba = None
                if hasattr(pipe.named_steps["clf"], "predict_proba"):
                    y_proba = pipe.predict_proba(X_test)[:,1]
                elif hasattr(pipe.named_steps["clf"], "decision_function"):
                    scores = pipe.decision_function(X_test)
                    if np.ndim(scores) > 1: scores = scores[:,1]
                    denom = (scores.max() - scores.min()) + 1e-12
                    y_proba = (scores - scores.min()) / denom

                acc = accuracy_score(y_test, y_pred)
                pre = precision_score(y_test, y_pred, pos_label=1, zero_division=0)
                rec = recall_score(y_test, y_pred, pos_label=1, zero_division=0)
                f1  = f1_score(y_test, y_pred, pos_label=1, zero_division=0)
                auc = roc_auc_score(y_test, y_proba) if y_proba is not None else np.nan

                rows.append({"Model": name, "Accuracy": acc, "Precision": pre, "Recall": rec, "F1": f1, "ROC-AUC": auc})
                trained[name] = (pipe, y_pred, y_proba)

        import pandas as pd
        res_df = pd.DataFrame(rows).sort_values(by=["F1","Accuracy"], ascending=False).reset_index(drop=True)
        st.dataframe(
            res_df.style.format("{:.4f}", subset=["Accuracy","Precision","Recall","F1","ROC-AUC"])
                        .highlight_max(axis=0, color='#d4edda', subset=["Accuracy","Precision","Recall","F1","ROC-AUC"]),
            use_container_width=True
        )

        best_name = res_df.iloc[0]["Model"]
        st.success(f"🏆 Best model: **{best_name}** (ตามค่า F1-Score)")
        best_pipe, best_pred, best_proba = trained[best_name]

        st.header("Evaluation ของโมเดลที่ชนะ")
        cm = confusion_matrix(y_test, best_pred, labels=[0,1])

        if _HAS_MPL:
            import matplotlib.pyplot as plt
            # Confusion Matrix
            fig1, ax1 = plt.subplots(figsize=(4,3))
            ax1.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
            ax1.set_xticks([0,1]); ax1.set_xticklabels(["ham(0)","spam(1)"])
            ax1.set_yticks([0,1]); ax1.set_yticklabels(["ham(0)","spam(1)"])
            ax1.set_xlabel("Predicted"); ax1.set_ylabel("True")
            for i in range(cm.shape[0]):
                for j in range(cm.shape[1]):
                    ax1.text(j, i, f"{cm[i, j]}", ha="center", va="center",
                             color="white" if cm[i, j] > cm.max()/2 else "black")
            st.pyplot(fig1, clear_figure=True)

            # ROC
            if best_proba is not None:
                from sklearn.metrics import roc_curve, roc_auc_score
                fpr, tpr, _ = roc_curve(y_test, best_proba)
                auc_val = roc_auc_score(y_test, best_proba)
                fig2, ax2 = plt.subplots(figsize=(4,3))
                ax2.plot(fpr, tpr, lw=2, label=f'ROC (AUC={auc_val:.2f})')
                ax2.plot([0,1],[0,1], lw=2, linestyle="--")
                ax2.set_xlabel("False Positive Rate"); ax2.set_ylabel("True Positive Rate")
                ax2.legend(loc="lower right")
                st.pyplot(fig2, clear_figure=True)
            else:
                st.info("โมเดลนี้ไม่มี probability/score จึงคำนวณ ROC-AUC ไม่ได้")
        else:
            st.info("ยังไม่ได้ติดตั้ง matplotlib — ติดตั้งก่อนเพื่อดูกราฟ (pip install matplotlib)")

        st.write("**Classification report:**")
        st.code(classification_report(y_test, best_pred, target_names=["ham(0)","spam(1)"], zero_division=0))

# ================== PAGE 4: Waste ==================
@st.cache_resource
def load_keras_model(path: str):
    import tensorflow as tf
    return tf.keras.models.load_model(path)

def render_waste():
    st.markdown("<h2>🗑️ Waste Classification</h2><div class='subtle'>อัปโหลดภาพหรือถ่ายภาพจากกล้อง + ใช้โมเดล Keras (.keras/.h5)</div>", unsafe_allow_html=True)

    class_names_str = st.text_input("ชื่อคลาส (คั่นด้วยจุลภาค, ลำดับต้องตรงกับตอนเทรน)", value="organic,reuse")
    class_names = [c.strip() for c in class_names_str.split(",") if c.strip()]

    # แหล่งภาพ
    src = st.radio("เลือกแหล่งภาพ", ["อัปโหลดไฟล์", "ถ่ายจากกล้อง (Camera)"], horizontal=True, key="waste_img_src")

    uploaded_img = None
    if src == "อัปโหลดไฟล์":
        up_img = st.file_uploader("อัปโหลดรูปภาพ", type=["jpg","jpeg","png"], key="waste_uploader")
        if up_img is not None:
            uploaded_img = Image.open(up_img).convert("RGB")
    else:
        cam_img = st.camera_input("ถ่ายภาพด้วยกล้อง", key="waste_camera")
        if cam_img is not None:
            uploaded_img = Image.open(cam_img).convert("RGB")

    if st.button("Predict", key="waste_predict_button"):
        if not WASTE_MODEL_PATH.exists():
            st.error(f"ไม่พบไฟล์โมเดลที่: {WASTE_MODEL_PATH}")
            return
        if uploaded_img is None:
            st.warning("กรุณาอัปโหลด/ถ่ายภาพก่อน")
            return

        try:
            import tensorflow as tf
            with st.spinner("กำลังโหลดโมเดลและทำนายผล..."):
                model = load_keras_model(str(WASTE_MODEL_PATH))

                ishape = model.inputs[0].shape
                H = int(ishape[1]) if ishape[1] is not None else 224
                W = int(ishape[2]) if ishape[2] is not None else 224

                img_resized = uploaded_img.resize((W, H))
                arr = np.asarray(img_resized, dtype="float32") / 255.0
                arr = np.expand_dims(arr, axis=0)

                pred = model.predict(arr)[0]
                idx  = int(np.argmax(pred))
                conf = float(pred[idx])

                label_show = f"Class {idx}"
                if class_names and len(class_names) > idx:
                    label_show = class_names[idx]

                st.success(f"ผลทำนาย: **{label_show}** | ความมั่นใจ {conf:.2%}")
                _img(img_resized, caption=f"ภาพที่ใช้ทำนาย ({W}×{H})")

                with st.expander("Probabilities (ทุกคลาส)"):
                    try:
                        import pandas as pd
                        names = class_names if (class_names and len(class_names) == len(pred)) else [f"Class_{i}" for i in range(len(pred))]
                        df_prob = pd.DataFrame({"class": names, "probability": pred})
                        st.dataframe(
                            df_prob.sort_values("probability", ascending=False)
                                   .reset_index(drop=True)
                                   .style.format({"probability": "{:.2%}"}),
                            use_container_width=True
                        )
                    except Exception:
                        st.write({f"Class {i}": p for i, p in enumerate(pred)})
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")

# ================== ROUTING ==================
if page == "profile":
    # โหลดรูปโปรไฟล์แบบพาธคงที่
    if IMG_PROFILE_PATH.exists():
        try:
            # ตรงตามที่ต้องการ: ใช้ Image.open("main/Bigdata/image/FUJI0041.jpg")
            img = Image.open(str(IMG_PROFILE_PATH))
            buf = BytesIO(); img.convert("RGB").save(buf, format="JPEG", quality=90)
            img_b64 = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"
        except Exception as e:
            img_b64 = None
            st.caption(f"โหลดรูปโปรไฟล์ล้มเหลว: {e}")
    else:
        img_b64 = None
        st.caption(f"ไม่พบรูปโปรไฟล์ที่ {IMG_PROFILE_PATH}")

    show_profile(
        name="นาย ศิรวัช ปัญญาสวรรค์",
        student_id="2313110526",
        major="Information Technology",
        interest="ผมสนใจด้าน Data Science เพราะมองว่า “ข้อมูล” สามารถบอกเล่าเรื่องราวและช่วยให้ตัดสินใจได้อย่างมีเหตุผล โดยเฉพาะการหาความสัมพันธ์หรือรูปแบบที่ซ่อนอยู่ในข้อมูล ซึ่งเป็นส่วนที่ท้าทายและสนุกมาก",
        experience="- 📌Mini Project วิชา ITE-436: Big Data & Data Mining — ทำโปรเจ็กต์ Spam Email Classification ด้วย SMSSpamCollection Dataset\n"
                  "- ☁️ โปรเจ็กต์วิเคราะห์ข้อมูล YouTube ศึกษาความสัมพันธ์ระหว่างความยาววิดีโอและยอดวิวโดยใช้ Pandas และ Seaborn\n"
                  " - 🧑‍💼Staff Event Maruya,Cosnatsu,TIGS,TGS\n"
                  " - 📸 ตากล้อง ถ่ายภาพในมหาวิทยาลัย,งานReshTech&ตั้งตัว",
        skills=["🐍 Python", "⚙️ SQL", "☁️ Streamlit", "🗄️ BigQuery", "✅ Excel", "📊 HTML"],
        img_url=img_b64
    )
elif page == "notion":
    render_notion()
elif page == "spam":
    render_spam()
elif page == "waste":
    render_waste()
