import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import matplotlib.pyplot as plt
import os

print("TensorFlow Version:", tf.__version__)

# ==========================================
# 1. ตั้งค่า Path และพารามิเตอร์ต่างๆ
# ==========================================
DATASET_DIR = r"C:\Users\usEr\Documents\Bigdata-Project-main\Bigdata\Bigdata\archive"
MODEL_SAVE_PATH = r"C:\Users\usEr\Documents\Bigdata-Project-main\Bigdata\waste_model.keras"

BATCH_SIZE = 32
IMG_SIZE = (224, 224) 
EPOCHS = 20  

# กำหนด 4 คลาสหลัก (เรียง A-Z)
TARGET_CLASSES = ['Hazardous', 'Non-Recyclable', 'Organic', 'Recyclable']

# ==========================================
# 🔍 ฟังก์ชันพิเศษ: ตรวจสอบและนับจำนวนรูปในหมวดย่อย
# ==========================================
print("\n🔎 กำลังสแกนโครงสร้างและนับจำนวนรูปภาพ...")
total_images = 0
for cls in TARGET_CLASSES:
    cls_path = os.path.join(DATASET_DIR, cls)
    if os.path.exists(cls_path):
        cls_count = 0
        subdirs_info = []
        # เดินตรวจดูทุกโฟลเดอร์ย่อย
        for root, dirs, files in os.walk(cls_path):
            # นับเฉพาะไฟล์รูปภาพ
            img_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            cls_count += len(img_files)
            if root != cls_path and len(img_files) > 0:
                subdirs_info.append(f"{os.path.basename(root)} ({len(img_files)} รูป)")
        
        total_images += cls_count
        print(f"📁 คลาส {cls}: รวม {cls_count} รูป")
        if subdirs_info:
            print(f"   ↳ หมวดย่อย: {', '.join(subdirs_info)}")
    else:
        print(f"❌ ไม่พบโฟลเดอร์: {cls_path}")
print(f"👉 สรุป: พบรูปภาพทั้งหมด {total_images} รูป\n")

# ==========================================
# 2. เตรียมชุดข้อมูล (Train & Validation Split)
# ==========================================
print("กำลังเตรียมชุดข้อมูลเข้าโมเดล...")
train_dataset = tf.keras.utils.image_dataset_from_directory(
    DATASET_DIR,
    validation_split=0.2, 
    subset="training",
    seed=123,
    image_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_names=TARGET_CLASSES 
)

validation_dataset = tf.keras.utils.image_dataset_from_directory(
    DATASET_DIR,
    validation_split=0.2,
    subset="validation",
    seed=123,
    image_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_names=TARGET_CLASSES 
)

AUTOTUNE = tf.data.AUTOTUNE
train_dataset = train_dataset.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)
validation_dataset = validation_dataset.cache().prefetch(buffer_size=AUTOTUNE)

# ==========================================
# 3. อัปเกรดสมอง AI (Transfer Learning ด้วย MobileNetV2)
# ==========================================
data_augmentation = keras.Sequential([
    layers.RandomFlip("horizontal", input_shape=(IMG_SIZE[0], IMG_SIZE[1], 3)),
    layers.RandomRotation(0.2), 
    layers.RandomZoom(0.2),
])

preprocess_input = tf.keras.applications.mobilenet_v2.preprocess_input
base_model = tf.keras.applications.MobileNetV2(
    input_shape=IMG_SIZE + (3,),
    include_top=False, 
    weights='imagenet' 
)

base_model.trainable = False 

num_classes = len(TARGET_CLASSES) 
inputs = keras.Input(shape=(224, 224, 3))
x = data_augmentation(inputs)
x = preprocess_input(x)       
x = base_model(x, training=False) 
x = layers.GlobalAveragePooling2D()(x) 
x = layers.Dropout(0.3)(x)    
outputs = layers.Dense(num_classes, activation='softmax')(x)

model = keras.Model(inputs, outputs)

model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), 
              loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=False),
              metrics=['accuracy'])

# ==========================================
# 4. เริ่มเทรนโมเดล (Training)
# ==========================================
early_stopping = tf.keras.callbacks.EarlyStopping(
    monitor='val_accuracy', 
    patience=5, 
    restore_best_weights=True
)

checkpoint_cb = tf.keras.callbacks.ModelCheckpoint(
    filepath=MODEL_SAVE_PATH,
    save_best_only=True,
    monitor='val_accuracy'
)

print("\n🚀 เริ่มต้นการเทรนโมเดล...")
history = model.fit(
    train_dataset,
    validation_data=validation_dataset,
    epochs=EPOCHS,
    callbacks=[checkpoint_cb, early_stopping]
)

print(f"\n🎉 เทรนเสร็จสิ้น! บันทึกโมเดลที่ดีที่สุดไว้ที่: {MODEL_SAVE_PATH}")

# ==========================================
# 5. วาดกราฟดูผลลัพธ์ (Plotting)
# ==========================================
acc = history.history['accuracy']
val_acc = history.history['val_accuracy']
loss = history.history['loss']
val_loss = history.history['val_loss']
epochs_range = range(len(acc))

plt.figure(figsize=(12, 5))
plt.subplot(1, 2, 1)
plt.plot(epochs_range, acc, label='Training Accuracy')
plt.plot(epochs_range, val_acc, label='Validation Accuracy')
plt.legend(loc='lower right')
plt.title('Training and Validation Accuracy')

plt.subplot(1, 2, 2)
plt.plot(epochs_range, loss, label='Training Loss')
plt.plot(epochs_range, val_loss, label='Validation Loss')
plt.legend(loc='upper right')
plt.title('Training and Validation Loss')

graph_path = os.path.join(os.path.dirname(MODEL_SAVE_PATH), "training_history_mobilenet.png")
plt.savefig(graph_path)
print(f"📊 บันทึกรูปกราฟไว้ที่: {graph_path}")
plt.show()