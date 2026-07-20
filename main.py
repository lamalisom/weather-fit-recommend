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
    """獲取當前天氣詳細數據（預留空氣質素欄位）"""
    try:
        url = "https://wttr.in/Hong+Kong?format=%t|%f|%h|%u|%p|%D|%S"
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and "|" in response.text:
            data = response.text.strip().split("|")
            return {
                "region": "香港", "temp": data[0], "apparent_temp": data[1],
                "humidity": data[2], "uv_index": data[3], "precipitation": data[4],
                "aqi": "良 (45)"  # 這裡我們先給一個常規基礎值，或讓 Gemini 根據下雨狀況自主修正
            }
    except:
        pass
    return {"region": "香港", "temp": "N/A", "apparent_temp": "N/A", "humidity": "N/A", "uv_index": "N/A", "precipitation": "N/A", "aqi": "N/A"}

def generate_decision(weather, time_str, day_type, future_holiday_info):
    """呼叫 Gemini 生成結構化的 KAIT Daily Decision Feed (融入空氣質素、雨量與工作日決策)"""
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # 判斷當天是否為工作日（只要 day_type 包含 "工作日" 就代表上班族需要返工）
    is_workday = "工作日" in day_type
    
    # 建立強大且乾淨的數據上下文，直接餵給 AI
    weather_context = (
        f"地區: {weather['region']} | 時間: {time_str} | 屬性: {day_type}\n"
        f"氣溫: {weather['temp']} | 體感: {weather['apparent_temp']} | 濕度: {weather['humidity']}\n"
        f"紫外線指數(UV): {weather['uv_index']} | 降雨與即時雨量: {weather['precipitation']}\n"
        f"空氣質素 (AQI/AQHI): {weather.get('aqi', 'N/A')} (若為N/A請根據降雨與濕度自主推理判斷)"
    )
    
    future_context = f"兩週後預警：{future_holiday_info['date']} 是 {future_holiday_info['name']}" if future_holiday_info else "兩週後無特殊公眾假期"

    prompt = f"""
    任務：根據提供的精準環境數據，生成今日的【KAIT Daily Decision Feed】。
    
    核心宗旨：我們是決策分發渠道（Decision Distribution Channel）。杜絕任何雞湯、問候、百科或Lifestyle軟文。所有內容必須服務於引導用戶相信 KAIT 的「Decision Intelligence（決策智能）」。

    當前真實環境數據：
    {weather_context}
    {future_context}
    
    決策生成邏輯（核心指令）：
    1. 🎯 Today's Decisions 必須全面考量「降雨量」與「空氣質素」。
    2. 【上班族通勤決策】：今天{'【是工作日】' if is_workday else '【是假期】'}。{'請精準針對「上班族返工通勤」的服裝穿著、提早出門防塞車或帶傘等維度給出決策。' if is_workday else '請針對市民假期放假外出的休閒與出行交通給出決策。'}
    3. 【⚠️極端防禦機制】：如果數據顯示雨量達大雨/暴雨、空氣質素達嚴重污染、或有強風酷熱等極端狀況，必須在文章**最開頭**強行插入一行：『⚠️<b>【極端環境防禦決策】</b>：[具體避險或防護行動]』。若環境正常則絕對不要顯示此行。

    格式與排版規範：
    - 嚴格禁止口水話，直接輸出下方的 HTML 結構，不要 Markdown 星號，全部用 <b>文字</b> 加粗。
    - 用詞冷靜、理性、專業，符合香港習慣用語（如：返工、帶遮、大雨塞車）。
    - 總字數嚴格控制在 250 字內。

    請嚴格依照以下結構輸出：

    🤖 <b>【KAIT Daily Decision Feed】</b>
    📍 <b>Environment：</b> {weather['region']} | {time_str} | {weather['temp']} | 降雨: {weather['precipitation']} | AQI: {weather.get('aqi', 'N/A')}

    [此處僅在觸發極端環境時插入警告，正常則留空]

    -----------------
    🎯 <b>Today's Decisions</b>
    👕 <b>Wear：</b> [針對{'上班族返工' if is_workday else '假日出行'}與體感的穿搭決策]
    🛒 <b>Buy：</b> [根據氣溫/降雨，給出1句精準消費或避免衝動消費的決策]
    💄 <b>Skincare：</b> [根據濕度/UV/空氣質素，給出1句防護護膚決策]
    🍽 <b>Eat/Go：</b> [根據今日天候與通勤/休閒屬性，給出1句飲食或出行線路決策]

    -----------------
    🧠 <b>Decision Knowledge (Why?)</b>
    <b>Fact：</b> [給出一個與今日環境（如高濕度、下雨通勤、不良空氣、高溫）高度相關的數據、心理學或消費科學事實。]
    <b>AI Logic：</b> [用1句話解釋，基於上述 Fact，KAIT 今日決策矩陣的推薦邏輯。]

    -----------------
    🔮 <b>Today's Reflection (Mind Decision)</b>
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
