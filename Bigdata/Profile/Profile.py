import streamlit as st

def show_profile(name, student_id, major, interest, experience, skills, profile_image=None):
    st.title("👤 Profile Page")
    
    col1, col2 = st.columns([1, 4]) 
    with col1:
        st.markdown('<div class="profile-img-container">', unsafe_allow_html=True)
        if profile_image:
            st.image(profile_image, width=200, clamp=True, output_format="JPEG", 
                     caption="Profile Picture",
                     use_column_width="auto", 
                     ) 
            st.markdown('<style>img {border-radius: 50%; border: 4px solid #4CAF50; box-shadow: 0 4px 8px rgba(0,0,0,0.2); object-fit: cover;} </style>', unsafe_allow_html=True)
        else:
            st.warning("ไม่พบรูปภาพ")
        st.markdown('</div>', unsafe_allow_html=True) 

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