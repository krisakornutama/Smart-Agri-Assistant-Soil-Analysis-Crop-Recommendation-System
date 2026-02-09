// =================================================================
//      CONFIGURATION
// =================================================================
const SPREADSHEET_ID = '1G9uMIHuALSGOVOQu-Q4aHNSV8vVJQE_aNuv3TvkrMww'; // <-- ID Sheet ของคุณ
const SHEET_NAME = "Sheet1";
const CACHE_EXPIRATION_SECONDS = 300; // 5 นาที
const LONG_CACHE_EXPIRATION_SECONDS = 3600; // 1 ชั่วโมง (สำหรับรายชื่อแปลง)

// =================================================================
//      doGet: Serves the HTML user interface
// =================================================================
function doGet(e) {
  return HtmlService.createHtmlOutputFromFile('Dashboard')
    .setTitle('Soil & Plant Dashboard')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

// =================================================================
//      doPost: Handles incoming data from ESP32
// =================================================================
function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      Logger.log('Error: No valid postData received.');
      return createJsonResponse({ status: 'Error', message: 'No valid data received.' });
    }
    const requestData = JSON.parse(e.postData.contents);
    const projectId = requestData.ProjectId || "unknown_project";

    const sheet = getSheet_();
    const timestamp = new Date();
    let plantsArray = [];
    if (requestData.Plants && Array.isArray(requestData.Plants)) {
      plantsArray = requestData.Plants;
    }

    let topSuitability = null;
    if (plantsArray.length > 0) {
       topSuitability = plantsArray.reduce((max, p) => (p.suitability > max ? p.suitability : max), plantsArray[0].suitability);
       topSuitability = parseFloat(topSuitability) || null;
    }

    sheet.appendRow([
      projectId,
      requestData.Location || null,
      timestamp,
      parseFloat(requestData.Moisture) || null,
      parseFloat(requestData.PH) || null,
      parseFloat(requestData.N) || null,
      parseFloat(requestData.P) || null,
      parseFloat(requestData.K) || null,
      parseFloat(requestData.Temp) || null,
      parseFloat(requestData.EC) || null,
      JSON.stringify(plantsArray),
      topSuitability
    ]);

    const cache = CacheService.getScriptCache();
    // *** [แก้ไข] ลบ 'a_' ออก ***
    cache.remove('data_' + projectId);
    cache.remove('data_default');
    cache.remove('project_list');

    Logger.log(`Data appended for [${projectId}] and caches cleared.`);
    return createJsonResponse({ status: 'OK', message: 'Data received and saved.' });

  } catch (error) {
    Logger.log('Error in doPost: ' + error.toString() + ' Stack: ' + error.stack);
    return createJsonResponse({ status: 'Error', message: error.toString() });
  }
}

// =================================================================
//      getProjectList: (Level 2)
// =================================================================
function getProjectList() {
  const cache = CacheService.getScriptCache();
  const cacheKey = 'project_list';
  const cachedData = cache.get(cacheKey);

  if (cachedData != null) {
    Logger.log('Serving project list from cache.');
    return JSON.parse(cachedData);
  }

  Logger.log('Cache miss. Fetching project list from Google Sheet.');
  try {
    const sheet = getSheet_();
    const lastRow = sheet.getLastRow();
    if (lastRow < 2) {
      return [];
    }

    const range = sheet.getRange(2, 1, lastRow - 1, 1);
    const values = range.getValues();
    const uniqueProjects = [...new Set(values.map(row => row[0]).filter(Boolean))];
    cache.put(cacheKey, JSON.stringify(uniqueProjects), LONG_CACHE_EXPIRATION_SECONDS);
    return uniqueProjects;

  } catch (error) {
    Logger.log('Error in getProjectList: ' + error.message);
    throw new Error('Could not retrieve project list. ' + error.message);
  }
}


// =================================================================
//      getDashboardData: (อัปเกรด Level 4)
// =================================================================
function getDashboardData(projectId) {
  const cache = CacheService.getScriptCache();
  const cacheKey = 'data_' + (projectId || 'default');

  const cachedData = cache.get(cacheKey);
  if (cachedData != null) {
    Logger.log(`Serving data from cache for key: [${cacheKey}]`);
    return JSON.parse(cachedData);
  }

  Logger.log(`Cache miss. Fetching data for key: [${cacheKey}] (Slow mode)`);
  try {
    const sheet = getSheet_();
    const allData = sheet.getDataRange().getValues();
    allData.shift();

    if (allData.length === 0) {
      return { latestReading: null, history: [], insights: [] };
    }

    let targetProjectId = projectId;
    if (!targetProjectId) {
      targetProjectId = allData[allData.length - 1][0];
      Logger.log(`No projectId specified. Defaulting to last known: [${targetProjectId}]`);
    }

    const projectData = allData.filter(row => row[0] === targetProjectId);
    if (projectData.length === 0) {
      Logger.log(`No data found for projectId: [${targetProjectId}]`);
      return { latestReading: null, history: [], insights: [] };
    }

    const recentProjectData = projectData.slice(-20);

    const data = recentProjectData.map(row => {
      let plantData = null;
      try {
        const plantString = row[10];
        if (plantString && typeof plantString === 'string') {
           plantData = JSON.parse(plantString.replace(/""/g, '"'));
        }
      } catch (e) {
        plantData = null;
      }

      let timestampValue = row[2];
      let isoTimestamp = null;
      if (timestampValue) {
        try {
          if (timestampValue instanceof Date) {
            isoTimestamp = timestampValue.toISOString();
          } else {
            isoTimestamp = new Date(timestampValue.toString().replace(' ', 'T')).toISOString();
          }
        } catch (e) {
          isoTimestamp = null;
        }
      }

      return {
        projectId: row[0],
        location: row[1],
        timestamp: isoTimestamp,
        moisture: row[3],
        pH: row[4],
        N: row[5],
        P: row[6],
        K: row[7],
        temp: row[8],
        ec: row[9],
        plants: plantData, // <-- นี่คือคำแนะนำ "ดิบ" จาก ESP32
        suitability: row[11]
      };
    });

    const reversedData = data.reverse();
    const historyData = reversedData.slice(0, 10);
    const latestReading = reversedData[0]; // <-- ดึงข้อมูลล่าสุดออกมาก่อน

    // --- [อัปเกรด Level 1] ---
    const insights = analyzeTrends_(historyData);

    // --- [อัปเกรด Level 4] ---
    // เรียก "สมอง" ใหม่ มาตรวจสอบและแก้ไขคำแนะนำพืช
    const correctedPlants = overridePlantLogic_(latestReading.plants, insights);

    // "เขียนทับ" คำแนะนำเดิมด้วยคำแนะนำที่ฉลาดขึ้น
    latestReading.plants = correctedPlants;
    // --- จบการอัปเกรด Level 4 ---

    const response = {
      latestReading: latestReading, // <-- ส่ง latestReading ที่ถูกแก้ไขแล้ว
      history: historyData,
      insights: insights
    };

    cache.put(cacheKey, JSON.stringify(response), CACHE_EXPIRATION_SECONDS);

    return response;

  } catch (error) {
    Logger.log('Error in getDashboardData: ' + error.message + ' Stack: ' + error.stack);
    throw new Error('Could not retrieve data from Google Sheet. ' + error.message);
  }
}

// =================================================================
//      [ฟังก์ชันใหม่] LEVEL 4: The Override Logic
// =================================================================
/**
 * ตรวจสอบคำแนะนำพืช (จาก ESP32) เทียบกับ "แนวโน้ม" (จาก Code.js)
 * และแก้ไขคะแนนความเหมาะสมให้ตรงกับ "ความเป็นจริง"
 * @param {Array} plantsArray - Array คำแนะนำพืชดิบจาก ESP32
 * @param {Array} insights - Array ข้อมูลเชิงลึก (เช่น "ดินแห้งเร็ว")
 * @returns {Array} - Array คำแนะนำพืชที่ถูกแก้ไขแล้ว
 */
function overridePlantLogic_(plantsArray, insights) {
  // 1. คัดลอก Array (สำคัญมาก เพื่อไม่ให้กระทบ Cache)
  let correctedPlants = [];
  if (Array.isArray(plantsArray)) {
      correctedPlants = JSON.parse(JSON.stringify(plantsArray));
  } else {
      Logger.log("Warning in overridePlantLogic_: plantsArray is not an array. Returning empty array.");
      return []; // คืนค่า Array ว่างถ้าข้อมูลเข้าผิดพลาด
  }

  if (!insights || !Array.isArray(insights)) {
    Logger.log("Warning in overridePlantLogic_: insights is not an array. Returning original plants.");
    return correctedPlants; // คืนค่าเดิมถ้า insights ผิดพลาด
  }

  // 2. ตรวจสอบ "ความเสี่ยง" จาก Insights
  let soilIsDryingFast = false;
  // let soilIsDepleted = false; // (เผื่อสำหรับอนาคต)

  insights.forEach(insight => {
    if (insight.text.includes("ดินกำลังแห้งลงอย่างรวดเร็ว")) {
      soilIsDryingFast = true;
    }
    // (เราสามารถเพิ่มตรรกะเช็ค N ต่ำ หรือ EC พุ่งได้อีก)
    // ...
  });

  // 3. ถ้าพบความเสี่ยง "ดินแห้งเร็ว" (เหมือนใน 'โซนเนินทราย 5')
  if (soilIsDryingFast) {
    Logger.log("Override Logic: 'ดินแห้งเร็ว' ทำงาน! กำลังปรับคะแนน...");

    correctedPlants.forEach(plant => {

      // ลดคะแนนพืชที่ "หิวน้ำ" (ไม่ทนแล้ง)
      if (plant.plant === "อ้อย" || plant.plant === "ปาล์มน้ำมัน" || plant.plant === "ข้าว") {
        plant.suitability = plant.suitability * 0.3; // ลดคะแนนลง 70%
      }

      // เพิ่มคะแนนพืชที่ "ทนแล้ง"
      if (plant.plant === "มันสำปะหลัง" || plant.plant === "สับปะรด") {
        plant.suitability = plant.suitability * 1.5; // เพิ่มคะแนน 50%
      }
    });
  }

  return correctedPlants; // คืนค่า Array ที่ถูกแก้ไขแล้ว
}


// =================================================================
//      LEVEL 1: The Trend Analyst (ยังอยู่)
// =================================================================
function analyzeTrends_(history) {
  let insights = [];
  if (!history || history.length < 5) {
    return insights;
  }
  const latest = history[0];
  const oldest = history[history.length - 1];

  // (ตรวจสอบให้แน่ใจว่า latest และ oldest มีค่า)
  if (!latest || !oldest) return insights;

  const nDelta = (latest.N || 0) - (oldest.N || 0);
  if (nDelta < -50) {
    insights.push({ type: 'warning', text: `ค่า N ลดลงเร็วผิดปกติ (ลดลง ${Math.abs(nDelta).toFixed(0)} mg/kg)` });
  }
  if (nDelta > 100) {
    insights.push({ type: 'info', text: `ค่า N เพิ่มขึ้นสูง (เพิ่ม ${nDelta.toFixed(0)} mg/kg)` });
  }
  const ecDelta = (latest.ec || 0) - (oldest.ec || 0);
  if (ecDelta > 500) {
     insights.push({ type: 'danger', text: `ค่า EC พุ่งสูงขึ้นเร็ว (เพิ่ม ${ecDelta.toFixed(0)} µs/cm)` });
  }
  const moistureDelta = (latest.moisture || 0) - (oldest.moisture || 0);
  if (moistureDelta < -30) {
     insights.push({ type: 'warning', text: `ดินกำลังแห้งลงอย่างรวดเร็ว (ความชื้นลด ${Math.abs(moistureDelta).toFixed(0)}%)` });
  }
  if (insights.length === 0) {
     insights.push({ type: 'success', text: `ค่าดินส่วนใหญ่คงที่` });
  }
  return insights;
}

// =================================================================
//      HELPER FUNCTIONS (เหมือนเดิม)
// =================================================================
function createJsonResponse(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function getSheet_() {
  try {
    const spreadSheet = SpreadsheetApp.openById(SPREADSHEET_ID);
    const sheet = spreadSheet.getSheetByName(SHEET_NAME);
    if (!sheet) {
      throw new Error(`Sheet "${SHEET_NAME}" not found in Spreadsheet ID: ${SPREADSHEET_ID}`);
    }
    return sheet;
  } catch (error) {
    Logger.log("Error in getSheet_: " + error.message);
    throw new Error('Could not access Google Sheet. ' + error.message);
  }
}
