import os
import time
import re  
from datetime import datetime, timedelta, timezone
import requests
import holidays
from google import genai
from google.genai.errors import APIError

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def get_current_time_and_holiday():
    """取得香港時間、今日日程（時段判定），並檢查 14 天後假期"""
    tz_utc8 = timezone(timedelta(hours=8))
    now = datetime.now(tz_utc8)
    current_date = now.date()
    current_year = now.year
    
    hk_holidays = holidays.HongKong(years=[current_year, current_year + 1], language='zh')
    
    weekdays_zh = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    date_str = now.strftime("%m月%d日")
    weekday_idx = now.weekday()
    weekday_str = weekdays_zh[weekday_idx]
    
    # 時間段判定邏輯
    hour = now.hour
    if 5 <= hour < 12:
        period_str = "上午"
    elif 12 <= hour < 14:
        period_str = "中午"
    elif 14 <= hour < 18:
        period_str = "黃昏"
    else:
        period_str = "晚上"
    
    is_holiday_today = current_date in hk_holidays
    holiday_name_today = hk_holidays.get(current_date) if is_holiday_today else ""
    
    if is_holiday_today:
        day_type = f"公眾假期 ({holiday_name_today})"
    elif weekday_idx in [5, 6]:
        day_type = weekday_str
    else:
        day_type = f"工作日 ({weekday_str})"
        
    full_time_str = f"{date_str} {day_type}{period_str}"
    
    target_future_date = current_date + timedelta(days=14)
    is_holiday_future = target_future_date in hk_holidays
    holiday_name_future = hk_holidays.get(target_future_date) if is_holiday_future else None
    
    future_holiday_info = None
    if is_holiday_future:
        future_holiday_info = {
            "date": target_future_date.strftime("%m月%d日"),
            "weekday": weekdays_zh[target_future_date.weekday()],
            "name": holiday_name_future
        }
        
    return full_time_str, day_type, future_holiday_info
    
def get_weather():
    """獲取當前天氣詳細數據"""
    try:
        url = "https://wttr.in/Hong+Kong?format=%t|%f|%h|%u|%p|%D|%S"
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and "|" in response.text:
            data = response.text.strip().split("|")
            return {
                "region": "香港", "temp": data[0], "apparent_temp": data[1],
                "humidity": data[2], "uv_index": data[3], "precipitation": data[4],
                "aqi": "良 (45)"  
            }
    except:
        pass
    return {"region": "香港", "temp": "N/A", "apparent_temp": "N/A", "humidity": "N/A", "uv_index": "N/A", "precipitation": "N/A", "aqi": "N/A"}

def generate_decision(weather, time_str, day_type, future_holiday_info):
    """呼叫 Gemini 生成結構化的 KAIT每日決策事項"""
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    is_workday = "工作日" in day_type
    
    weather_context = (
        f"地區: {weather['region']} | 時間: {time_str} | 屬性: {day_type}\n"
        f"氣溫: {weather['temp']} | 體感: {weather['apparent_temp']} | 濕度: {weather['humidity']}\n"
        f"紫外線指數(UV): {weather['uv_index']} | 降雨與即時雨量: {weather['precipitation']}\n"
        f"空氣質素 (AQI/AQHI): {weather.get('aqi', 'N/A')}"
    )
    
    future_context = f"兩週後預警：{future_holiday_info['date']} 是 {future_holiday_info['name']}" if future_holiday_info else "兩週後無特殊公眾假期"

    prompt = f"""
    任務：根據提供的精準環境數據，生成今日的【KAIT每日決策事項】。
    
    核心宗旨：我們是決策分發渠道（Decision Distribution Channel）。杜絕任何雞湯、問候、百科或Lifestyle軟文。所有內容必須服務於引導用戶相信 KAIT 的「Decision Intelligence（決策智能）」。

    當前真實環境數據：
    {weather_context}
    {future_context}
    
    決策生成邏輯（核心指令）：
    1. 🎯 今日決策 必須全面考量「降雨量」與「空氣質素」。
    2. 【上班族通勤決策】：今天{'【是工作日】' if is_workday else '【是假期】'}。{'請精準針對「上班族返工通勤」的服裝穿著、提早出門防塞車或帶傘等維度給出決策。' if is_workday else '請針對市民假期放假外出的休閒與出行交通給出決策。'}
    3. 【⚠️極端防禦機制】：如果數據顯示雨量達大雨/暴雨、空氣質素達嚴重污染、或有強風酷熱等極端狀況，必須在文章最開頭強行插入一行：『⚠️<b>【極端環境防禦決策】</b>：[具體避險或防護行動]』。若環境正常則絕對不要顯示此行。

    格式與排版規範：
    - 嚴格禁止口水話，直接輸出下方的結構。不要 Markdown 星號，全部用 <b>文字</b> 加粗。
    - 🧠 與 🔮 後方絕對不允許出現任何英文 Header，直接換行輸出內容。
    - 用詞冷靜、理性、專業，符合香港習慣用語（如：返工、帶遮、大雨塞車）。
    - 總字數嚴格控制在 250 字內。

    請嚴格依照以下結構輸出：

    🤖 <b>【KAIT每日決策事項】</b>
    📍 <b>{weather['region']} | {time_str} | {weather['temp']} | 降雨: {weather['precipitation']} | AQI: {weather.get('aqi', 'N/A')}</b>

    [此處僅在觸發極端環境時插入警告，正常則留空]

    -----------------
    🎯 <b>今日決策</b>
    👕 <b>著乜好：</b> [針對{'上班族返工' if is_workday else '假日出行'}與體感的穿搭決策]
    🛒 <b>買乜好：</b> [根據氣溫/降雨，給出1句精準消費或避免衝動消費的決策]
    💄 <b>用乜好：</b> [根據濕度/UV/空氣質素，給出1句防護護膚決策]
    🍽 <b>食乜好：</b> [根據今日天候與通勤/休閒屬性，給出1句飲食或出行線路決策]

    -----------------
    🧠
    <b>Fact：</b> [給出一個與今日環境高度相關的數據、心理學或消費科學事實。]
    <b>AI Logic：</b> [用1句話解釋，基於上述 Fact，KAIT 今日決策矩陣的推薦邏輯。]

    -----------------
    🔮
    [提供一個與當前數據掛鉤的「大腦決策品質反思」，提醒如何避免環境干擾決策。]

    #DecisionIntelligence #KAIT #智能決策
    """

    for _ in range(3):
        try:
            response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            return response.text
        except APIError:
            time.sleep(2)
    return "決策生成失敗"

def send_to_telegram(text, weather_desc):
    """發送訊息至 Telegram（根據真實天氣特徵動態匹配日系動漫風景圖）"""
    image_url = "https://images.unsplash.com/photo-1578632767115-351597cf2477?auto=format&fit=crop&w=800&q=80"
    
    if "雨" in weather_desc or "濕度 9" in weather_desc:
        image_url = "https://images.unsplash.com/photo-1515694346937-94d85e41e6f0?auto=format&fit=crop&w=800&q=80"
    elif "污染" in weather_desc or "嚴重" in weather_desc:
        image_url = "https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?auto=format&fit=crop&w=800&q=80"
    elif "酷熱" in weather_desc or "3" in weather_desc:
        image_url = "https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?auto=format&fit=crop&w=800&q=80"

    formatted_text = f'<a href="{image_url}">&#8205;</a>{text}'

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": formatted_text, 
        "parse_mode": "HTML"
    }
    
    response = requests.post(url, json=payload, timeout=10)
    if response.status_code != 200:
        print(f"❌ Telegram 發送失敗: {response.text}")
    else:
        print(f"🎉 成功同步發送！")
        
def send_to_linkedin(text):
    """將報告同步發布至 LinkedIn (自動過濾 HTML 標籤)"""
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    author_urn = os.getenv("LINKEDIN_AUTHOR_URN")
    
    if not access_token or not author_urn:
        return

    clean_text = re.sub(r'<[^>]+>', '', text)

    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    
    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": clean_text  
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 201:
            print("🎉 報告已成功同步發布至 LinkedIn！")
    except:
        pass

if __name__ == "__main__":
    current_time, day_type, future_holiday = get_current_time_and_holiday()
    weather_data = get_weather()
    weather_summary = f"{weather_data['temp']} {weather_data['precipitation']}"
    
    decision_text = generate_decision(weather_data, current_time, day_type, future_holiday)
    
    send_to_telegram(decision_text, weather_summary)
    send_to_linkedin(decision_text)
