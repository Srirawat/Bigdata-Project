import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
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
import os
import numpy as np

def render_spam():
    st.markdown("<h2>📧 SMS/Email Spam</h2><div class='subtle'>ทดสอบข้อความว่าเป็น Ham หรือ Spam</div>", unsafe_allow_html=True)

    # Set up Paths properly
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIR = os.path.dirname(CURRENT_DIR)
    
    model_path = os.path.join(ROOT_DIR, "Bigdata", "spam_model.pkl")
    vec_path = os.path.join(ROOT_DIR, "Bigdata", "vectorizer.pkl")
    data_path = os.path.join(ROOT_DIR, "Bigdata", "SMSSpamCollection.csv")

    with st.container():
        st.markdown("### 🔎 ทำนายข้อความเดี่ยว")
        
        # ---------------- ADDED: บล็อกข้อความตัวอย่าง ----------------
        with st.expander("💡 ดูข้อความตัวอย่าง (คัดลอกไปทดสอบได้เลย)"):
            st.markdown("**ตัวอย่าง Spam 🔴** (ข้อความขยะ/หลอกลวง)")
            st.code("URGENT! You have won a 1 week FREE membership in our £100,000 Prize Jackpot! Txt the word: CLAIM to No: 81010", language="text")
            st.code("Congratulations ur awarded 500 of CD vouchers or 125gift guaranteed & Free entry 2 100 wkly draw txt MUSIC to 87066", language="text")
            
            st.markdown("**ตัวอย่าง Ham 🟢** (ข้อความปกติ)")
            st.code("Hey, are we still on for lunch today?", language="text")
            st.code("I've been searching for the right words to thank you for this breather. I promise i wont take your help for granted.", language="text")
        # -----------------------------------------------------------

        txt = st.text_area("ใส่ข้อความที่ต้องการทำนาย", height=100, placeholder="เช่น: Win a FREE iPhone now! Click link…")

        if st.button("ทำนาย", use_container_width=True):
            if not txt.strip():
                st.warning("กรุณาใส่ข้อความก่อนทำนาย")
            else:
                try:
                    if not os.path.exists(model_path) or not os.path.exists(vec_path):
                        st.error(f"ไม่พบไฟล์โมเดล '{model_path}' หรือ '{vec_path}'. กรุณาวางไฟล์ทั้งสองไว้ในโฟลเดอร์ Bigdata")
                    else:
                        model = joblib.load(model_path)
                        vectorizer = joblib.load(vec_path)
                        X = vectorizer.transform([txt])
                        if hasattr(model, "predict_proba"):
                            p = model.predict_proba(X)[0]
                            spam_class_index = np.where(model.classes_ == 1)[0][0]
                            ham_class_index = np.where(model.classes_ == 0)[0][0]
                            spam_p = float(p[spam_class_index])
                            ham_p = float(p[ham_class_index])
                            
                            pred = "Spam" if spam_p > ham_p else "Ham"
                            st.success(f"ผลทำนาย: **{pred}** | Ham={ham_p:.4f}  Spam={spam_p:.4f}")
                        else:
                            y = model.predict(X)[0]
                            pred_label = "Spam" if y == 1 else "Ham"
                            st.success(f"ผลทำนาย: **{pred_label}**")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")

    st.markdown("---")

    with st.expander("💼 Business Value & Use Cases", expanded=True):
        st.markdown("""
- ลดความเสี่ยงฟิชชิง/หลอกลวง, ประหยัดเวลาคัดกรองข้อความ, เพิ่มความเชื่อมั่นให้ผู้ใช้
- ใช้งาน: กรองสแปมอีเมล/แชตแบบเรียลไทม์, เตือนข้อความเสี่ยง, บันทึกเหตุการณ์อัตโนมัติ
        """)
    with st.expander("📚 แหล่งข้อมูล (Dataset)", expanded=True):
        st.markdown("""
- **ชุดข้อมูล:** *SMS Spam Collection* (ป้ายกำกับ `ham`/`spam`)
- **ที่มา (UCI ML Repository):** https://archive.ics.uci.edu/ml/datasets/sms+spam+collection
- **ไฟล์:** `SMSSpamCollection.csv` (TSV: `label\\tmessage`)
        """)

    test_size = 0.2
    random_state = 42
    vec_name = "TfidfVectorizer"
    ngram = "(1,2)"
    max_features = 5000
    stop_words = "english"

    go = st.button("🚀 Run report (ใช้ไฟล์จากเครื่องโดยอัตโนมัติ)", use_container_width=True)

    def build_vectorizer():
        return TfidfVectorizer(lowercase=True, stop_words=stop_words, ngram_range=(1,2), max_features=max_features)

    def build_models():
        return {
            "LogisticRegression": LogisticRegression(max_iter=2000),
            "LinearSVC": LinearSVC(dual=True),
            "MultinomialNB": MultinomialNB(),
            "ComplementNB": ComplementNB(),
            "RandomForest": RandomForestClassifier(n_estimators=100, random_state=random_state, n_jobs=-1),
        }

    def compute_metrics(y_true, y_pred, y_prob=None):
        acc = accuracy_score(y_true, y_pred)
        pre = precision_score(y_true, y_pred, pos_label=1, zero_division=0)
        rec = recall_score(y_true, y_pred, pos_label=1, zero_division=0)
        f1  = f1_score(y_true, y_pred, pos_label=1, zero_division=0)
        auc = None
        if y_prob is not None:
            try:
                auc = roc_auc_score(y_true, y_prob)
            except Exception:
                pass
        return {"accuracy":acc,"precision":pre,"recall":rec,"f1":f1,"roc_auc":auc}

    def plot_cm(cm, labels=("ham(0)","spam(1)")):
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
        ax.set_xticks([0,1]); ax.set_xticklabels(labels, rotation=0)
        ax.set_yticks([0,1]); ax.set_yticklabels(labels)
        ax.set_xlabel("Predicted label")
        ax.set_ylabel("True label")
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                ax.text(j, i, f"{cm[i, j]}", ha="center", va="center", color="white" if cm[i, j] > cm.max() / 2 else "black")
        fig.tight_layout()
        return fig

    def plot_roc(y_true, y_prob):
        fpr, tpr, _ = roc_curve(y_true, y_prob)
        auc_val = roc_auc_score(y_true, y_prob)
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {auc_val:.2f})')
        ax.plot([0,1],[0,1], color='navy', lw=2, linestyle="--")
        ax.set_xlabel("False Positive Rate")
        ax.set_ylabel("True Positive Rate")
        ax.set_title("Receiver Operating Characteristic")
        ax.legend(loc="lower right")
        fig.tight_layout()
        return fig, auc_val

    if go:
        st.header("1) Data preprocessing")

        if not os.path.exists(data_path):
            st.error(f"ไม่พบไฟล์: {data_path}. กรุณาวางไฟล์ข้อมูลในโฟลเดอร์ Bigdata")
            st.stop()

        try:
            df = pd.read_csv(data_path, sep="\t", header=None, names=["label","message"], encoding="latin1")
        except Exception as e:
            st.error(f"อ่านไฟล์ไม่สำเร็จ: {e}")
            st.stop()

        st.markdown(f"""
- แปลง **label**: `ham→0`, `spam→1`
- ลบข้อความว่าง (`NaN`) และข้อความซ้ำ
- แปลงข้อความ → ตัวเลขด้วย **{vec_name}** (`ngram_range={ngram}`, `max_features={max_features}`)
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

        st.header("2) Model training & comparison")

        X_train, X_test, y_train, y_test = train_test_split(
            df["message"].astype(str), df["label"].astype(int),
            test_size=test_size, random_state=random_state, stratify=df["label"].astype(int)
        )

        vectorizer = build_vectorizer()
        models = build_models()

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
                    if len(scores.shape) > 1:
                        scores = scores[:, 1]
                    y_proba = (scores - scores.min()) / (scores.max() - scores.min() + 1e-12)

                m = compute_metrics(y_test, y_pred, y_proba)
                rows.append({"Model": name, "Accuracy": m["accuracy"], "Precision": m["precision"],
                             "Recall": m["recall"], "F1": m["f1"], "ROC-AUC": m["roc_auc"]})
                trained[name] = (pipe, y_pred, y_proba)

        res_df = pd.DataFrame(rows).sort_values(by=["F1","Accuracy"], ascending=False).reset_index(drop=True)
        st.write("ตารางเปรียบเทียบผลลัพธ์:")
        numeric_cols = ["Accuracy", "Precision", "Recall", "F1", "ROC-AUC"]

        st.dataframe(
            res_df.style.format("{:.4f}", subset=numeric_cols)
                  .highlight_max(axis=0, color='#d4edda', subset=numeric_cols),
            use_container_width=True
        )

        best_name = res_df.iloc[0]["Model"]
        st.success(f"🏆 Best model: **{best_name}** (ตามค่า F1-Score)")
        best_pipe, best_pred, best_proba = trained[best_name]

        st.header("3) Evaluation (ของโมเดลที่ชนะ)")
        cm = confusion_matrix(y_test, best_pred, labels=[0,1])
        cm_fig = plot_cm(cm)

        cA, cB = st.columns(2)
        with cA:
            st.write("**Confusion Matrix:**")
            st.pyplot(cm_fig, clear_figure=True)
        with cB:
            if best_proba is not None:
                st.write("**ROC Curve:**")
                roc_fig, auc_val = plot_roc(y_test, best_proba)
                st.pyplot(roc_fig, clear_figure=True)
            else:
                st.info("โมเดลนี้ไม่มี probability/score จึงคำนวณ ROC-AUC ไม่ได้")

        st.write("**Classification report:**")
        st.code(classification_report(y_test, best_pred, target_names=["ham(0)","spam(1)"], zero_division=0))

        st.header("4) สรุปผลลัพธ์และข้อเสนอแนะ")
        best_row = res_df.iloc[0].to_dict()
        st.markdown(f"""
- **โมเดลที่ดีที่สุด**: `{best_name}`
- **ผลลัพธ์เด่น**: Accuracy={best_row['Accuracy']:.3f}, Precision={best_row['Precision']:.3f}, Recall={best_row['Recall']:.3f}, F1={best_row['F1']:.3f}{", ROC-AUC="+str(round(best_row['ROC-AUC'],3)) if pd.notnull(best_row['ROC-AUC']) else ""}

**ข้อสังเกต & คำแนะนำ**
- ถ้าต้องการ “กันสแปมหลุด” (ลด False Negative) ให้เน้นค่า **Recall ของ Spam** → อาจต้องยอมรับ Precision ที่ลดลงเล็กน้อย
- เพิ่ม **ฟีเจอร์ใหม่ๆ (Feature Engineering)**: เช่น ความยาวข้อความ, จำนวน URL/ตัวเลข/สัญลักษณ์พิเศษ, การใช้คำที่เป็นตัวพิมพ์ใหญ่ล้วน
- ทดลอง **Hyperparameter Tuning** สำหรับโมเดลที่ดีที่สุดเพื่อเพิ่มประสิทธิภาพ
- ในงานจริง ควรมีการ **ติดตามผล (Monitoring)** ของโมเดล และ **เทรนใหม่ (Retraining)** เป็นระยะเมื่อข้อมูลมีการเปลี่ยนแปลง
        """)

        with st.container():
            st.markdown("#### 💾 บันทึกโมเดล/เวกเตอร์ (เพื่อใช้กับการทำนายข้อความเดี่ยว)")
            csm = st.columns(3)
            with csm[0]:
                save_model_path = st.text_input("บันทึกโมเดลเป็น", value=model_path, key="save_model")
            with csm[1]:
                save_vec_path = st.text_input("บันทึกเวกเตอร์เป็น", value=vec_path, key="save_vec")
            with csm[2]:
                if st.button("บันทึก (joblib.dump)", use_container_width=True, key="save_button"):
                    best_model_to_save = best_pipe.named_steps["clf"]
                    best_vec_to_save = best_pipe.named_steps["vec"]
                    joblib.dump(best_model_to_save, save_model_path)
                    joblib.dump(best_vec_to_save, save_vec_path)
                    st.success(f"บันทึกแล้ว: {save_model_path}, {save_vec_path}")