import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.utils import to_categorical
import joblib

# โหลดข้อมูล
df = pd.read_csv("E:/ProjectPython/models/thai_soil_train_isan_phangkhon_npk_separated.csv")

# Preprocessing
# Encode categorical features
le_plant = LabelEncoder()
df['plant_encoded'] = le_plant.fit_transform(df['plant'])
le_region = LabelEncoder()
df['region_encoded'] = le_region.fit_transform(df['region'])
le_soil = LabelEncoder()
df['soil_type_encoded'] = le_soil.fit_transform(df['soil_type'])
le_season = LabelEncoder()
df['season_encoded'] = le_season.fit_transform(df['season'])

# แยก features และ target
X = df[['moisture', 'pH', 'N', 'P', 'K', 'region_encoded', 'soil_type_encoded', 'season_encoded']]
y = to_categorical(df['plant_encoded'])  # One-hot encoding สำหรับ output (17 คลาส)

# Feature scaling
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# แบ่งข้อมูล train/test
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

# สร้างโมเดล MLP
model = Sequential([
    Dense(128, activation='relu', input_shape=(8,)),  # 8 features: moisture, pH, N, P, K, region, soil_type, season
    Dropout(0.3),  # ป้องกัน overfitting
    Dense(64, activation='relu'),
    Dropout(0.3),
    Dense(22, activation='softmax')  # 17 คลาส (จำนวนพืชใน dataset)
])

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

# ฝึกโมเดล
model.fit(X_train, y_train, epochs=100, batch_size=32, validation_split=0.2, verbose=1)

# ประเมินผล
loss, accuracy = model.evaluate(X_test, y_test)
print(f"Test Accuracy: {accuracy:.2f}")

# บันทึกโมเดลและ encoders/scaler
model.save("E:/ProjectPython/models/soil_plant_mlp_isan_npk_separated.h5")
joblib.dump(le_plant, "E:/ProjectPython/models/label_encoder_plant_isan_npk_separated.pkl")
joblib.dump(le_region, "E:/ProjectPython/models/label_encoder_region_isan_npk_separated.pkl")
joblib.dump(le_soil, "E:/ProjectPython/models/label_encoder_soil_isan_npk_separated.pkl")
joblib.dump(le_season, "E:/ProjectPython/models/label_encoder_season_isan_npk_separated.pkl")
joblib.dump(scaler, "E:/ProjectPython/models/scaler_isan_npk_separated.pkl")

# ตัวอย่างการทำนาย (ใช้ค่าที่สมจริงสำหรับสกลนคร)
sample = [[55.0, 5.0, 35.0, 5.0, 90.0, le_region.transform(['อีสาน'])[0], 
           le_soil.transform(['ดินร่วนทราย'])[0], le_season.transform(['ฝน'])[0]]]
sample_scaled = scaler.transform(sample)
pred = model.predict(sample_scaled)
predicted_plant = le_plant.inverse_transform([np.argmax(pred)])[0]
print(f"Predicted plant for moisture=55.0, pH=5.0, N=35.0, P=5.0, K=90.0, region=อีสาน, soil_type=ดินร่วนทราย, season=ฝน: {predicted_plant}")

print("\n\n-----------------------------------------------------------")
print("✅  คัดลอกค่า C++ ข้างล่างนี้ไปใช้ใน Arduino ของคุณ")
print("-----------------------------------------------------------")

# พิมพ์ค่า Mean และ Scale ในรูปแบบ C++
print("const float scaler_mean[8] = {", end="")
print(*scaler.mean_, sep=", ", end="};\n")

print("const float scaler_scale[8] = {", end="")
print(*scaler.scale_, sep=", ", end="};\n")

# พิมพ์รายชื่อพืช (Plant Classes) ในรูปแบบ C++
print("const char* plant_classes[] = {", end="")
class_list = [f'"{name}"' for name in le_plant.classes_]
print(*class_list, sep=", ", end="};\n")

print("-----------------------------------------------------------")