# ⏰ 終極智慧環境感應流水線
@app.post("/api/v1/cron/trigger-daily")
async def trigger_daily_pipeline():
    try:
        target_city = "Hong Kong"
        amazon_tag = os.getenv("AMAZON_TAG")
        
        # 1. 獲取天氣數據 (假設 fetch_weather 已實作)
        weather = await fetch_weather(target_city)
        uv = weather["uv"]
        humidity = weather["humidity"]
        temp = weather["temp"]
        
        final_promo_pool = [] # 最終交給 Gemini 寫文案的商品池
        triggered_scrapers = {}

        # =================【1. AMAZON 配件類部署邏輯】=================
        # 策略：根據天氣直接去 Supabase 撈取對應的配件，免爬蟲
        amazon_sub_cat = "socks" # 預設一般天氣
        if uv > 6:
            amazon_sub_cat = "sun_glasses" # 紫外線強，推薦太陽眼鏡/太陽帽
        elif temp < 15:
            amazon_sub_cat = "scarf" # 天氣冷，推薦頸巾/絲巾
            
        amazon_res = supabase.table("static_products")\
            .select("product_name", "raw_url")\
            .eq("platform", "amazon")\
            .eq("sub_category", amazon_sub_cat).execute()
            
        if amazon_res.data:
            for item in amazon_res.data[:2]: # 挑選 2 個
                affiliate_url = convert_to_amazon_affiliate_link(item["raw_url"], amazon_tag)
                final_promo_pool.append({
                    "name": item["product_name"], "url": affiliate_url, 
                    "platform": "Amazon", "category": "Accessories"
                })

        # =================【2. SEPHORA 美妝類部署邏輯】=================
        # 策略：指派 Apify 實時抓取最熱門的當季美妝
        sephora_keyword = "lipstick" # 預設一般天氣推薦口紅、眼影
        if uv > 6:
            sephora_keyword = "sunscreen SPF50" # UV 強烈推薦太陽油
        elif humidity > 85:
            sephora_keyword = "matte foundation" # 潮濕天氣推薦控油/啞光粉底
            
        # 呼叫你在截圖中選定的 Richard Feng 的 Scraper
        sephora_task = await trigger_apify_scraper(
            actor_id="richard_feng/sephora", 
            payload={"search": sephora_keyword, "maxItems": 3, "country": "HK"}
        )
        triggered_scrapers["sephora_job"] = sephora_task

        # =================【3. ZALORA 服飾類部署邏輯】=================
        # 策略：根據氣溫與濕度，指派 Apify 實時抓取衣服衣服
        zalora_keyword = "casual top" # 預設上衣
        if temp > 28 and uv > 7:
            zalora_keyword = "swimwear" # 大晴天、高溫推薦泳衣
        elif temp < 18:
            zalora_keyword = "jacket" # 降溫推薦外套/長褲
            
        zalora_task = await trigger_apify_scraper(
            actor_id="apify/zalora-scraper", 
            payload={"search": zalora_keyword, "maxItems": 3, "country": "hk"}
        )
        triggered_scrapers["zalora_job"] = zalora_task

        # =================【4. 紀錄日誌並返回】=================
        # 這裡我們將立即得到的 Amazon 商品與正在跑的爬蟲任務打包
        return {
            "status": "success",
            "city": target_city,
            "weather_metrics": {"temp": f"{temp}°C", "uv": uv, "humidity": f"{humidity}%"},
            "instant_recommendations": final_promo_pool, # 這裡面含有 Amazon 的太陽眼鏡或絲巾
            "background_crawling_tasks": triggered_scrapers # 這裡面含有 Sephora(太陽油/粉底) 與 Zalora(泳衣/外套) 的異步任務
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
