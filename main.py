import os
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


def generate_weather_poster(temp, uv, humidity, items):
    """
    升級版時尚海報生成引擎 (1080 x 1350)
    風格：Minimalist Black & Gold / Luxury Magazine Layout
    """
    # 1. 創建黃金比例畫布
    canvas_w, canvas_h = 1080, 1350
    image = Image.new("RGB", (canvas_w, canvas_h), color="#0D0D0F")
    draw = ImageDraw.Draw(image)
    
    # 2. 字體加粗與字級放大設定
    try:
        font_path = "main_font.ttf" 
        font_brand = ImageFont.truetype(font_path, 56)      
        font_subtitle = ImageFont.truetype(font_path, 28)   
        font_num = ImageFont.truetype(font_path, 90)        
        font_label = ImageFont.truetype(font_path, 24)      
        font_section = ImageFont.truetype(font_path, 36)    
        font_item_title = ImageFont.truetype(font_path, 32) 
        font_action = ImageFont.truetype(font_path, 26)     
    except IOError:
        # 防禦機制：若無外部字體檔，使用系統預設，並利用內建的 font_size 參數嘗試放大（需 Pillow 10.0+）
        try:
            font_brand = ImageFont.load_default(size=56)
            font_subtitle = ImageFont.load_default(size=28)
            font_num = ImageFont.load_default(size=75)
            font_label = ImageFont.load_default(size=22)
            font_section = ImageFont.load_default(size=36)
            font_item_title = ImageFont.load_default(size=30)
            font_action = ImageFont.load_default(size=24)
        except Exception:
            font_brand = font_subtitle = font_num = font_label = \
            font_section = font_item_title = font_action = ImageFont.load_default()

    # 3. 頂部品牌 Header 區塊
    draw.text((90, 90), "K A I T  .  H K", fill="#FFFFFF", font=font_brand)
    draw.text((90, 170), "TODAY'S WEATHER & OUTFIT INSIGHTS", fill="#666672", font=font_subtitle)
    draw.line([(90, 230), (990, 230)], fill="#222226", width=2)

    # 4. 天氣核心數據區塊 (橫向三欄式排版)
    col_width = 270
    start_x = 90
    gap = 45
    y_top = 290
    
    weather_data = [
        {"val": f"{temp}°C", "lbl": "TEMPERATURE", "color": "#FF4D4D"}, 
        {"val": f"{uv}", "lbl": "UV INDEX", "color": "#FFC048"},       
        {"val": f"{humidity}%", "lbl": "HUMIDITY", "color": "#2BCCB8"}  
    ]
    
    for i, data in enumerate(weather_data):
        col_x = start_x + i * (col_width + gap)
        
        # 💡 安全性 100% 的寫法：直接使用 draw.rectangle 畫直角方塊，拿掉 radius 參數！
        draw.rectangle([col_x, y_top, col_x + col_width, y_top + 180], fill="#141419")
        
        draw.text((col_x + 25, y_top + 25), data["val"], fill=data["color"], font=font_num)
        draw.text((col_x + 25, y_top + 125), data["lbl"], fill="#8E8E9F", font=font_label)
    
    # 5. 下方穿搭推薦區塊
    y_recommend = 540
    draw.text((90, y_recommend), "RECOMMENDED PIECES FOR YOU", fill="#FFFFFF", font=font_section)
    draw.line([(90, y_recommend + 60), (990, y_recommend + 60)], fill="#222226", width=2)

    # 6. 動態商品清單排版
    y_item_start = 650
    item_height = 240
    item_gap = 40
    
    display_items = items if items else [{"name": "Minimalist Essentials Set", "platform": "Amazon"}]
    
    for idx, item in enumerate(display_items[:2]):
        current_y = y_item_start + idx * (item_height + item_gap)
        
        draw.rectangle([90, current_y, 990, current_y + item_height], fill="#111115")
        draw.rectangle([90, current_y, 102, current_y + item_height], fill="#D4AF37")
        
        raw_name = item.get("name", "Exclusive Premium Accessory")
        clean_name = raw_name if len(raw_name) < 45 else raw_name[:42] + "..."
        
        draw.text((130, current_y + 40), f"ITEM 0{idx+1} : {clean_name}", fill="#FFFFFF", font=font_item_title)
        
        platform_str = f"PLATFORM: {item.get('platform', 'Global')}"
        action_str = f"{platform_str}  |  CLICK LINK IN BIO TO SHOP"
        draw.text((130, current_y + 130), action_str, fill="#A4E37A", font=font_action)

    # 7. 打包成二進位流
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG', quality=95)
    img_byte_arr.seek(0)
    
    return img_byte_arr.getvalue()


async def post_to_threads_with_image(text_content: str, image_url: str = None):
    """
    透過高級 Threads API 發佈「富畫面」或「純文字」貼文
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
    
    if image_url:
        payload = {
            "media_type": "IMAGE",
            "image_url": image_url,
            "text": text_content
        }
    else:
        payload = {
            "media_type": "TEXT",
            "text": text_content
        }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=20.0)
            if response.status_code == 200:
                print("🎉 成功！貼文已同步發佈至 Threads！")
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
        feels_like = weather["feels_like"]
        
        final_promo_pool = []
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
            actor_id="getdataforme/sephora-scraper-ingredients",  
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
            actor_id="piotrv1001/zalora-listings-scraper",  
            payload={"search": zalora_keyword, "maxItems": 3, "country": "hk"}
        )
        triggered_scrapers["zalora_job"] = zalora_task

# =================【4. PILOW 自動化海報繪製 & SUPABASE 上傳】=================
        public_image_url = ""
        if supabase:
            try:
                poster_bytes = generate_weather_poster(temp, uv, humidity, final_promo_pool)
                file_name = "today_kait_report.jpg"

                # 💡 1. 嘗試刪除舊檔案
                try:
                    supabase.storage.from_("posters").remove([file_name])
                except Exception as rem_err:
                    print(f"⚠️ 刪除舊檔失敗(通常可忽略): {str(rem_err)}")

                # 💡 2. 元組格式乾淨上傳
                supabase.storage.from_("posters").upload(
                    path=file_name,
                    file=(file_name, poster_bytes, "image/jpeg")
                )
                print("✅ Supabase 檔案上傳動作已執行完畢")
                
                # 💡 3. 取得公開網址（加上最安全的防禦與手動拼接）
                try:
                    url_res = supabase.storage.from_("posters").get_public_url(file_name)
                    if hasattr(url_res, "public_url"):
                        public_image_url = url_res.public_url
                    elif isinstance(url_res, dict) and "publicUrl" in url_res:
                        public_image_url = url_res["publicUrl"]
                    else:
                        public_image_url = str(url_res)
                except Exception as url_err:
                    print(f"⚠️ SDK 取得網址失敗，啟動手動拼接防禦: {str(url_err)}")
                    # 💥 如果 SDK 耍笨拿不到，我們直接手動拼出 Supabase 標準公開圖片網址
                    # 請確保 "posters" 這個 bucket 在 Supabase 後台有設為 Public 
                    public_image_url = f"{SUPABASE_URL}/storage/v1/object/public/posters/{file_name}"
                    
                print(f"📸 雲端海報生成成功，網址: {public_image_url}")

            except Exception as e:
                # 📢 這行非常重要！會在 Render 日誌裡印出真正死在第幾步、什麼錯誤
                print(f"❌ 繪圖或上傳雲端失敗，具體原因: {str(e)}")    
                
        # =================【5. 免費社群富畫面引流發佈】=================
        promo_text = (
            f"【@kait.hk 今日香港環境穿搭通報】\n\n"
            f"📊 實時氣溫：{temp}°C | 🌡️ 體感溫度：{feels_like}°C\n"
            f"☀️ 紫外線：{uv} | 💧 濕度：{humidity}%\n\n"
            f"💡 今日專屬美妝服飾爬蟲已鎖定：{sephora_keyword} & {zalora_keyword}\n\n"
            f"🎒 穿搭細節與推薦單品，已同步更新在海報上！\n"
            f"👉 點擊頭像進入主頁 Link in Bio，即可一鍵前往官網獲取完整購買傳送門！✨"
        )
        
        if public_image_url:
            background_tasks.add_task(post_to_threads_with_image, promo_text, public_image_url)
        else:
            background_tasks.add_task(post_to_threads_with_image, promo_text, None)

        # =================【6. 返回部署日誌報告】=================
        return {
            "status": "success",
            "city": target_city,
            "weather_metrics": {"temp": f"{temp}°C", "feels_like": f"{feels_like}°C", "uv": uv, "humidity": f"{humidity}%"},
            "generated_poster_url": public_image_url if public_image_url else "Failed to generate",
            "background_crawling_tasks": triggered_scrapers,
            "threads_posting": "Scheduled in background with rich layout"
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
