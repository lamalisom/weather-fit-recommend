import os
import io
import httpx
from fastapi import FastAPI, BackgroundTasks
from supabase import create_client, Client
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

app = FastAPI(title="KAIT Weather Promotion Engine (Multi-Version Edition)", version="3.0.0")

# =================【初始化 Supabase 客戶端】=================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("⚠️ 警告：Supabase 環境變數未完全設定！")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY else None


# =================【核心輔助工具函數】=================

async def fetch_weather(city: str = "Hong Kong") -> dict:
    """透過 RapidAPI 獲取即時香港天氣狀況"""
    raw_url = os.getenv("WEATHER_API_URL", "https://weatherapi-com.p.rapidapi.com/current.json")
    url = raw_url if raw_url.startswith("http") else f"https://{raw_url}"
    
    headers = {
        "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
        "X-RapidAPI-Host": os.getenv("WEATHER_API_HOST", "weatherapi-com.p.rapidapi.com")
    }
    params = {"q": city}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                current = data.get("current", {})
                return {
                    "temp": current.get("temp_c", 22.0),
                    "feels_like": current.get("feelslike_c", 22.0),
                    "uv": current.get("uv", 4.0),
                    "humidity": current.get("humidity", 70)
                }
            else:
                print(f"❌ 天氣 API 請求失敗: {response.status_code}")
                return {"temp": 22.0, "feels_like": 22.0, "uv": 4.0, "humidity": 70}
        except Exception as e:
            print(f"💥 天氣 API 連線異常: {str(e)}")
            return {"temp": 22.0, "feels_like": 22.0, "uv": 4.0, "humidity": 70}


def convert_to_amazon_affiliate_link(raw_url: str, amazon_tag: str) -> str:
    """自動將商品網址注入聯盟行銷標籤"""
    if not raw_url:
        return ""
    if not amazon_tag:
        return raw_url
    base_url = raw_url.split("?")[0]
    return f"{base_url}?tag={amazon_tag}"


async def trigger_apify_scraper(actor_id: str, payload: dict) -> str:
    """指派 Apify 雲端爬蟲出動"""
    apify_token = os.getenv("APIFY_TOKEN")
    if not apify_token:
        return "Missing Apify Token"
        
    safe_actor_id = actor_id.replace("/", "~")
    url = f"https://api.apify.com/v2/acts/{safe_actor_id}/runs?token={apify_token}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=15.0)
            if response.status_code in [200, 201]:
                run_data = response.json()
                return run_data.get("data", {}).get("id", "Run triggered")
            return f"Failed with status {response.status_code}"
    except Exception as e:
        return f"Trigger Error: {str(e)}"


# =================【版本 A：雲端海報生成引擎】=================
def generate_weather_poster(temp, uv, humidity, items):
    """HTML/CSS 雲端高奢海報生成引擎 (1080 x 1350)"""
    clean_temp = str(temp).replace("°C", "").strip()
    clean_humidity = str(humidity).replace("%", "").strip()
    clean_uv = str(uv).strip()
    
    display_items = items if items else [{"name": "Minimalist Essentials Set", "platform": "Amazon"}]
    
    items_html = ""
    for idx, item in enumerate(display_items[:2]):
        raw_name = item.get("name", "Exclusive Premium Accessory")
        clean_name = raw_name if len(raw_name) < 45 else raw_name[:42] + "..."
        platform = item.get("platform", "Global")
        
        items_html += f"""
        <div style="display: flex; background: #111115; margin-bottom: 20px; border-left: 6px solid #D4AF37; padding: 20px;">
            <div style="padding-left: 15px;">
                <div style="font-size: 24px; color: #FFFFFF; font-weight: bold; font-family: 'Playfair Display', serif; margin-bottom: 5px;">
                    ITEM 0{idx+1} : {clean_name}
                </div>
                <div style="font-size: 18px; color: #A4E37A; font-weight: 500; letter-spacing: 1px;">
                    PLATFORM: {platform}  |  CLICK LINK IN BIO TO SHOP
                </div>
            </div>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;700&family=Playfair+Display:ital,wght@0,700;1,400&display=swap" rel="stylesheet">
        <style>
            body {{ margin: 0; padding: 0; width: 1080px; height: 1350px; background-color: #0D0D0F; color: #FFFFFF; font-family: 'Montserrat', sans-serif; box-sizing: border-box; }}
            .container {{ padding: 90px; height: 100%; display: flex; flex-direction: column; justify-content: space-between; }}
            .header {{ border-bottom: 2px solid #222226; padding-bottom: 30px; }}
            .brand {{ font-size: 56px; font-weight: 700; letter-spacing: 12px; font-family: 'Playfair Display', serif; margin: 0; }}
            .subtitle {{ font-size: 22px; color: #666672; letter-spacing: 2px; margin-top: 15px; font-weight: 300; }}
            .weather-grid {{ display: flex; gap: 35px; margin-top: 50px; }}
            .weather-card {{ flex: 1; background: #141419; padding: 30px; border-radius: 4px; }}
            .weather-val {{ font-size: 65px; font-weight: 700; margin-bottom: 10px; font-family: 'Playfair Display', serif; }}
            .weather-lbl {{ font-size: 16px; color: #8E8E9F; letter-spacing: 2px; font-weight: 700; }}
            .section-title {{ font-size: 28px; font-weight: 700; letter-spacing: 3px; margin-top: 60px; margin-bottom: 20px; border-bottom: 2px solid #222226; padding-bottom: 15px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="brand">K A I T  .  H K</div>
                <div class="subtitle">TODAY'S WEATHER & OUTFIT INSIGHTS</div>
            </div>
            <div class="weather-grid">
                <div class="weather-card"><div class="weather-val" style="color: #FF4D4D;">{clean_temp}°C</div><div class="weather-lbl">TEMPERATURE</div></div>
                <div class="weather-card"><div class="weather-val" style="color: #FFC048;">{clean_uv}</div><div class="weather-lbl">UV INDEX</div></div>
                <div class="weather-card"><div class="weather-val" style="color: #2BCCB8;">{clean_humidity}%</div><div class="weather-lbl">HUMIDITY</div></div>
            </div>
            <div>
                <div class="section-title">RECOMMENDED PIECES FOR YOU</div>
                {items_html}
            </div>
            <div style="text-align: center; color: #44444a; font-size: 14px; letter-spacing: 4px; margin-top: 40px;">
                © KAIT AUTOMATION SYSTEM BY ALISON
            </div>
        </div>
    </body>
    </html>
    """

    hcti_user = os.getenv("HCTI_USER_ID")
    hcti_key = os.getenv("HCTI_API_KEY")
    if not hcti_user or not hcti_key:
        raise ValueError("缺少 HCTI_USER_ID 或 HCTI_API_KEY 環境變數")

    api_url = "https://hcti.io/v1/image"
    data = {"html": html_content, "width": 1080, "height": 1350}
    
    with httpx.Client() as client:
        response = client.post(api_url, data=data, auth=(hcti_user, hcti_key), timeout=30.0)
        if response.status_code == 200:
            image_url = response.json().get("url")
            img_response = client.get(image_url)
            return img_response.content
        else:
            raise Exception(f"HCTI API 錯誤: {response.text}")


# =================【社群核心發佈端點】=================
async def post_to_threads_engine(text_content: str, image_url: str = None):
    """萬能 Threads 發佈引擎（自動判定富畫面或純文字）"""
    access_token = os.getenv("THREADS_ACCESS_TOKEN")
    if not access_token:
        print("❌ 錯誤：未設定 THREADS_ACCESS_TOKEN，跳過社群發佈。")
        return None

    url = "https://graph.threads.net/v1.0/me/threads"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    
    payload = {"media_type": "IMAGE", "image_url": image_url, "text": text_content} if image_url else {"media_type": "TEXT", "text": text_content}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=20.0)
            if response.status_code == 200:
                print(f"🎉 成功！貼文（類型:{'富畫面' if image_url else '純文字'}）已同步至 Threads！")
                return response.json()
            else:
                print(f"❌ Threads 發佈失敗: {response.status_code}, 回傳: {response.text}")
                return None
    except Exception as e:
        print(f"💥 呼叫 Threads API 時發生異常: {str(e)}")
        return None


# =================【健康檢查端點】=================
@app.get("/")
async def root_status():
    current_version = os.getenv("KAIT_OUTPUT_VERSION", "TEXT").upper()
    return {
        "status": "online", 
        "current_active_mode": "Pure Text Mode" if current_version == "TEXT" else "Rich Image Mode",
        "database_connected": supabase is not None
    }


# =================【⏰ 終極環境感應流水線】=================
@app.post("/api/v1/cron/trigger-daily")
async def trigger_daily_pipeline(background_tasks: BackgroundTasks):
    try:
        # 0. 讀取版本核心控制閥： "TEXT" 或者是 "IMAGE" (預設為 TEXT 安全版)
        active_version = os.getenv("KAIT_OUTPUT_VERSION", "TEXT").upper()
        
        target_city = "Hong Kong"
        amazon_tag = os.getenv("AMAZON_TAG", "kait-20")
        
        # 1. 獲取即時天氣數據
        weather = await fetch_weather(target_city)
        uv = weather["uv"]
        humidity = weather["humidity"]
        temp = weather["temp"]
        feels_like = weather["feels_like"]
        
        final_promo_pool = []
        triggered_scrapers = {}

        # =================【1. AMAZON 选品】=================
        amazon_sub_cat = "socks"
        if uv > 6: amazon_sub_cat = "sun_glasses"
        elif temp < 15: amazon_sub_cat = "scarf"
            
        if supabase:
            try:
                amazon_res = supabase.table("static_products").select("product_name", "raw_url").eq("platform", "amazon").eq("sub_category", amazon_sub_cat).execute()
                if amazon_res.data:
                    for item in amazon_res.data[:2]:
                        affiliate_url = convert_to_amazon_affiliate_link(item["raw_url"], amazon_tag)
                        final_promo_pool.append({"name": item["product_name"], "url": affiliate_url, "platform": "Amazon"})
            except Exception as db_err:
                print(f"⚠️ 讀取 Supabase 失敗: {str(db_err)}")

        if not final_promo_pool:
            final_promo_pool = [
                {"name": "Premium Moisture-Wicking Multi-Pack Socks", "platform": "Amazon", "url": f"https://www.amazon.com?tag={amazon_tag}"},
                {"name": "UV Protection Ultralight Travel Umbrella", "platform": "Amazon", "url": f"https://www.amazon.com?tag={amazon_tag}"}
            ]

        # =================【2. APYFI 爬蟲指派】=================
        sephora_keyword = "lipstick"
        if uv > 6: sephora_keyword = "sunscreen SPF50"
        elif humidity > 85: sephora_keyword = "matte foundation"
        triggered_scrapers["sephora_job"] = await trigger_apify_scraper("getdataforme/sephora-scraper-ingredients", {"search": sephora_keyword, "maxItems": 3, "country": "HK"})

        zalora_keyword = "casual top"
        if temp > 28 and uv > 7: zalora_keyword = "swimwear"
        elif temp < 18: zalora_keyword = "jacket"
        triggered_scrapers["zalora_job"] = await trigger_apify_scraper("piotrv1001/zalora-listings-scraper", {"search": zalora_keyword, "maxItems": 3, "country": "hk"})

        # =================【3. 根據環境變數控制：執行對應的版本分支】=================
        public_image_url = ""
        
        if active_version == "IMAGE":
            # 📸 分支一：【富畫面海報版】
            if supabase:
                try:
                    poster_bytes = generate_weather_poster(temp, uv, humidity, final_promo_pool)
                    file_name = "today_kait_report.jpg"
                    try:
                        supabase.storage.from_("posters").remove([file_name])
                    except Exception: pass
                    
                    supabase.storage.from_("posters").upload(path=file_name, file=(file_name, poster_bytes, "image/jpeg"))
                    url_res = supabase.storage.from_("posters").get_public_url(file_name)
                    public_image_url = url_res.public_url if hasattr(url_res, "public_url") else str(url_res)
                except Exception as img_err:
                    print(f"❌ 雲端繪圖分支出錯，自動降級為純文字發佈: {str(img_err)}")

            # 配合圖片的推文文本
            promo_text = (
                f"【@kait.hk 今日香港環境穿搭通報】\n\n"
                f"📊 實時氣溫：{temp}°C | 🌡️ 體感溫度：{feels_like}°C\n"
                f"☀️ 紫外線：{uv} | 💧 濕度：{humidity}%\n\n"
                f"💡 今日專屬美妝服飾爬蟲已鎖定：{sephora_keyword} & {zalora_keyword}\n\n"
                f"🎒 穿搭細節與推薦單品，已同步更新在海報上！\n"
                f"👉 點擊頭像進入主頁 Link in Bio，即可一鍵前往官網獲取完整購買傳送門！✨"
            )
        else:
            # 📝 分支二：【純文字輕雜誌版】 (預設安全牌，完全不碰圖片)
            item_text_blocks = ""
            for idx, item in enumerate(final_promo_pool[:2]):
                item_text_blocks += f"🛒 𝗜𝗧𝗘𝗠 𝟬{idx+1} : {item['name']}\n"
                item_text_blocks += f"🔗 購買傳送門 : {item['url']}\n\n"

            promo_text = (
                f"✦ 𝗞 𝗔 Ｉ 𝗧  .  𝗛 𝗞 ✦\n"
                f"──────────────────────\n"
                f"𝗧𝗢𝗗𝗔𝗬'𝗦 𝗪𝗘𝗔𝗧𝗛𝗘𝗥 & 𝗢𝗨𝗧𝗙𝗜𝗧 𝗜𝗡𝗦𝗜𝗚𝗛𝗧\n\n"
                f"[ 📊 今日香港環境數據 ]\n"
                f"🌡️ 實時氣溫 ｜ {temp}°C (體感 {feels_like}°C)\n"
                f"☀️ 紫外線指數 ｜ {uv}\n"
                f"💧 空氣濕度 ｜ {humidity}%\n\n"
                f"──────────────────────\n"
                f"[ 🎒 𝗞𝗔𝗜𝗧 智選穿搭提案 ]\n\n"
                f"{item_text_blocks}"
                f"💡 今日美妝/服飾自動爬蟲已鎖定：#{sephora_keyword} 與 #{zalora_keyword}，完整穿搭報告已在後台更新！\n\n"
                f"👉 點擊主頁 Link in Bio 獲取一鍵穿搭購買清單！\n"
                f"#KAITStyle #今日穿搭 #天氣穿搭 #香港穿搭"
            )
        # 4. 指派社群發佈任務, 🟢 改成直接同步等待 (Await) 發佈結果：
        print("📢 啟動 Threads 同步發佈主線程...")
        threads_response = await post_to_threads_engine(promo_text, public_image_url if public_image_url else None)
        print(f"📡 Threads 官方終端回報: {threads_response}")

        # 5. 回傳日誌報告
        return {
            "status": "success",
            "active_mode": "Rich Image Mode" if public_image_url else "Pure Text Mode",
            "weather_metrics": {"temp": f"{temp}°C", "uv": uv, "humidity": f"{humidity}%"},
            "generated_poster_url": public_image_url if public_image_url else "None (Text Mode Active or Failed)",
            "threads_api_response": threads_response, # 這樣我們在 Colab 就能直接抓到 Meta 給的發佈 ID 或錯誤碼
            "background_crawling_tasks": triggered_scrapers
        }
        
        # 5. 回傳日誌報告
        return {
            "status": "success",
            "active_mode": "Rich Image Mode" if public_image_url else "Pure Text Mode",
            "weather_metrics": {"temp": f"{temp}°C", "uv": uv, "humidity": f"{humidity}%"},
            "generated_poster_url": public_image_url if public_image_url else "None (Text Mode Active or Failed)",
            "background_crawling_tasks": triggered_scrapers
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
