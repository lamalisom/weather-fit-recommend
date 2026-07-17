import os
import time
from datetime import datetime
import requests
from google import genai
from google.genai.errors import APIError

# 1. 讀取 GitHub Secrets 的環境變數
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def get_current_time_str():
    """取得香港/台北標準時間 (UTC+8) 的精確日期與星期"""
    # 由於 GitHub Actions 伺服器通常是 UTC 時間，我們手動加上 8 小時偏移
    from datetime import timedelta, timezone
    tz_utc8 = timezone(timedelta(hours=8))
    now = datetime.now(tz_utc8)
    
    weekdays_zh = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    date_str = now.strftime("%Y年%m月%d日")
    time_str = now.strftime("%H:%M")
    weekday_str = weekdays_zh[now.weekday()]
    
    return f"{date_str} ({weekday_str}) {time_str}"

def get_weather():
    """獲取精準地區的天氣、體感、雨量、紫外線與日照時間（日出/日落）"""
    try:
        # 1. 抓取香港即時天氣細節
        # %t: 氣溫, %f: 體感溫度, %h: 濕度, %u: 紫外線, %p: 降雨量
        # %D: 日出時間, %S: 日落時間
        url = "https://wttr.in/Hong+Kong?format=%t|%f|%h|%u|%p|%D|%S"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200 and "|" in response.text:
            data = response.text.strip().split("|")
            weather_dict = {
                "region": "香港 (Hong Kong)",
                "temp": data[0],
                "apparent_temp": data[1],
                "humidity": data[2],
                "uv_index": data[3],
                "precipitation": data[4],
                "sunrise": data[5],
                "sunset": data[6]
            }
            return weather_dict
        else:
            # 備用方案
            return {
                "region": "香港",
                "temp": "N/A",
                "apparent_temp": "N/A",
                "humidity": "N/A",
                "uv_index": "N/A",
                "precipitation": "N/A",
                "sunrise": "N/A",
                "sunset": "N/A"
            }
    except Exception as e:
        print(f"天氣抓取失敗: {str(e)}")
        return None

def generate_decision(weather, time_str):
    """呼叫 Gemini 進行環境適應決策"""
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # 組織給 Gemini 的結構化天氣輸入
    weather_context = f"""
    - 報告地區: {weather['region']}
    - 報告時間: {time_str}
    - 實時氣溫: {weather['temp']}
    - 體感氣溫: {weather['apparent_temp']}
    - 空氣濕度: {weather['humidity']}
    - 紫外線指數: {weather['uv_index']}
    - 降雨量: {weather['precipitation']}
    - 日照時間: 日出 {weather['sunrise']} / 日落 {weather['sunset']}
    """
    
    prompt = f"""
    你是 KAIT 決策智能。請根據以下當日實時環境數據：
    {weather_context}
    
    為我們的 Telegram 訂閱者撰寫一份「今日環境決策智能報告」。
    
    【寫作規範】
    1. 不要生硬地羅列數據，請將體感溫度、雨量、紫外線與日照時間（日出/日落）「有機地融合」在首段的溫暖導言與後半段的生活建議中。
    2. 特別關注「放狗（注意地面溫度是否燙傷肉墊、是否有雨）」、「瑜伽（室內或戶外拉伸）」、「留家烘焙/煮食」這三個核心場景。
    3. 嚴格遵守以下格式輸出，字體样式請使用 Telegram 支持的標準 Markdown（用 * 加粗，• 作為清單符號）：
    
    🤖 *【KAIT 環境決策智能報告】*
    📍 *監測地區：* {weather['region']}
    📅 *報告時間：* {time_str}
    
    (請在此處寫一段 80-120 字、溫暖且富有科學洞察力的生活適應建議。請主動融入今天的體感溫度、雨量、紫外線與日出/日落時間，並綜合評估放狗、瑜伽或留家烘焙的合適度。)
    
    💡 *今日建議（Do）：*
    • (基於今日紫外線與雨量的極短行動建議，例如：日落時間為 {weather['sunset']}，適合傍晚帶狗狗出門避開熱浪)
    • (第二個極短行動建議)
    
    ⚠️ *今日避忌（Don't）：*
    • (基於今日體感與環境的避忌建議，例如：體感溫度高達 {weather['apparent_temp']}，午後柏油路面極燙，切勿在此時放狗)
    • (第二個避忌建議)
    
    #環境決策 #KAIT #生活日常 #智能適應
    """

    max_retries = 3
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            print(f"嘗試調用 Gemini API (第 {attempt + 1}/{max_retries} 次)...")
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            return response.text
        except APIError as e:
            if attempt < max_retries - 1:
                print(f"⚠️ 遇到 API 錯誤: {e.message}。{retry_delay} 秒後重試...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print("❌ 已達到最大重試次數。")
                raise e

def send_to_telegram(text):
    """透過 Telegram API 直接發文"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload, timeout=10)
    if response.status_code == 200:
        print("🎉 訊息已成功發送至 Telegram！")
    else:
        print(f"❌ Telegram 發送失敗: {response.text}")

if __name__ == "__main__":
    print("Step 1: 獲取系統時間與實時天氣細節...")
    current_time = get_current_time_str()
    weather_data = get_weather()
    
    if weather_data:
        print(f"時間: {current_time}")
        print(f"實時數據: {weather_data}")
        
        print("Step 2: 請求 Gemini 決策...")
        try:
            decision_text = generate_decision(weather_data, current_time)
            print("決策文案生成完畢。")
            
            print("Step 3: 發布至 Telegram...")
            send_to_telegram(decision_text)
        except Exception as error:
            print(f"💥 任務因不可抗力失敗: {error}")
    else:
        print("💥 無法取得天氣數據，流程中斷。")
