import streamlit as st
import numpy as np
import os
from PIL import Image

@st.cache_resource
def load_keras_model(path: str):
    import tensorflow as tf
    return tf.keras.models.load_model(path)

def render_waste():
    def _img(img, caption=None):
        try:
            st.image(img, caption=caption, use_container_width=True)
        except TypeError:
            st.image(img, caption=caption, use_column_width=True)

    st.markdown("<h2>🗑️ Waste Classification</h2><div class='subtle'>อัปโหลดภาพหรือถ่ายภาพจากกล้อง + ใช้โมเดล Keras (.keras/.h5)</div>", unsafe_allow_html=True)

    # Set up paths
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIR = os.path.dirname(CURRENT_DIR)
    default_model_path = os.path.join(ROOT_DIR, "Bigdata", "waste_model.keras")

    # ---------------- กล่องข้อมูล Dataset ----------------
    with st.expander("📚 แหล่งข้อมูลและโมเดล (Dataset & Model)", expanded=True):
        st.markdown(r"""
- **ชุดข้อมูล:** *Waste Classification Dataset* จาก Kaggle 
- **ตำแหน่งอ้างอิงชุดข้อมูล (Local):** `C:\Users\usEr\Documents\Bigdata-Project-main\Bigdata\Bigdata\archive`
- **การจำแนกประเภท (4 Classes):** จำลองการแยกขยะลงถัง 4 ประเภท ได้แก่ `Organic`, `Non-Recyclable`, `Hazardous`, และ `Recyclable`
        """)
    # --------------------------------------------------------

    # 1. แสดงรูปถังขยะและเขียนอธิบาย
    bin_image_path = r"C:\Users\usEr\Documents\Bigdata-Project-main\Bigdata\Bigdata\image\ถังขยะ.jpg"
    try:
        bin_image = Image.open(bin_image_path)
        _img(bin_image, caption="ถังขยะแยกประเภท")
    except FileNotFoundError:
        st.warning(f"ไม่พบไฟล์รูปภาพถังขยะ กรุณาตรวจสอบ Path: {bin_image_path}")

    st.markdown("""
        **🏷️ การแยกขยะตามสีถัง:**
        - <span style='color: green;'>🟢 <strong>ถังขยะสีเขียว:</strong></span> ขยะเปียก (Organic) – เศษอาหาร, เศษผัก, ผลไม้
        - <span style='color: blue;'>🔵 <strong>ถังขยะสีน้ำเงิน:</strong></span> ขยะทั่วไป (Non-Recyclable) – ถุงพลาสติก, กล่องโฟม, ผ้าอ้อมสำเร็จรูป, ผ้าอนามัย
        - <span style='color: red;'>🔴 <strong>ถังขยะสีแดง:</strong></span> ขยะอันตราย (Hazardous) – ถ่านไฟฉาย, ขยะอิเล็กทรอนิกส์, กระป๋องสเปรย์
        - <span style='color: #D4AF37;'>🟡 <strong>ถังขยะสีเหลือง:</strong></span> ขยะรีไซเคิล (Recyclable) – ขวดพลาสติก, ขวดแก้ว, กระดาษ, กระป๋อง
    """, unsafe_allow_html=True)

    st.markdown("---")

    model_path = st.text_input("Path โมเดล (.keras หรือ .h5)", value=default_model_path)
    class_names_str = st.text_input("ชื่อคลาส (คั่นด้วยจุลภาค, ลำดับต้องตรงกับตอนเทรน)", value="Hazardous,Non-Recyclable,Organic,Recyclable")
    class_names = [c.strip() for c in class_names_str.split(",") if c.strip()]

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

    # 🎨 แก้ไขตรงนี้: ใช้อีโมจิแทน HTML เพื่อให้ Streamlit รองรับ 100%
    bin_info_lookup = {
        "Organic": {"color_name": "🟢 ถังสีเขียว", "label_th": "ขยะเปียก"},
        "Non-Recyclable": {"color_name": "🔵 ถังสีน้ำเงิน", "label_th": "ขยะทั่วไป"},
        "Hazardous": {"color_name": "🔴 ถังสีแดง", "label_th": "ขยะอันตราย"},
        "Recyclable": {"color_name": "🟡 ถังสีเหลือง", "label_th": "ขยะรีไซเคิล"} 
    }

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
                # 🔴 แก้ไขตรงนี้: ไม่ต้องหาร 255 แล้ว เพราะ MobileNetV2 จัดการให้เองในตัวโมเดล
                arr = np.asarray(img_resized, dtype="float32") 
                arr = np.expand_dims(arr, axis=0)

                pred = model.predict(arr)[0]
                idx  = int(np.argmax(pred))
                conf = float(pred[idx])

                # แสดงผลลัพธ์
                bin_info = None
                category_name = f"Class {idx}"

                if class_names and len(class_names) > idx:
                    category_name = class_names[idx] 
                    bin_info = bin_info_lookup.get(category_name) 

                if bin_info:
                    st.success(f"ผลทำนาย: **{bin_info['color_name']} ({category_name})** | ความมั่นใจ {conf:.2%}")
                else:
                    st.success(f"ผลทำนาย: **{category_name}** | ความมั่นใจ {conf:.2%}")

                _img(img_resized, caption=f"ภาพที่ใช้ทำนาย ({W}×{H})")

                # แสดงตารางความน่าจะเป็น
                with st.expander("Probabilities (ความน่าจะเป็นของทุกคลาส)"):
                    try:
                        import pandas as pd
                        table_data = []
                        if class_names and len(class_names) == len(pred):
                            for i, p in enumerate(pred):
                                cat_name = class_names[i]
                                b_info = bin_info_lookup.get(cat_name)
                                if b_info:
                                    class_label_th = b_info.get("label_th", "อื่นๆ")
                                    name_to_display = f"{b_info['color_name']} ({class_label_th})"
                                else:
                                    name_to_display = cat_name
                                table_data.append({"ถังขยะ (ประเภท)": name_to_display, "probability": p})
                        else:
                            for i, p in enumerate(pred):
                                table_data.append({"ถังขยะ (ประเภท)": f"Class_{i}", "probability": p})

                        df_prob = pd.DataFrame(table_data)
                        st.dataframe(df_prob.sort_values("probability", ascending=False).reset_index(drop=True).style.format({"probability": "{:.2%}"}), use_container_width=True)
                    except Exception:
                        st.write({f"Class {i}": p for i, p in enumerate(pred)})

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")

    st.markdown("---")
    st.subheader("📌 สรุปการประยุกต์ใช้งานจริง & ประโยชน์")
    st.markdown("""
- **คัดแยกขยะอัจฉริยะ (Smart Bins / MRF):** ติดกล้องที่ถังขยะหรือสายพานลำเลียงให้ระบบจำแนกประเภทอัตโนมัติ ลดภาระคนงาน และเพิ่มความแม่นยำการรีไซเคิล
- **IoT + กล้อง ณ จุดทิ้งขยะ:** แจ้งเตือนเมื่อพบการทิ้งผิดประเภท (เช่น ขยะอันตรายปะปน) หรือคัดแยกเบื้องต้นก่อนเข้าระบบหลัก
- **งานเทศบาล/มหาวิทยาลัย/ห้างฯ:** สื่อสาร “ทิ้งให้ถูกที่” แบบเรียลไทม์ผ่านจอ/แอป ช่วยปรับพฤติกรรมประชาชนและเพิ่มอัตรารีไซเคิล
- **ธุรกิจรีไซเคิล/โลจิสติกส์:** ตรวจคุณภาพวัสดุเข้าโรงรีไซเคิล ออกใบรับรองหรือคำนวณมูลค่าจากประเภทวัสดุได้รวดเร็ว
- **ประโยชน์ทางเศรษฐกิจ & สิ่งแวดล้อม:** ลดต้นทุนแรงงานและความผิดพลาด เพิ่มอัตรารีไซเคิล ลดของเสียฝังกลบและการปล่อยก๊าซเรือนกระจก
- **ต่อยอดโมเดล:** เก็บภาพจริงหน้างานมาปรับปรุงชุดข้อมูล, ทำ active learning, เพิ่มคลาส/ย่อยคลาส (เช่น พลาสติกใส/ทึบ), และติดตามผลแบบ dashboard
    """)
    st.info("หมายเหตุ: การถ่ายด้วยกล้องผ่านเบราว์เซอร์ต้องอยู่บน HTTPS หรือ localhost และอนุญาตสิทธิ์การใช้กล้อง")