Okayimport os
import io
import httpx
from fastapi import FastAPI, BackgroundTasks
from supabase import create_client, Client
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# 載入環境變數（在 iPad 本地讀取 .env，在 Render 上會讀取 Environment Variables）
load_dotenv()

app = FastAPI(title="KAIT Weather Promotion Engine", version="2.0.0")

# =================【初始化 Supabase 客戶端】=================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("⚠️ 警告：Supabase 環境變數未完全設定！")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY else None


# =================【核心輔助工具函數】=================

async def fetch_weather(city: str = "Hong Kong") -> dict:
    """
    透過 RapidAPI 獲取即時香港天氣狀況，並補足 https:// 協定
    """
    raw_url = os.getenv("WEATHER_API_URL", "https://weatherapi-com.p.rapidapi.com/current.json")
    # 核心安全修正：確保 URL 一定帶有 https:// 協定
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
                    "feels_like": current.get("feelslike_c", 22.0),  # 👈 新增這一行抓取體感溫度
                    "uv": current.get("uv", 4.0),
                    "humidity": current.get("humidity", 70)
                }
            else:
                print(f"❌ 天氣 API 請求失敗: {response.status_code}")
                return {"temp": 22.0, "uv": 4.0, "humidity": 70}
        except Exception as e:
            print(f"💥 天氣 API 連線異常: {str(e)}")
            return {"temp": 22.0, "uv": 4.0, "humidity": 70}


def convert_to_amazon_affiliate_link(raw_url: str, amazon_tag: str) -> str:
    """
    自動將乾淨的 Amazon 商品網址注入你的聯盟行銷 Partner Tag 追蹤碼
    """
    if not raw_url:
        return ""
    if not amazon_tag:
        return raw_url
    base_url = raw_url.split("?")[0]
    return f"{base_url}?tag={amazon_tag}"


async def trigger_apify_scraper(actor_id: str, payload: dict) -> str:
    """
    指派 Apify 雲端爬蟲出動，實時撈取熱門商品
    """
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


def generate_weather_poster(temp: float, uv: float, humidity: int, items: list) -> bytes:
    """
    利用 Pillow 後端自動生成 1080x1350 精美時尚風格的穿搭引流海報
    """
    # 創建高級感暗黑背景海報
    width, height = 1080, 1350
    image = Image.new("RGB", (width, height), color="#121212")
    draw = ImageDraw.Draw(image)
    
    # 由於 iPad 環境與雲端部署環境預設沒有自訂字體，這裡安全使用預設字體
    # 在真正商業運作時，可在代碼根目錄放一個 Arial.ttf 檔案並載入它
    try:
        font_title = ImageFont.load_default()
    except Exception:
        font_title = None

    # 開始繪製時尚品牌視覺元素
    draw.text((80, 100), "KAIT . HK", fill="#FFFFFF", font=font_title)
    draw.text((80, 140), "TODAY'S WEATHER & OUTFIT ACCENTS", fill="#8E8E93")
    
    # 繪製實時天氣指標框框
    draw.rectangle([80, 220, 1000, 420], fill="#1C1C1E", outline="#2C2C2E", width=2)
    draw.text((120, 260), f"TEMPERATURE: {temp} °C", fill="#FF453A")
    draw.text((120, 310), f"UV INDEX: {uv}", fill="#FFD60A")
    draw.text((120, 360), f"HUMIDITY: {humidity} %", fill="#0A84FF")
    
    # 繪製推薦單品區
    draw.text((80, 490), "RECOMMENDED ACCESSORIES FOR YOU", fill="#E5E5EA")
    
    start_y = 560
    if items:
        for idx, item in enumerate(items[:2]):
            box_y = start_y + (idx * 220)
            draw.rectangle([80, box_y, 1000, box_y + 180], fill="#2C2C2E")
            draw.text((120, box_y + 40), f"ITEM 0{idx+1}: {item['name'][:45]}...", fill="#FFFFFF")
            draw.text((120, box_y + 100), f"PLATFORM: {item['platform']} | CLICK LINK IN BIO TO SHOP", fill="#30D158")
    else:
        draw.text((120, 580), "Style Concept: Wear your favorite classic items comfortably.", fill="#BFBFBF")
        
    # 底部浮水印與引流宣告
    draw.text((80, 1200), "Generated automatically by KAIT AI Engine.", fill="#48484A")
    draw.text((80, 1240), "Visit our website for full personalized skincare & dress recommendations.", fill="#8E8E93")
    
    # 轉為二進位流數據，供 Supabase 上傳
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG', quality=90)
    return img_byte_arr.getvalue()


async def post_to_threads_with_image(text_content: str, image_url: str):
    """
    透過高級 Threads API 發佈「富畫面」貼文
    """
    access_token = os.getenv("THREADS_ACCESS_TOKEN")
    if not access_token:
        print("❌ 錯誤：未設定 THREADS_ACCESS_TOKEN，跳過社群發佈。")
        return None

    url = "https://graph.threads.net/v1.0/me/threads"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # 改為 IMAGE 類型，附帶自動生成的 Supabase 圖片網址
    payload = {
        "media_type": "IMAGE",
        "image_url": image_url,
        "text": text_content
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=20.0)
            if response.status_code == 200:
                print("🎉 成功！帶圖的豐富畫面穿搭海報已同步發佈至 Threads！")
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
    return {
        "status": "online", 
        "message": "KAIT Promotion Engine is Fully Powered!",
        "database_connected": supabase is not None
    }


# =================【⏰ 終極環境感應流水線】=================
@app.post("/api/v1/cron/trigger-daily")
async def trigger_daily_pipeline(background_tasks: BackgroundTasks):
    try:
        target_city = "Hong Kong"
        amazon_tag = os.getenv("AMAZON_TAG", "kait-20")
        
        # 1. 獲取即時天氣數據
        weather = await fetch_weather(target_city)
        uv = weather["uv"]
        humidity = weather["humidity"]
        temp = weather["temp"]
        feels_like = weather["feels_like"]  # 👈 拿出身體感受溫度
        
        final_promo_pool = []  # 最終商品池
        triggered_scrapers = {}

        # =================【1. AMAZON 配件類部署邏輯】=================
        amazon_sub_cat = "socks"
        if uv > 6:
            amazon_sub_cat = "sun_glasses"
        elif temp < 15:
            amazon_sub_cat = "scarf"
            
        if supabase:
            try:
                amazon_res = supabase.table("static_products")\
                    .select("product_name", "raw_url")\
                    .eq("platform", "amazon")\
                    .eq("sub_category", amazon_sub_cat).execute()
                    
                if amazon_res.data:
                    for item in amazon_res.data[:2]:
                        affiliate_url = convert_to_amazon_affiliate_link(item["raw_url"], amazon_tag)
                        final_promo_pool.append({
                            "name": item["product_name"], 
                            "url": affiliate_url, 
                            "platform": "Amazon", 
                            "category": "Accessories"
                        })
            except Exception as db_err:
                print(f"⚠️ 讀取 Supabase 商品表失敗，使用安全預設邏輯: {str(db_err)}")

        # 如果資料庫為空，給予兩個優雅的靜態備用推薦項，防止畫布空白
        if not final_promo_pool:
            final_promo_pool = [
                {"name": "Premium Moisture-Wicking Multi-Pack Socks", "platform": "Amazon", "url": "https://www.amazon.com"},
                {"name": "UV Protection Ultralight Travel Umbrella", "platform": "Amazon", "url": "https://www.amazon.com"}
            ]

        # =================【2. SEPHORA 美妝類部署邏輯】=================
        sephora_keyword = "lipstick"
        if uv > 6:
            sephora_keyword = "sunscreen SPF50"
        elif humidity > 85:
            sephora_keyword = "matte foundation"
            
        sephora_task = await trigger_apify_scraper(
            actor_id="richard_feng/sephora", 
            payload={"search": sephora_keyword, "maxItems": 3, "country": "HK"}
        )
        triggered_scrapers["sephora_job"] = sephora_task

        # =================【3. ZALORA 服飾類部署邏輯】=================
        zalora_keyword = "casual top"
        if temp > 28 and uv > 7:
            zalora_keyword = "swimwear"
        elif temp < 18:
            zalora_keyword = "jacket"
            
        zalora_task = await trigger_apify_scraper(
            actor_id="apify/zalora-scraper", 
            payload={"search": zalora_keyword, "maxItems": 3, "country": "hk"}
        )
        triggered_scrapers["zalora_job"] = zalora_task

        # =================【4. PILOW 自動化海報繪製 & SUPABASE 上傳】=================
        public_image_url = ""
        if supabase:
            try:
                # 調用繪圖引擎生成圖片二進位數據
                poster_bytes = generate_weather_poster(temp, uv, humidity, final_promo_pool)
                
                # 自動上傳到名為 "posters" 的公開 Storage Bucket (開啟 upsert=true 以便每日自動覆蓋)
                file_name = "today_kait_report.jpg"
                supabase.storage.from_("posters").upload(
                    file_name,
                    poster_bytes,
                    file_options={"content-type": "image/jpeg", "upsert": "true"}
                )
                # 拼接最終的公開圖片 URL
                public_image_url = f"{SUPABASE_URL}/storage/v1/object/public/posters/{file_name}"
                print(f"📸 雲端海報生成成功，網址: {public_image_url}")
            except Exception as img_err:
                print(f"❌ 繪圖或上傳雲端失敗: {str(img_err)}")

        # =================【5. 免費社群富畫面引流發佈】=================
        promo_text = (
            f"【@kait.hk 今日香港環境穿搭通報】\n\n"
            f"📊 實時氣溫：{temp}°C | 🌡️ 體感溫度：{feels_like}°C\n"
            f"☀️ 紫外線：{uv} | 💧 濕度：{humidity}%\n\n"
            f"💡 今日專屬美妝服飾爬蟲已鎖定：{sephora_keyword} & {zalora_keyword}\n\n"
            f"🎒 穿搭細節與推薦單品，已同步更新在海報上！\n"
            f"👉 點擊頭像進入主頁 Link in Bio，即可一鍵前往官網獲取完整購買傳送門！✨"
        )
        
        # 如果成功上傳了海報圖片，則使用圖文並茂發佈；否則安全降級為純文字發佈
        if public_image_url:
            background_tasks.add_task(post_to_threads_with_image, promo_text, public_image_url)
        else:
            # 備用降級方案（發純文字）
            from main import post_to_threads
            background_tasks.add_task(post_to_threads, promo_text)

        # =================【6. 返回部署日誌報告】=================
        return {
            "status": "success",
            "city": target_city,
            "weather_metrics": {"temp": f"{temp}°C", "uv": uv, "humidity": f"{humidity}%"},
            "generated_poster_url": public_image_url if public_image_url else "Failed to generate",
            "background_crawling_tasks": triggered_scrapers,
            "threads_posting": "Scheduled in background with rich layout"
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
