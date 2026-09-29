from fastapi import FastAPI
from patchright.sync_api import sync_playwright
import urllib.parse
from datetime import datetime, timezone
import threading

app = FastAPI()
USER_DATA_DIR = "./twitter_session"

# Kunci antrean (Lock) agar memori browser tidak tabrakan
scrape_lock = threading.Lock()

@app.get("/scrape")
def scrape_x_data(keyword: str, limit: int = 15):
    try:
        # Memaksa request yang masuk bersamaan untuk antre satu per satu
        with scrape_lock:
            query = urllib.parse.quote(keyword)
            url = f"https://x.com/search?q={query}&src=typed_query&f=live"
            results = []

            now_utc = datetime.now(timezone.utc)

            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=USER_DATA_DIR,
                    headless=True, 
                )
                
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(url)
                
                if "login" in page.url or "i/flow/login" in page.url:
                    context.close()
                    return {
                        "status": "error", 
                        "detail": "Sesi login kedaluwarsa. Silakan ubah headless=False di main.py, jalankan ulang, dan login kembali."
                    }

                page.wait_for_selector('article[data-testid="tweet"]', timeout=20000)
                tweets = page.query_selector_all('article[data-testid="tweet"]')[:limit]
                
                for tweet in tweets:
                    time_el = tweet.query_selector('time')
                    time_post = time_el.get_attribute('datetime') if time_el else None
                    
                    if time_post:
                        try:
                            tweet_time_str = time_post.replace('Z', '+00:00')
                            tweet_time = datetime.fromisoformat(tweet_time_str)
                            time_diff = now_utc - tweet_time
                            
                            # Filter 1 Jam
                            if time_diff.total_seconds() > 3600:
                                continue
                        except ValueError:
                            pass 
                    else:
                        time_post = "Unknown"

                    text_el = tweet.query_selector('[data-testid="tweetText"]')
                    text = text_el.inner_text() if text_el else "Tidak ada teks"
                    
                    user_el = tweet.query_selector('[data-testid="User-Name"]')
                    username = user_el.inner_text().replace('\n', ' | ') if user_el else "Unknown"
                    
                    link_el = tweet.query_selector('a:has(time)')
                    href = link_el.get_attribute('href') if link_el else None
                    tweet_link = f"https://x.com{href}" if href else "Link tidak ditemukan"
                    
                    reply_el = tweet.query_selector('[data-testid="reply"]')
                    reply_count = reply_el.inner_text() if reply_el and reply_el.inner_text() else "0"
                    
                    like_el = tweet.query_selector('[data-testid="like"]')
                    like_count = like_el.inner_text() if like_el and like_el.inner_text() else "0"
                    
                    results.append({
                        "keyword": keyword,
                        "username": username,
                        "text": text,
                        "time": time_post,
                        "link": tweet_link,
                        "replies": reply_count,
                        "likes": like_count
                    })
                
                context.close()
                
            return {"status": "success", "total": len(results), "data": results}

    except Exception as e:
        return {"status": "error", "detail": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)