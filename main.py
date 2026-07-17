import os
import requests
from google import genai

# 1. 讀取 GitHub Secrets 的環境變數
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def get_weather():
    """使用 wttr.in 免費抓取香港即時天氣"""
    try:
        # 抓取香港天氣：溫度、濕度、紫外線、降雨機率
        url = "https://wttr.in/Hong+Kong?format=%t+Humidity:%h+UV:%u+Precipitation:%p"
        response = requests.get(url, timeout=10)
        return response.text if response.status_code == 200 else "無法取得天氣數據"
    except Exception as e:
        return f"天氣抓取失敗: {str(e)}"

def generate_decision(weather_data):
    """呼叫 Gemini 2.5 進行環境適應決策"""
    # 2026年最新採用的 Google GenAI 官方 SDK 初始化方式
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    你是 KAIT 決策智能。請根據以下當日天氣數據：
    Raw Weather: {weather_data}
    
    為我們的 Telegram 訂閱者撰寫一份「今日生活適應指南」。
    
    請嚴格遵守以下格式輸出，字體样式請使用 Telegram 支持的標準 Markdown（用 * 加粗）：
    
    🤖 *【KAIT 環境決策智能報告】*
    今日決策模式：[請根據天氣填入：避難 Shelter / 動態 Move / 探索 Explore / 留家 Stay]
    
    (請在此處寫一段 50 字內、溫暖且富有洞察力的生活適應建議。特別提及「放狗、瑜伽、留家煮食或烘焙」的實時合適度。)
    
    💡 *今日建議（Do）：*
    • (極短行動建議，例如：適合室內瑜伽，讓身心舒展)
    • (極短行動建議)
    
    ⚠️ *今日避忌（Don't）：*
    • (避忌建議，例如：地表溫度高，午後切勿帶狗狗出門以免燙傷)
    • (避忌建議)
    
    #環境決策 #KAIT #生活日常 #智能適應
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    return response.text

def send_to_telegram(text):
    """透過 Telegram API 直接發文"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"  # 讓 Telegram 渲染我們 Markdown 的加粗與符號
    }
    response = requests.post(url, json=payload, timeout=10)
    if response.status_code == 200:
        print("🎉 訊息已成功發送至 Telegram！")
    else:
        print(f"❌ Telegram 發送失敗: {response.text}")

if __name__ == "__main__":
    print("Step 1: 獲取實時天氣...")
    weather = get_weather()
    print(f"天氣數據: {weather}")
    
    print("Step 2: 請求 Gemini 決策...")
    decision_text = generate_decision(weather)
    print("決策文案生成完畢。")
    
    print("Step 3: 發布至 Telegram...")
    send_to_telegram(decision_text)
