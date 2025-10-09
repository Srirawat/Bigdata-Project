# mix.py
import streamlit as st
from bs4 import BeautifulSoup
from urllib.parse import unquote
from pathlib import Path
from PIL import Image
from io import BytesIO
import tempfile
import base64, zipfile, io, os, re, numpy as np

# ================== CONFIG ==================
st.set_page_config(page_title="Profile + Notion + Spam + Waste", layout="wide")

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

    /* NEW CSS for profile image styling */
    .profile-img-container {
        display: flex;
        justify-content: center; /* Center horizontally */
        align-items: center;     /* Center vertically */
        height: 100%;            /* Take full height of its column */
    }
    .profile-img {
        border-radius: 50%; /* Make it circular */
        object-fit: cover;  /* Ensure image covers the area without distortion */
        border: 4px solid var(--brand); /* Add a border matching brand color */
        box-shadow: 0 4px 8px rgba(0,0,0,0.2); /* Add a subtle shadow */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ================== SESSION ==================
if "page" not in st.session_state:
    st.session_state.page = "profile"

def nav_click(target: str):
    st.session_state.page = target

# ================== Generic Helpers ==================
def _img(img, caption=None):
    try:
        st.image(img, caption=caption, use_container_width=True)
    except TypeError:
        st.image(img, caption=caption, use_column_width=True)

def image_to_base64(path: str):
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
            return f"data:image/jpeg;base64,{data}"
    except Exception:
        return None

def first_existing_path(paths):
    for p in paths:
        if p and Path(p).exists():
            return p
    return None

# ===== Notion helpers (inline asset) =====
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

def extract_first_html_from_zip(zf: zipfile.ZipFile):
    html_names = [n for n in zf.namelist() if n.lower().endswith(".html")]
    if not html_names: return None
    for n in html_names:
        if os.path.basename(n).lower() in ("index.html","notion.html"):
            return n
    return html_names[0]

# ================== Sidebar ==================
with st.sidebar:
    st.markdown("<div class='sidebar-label'>📌 เลือกหน้า</div>", unsafe_allow_html=True)
    st.button("👤 Profile", key="profile_btn", use_container_width=True, on_click=nav_click, args=("profile",))
    st.button("🗒️ Notion", key="notion_btn", use_container_width=True, on_click=nav_click, args=("notion",))
    st.button("📧 Spam", key="spam_btn", use_container_width=True, on_click=nav_click, args=("spam",))
    st.button("🗑️ Waste", key="waste_btn", use_container_width=True, on_click=nav_click, args=("waste",))
    st.markdown('<hr style="border:none;border-top:1px solid #e8e8e8;margin:10px 0 8px;">', unsafe_allow_html=True)

page = st.session_state.page

# ================== PAGE 1: Profile ==================
def show_profile(name, student_id, major, interest, experience, skills, profile_image=None):
    st.title("👤 Profile Page")
    
    col1, col2 = st.columns([1, 4]) # Adjust column ratio as needed
    with col1:
        st.markdown('<div class="profile-img-container">', unsafe_allow_html=True)
        if profile_image:
            # Use st.image with class for styling
            st.image(profile_image, width=150, clamp=True, output_format="JPEG", # Adjust width as needed
                     caption="Profile Picture",
                     use_column_width="auto", # Let Streamlit handle column width
                     # This CSS class is critical for styling the image within Streamlit's div
                     ) 
            st.markdown('<style>img {border-radius: 50%; border: 4px solid #4CAF50; box-shadow: 0 4px 8px rgba(0,0,0,0.2); object-fit: cover;} </style>', unsafe_allow_html=True)
        else:
            st.warning("ไม่พบรูปภาพ")
        st.markdown('</div>', unsafe_allow_html=True) # Close the container div

    with col2:
        st.title(name)
        st.markdown(f"**รหัสนักศึกษา:** {student_id}")
        st.markdown(f"**สาขา:** {major}")
    
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


# ================== PAGE 2: Notion (with YouTube Dashboard Mode) ==================
def render_notion():
    st.markdown("<h2>🗒️ Notion</h2><div class='subtle'>โหมดแสดงผล Notion หรือ Dashboard YouTube (เฉพาะหน้านี้)</div>", unsafe_allow_html=True)

    mode = st.radio("โหมดการใช้งาน", ["Notion Viewer", "YouTube TH Top 1000 Dashboard"], horizontal=True)

    # -------- Mode A: Notion Viewer --------
    if mode == "Notion Viewer":
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
                    candidate = None
                    html_files = list(tmpdir.rglob("*.html"))
                    if not html_files:
                        st.error("ไม่พบไฟล์ HTML ภายใน ZIP")
                        return
                    for p in html_files:
                        if p.name.lower() == "index.html":
                            candidate = p
                            break
                    if candidate is None:
                        candidate = html_files[0]
                    raw_html = candidate.read_text(encoding="utf-8", errors="ignore")
                    inlined_html = inline_assets(raw_html, candidate.parent)
                    st.components.v1.html(inlined_html, height=820, scrolling=True)
                    num_imgs = len(list(candidate.parent.rglob("*.png"))) + len(list(candidate.parent.rglob("*.jpg"))) + len(list(candidate.parent.rglob("*.jpeg"))) + len(list(candidate.parent.rglob("*.gif"))) + len(list(candidate.parent.rglob("*.svg")))
                    st.caption(f"✅ Inline assets เสร็จสิ้น ~{num_imgs} รูป")
            except Exception as e:
                st.error(f"อ่าน ZIP ไม่สำเร็จ: {e}")

    # -------- Mode B: YouTube Dashboard (your provided code) --------
    else:
        import requests, bs4, pandas as pd, altair as alt

        st.title('📊 Dashboard วิเคราะห์ Top 1000 YouTube Videos in Thailand')
        st.markdown("""
แอปพลิเคชันนี้ทำการดึงข้อมูล (Scraping) จากเว็บ
[youtubers.me](https://th.youtubers.me/thailand/all/top-1000-youtube-videos-in-thailand)
เพื่อวิเคราะห์แนวโน้มและ Insight ที่น่าสนใจของวิดีโอยอดนิยม 1,000 อันดับแรกในประเทศไทย
""")

        @st.cache_data
        def load_and_clean_data():
            response = requests.get('https://th.youtubers.me/thailand/all/top-1000-youtube-videos-in-thailand')
            response.encoding = 'utf-8'
            soup = bs4.BeautifulSoup(response.text, 'html.parser')

            data = []
            tables = soup.find_all('table')
            if not tables:
                return pd.DataFrame(columns=['Rank','Vid_name','Views','Like','Dislike','Category','Publish'])

            for row in tables[0].find_all('tr'):
                columns = row.find_all('td')
                if len(columns) >= 7:
                    rank = columns[0].text.strip()
                    views = columns[2].text.strip()
                    like = columns[3].text.strip()
                    dislike = columns[4].text.strip()
                    category = columns[5].text.strip()
                    publish = columns[6].text.strip()
                    img_tag = columns[1].find('img')
                    vid_name = img_tag['alt'].strip() if img_tag else 'N/A'
                    data.append([rank, vid_name, views, like, dislike, category, publish])

            import pandas as pd
            df = pd.DataFrame(data, columns=['Rank', 'Vid_name', 'Views', 'Like', 'Dislike', 'Category', 'Publish'])
            df = df[df['Category'] != '']

            for col in ['Views', 'Like', 'Dislike']:
                df[col] = pd.to_numeric(df[col].str.replace(',', ''), errors='coerce')

            df.dropna(subset=['Views', 'Like'], inplace=True)
            df = df.astype({'Views': 'int64', 'Like': 'int64'})

            df['Engagement_Rate'] = df.apply(
                lambda row: (row['Like'] / row['Views']) * 100 if row['Views'] > 0 else 0, axis=1
            )
            return df

        with st.spinner('กำลังดึงและประมวลผลข้อมูลล่าสุด...'):
            df = load_and_clean_data()

        # KPIs
        st.header('ภาพรวมข้อมูล (Overall KPIs)')
        col1, col2, col3 = st.columns(3)
        total_videos = len(df)
        total_views = df['Views'].sum()
        top_category = df['Category'].mode()[0] if not df.empty else "-"
        col1.metric("จำนวนวิดีโอที่วิเคราะห์", f"{total_videos:,.0f}")
        col2.metric("ยอดวิวรวมทั้งหมด", f"{total_views/1e9:.2f} พันล้าน")
        col3.metric("หมวดหมู่ยอดนิยมที่สุด", top_category)
        st.divider()

        # Yearly Trends
        st.header('1. แนวโน้มภาพรวมในแต่ละปี (Yearly Trends)')
        if not df.empty:
            df['Publish'] = pd.to_numeric(df['Publish'], errors='coerce')
            df_filtered_years = df.dropna(subset=['Publish'])
            df_filtered_years = df_filtered_years[(df_filtered_years['Publish'] >= 2014) & (df_filtered_years['Publish'] <= 2025)]
            if not df_filtered_years.empty:
                yearly_stats = df_filtered_years.groupby('Publish').agg(
                    Video_Count=('Vid_name', 'count'),
                    Average_Views=('Views', 'mean')
                ).reset_index().rename(columns={'Publish': 'Year'})
                st.dataframe(yearly_stats, use_container_width=True)
                st.line_chart(yearly_stats.rename(columns={'Year':'index'}).set_index('index')['Average_Views'])
                st.caption("กราฟเส้นแสดงยอดวิวเฉลี่ยของวิดีโอที่ติด Top 1000 ในแต่ละปี")
            else:
                st.info("ไม่มีข้อมูลในช่วงปีที่กำหนด (2014-2025)")
        else:
            st.info("ไม่มีข้อมูลเพียงพอสำหรับ Yearly Trends")
        st.divider()

        # Category Popularity
        st.header('2. หมวดหมู่ยอดนิยมในแต่ละปี (Category Popularity)')
        if not df.empty and not df_filtered_years.empty:
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.subheader("สัดส่วนหมวดหมู่ยอดนิยมอันดับ 1")
                def get_top_category_proportion(group):
                    category_counts = group['Category'].value_counts()
                    if category_counts.empty:
                        return pd.Series({'Top Video Category': None, 'Top Category Proportion (%)': 0})
                    top_category = category_counts.index[0]
                    proportion = (category_counts.iloc[0] / category_counts.sum()) * 100
                    return pd.Series({'Top Video Category': top_category, 'Top Category Proportion (%)': proportion})

                yearly_category_stats = df_filtered_years.groupby('Publish').apply(get_top_category_proportion).reset_index()
                yearly_category_stats = yearly_category_stats.rename(columns={'Publish': 'Year'})

                import altair as alt
                chart1 = alt.Chart(yearly_category_stats).mark_bar().encode(
                    x=alt.X('Year:O', title='ปี'),
                    y=alt.Y('Top Category Proportion (%):Q', title='สัดส่วน (%)'),
                    color=alt.Color('Top Video Category:N', title='หมวดหมู่'),
                    tooltip=['Year', 'Top Video Category', 'Top Category Proportion (%)']
                ).properties(title='สัดส่วนของหมวดหมู่วิดีโอยอดนิยมอันดับ 1 ในแต่ละปี')
                st.altair_chart(chart1, use_container_width=True)

            with col_chart2:
                st.subheader("สัดส่วนหมวดหมู่อันดับ 2 และ 3")
                def get_top2_top3_category_proportion(group):
                    category_counts = group['Category'].value_counts()
                    total_count = category_counts.sum()
                    top2_category, top2_proportion = (None, None)
                    top3_category, top3_proportion = (None, None)
                    if len(category_counts) >= 2:
                        top2_category = category_counts.index[1]
                        top2_proportion = (category_counts.iloc[1] / total_count) * 100
                    if len(category_counts) >= 3:
                        top3_category = category_counts.index[2]
                        top3_proportion = (category_counts.iloc[2] / total_count) * 100
                    return pd.Series({
                        'Top 2 Category': top2_category, 'Top 2 Proportion (%)': top2_proportion,
                        'Top 3 Category': top3_category, 'Top 3 Proportion (%)': top3_proportion
                    })

                yearly_top2_top3_stats = df_filtered_years.groupby('Publish').apply(get_top2_top3_category_proportion).reset_index()
                yearly_top2_top3_stats = yearly_top2_top3_stats.rename(columns={'Publish': 'Year'})
                melted_data = yearly_top2_top3_stats.melt(
                    id_vars=['Year'],
                    value_vars=['Top 2 Proportion (%)', 'Top 3 Proportion (%)'],
                    var_name='Rank', value_name='Proportion'
                )
                chart2 = alt.Chart(melted_data).mark_bar().encode(
                    x=alt.X('Year:O', title='ปี'),
                    y=alt.Y('Proportion:Q', title='สัดส่วน (%)'),
                    color=alt.Color('Rank:N', title='อันดับ'),
                    tooltip=['Year', 'Rank', 'Proportion']
                ).properties(title='สัดส่วนของหมวดหมู่วิดีโอยอดนิยมอันดับ 2 และ 3')
                st.altair_chart(chart2, use_container_width=True)
        else:
            st.info("ไม่มีข้อมูลเพียงพอสำหรับ Category Popularity")
        st.divider()

        # Deep Dive + Engagement
        st.header('3. เจาะลึกรายหมวดหมู่และ Engagement (Deep Dive)')
        if not df.empty:
            col_engage, col_search = st.columns([1, 2])
            with col_engage:
                st.subheader("หมวดหมู่ที่สร้าง Engagement สูงสุด")
                engagement_by_category = df.groupby('Category')['Engagement_Rate'].mean().sort_values(ascending=False).reset_index()
                st.dataframe(
                    engagement_by_category,
                    column_config={
                        "Category": "หมวดหมู่",
                        "Engagement_Rate": st.column_config.ProgressColumn(
                            "Engagement Rate (Avg %)",
                            format="%.2f%%",
                            min_value=0,
                            max_value=float(engagement_by_category['Engagement_Rate'].max()) if not engagement_by_category.empty else 1
                        )
                    },
                    use_container_width=True
                )
                st.caption("คำนวณจาก (Likes / Views) * 100")
            with col_search:
                st.subheader("ค้นหาวิดีโอยอดนิยมตามหมวดหมู่")
                category_list = ['All'] + sorted(df['Category'].dropna().unique().tolist())
                selected_category = st.selectbox("เลือกหมวดหมู่ที่สนใจ:", category_list)
                display_df = df if selected_category == 'All' else df[df['Category'] == selected_category]
                st.dataframe(display_df[['Rank', 'Vid_name', 'Views', 'Like', 'Publish']].head(20), use_container_width=True)
        else:
            st.info("ไม่มีข้อมูลเพียงพอสำหรับการเจาะลึก")
        st.divider()
        st.info("Dashboard นี้สร้างขึ้นโดยใช้ข้อมูลจากการวิเคราะห์โค้ด Python ของคุณ (รวมอยู่ในหน้า Notion เท่านั้น)")

# ================== PAGE 3: Spam ==================
def render_spam():
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

    st.markdown("<h2>📧 SMS/Email Spam</h2><div class='subtle'>ทดสอบข้อความว่าเป็น Ham หรือ Spam</div>", unsafe_allow_html=True)

    # ---- ทำนายข้อความเดี่ยว ----
    with st.container():
        st.markdown("### 🔎 ทำนายข้อความเดี่ยว")
        txt = st.text_area("ใส่ข้อความที่ต้องการทำนาย", height=100, placeholder="เช่น: Win a FREE iPhone now! Click link…")

        model_path = r"Bigdata/spam_model.pkl"
        vec_path = r"Bigdata/vectorizer.pkl"

        if st.button("ทำนาย", use_container_width=True):
            if not txt.strip():
                st.warning("กรุณาใส่ข้อความก่อนทำนาย")
            else:
                try:
                    if not os.path.exists(model_path) or not os.path.exists(vec_path):
                        st.error(f"ไม่พบไฟล์โมเดล '{model_path}' หรือ '{vec_path}'. กรุณาวางไฟล์ทั้งสองไว้ในโฟลเดอร์เดียวกับสคริปต์นี้")
                    else:
                        model = joblib.load(model_path)
                        vectorizer = joblib.load(vec_path)
                        X = vectorizer.transform([txt])
                        if hasattr(model, "predict_proba"):
                            p = model.predict_proba(X)[0]
                            # Assuming class 0 is ham, class 1 is spam
                            # Find the index of the 'spam' class in the model's classes_ attribute
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

    # ---- Business & Dataset ----
    with st.expander("💼 Business Value & Use Cases", expanded=True):
        st.markdown(
            """
- ลดความเสี่ยงฟิชชิง/หลอกลวง, ประหยัดเวลาคัดกรองข้อความ, เพิ่มความเชื่อมั่นให้ผู้ใช้
- ใช้งาน: กรองสแปมอีเมล/แชตแบบเรียลไทม์, เตือนข้อความเสี่ยง, บันทึกเหตุการณ์อัตโนมัติ
            """
        )
    with st.expander("📚 แหล่งข้อมูล (Dataset)", expanded=True):
        st.markdown(
            """
- **ชุดข้อมูล:** *SMS Spam Collection* (ป้ายกำกับ `ham`/`spam`)
- **ที่มา (UCI ML Repository):** https://archive.ics.uci.edu/ml/datasets/sms+spam+collection
- **ไฟล์:** `SMSSpamCollection.csv` (TSV: `label\\tmessage`)
            """
        )

    # ---- ค่ามาตรฐาน ----
    data_path       = r"Bigdata/SMSSpamCollection.csv"
    test_size       = 0.2
    random_state    = 42
    vec_name        = "TfidfVectorizer"
    ngram           = "(1,2)"
    max_features    = 5000
    stop_words      = "english"

    go = st.button("🚀 Run report (ใช้ไฟล์จากเครื่องโดยอัตโนมัติ)", use_container_width=True)

    # ---- Helpers ----
    def build_vectorizer():
        return TfidfVectorizer(lowercase=True, stop_words=stop_words, ngram_range=(1,2), max_features=max_features)

    def build_models():
        return {
            "LogisticRegression": LogisticRegression(max_iter=2000),
            "LinearSVC": LinearSVC(dual=True), # Added dual=True for newer scikit-learn versions
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
                auc = None
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

    # -------------------- Section: Data preprocessing --------------------
    if go:
        st.header("1) Data preprocessing")

        if not os.path.exists(data_path):
            st.error(f"ไม่พบไฟล์: {data_path}. กรุณาวางไฟล์ข้อมูลในโฟลเดอร์เดียวกับสคริปต์")
            st.stop()

        try:
            df = pd.read_csv(data_path, sep="\t", header=None, names=["label","message"], encoding="latin1") # Changed encoding
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

        # -------------------- Section: Model training & Comparison --------------------
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
                    if len(scores.shape) > 1: # Handle multi-class case if it ever occurs
                        scores = scores[:, 1]
                    y_proba = (scores - scores.min()) / (scores.max() - scores.min() + 1e-12)

                m = compute_metrics(y_test, y_pred, y_proba)
                rows.append({"Model": name, "Accuracy": m["accuracy"], "Precision": m["precision"],
                             "Recall": m["recall"], "F1": m["f1"], "ROC-AUC": m["roc_auc"]})
                trained[name] = (pipe, y_pred, y_proba)

        res_df = pd.DataFrame(rows).sort_values(by=["F1","Accuracy"], ascending=False).reset_index(drop=True)
        st.write("ตารางเปรียบเทียบผลลัพธ์:")
        # กำหนดรายชื่อคอลัมน์ที่เป็นตัวเลข
        numeric_cols = ["Accuracy", "Precision", "Recall", "F1", "ROC-AUC"]

        # ใช้ subset เพื่อระบุให้จัดรูปแบบและไฮไลท์เฉพาะคอลัมน์เหล่านี้
        st.dataframe(
            res_df.style.format("{:.4f}", subset=numeric_cols)
                          .highlight_max(axis=0, color='#d4edda', subset=numeric_cols),
            use_container_width=True
        )

        best_name = res_df.iloc[0]["Model"]
        st.success(f"🏆 Best model: **{best_name}** (ตามค่า F1-Score)")
        best_pipe, best_pred, best_proba = trained[best_name]

        # -------------------- Section: Evaluation --------------------
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

        # -------------------- Section: สรุปผลลัพธ์และข้อเสนอแนะ --------------------
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

        # Save best model/vectorizer
        with st.container():
            st.markdown("#### 💾 บันทึกโมเดล/เวกเตอร์ (เพื่อใช้กับการทำนายข้อความเดี่ยว)")
            csm = st.columns(3)
            with csm[0]:
                save_model_path = st.text_input("บันทึกโมเดลเป็น", value="spam_model.pkl", key="save_model")
            with csm[1]:
                save_vec_path = st.text_input("บันทึกเวกเตอร์เป็น", value="vectorizer.pkl", key="save_vec")
            with csm[2]:
                if st.button("บันทึก (joblib.dump)", use_container_width=True, key="save_button"):
                    best_model_to_save = best_pipe.named_steps["clf"]
                    best_vec_to_save = best_pipe.named_steps["vec"]
                    joblib.dump(best_model_to_save, save_model_path)
                    joblib.dump(best_vec_to_save, save_vec_path)
                    st.success(f"บันทึกแล้ว: {save_model_path}, {save_vec_path}")

# ================== PAGE 4: Waste (Keras .keras, auto input size + CAMERA) ==================
@st.cache_resource
def load_keras_model(path: str):
    import tensorflow as tf
    return tf.keras.models.load_model(path)

def render_waste():
    st.markdown("<h2>🗑️ Waste Classification</h2><div class='subtle'>อัปโหลดภาพหรือถ่ายภาพจากกล้อง + ใช้โมเดล Keras (.keras/.h5)</div>", unsafe_allow_html=True)

    # ---- Settings ----
    model_path = st.text_input("Path โมเดล (.keras หรือ .h5)", value=r"Bigdata/waste_model.keras")
    class_names_str = st.text_input("ชื่อคลาส (คั่นด้วยจุลภาค, ลำดับต้องตรงกับตอนเทรน)", value="organic,recyclable")
    class_names = [c.strip() for c in class_names_str.split(",") if c.strip()]

    # ---- Image Source Selector ----
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
        if not model_path:
            st.warning("กรุณาระบุ path ของโมเดลก่อน")
            return
        if not os.path.exists(model_path):
            st.error(f"ไม่พบไฟล์โมเดลที่: {model_path}")
            return
        if uploaded_img is None:
            st.warning("กรุณาอัปโหลด/ถ่ายภาพก่อน")
            return

        try:
            import tensorflow as tf

            with st.spinner("กำลังโหลดโมเดลและทำนายผล..."):
                model = load_keras_model(model_path)

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
                        st.dataframe(df_prob.sort_values("probability", ascending=False).reset_index(drop=True).style.format({"probability": "{:.2%}"}), use_container_width=True)
                    except Exception:
                        st.write({f"Class {i}": p for i, p in enumerate(pred)})

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")

    # ---- Practical Summary ----
    st.markdown("---")
    st.subheader("📌 สรุปการประยุกต์ใช้งานจริง & ประโยชน์")
    st.markdown(
        """
- **คัดแยกขยะอัจฉริยะ (Smart Bins / MRF):** ติดกล้องที่ถังขยะหรือสายพานลำเลียงให้ระบบจำแนกประเภทอัตโนมัติ ลดภาระคนงาน และเพิ่มความแม่นยำการรีไซเคิล
- **IoT + กล้อง ณ จุดทิ้งขยะ:** แจ้งเตือนเมื่อพบการทิ้งผิดประเภท (เช่น ขยะอันตรายปะปน) หรือคัดแยกเบื้องต้นก่อนเข้าระบบหลัก
- **งานเทศบาล/มหาวิทยาลัย/ห้างฯ:** สื่อสาร “ทิ้งให้ถูกที่” แบบเรียลไทม์ผ่านจอ/แอป ช่วยปรับพฤติกรรมประชาชนและเพิ่มอัตรารีไซเคิล
- **ธุรกิจรีไซเคิล/โลจิสติกส์:** ตรวจคุณภาพวัสดุเข้าโรงรีไซเคิล ออกใบรับรองหรือคำนวณมูลค่าจากประเภทวัสดุได้รวดเร็ว
- **ประโยชน์ทางเศรษฐกิจ & สิ่งแวดล้อม:** ลดต้นทุนแรงงานและความผิดพลาด เพิ่มอัตรารีไซเคิล ลดของเสียฝังกลบและการปล่อยก๊าซเรือนกระจก
- **ต่อยอดโมเดล:** เก็บภาพจริงหน้างานมาปรับปรุงชุดข้อมูล, ทำ active learning, เพิ่มคลาส/ย่อยคลาส (เช่น พลาสติกใส/ทึบ), และติดตามผลแบบ dashboard
        """
    )
    st.info("หมายเหตุ: การถ่ายด้วยกล้องผ่านเบราว์เซอร์ต้องอยู่บน HTTPS หรือ localhost และอนุญาตสิทธิ์การใช้กล้อง")

# ================== ROUTING ==================
if page == "profile":
    # --- Load image directly from the specified path ---
    image_path = "image/FUJI0041.jpg" # Make sure this path is correct
    profile_image = None
    
    # Optional: Keep debugging info for a while if you still have issues
    # st.subheader("🕵️‍♂️ Debugging Information (ลบออกได้ทีหลัง)")
    # st.write(f"**Current Directory:** `{os.getcwd()}`")
    # st.write(f"**Attempting to open:** `{os.path.abspath(image_path)}`")
    # file_exists = os.path.exists(image_path)
    # st.write(f"**Does the file exist at this path?** `{file_exists}`")
    # st.markdown("---")

    try:
        if os.path.exists(image_path):
            profile_image = Image.open(image_path)
        else:
            st.warning(f"ไม่พบไฟล์รูปภาพที่ '{image_path}'. กรุณาตรวจสอบโครงสร้างโฟลเดอร์และการสะกดชื่อไฟล์")
    except Exception as e:
        st.error(f"ไม่สามารถโหลดรูปภาพได้: {e}")

    show_profile(
        name="นาย ศิรวัช ปัญญาสวรรค์",
        student_id="2313110526",
        major="Information Technology",
        interest="ผมสนใจด้าน Data Science เพราะมองว่า “ข้อมูล” สามารถบอกเล่าเรื่องราวและช่วยให้ตัดสินใจได้อย่างมีเหตุผล โดยเฉพาะการหาความสัมพันธ์หรือรูปแบบที่ซ่อนอยู่ในข้อมูล ซึ่งเป็นส่วนที่ท้าทายและสนุกมาก",
        experience="- 📌Mini Project วิชา ITE-436: Big Data & Data Mining — ทำโปรเจ็กต์ Spam Email Classification ด้วย SMSSpamCollection Dataset\n"
                   "- ☁️ โปรเจ็กต์วิเคราะห์ข้อมูล YouTube ศึกษาความสัมพันธ์ระหว่างความยาววิดีโอและยอดวิวโดยใช้ Pandas และ seaborn\n"
                   " - 🧑‍💼Staff Event Maruya,Cosnatsu,TIGS,TGS\n"
                   " - 📸 ตากล้อง ถ่ายภาพในมหาวิทยาลัย,งานReshTech&ตั้งตัว",
        skills=["🐍 Python", "⚙️ SQL", "☁️ Streamlit", "🗄️ BigQuery", "✅ Excel", "📊 HTML"],
        profile_image=profile_image
    )
elif page == "notion":
    render_notion()
elif page == "spam":
    render_spam()
elif page == "waste":
    render_waste()