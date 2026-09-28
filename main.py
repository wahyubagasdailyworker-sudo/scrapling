from fastapi import FastAPI, HTTPException
from scrapling import StealthyFetcher
import urllib.parse

app = FastAPI()

@app.get("/scrape")
def scrape_x_data(keyword: str, limit: int = 10):
    try:
        # Menyiapkan URL pencarian Twitter
        query = urllib.parse.quote(keyword)
        url = f"https://x.com/search?q={query}&src=typed_query&f=live"

        # Menjalankan Scrapling dengan mode browser tersembunyi
        fetcher = StealthyFetcher(headless=True)
        page = fetcher.get(url)
        
        # JEDA: Menunggu elemen tweet (artikel) dimuat oleh JavaScript Twitter
        page.wait_for_selector('article[data-testid="tweet"]', timeout=15000)
        
        results = []
        tweets = page.css('article[data-testid="tweet"]')[:limit]
        
        for tweet in tweets:
            # Menggunakan Scrapling AI/Adaptive element finder secara manual
            text = tweet.css('[data-testid="tweetText"]').text(default="Tidak ada teks")
            username = tweet.css('[data-testid="User-Name"]').text(default="Unknown")
            time_post = tweet.css('time').attrib.get('datetime', 'Unknown')
            
            results.append({
                "keyword": keyword,
                "username": username,
                "text": text,
                "time": time_post
            })
            
        return {"status": "success", "total": len(results), "data": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Penting untuk Render
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
