import streamlit as st
import requests
import bs4
import pandas as pd
import numpy as np
import altair as alt

def render_notion():
    st.markdown("<h2>📊 YouTube TH Top 1000 Dashboard</h2><div class='subtle'>วิเคราะห์แนวโน้มและ Insight ของวิดีโอยอดนิยม 1,000 อันดับแรกในไทย</div>", unsafe_allow_html=True)
    st.markdown("""
แอปพลิเคชันนี้ทำการดึงข้อมูล (Scraping) จากเว็บ
[youtubers.me](https://th.youtubers.me/thailand/all/top-1000-youtube-videos-in-thailand)
เพื่อวิเคราะห์แนวโน้มและ Insight ที่น่าสนใจของวิดีโอยอดนิยม 1,000 อันดับแรกในประเทศไทย
""")

    # ปุ่มสำหรับเคลียร์ Cache เผื่อเว็บอัปเดตหรือโหลดค้าง
    if st.button("🔄 โหลดข้อมูลใหม่ (Clear Cache)"):
        st.cache_data.clear()

    @st.cache_data(ttl=3600) # ให้ระบบจำข้อมูลไว้ 1 ชั่วโมง จะได้ไม่ต้องดึงเว็บรัวๆ
    def load_and_clean_data():
        try:
            # 1. ปลอมตัวเป็นเบราว์เซอร์เพื่อหลบการบล็อก
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7'
            }
            response = requests.get(
                'https://th.youtubers.me/thailand/all/top-1000-youtube-videos-in-thailand', 
                headers=headers, 
                timeout=15
            )
            response.raise_for_status() 
            response.encoding = 'utf-8'
            soup = bs4.BeautifulSoup(response.text, 'html.parser')

            data = []
            tables = soup.find_all('table')
            if not tables:
                return pd.DataFrame()

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

            df = pd.DataFrame(data, columns=['Rank', 'Vid_name', 'Views', 'Like', 'Dislike', 'Category', 'Publish'])
            df = df[df['Category'] != '']

            # แปลงตัวเลข และจัดการกับค่าว่าง (NaN) ให้เป็น 0 เพื่อป้องกัน React Error
            for col in ['Views', 'Like', 'Dislike']:
                df[col] = pd.to_numeric(df[col].str.replace(',', ''), errors='coerce').fillna(0)
            
            df['Publish'] = pd.to_numeric(df['Publish'], errors='coerce')

            df = df.astype({'Views': 'int64', 'Like': 'int64'})

            # คำนวณ Engagement Rate
            df['Engagement_Rate'] = df.apply(
                lambda row: (row['Like'] / row['Views']) * 100 if row['Views'] > 0 else 0, axis=1
            )
            
            # 🛡️ จุดสำคัญ: กำจัดค่า Infinity และ NaN ที่ทำให้เกิด Error 185
            df['Engagement_Rate'] = df['Engagement_Rate'].replace([np.inf, -np.inf], 0).fillna(0)

            return df
            
        except Exception as e:
            st.error(f"⚠️ ไม่สามารถดึงข้อมูลจากเว็บได้ชั่วคราว: {e}")
            return pd.DataFrame() 

    with st.spinner('กำลังดึงและประมวลผลข้อมูลล่าสุด...'):
        df = load_and_clean_data()

    if df.empty:
        st.warning("ไม่มีข้อมูลสำหรับแสดงผลในขณะนี้ กรุณากดปุ่ม 'โหลดข้อมูลใหม่' ด้านบน หรือลองอีกครั้งภายหลัง")
        return

    # ================= KPIs =================
    st.header('ภาพรวมข้อมูล (Overall KPIs)')
    col1, col2, col3 = st.columns(3)
    total_videos = len(df)
    total_views = df['Views'].sum()
    top_category = df['Category'].mode()[0] if not df.empty else "-"
    col1.metric("จำนวนวิดีโอที่วิเคราะห์", f"{total_videos:,.0f}")
    col2.metric("ยอดวิวรวมทั้งหมด", f"{total_views/1e9:.2f} พันล้าน")
    col3.metric("หมวดหมู่ยอดนิยมที่สุด", top_category)
    st.divider()

    # ================= 🎚️ YEAR SLIDER =================
    st.header('1. แนวโน้มภาพรวมในแต่ละปี (Yearly Trends)')
    
    valid_years = df.dropna(subset=['Publish'])['Publish'].astype(int)
    if not valid_years.empty:
        min_year = int(valid_years.min())
        max_year = int(valid_years.max())
        
        # แสดง Slider
        selected_years = st.slider(
            "🗓️ เลือกช่วงปีที่ต้องการวิเคราะห์:",
            min_value=min_year,
            max_value=max_year,
            value=(min_year, max_year) # ค่าเริ่มต้นคือคลุมทุกปี
        )
        
        # กรองข้อมูลตารางและกราฟทั้งหมดตามปีที่เลือก!
        df_filtered_years = df[(df['Publish'] >= selected_years[0]) & (df['Publish'] <= selected_years[1])]
    else:
        df_filtered_years = pd.DataFrame()
        st.info("ไม่พบข้อมูลปีที่สามารถวิเคราะห์ได้")

    if not df_filtered_years.empty:
        yearly_stats = df_filtered_years.groupby('Publish').agg(
            Video_Count=('Vid_name', 'count'),
            Average_Views=('Views', 'mean')
        ).reset_index().rename(columns={'Publish': 'Year'})
        
        st.dataframe(yearly_stats, use_container_width=True)
        st.line_chart(yearly_stats.rename(columns={'Year':'index'}).set_index('index')['Average_Views'])
        st.caption("กราฟเส้นแสดงยอดวิวเฉลี่ยของวิดีโอในช่วงปีที่เลือก")
    st.divider()

    # ================= Category Popularity =================
    st.header('2. หมวดหมู่ยอดนิยมในช่วงปีที่เลือก (Category Popularity)')
    if not df_filtered_years.empty:
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

            chart1 = alt.Chart(yearly_category_stats).mark_bar().encode(
                x=alt.X('Year:O', title='ปี', axis=alt.Axis(format='d')), # ตั้งค่าให้แกนปีไม่มีคอมม่า (เช่น 2020 ไม่ใช่ 2,020)
                y=alt.Y('Top Category Proportion (%):Q', title='สัดส่วน (%)'),
                color=alt.Color('Top Video Category:N', title='หมวดหมู่'),
                tooltip=['Year', 'Top Video Category', 'Top Category Proportion (%)']
            ).properties(title='สัดส่วนของหมวดหมู่วิดีโอยอดนิยมอันดับ 1')
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
        st.info("ไม่มีข้อมูลเพียงพอสำหรับสร้างกราฟ Category Popularity")
    st.divider()

    # ================= Deep Dive =================
    st.header('3. เจาะลึกรายหมวดหมู่และ Engagement (Deep Dive)')
    col_engage, col_search = st.columns([1, 2])
    
    # ดึงข้อมูลจาก Slider (หรือใช้ข้อมูลทั้งหมดถ้าไม่ได้เลือกปี)
    target_df = df_filtered_years if not df_filtered_years.empty else df
    
    with col_engage:
        st.subheader("หมวดหมู่ที่สร้าง Engagement สูงสุด")
        engagement_by_category = target_df.groupby('Category')['Engagement_Rate'].mean().sort_values(ascending=False).reset_index()
        
        # 🛡️ จัดการค่า max_value ให้ปลอดภัย ไม่เป็นสาเหตุของ React Error #185
        if not engagement_by_category.empty:
            max_eng = float(engagement_by_category['Engagement_Rate'].max())
            if np.isnan(max_eng) or np.isinf(max_eng) or max_eng <= 0:
                max_eng = 100.0 
        else:
            max_eng = 100.0

        st.dataframe(
            engagement_by_category,
            column_config={
                "Category": "หมวดหมู่",
                "Engagement_Rate": st.column_config.ProgressColumn(
                    "Engagement Rate (Avg %)",
                    format="%.2f%%",
                    min_value=0,
                    max_value=max_eng
                )
            },
            use_container_width=True
        )
        st.caption("คำนวณจาก (Likes / Views) * 100")
        
    with col_search:
        st.subheader("ค้นหาวิดีโอยอดนิยมตามหมวดหมู่")
        category_list = ['All'] + sorted(target_df['Category'].dropna().unique().tolist())
        selected_category = st.selectbox("เลือกหมวดหมู่ที่สนใจ:", category_list)
        
        display_df = target_df if selected_category == 'All' else target_df[target_df['Category'] == selected_category]
        
        # เคลียร์ค่า NaN สำหรับแสดงผลในตาราง
        display_df = display_df.fillna(0)
        
        st.dataframe(
            display_df[['Rank', 'Vid_name', 'Views', 'Like', 'Publish']].head(20), 
            use_container_width=True
        )