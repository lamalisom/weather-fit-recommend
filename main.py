import os
import time
from datetime import datetime, timedelta, timezone
import requests
import holidays
from google import genai
from google.genai.errors import APIError

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def get_current_time_and_holiday():
    """取得香港時間、今日日程，並檢查 14 天後假期"""
    tz_utc8 = timezone(timedelta(hours=8))
    now = datetime.now(tz_utc8)
    current_date = now.date()
    current_year = now.year
    
    hk_holidays = holidays.HongKong(years=[current_year, current_year + 1], language='zh')
    
    weekdays_zh = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    date_str = now.strftime("%m月%d日")
    time_str = now.strftime("%H:%M")
    weekday_idx = now.weekday()
    weekday_str = weekdays_zh[weekday_idx]
    
    is_holiday_today = current_date in hk_holidays
    holiday_name_today = hk_holidays.get(current_date) if is_holiday_today else ""
    
    if is_holiday_today:
        day_type = f"公眾假期 ({holiday_name_today})"
    elif weekday_idx in [5, 6]:
        day_type = weekday_str
    else:
        day_type = f"工作日 ({weekday_str})"
        
    full_time_str = f"{date_str} {day_type} {time_str}"
    
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
                "humidity": data[2], "uv_index": data[3], "precipitation": data[4]
            }
    except:
        pass
    return {"region": "香港", "temp": "N/A", "apparent_temp": "N/A", "humidity": "N/A", "uv_index": "N/A", "precipitation": "N/A"}

def generate_decision(weather, time_str, day_type, future_holiday_info):
    """呼叫 Gemini 生成精簡內文"""
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    weather_context = f"地區:{weather['region']}|時間:{time_str}|氣溫:{weather['temp']}|體感:{weather['apparent_temp']}|濕度:{weather['humidity']}|紫外線:{weather['uv_index']}|降雨:{weather['precipitation']}"
    future_context = f"兩週後假期: {future_holiday_info['name']} ({future_holiday_info['date']})" if future_holiday_info else "無特殊假期"

    prompt = f"""
    任務：根據環境數據寫一份極精簡的 Telegram 生活指南。
    數據：{weather_context} | {future_context}
    
    排版規範：
    1. ❌ 嚴格禁止出現 "Do/Don't/建議/避忌/優點/缺點" 等標籤。字數控制在 150-200 字內，越精煉越好。
    2. 將「放狗」、「瑜伽」、「留家烘焙/煮食」流暢融入兩段內文。
    3. 如果有兩週後假期，在底部加上「🔮 【KAIT 假期前瞻】」區塊（1-2句流暢內文）。
    4. 請嚴格遵守以下格式輸出（使用 Telegram 標準 Markdown，用 * 加粗）：
    
    🤖 *【KAIT 環境決策】*
    📍 *監測：* {weather['region']} | {time_str}
    
    (此處寫第一段：結合天候的放狗與瑜伽指南，文字要流暢、優雅、精簡。)
    
    (此處寫第二段：結合濕度與時間的烘焙/料理提案。)
    
    {"🔮 *【KAIT 假期前瞻】*" if future_holiday_info else ""}
    {"(此處寫流暢內文：提醒兩週後{}是*{}*，並結合當前季節給出一句出行或烘焙的提早準備建議。)".format(future_holiday_info['date'], future_holiday_info['name']) if future_holiday_info else ""}
    
    #環境決策 #KAIT #智能生活
    """

    for _ in range(3):
        try:
            response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            return response.text
        except APIError:
            time.sleep(2)
    return "決策生成失敗"

def send_to_telegram(text, weather_desc):
    """發送訊息至 Telegram（附帶自動匹配的日系動漫風風景圖）"""
    
    # 💡 修正點 1：改用穩定有效的動漫風景圖網址，並根據雨天或晴天做簡單切換
    if "濕" in weather_desc or "雨" in weather_desc:
        # 雨天/陰天氛圍的動漫風風景
        image_url = "https://images.unsplash.com/photo-1515694346937-94d85e41e6f0?auto=format&fit=crop&w=800&q=80"
    else:
        # 晴天/新海誠風藍天動漫風景
        image_url = "https://images.unsplash.com/photo-1578632767115-351597cf2477?auto=format&fit=crop&w=800&q=80" 

    # 💡 修正點 2：使用 HTML 的零寬度空格隱藏網址，Telegram 展開圖片最穩定
    # 把圖片網址塞在最前面，點擊不會顯示網址，但上方會自動跳出圖案
    formatted_text = f'<a href="{image_url}">&#8205;</a>{text}'

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": formatted_text, 
        "parse_mode": "HTML"  # 💡 修正點 3：改用 HTML 模式配合上面的 <a> 標籤
    }
    
    response = requests.post(url, json=payload, timeout=10)
    if response.status_code != 200:
        print(f"Telegram 發送失敗: {response.text}")
    else:
        print("🎉 訊息與動漫封面已成功發送！")

def send_to_linkedin(text):
    """將純文字報告同步發布至 LinkedIn 公開動態"""
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    author_urn = os.getenv("LINKEDIN_AUTHOR_URN")
    
    # 如果 GitHub Secrets 沒有設定 LinkedIn 憑證，就跳過不執行，不影響 Telegram
    if not access_token or not author_urn:
        print("說明：未設定 LinkedIn 憑證，跳過 LinkedIn 同步發布。")
        return

    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    
    # 建立符合 LinkedIn 規範的 JSON 結構
    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": text  # 傳入純文字
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC" # 設定為對公眾公開
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 201:
            print("🎉 報告已成功同步發布至 LinkedIn！")
        else:
            print(f"❌ LinkedIn 發布失敗: {response.text}")
    except Exception as e:
        print(f"❌ LinkedIn 連線失敗: {str(e)}")

if __name__ == "__main__":
    current_time, day_type, future_holiday = get_current_time_and_holiday()
    weather_data = get_weather()
    weather_summary = f"{weather_data['temp']} {weather_data['precipitation']}"
    
    # 1. 讓 Gemini 生成基礎的環境決策純文字
    decision_text = generate_decision(weather_data, current_time, day_type, future_holiday)
    
    # 2. 發送到 Telegram（此函數內部會自己幫文字加上動漫封面網址與 HTML 標籤）
    send_to_telegram(decision_text, weather_summary)
    
    # 3. 同步發送到 LinkedIn（直接發送乾淨的純文字內容）
    send_to_linkedin(decision_text)
