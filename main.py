import os
import time
from datetime import datetime, timedelta, timezone
import requests
import holidays
from google import genai
from google.genai.errors import APIError

# 1. 讀取 GitHub Secrets 的環境變數
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def get_current_time_and_holiday():
    """取得香港標準時間 (UTC+8)，判定今日屬性，並檢查 14 天後是否有公眾假期"""
    tz_utc8 = timezone(timedelta(hours=8))
    now = datetime.now(tz_utc8)
    current_date = now.date()
    current_year = now.year
    
    # 初始化香港假期套件
    hk_holidays = holidays.HongKong(years=[current_year, current_year + 1], language='zh')
    
    weekdays_zh = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    date_str = now.strftime("%Y年%m月%d日")
    time_str = now.strftime("%H:%M")
    weekday_idx = now.weekday()
    weekday_str = weekdays_zh[weekday_idx]
    
    is_holiday_today = current_date in hk_holidays
    holiday_name_today = hk_holidays.get(current_date) if is_holiday_today else ""
    
    if is_holiday_today:
        day_type = f"公眾假期 ({holiday_name_today})"
    elif weekday_idx in [5, 6]:
        day_type = f"週末 ({weekday_str})"
    else:
        day_type = f"常規工作日 ({weekday_str})"
        
    full_time_str = f"{date_str} {day_type} {time_str}"
    
    # 檢查 14 天後是否有公眾假期
    target_future_date = current_date + timedelta(days=14)
    is_holiday_future = target_future_date in hk_holidays
    holiday_name_future = hk_holidays.get(target_future_date) if is_holiday_future else None
    
    future_holiday_info = None
    if is_holiday_future:
        future_weekday_str = weekdays_zh[target_future_date.weekday()]
        future_holiday_info = {
            "date": target_future_date.strftime("%Y年%m月%d日"),
            "weekday": future_weekday_str,
            "name": holiday_name_future
        }
        
    return full_time_str, day_type, future_holiday_info

def get_weather():
    """獲取精準地區的當前天氣細節"""
    try:
        url = "https://wttr.in/Hong+Kong?format=%t|%f|%h|%u|%p|%D|%S"
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and "|" in response.text:
            data = response.text.strip().split("|")
            return {
                "region": "香港 (Hong Kong)",
                "temp": data[0],
                "apparent_temp": data[1],
                "humidity": data[2],
                "uv_index": data[3],
                "precipitation": data[4],
                "sunrise": data[5],
                "sunset": data[6]
            }
    except Exception as e:
        print(f"天氣抓取失敗: {str(e)}")
    
    return {
        "region": "香港", "temp": "N/A", "apparent_temp": "N/A", "humidity": "N/A",
        "uv_index": "N/A", "precipitation": "N/A", "sunrise": "N/A", "sunset": "N/A"
    }

def generate_decision(weather, time_str, day_type, future_holiday_info):
    """呼叫 Gemini 進行智能決策，改為純內文流暢敘事格式"""
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    weather_context = f"""
    - 報告地區: {weather['region']}
    - 報告時間: {time_str}
    - 今日日程屬性: {day_type}
    - 今日實時氣溫: {weather['temp']}
    - 今日體感氣溫: {weather['apparent_temp']}
    - 今日空氣濕度: {weather['humidity']}
    - 今日紫外線指數: {weather['uv_index']}
    - 今日降雨量: {weather['precipitation']}
    - 今日日照時間: 日出 {weather['sunrise']} / 日落 {weather['sunset']}
    """
    
    if future_holiday_info:
        future_context = f"""
        ⚠️ 【重要預告：兩星期後有公眾假期！】
        - 假期名稱: {future_holiday_info['name']}
        - 假期日期: {future_holiday_info['date']} ({future_holiday_info['weekday']})
        - 決策任務: 請結合目前香港的季節氣候趨勢，提供該假期的前瞻性生活/烘焙/放狗規劃建議。
        """
    else:
        future_context = "- 未來兩星期內無特殊法定公眾假期。"

    prompt = f"""
    你是 KAIT 決策智能。請根據以下當日實時環境數據與未來假期預告：
    {weather_context}
    
    {future_context}
    
    為我們的 Telegram 訂閱者撰寫一份「今日環境決策智能報告」。
    
    【核心寫作與排版規範】
    1. ❌ 嚴格禁止出現 "Do", "Don't", "今日建議", "今日避忌" 等任何生硬的標籤字眼。
    2. 請將所有的行動指引、環境適應策略與避忌事項，完全轉化為溫暖、富有洞察力的「純內文敘事」。
    3. 必須涵蓋「放狗」、「瑜伽」、「留家烘焙/煮食」三個核心場景，並根據今天的日程屬性（工作日/週末/假期）來編排節奏。
    4. 如果有兩星期後的假期預告，請獨立開闢一個「🔮 【KAIT 假期前瞻部署】」小區塊，以流暢內文提出前瞻備案。
    5. 嚴格遵守以下格式輸出（使用 Telegram 標準 Markdown，用 * 加粗）：
    
    🤖 *【KAIT 環境決策智能報告】*
    📍 *監測地區：* {weather['region']}
    📅 *報告時間：* {time_str}
    
    (請在此處寫第一段：結合今日天候與工作日/週末特性的環境適應導言，約 100 字。)
    
    (請在此處寫第二段：針對「放狗」與「瑜伽」的實時環境決策。將該做什麼、該避開什麼時間點，自然地寫成連續的內文，不要用清單。)
    
    (請在此處寫第三段：針對「留家烘焙/煮食」的決策。結合天候濕度與今日時間充裕度給出具體提案。)
    
    {"🔮 *【KAIT 假期前瞻部署】*" if future_holiday_info else ""}
    {"(請在此處以流暢的內文寫下：提醒讀者兩星期後（{}）是*{}*，並結合當前季節氣候趨勢，給出一個關於放狗、戶外瑜伽或烘焙的前瞻性提早準備建議。)".format(future_holiday_info['date'], future_holiday_info['name']) if future_holiday_info else ""}
    
    #環境決策 #KAIT #智能適應 #生活美學
    """

    max_retries = 3
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            print(f"嘗試調用 Gemini API...")
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            return response.text
        except APIError as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise e

def send_to_telegram(text):
    """透過 Telegram API 直接發文"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    response = requests.post(url, json=payload, timeout=10)
    if response.status_code == 200:
        print("🎉 訊息已成功發送至 Telegram！")
    else:
        print(f"❌ Telegram 發送失敗: {response.text}")

if __name__ == "__main__":
    print("Step 1: 獲取時間、假期預告與實時天氣...")
    current_time, day_type, future_holiday = get_current_time_and_holiday()
    weather_data = get_weather()
    
    if weather_data:
        print("Step 2: 請求 Gemini 決策...")
        try:
            decision_text = generate_decision(weather_data, current_time, day_type, future_holiday)
            print("Step 3: 發布至 Telegram...")
            send_to_telegram(decision_text)
        except Exception as error:
            print(f"💥 任務失敗: {error}")
