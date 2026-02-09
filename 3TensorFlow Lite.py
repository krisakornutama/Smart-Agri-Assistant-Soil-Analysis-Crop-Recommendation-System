import tensorflow as tf
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
import joblib

# โหลดข้อมูลเพื่อสร้าง representative dataset
df = pd.read_csv("E:/ProjectPython/models/thai_soil_train_isan_phangkhon_npk_separated.csv")

# Encode categorical features (เหมือนในขั้นตอนฝึกโมเดล)
le_region = LabelEncoder()
df['region_encoded'] = le_region.fit_transform(df['region'])
le_soil = LabelEncoder()
df['soil_type_encoded'] = le_soil.fit_transform(df['soil_type'])
le_season = LabelEncoder()
df['season_encoded'] = le_season.fit_transform(df['season'])

# โหลด scaler จากไฟล์
scaler = joblib.load("E:/ProjectPython/models/scaler_isan_npk_separated.pkl")

# เตรียม features สำหรับ representative dataset (เก็บเป็น DataFrame เพื่อรักษาชื่อคอลัมน์)
X = df[['moisture', 'pH', 'N', 'P', 'K', 'region_encoded', 'soil_type_encoded', 'season_encoded']]

# ฟังก์ชัน representative dataset
def representative_dataset():
    for _, row in X.iterrows():
        # ส่ง DataFrame row พร้อมชื่อคอลัมน์เข้า scaler.transform
        scaled_data = scaler.transform([row])[0]
        yield [scaled_data.astype(np.float32)]

# โหลดโมเดล MLP
model = tf.keras.models.load_model("E:/ProjectPython/models/soil_plant_mlp_isan_npk_separated.h5")

# แปลงเป็น TensorFlow Lite
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.representative_dataset = representative_dataset
converter.target_spec.supported_types = [tf.int8]
converter.inference_input_type = tf.int8
converter.inference_output_type = tf.int8

# แปลงโมเดล
try:
    tflite_model = converter.convert()
    # บันทึกโมเดล .tflite
    with open("E:/ProjectPython/models/soil_plant_mlp_isan_npk_separated.tflite", "wb") as f:
        f.write(tflite_model)
    print("✅ แปลงโมเดลเป็น soil_plant_mlp_isan_npk_separated.tflite เรียบร้อยแล้ว!")
except Exception as e:
    print(f"เกิดข้อผิดพลาดในการแปลงโมเดล: {e}")

# บันทึก LabelEncoders เพื่อใช้ในการ decode ผลลัพธ์
joblib.dump(le_region, "E:/ProjectPython/models/label_encoder_region_isan_npk_separated.pkl")
joblib.dump(le_soil, "E:/ProjectPython/models/label_encoder_soil_isan_npk_separated.pkl")
joblib.dump(le_season, "E:/ProjectPython/models/label_encoder_season_isan_npk_separated.pkl")
joblib.dump(joblib.load("E:/ProjectPython/models/label_encoder_plant_isan_npk_separated.pkl"), 
            "E:/ProjectPython/models/label_encoder_plant_isan_npk_separated.pkl")