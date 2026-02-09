import pandas as pd
import numpy as np

# Plants dict adjusted for Isan saline acidic soil, with separate N, P, K ranges
plants_isan = {
    "ข้าว": {"moisture": (60, 80, 5), "pH": (5.0, 6.0, 0.3), "N": (20, 50, 5), "P": (1, 10, 2), "K": (20, 160, 20)},
    "ข้าวโพด": {"moisture": (50, 70, 5), "pH": (5.0, 6.5, 0.4), "N": (30, 60, 5), "P": (5, 15, 3), "K": (50, 160, 20)},
    "มันสำปะหลัง": {"moisture": (40, 60, 5), "pH": (4.5, 6.0, 0.3), "N": (20, 40, 5), "P": (1, 10, 2), "K": (20, 140, 20)},
    "อ้อย": {"moisture": (50, 70, 5), "pH": (5.0, 7.0, 0.5), "N": (30, 60, 5), "P": (5, 15, 3), "K": (50, 160, 25)},
    "ถั่วเขียว": {"moisture": (50, 70, 5), "pH": (5.5, 6.5, 0.3), "N": (20, 40, 5), "P": (5, 10, 2), "K": (20, 120, 15)},
    "ขิง": {"moisture": (50, 70, 5), "pH": (5.0, 6.0, 0.3), "N": (20, 40, 5), "P": (1, 10, 2), "K": (20, 120, 15)},
    "ขมิ้น": {"moisture": (50, 70, 5), "pH": (5.0, 6.0, 0.3), "N": (20, 40, 5), "P": (1, 10, 2), "K": (20, 120, 15)},
    "มะม่วง": {"moisture": (40, 60, 5), "pH": (5.0, 6.5, 0.4), "N": (20, 40, 5), "P": (1, 10, 2), "K": (20, 140, 20)},
    "กล้วย": {"moisture": (60, 80, 5), "pH": (5.0, 6.0, 0.3), "N": (30, 60, 5), "P": (5, 15, 3), "K": (50, 160, 25)},
    "ยางพารา": {"moisture": (50, 70, 5), "pH": (4.5, 5.5, 0.3), "N": (20, 40, 5), "P": (1, 10, 2), "K": (20, 120, 15)},
    "ปาล์มน้ำมัน": {"moisture": (50, 70, 5), "pH": (4.5, 6.0, 0.4), "N": (20, 50, 5), "P": (1, 10, 2), "K": (20, 140, 20)},
    "สับปะรด": {"moisture": (40, 60, 5), "pH": (4.5, 5.5, 0.3), "N": (20, 40, 5), "P": (1, 10, 2), "K": (20, 120, 15)},
    "ชา": {"moisture": (50, 70, 5), "pH": (4.5, 5.5, 0.3), "N": (20, 40, 5), "P": (1, 10, 2), "K": (20, 120, 15)},
    "กาแฟ": {"moisture": (50, 70, 5), "pH": (5.0, 6.0, 0.3), "N": (20, 40, 5), "P": (1, 10, 2), "K": (20, 140, 20)},
    "ข้าวเหนียวดำ": {"moisture": (60, 80, 5), "pH": (5.0, 6.0, 0.3), "N": (20, 50, 5), "P": (1, 10, 2), "K": (20, 160, 20)},
    "กล้วยน้ำว้า": {"moisture": (60, 80, 5), "pH": (5.0, 6.0, 0.3), "N": (30, 60, 5), "P": (5, 15, 3), "K": (50, 160, 25)},
    "สะตอ": {"moisture": (50, 70, 5), "pH": (5.0, 6.0, 0.3), "N": (20, 40, 5), "P": (1, 10, 2), "K": (20, 140, 20)},
    "มะละกอ": {"moisture": (50, 70, 5), "pH": (5.5, 7.0, 0.4), "N": (30, 50, 5), "P": (5, 15, 3), "K": (50, 150, 20)},
    "มะม่วงหิมพานต์": {"moisture": (40, 60, 5), "pH": (5.0, 6.5, 0.3), "N": (20, 40, 5), "P": (1, 10, 2), "K": (20, 120, 15)},
    "แตงโม": {"moisture": (50, 70, 5), "pH": (5.5, 6.5, 0.3), "N": (30, 60, 5), "P": (5, 15, 3), "K": (40, 140, 20)},
    "พริก": {"moisture": (50, 65, 5), "pH": (5.0, 6.5, 0.4), "N": (20, 50, 5), "P": (5, 15, 3), "K": (50, 150, 20)},
    "ยาสูบ": {"moisture": (40, 60, 5), "pH": (5.0, 6.0, 0.3), "N": (20, 40, 5), "P": (1, 10, 2), "K": (20, 100, 15)}
}

# Fixed region to อีสาน
region = "อีสาน"

# Soil types relevant to Isan (added saline clay)
soil_types = ["ดินร่วนทราย", "ดินทราย", "ดินเหนียวเค็ม"]

# Seasons in Isan
seasons = ["ฝน", "ร้อน", "หนาว"]

# Real means from Phang Khon soil data
real_ph_mean = 5.0
real_moisture_mean = 55.0
real_n_mean = 35.0  # Low nitrogen
real_p_mean = 5.0   # Very low phosphorus
real_k_mean = 90.0  # Low to medium potassium

data = []
num_samples_per_plant = 200  # For deep learning

for plant, ranges in plants_isan.items():
    for _ in range(num_samples_per_plant):
        # Use real means with variance
        moisture = np.clip(np.random.normal(real_moisture_mean, ranges["moisture"][2]), 
                           ranges["moisture"][0], ranges["moisture"][1])
        pH = np.clip(np.random.normal(real_ph_mean, ranges["pH"][2]), 
                     ranges["pH"][0], ranges["pH"][1])
        N = np.clip(np.random.normal(real_n_mean, ranges["N"][2]), 
                    ranges["N"][0], ranges["N"][1])
        P = np.clip(np.random.normal(real_p_mean, ranges["P"][2]), 
                    ranges["P"][0], ranges["P"][1])
        K = np.clip(np.random.normal(real_k_mean, ranges["K"][2]), 
                    ranges["K"][0], ranges["K"][1])
        
        soil_type = np.random.choice(soil_types)
        season = np.random.choice(seasons)
        
        # Round values
        moisture = round(moisture, 1)
        pH = round(pH, 2)
        N = round(N, 2)
        P = round(P, 2)
        K = round(K, 2)
        
        data.append([moisture, pH, N, P, K, region, soil_type, season, plant])

# Create DataFrame
df = pd.DataFrame(data, columns=["moisture", "pH", "N", "P", "K", "region", "soil_type", "season", "plant"])

# Save to CSV
df.to_csv("E:/ProjectPython/models/thai_soil_train_isan_phangkhon_npk_separated.csv", index=False)

print("✅ สร้างไฟล์ 'thai_soil_train_isan_phangkhon_npk_separated.csv' เรียบร้อยแล้ว!")
print(f"จำนวนพืช: {len(plants_isan)} ชนิด, จำนวนแถวข้อมูล: {len(df)} แถว")
print("\nตัวอย่างข้อมูล:")
print(df.head(10))