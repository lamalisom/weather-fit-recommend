import os
import httpx
from fastapi import FastAPI, BackgroundTasks
from supabase import create_client, Client
from dotenv import load_dotenv

# 載入環境變數（在 iPad 本地讀取 .env，在 Render 上會讀取 Environment Variables）
load_dotenv()

app = FastAPI(title="KAIT Weather Promotion Engine", version="1.0.0")

# =================【初始化 Supabase 客戶端】=================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("⚠️ 警告：Supabase 環境變數未完全設定！")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY else None


# =================【核心輔助工具函數】=================

async def fetch_weather(city: str = "Hong Kong") -> dict:
    """
    透過 RapidAPI 獲取即時香港天氣狀況
    """
    url = os.getenv("WEATHER_API_URL", "https://weatherapi-com.p.rapidapi.com/current.json")
    headers = {
        "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
        "X-RapidAPI-Host": os.getenv("WEATHER_API_HOST", "weatherapi-com.p.rapidapi.com")
    }
    params = {"q": city}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            current = data.get("current", {})
            return {
                "temp": current.get("temp_c", 22.0),
                "uv": current.get("uv", 4.0),
                "humidity": current.get("humidity", 70)
            }
        else:
            print(f"❌ 天氣 API 請求失敗: {response.status_code}")
            # 失敗時回傳安全預設值
            return {"temp": 22.0, "uv": 4.0, "humidity": 70}


def convert_to_amazon_affiliate_link(raw_url: str, amazon_tag: str) -> str:
    """
    自動將乾淨的 Amazon 商品網址注入你的聯盟行銷 Partner Tag 追蹤碼
    """
    if not raw_url:
        return ""
    if not amazon_tag:
        return raw_url
    
    # 清除網址尾巴可能存在的既有參數，並補上你的專屬 Tag
    base_url = raw_url.split("?")[0]
    return f"{base_url}?tag={amazon_tag}"


async def trigger_apify_scraper(actor_id: str, payload: dict) -> str:
    """
    指派 Apify 雲端爬蟲出動，實時撈取熱門商品
    """
    apify_token = os.getenv("APIFY_TOKEN")
    if not apify_token:
        return "Missing Apify Token"
        
    # 將斜線轉換成符合網址規範的格式（如 richard_feng/sephora -> richard_feng~sephora）
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


async def post_to_threads(text_content: str):
    """
    完全免費！直接將文案同步發佈到你的 Meta Threads 官方引流帳戶
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
    payload = {
        "media_type": "TEXT",
        "text": text_content
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                print("🎉 成功！文案已完全免費發佈至 Threads！")
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
        "message": "KAIT Promotion Engine is Ready!",
        "database_connected": supabase is not None
    }


# =================【⏰ 終極智慧環境感應流水線】=================
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
        
        final_promo_pool = []  # 最終交給文案模型的商品池
        triggered_scrapers = {}

        # =================【1. AMAZON 配件類部署邏輯】=================
        # 策略：根據天氣直接去 Supabase 撈取對應的配件，免爬蟲
        amazon_sub_cat = "socks"  # 預設一般天氣
        if uv > 6:
            amazon_sub_cat = "sun_glasses"  # 紫外線強，推薦太陽眼鏡/太陽帽
        elif temp < 15:
            amazon_sub_cat = "scarf"  # 天氣冷，推薦頸巾/絲巾
            
        if supabase:
            amazon_res = supabase.table("static_products")\
                .select("product_name", "raw_url")\
                .eq("platform", "amazon")\
                .eq("sub_category", amazon_sub_cat).execute()
                
            if amazon_res.data:
                for item in amazon_res.data[:2]:  # 挑選 2 個
                    affiliate_url = convert_to_amazon_affiliate_link(item["raw_url"], amazon_tag)
                    final_promo_pool.append({
                        "name": item["product_name"], 
                        "url": affiliate_url, 
                        "platform": "Amazon", 
                        "category": "Accessories"
                    })

        # =================【2. SEPHORA 美妝類部署邏輯】=================
        # 策略：指派 Apify 實時抓取最熱門的當季美妝
        sephora_keyword = "lipstick"  # 預設一般天氣推薦口紅、眼影
        if uv > 6:
            sephora_keyword = "sunscreen SPF50"  # UV 強烈推薦太陽油
        elif humidity > 85:
            sephora_keyword = "matte foundation"  # 潮濕天氣推薦控油/啞光粉底
            
        sephora_task = await trigger_apify_scraper(
            actor_id="richard_feng/sephora", 
            payload={"search": sephora_keyword, "maxItems": 3, "country": "HK"}
        )
        triggered_scrapers["sephora_job"] = sephora_task

        # =================【3. ZALORA 服飾類部署邏輯】=================
        # 策略：根據氣溫與濕度，指派 Apify 實時抓取衣服
        zalora_keyword = "casual top"  # 預設上衣
        if temp > 28 and uv > 7:
            zalora_keyword = "swimwear"  # 大晴天、高溫推薦泳衣
        elif temp < 18:
            zalora_keyword = "jacket"  # 降溫推薦外套/長褲
            
        zalora_task = await trigger_apify_scraper(
            actor_id="apify/zalora-scraper", 
            payload={"search": zalora_keyword, "maxItems": 3, "country": "hk"}
        )
        triggered_scrapers["zalora_job"] = zalora_task

        # =================【4. 免費社群引流發佈】=================
        # 自動組裝一段基本的環境通報與 Amazon 配件引流文案
        accessories_links = ", ".join([f"{item['name']}: {item['url']}" for item in final_promo_pool])
        promo_text = (
            f"【KAIT 今日香港智能穿搭通報】\n"
            f"📊 今日體感：氣溫 {temp}°C | 紫外線指數 {uv} | 濕度 {humidity}%\n"
            f"💡 專屬美妝服飾爬蟲已火速出動！為您鎖定今日最合適的 {sephora_keyword} 與 {zalora_keyword}！\n"
            f"🎒 建議出門必帶防護配件：\n{accessories_links if accessories_links else '穿你最舒適的日常單品！'}"
        )
        
        # 善用 FastAPI 的 BackgroundTasks，讓發文在後台偷偷執行，不拖慢 Cron Job 的回傳速度
        background_tasks.add_task(post_to_threads, promo_text)

        # =================【5. 返回部署日誌報告】=================
        return {
            "status": "success",
            "city": target_city,
            "weather_metrics": {"temp": f"{temp}°C", "uv": uv, "humidity": f"{humidity}%"},
            "instant_recommendations": final_promo_pool,
            "background_crawling_tasks": triggered_scrapers,
            "threads_posting": "Scheduled in background"
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
