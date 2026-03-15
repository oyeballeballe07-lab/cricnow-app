"""
CricNow Real-Time Scraper
=========================
Scrapes live scores + news every 5 seconds
Pushes to a local JSON file that the HTML app reads

Requirements:
  pip install aiohttp asyncio beautifulsoup4 requests

Run:
  python3 cricnow-scraper.py
"""

import asyncio
import aiohttp
import json
import time
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup

# ── CONFIG ──────────────────────────────────────────
SCORE_INTERVAL   = 5    # seconds between score updates
NEWS_INTERVAL    = 300  # seconds between news updates (5 min)
OUTPUT_FILE      = "cricnow_live_data.json"
CRICAPI_KEY      = os.getenv("CRICAPI_KEY", "")      # set in env
NEWSAPI_KEY      = os.getenv("NEWSAPI_KEY", "")      # set in env
# ────────────────────────────────────────────────────

# Shared state
live_data = {
    "matches": [],
    "news": [],
    "last_score_update": "",
    "last_news_update": "",
    "status": "running"
}

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")

def save_data():
    """Save current data to JSON file for HTML app to read"""
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(live_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"Save error: {e}", "ERR")

# ══════════════════════════════════════════════════════
# SCORE SCRAPERS
# ══════════════════════════════════════════════════════

async def fetch_scores_cricapi(session):
    """Fetch live scores from CricAPI (free tier)"""
    if not CRICAPI_KEY:
        return None
    url = f"https://cricapi.com/api/currentMatches?apikey={CRICAPI_KEY}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
            if r.status == 200:
                data = await r.json()
                return parse_cricapi(data)
    except Exception as e:
        log(f"CricAPI error: {e}", "ERR")
    return None

def parse_cricapi(data):
    """Convert CricAPI response to our format"""
    matches = []
    for m in data.get("matches", [])[:20]:
        try:
            teams = m.get("team-1", "?") + " vs " + m.get("team-2", "?")
            status = m.get("matchStarted", False)
            score_t1 = m.get("score", {}).get(m.get("team-1",""), "")
            score_t2 = m.get("score", {}).get(m.get("team-2",""), "")
            
            match = {
                "id": str(m.get("unique_id", "")),
                "t1": m.get("team-1", "TBA"),
                "t2": m.get("team-2", "TBA"),
                "f1": get_flag(m.get("team-1","")),
                "f2": get_flag(m.get("team-2","")),
                "series": m.get("type","T20") + " · " + m.get("series",""),
                "venue": m.get("venue",""),
                "status": "live" if status else "upcoming",
                "s1": score_t1,
                "s2": score_t2,
                "note": m.get("status",""),
                "cat": classify_match(m.get("series",""), m.get("type","")),
                "time": m.get("date",""),
            }
            matches.append(match)
        except Exception as e:
            log(f"Parse match error: {e}", "WARN")
    return matches

async def scrape_espncricinfo(session):
    """
    Scrape ESPNCricinfo live scores page
    NOTE: Use only for personal/dev use, respect robots.txt
    """
    url = "https://www.espncricinfo.com/live-cricket-scores"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; CricNow/1.0)"}
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status == 200:
                html = await r.text()
                return parse_espn_scores(html)
    except Exception as e:
        log(f"ESPN scrape error: {e}", "WARN")
    return None

def parse_espn_scores(html):
    """Parse ESPN Cricinfo live scores page"""
    soup = BeautifulSoup(html, "html.parser")
    matches = []
    
    # ESPN uses various class names, try multiple
    cards = soup.find_all("div", class_=re.compile(r"match-info|live-score|scorecard"))
    
    for card in cards[:10]:
        try:
            teams = card.find_all(class_=re.compile(r"team|name"))
            scores = card.find_all(class_=re.compile(r"score|runs"))
            status_el = card.find(class_=re.compile(r"status|result"))
            
            if len(teams) >= 2:
                m = {
                    "id": f"espn_{int(time.time())}",
                    "t1": teams[0].get_text(strip=True),
                    "t2": teams[1].get_text(strip=True),
                    "f1": "🏏", "f2": "🏏",
                    "s1": scores[0].get_text(strip=True) if scores else "",
                    "s2": scores[1].get_text(strip=True) if len(scores)>1 else "",
                    "note": status_el.get_text(strip=True) if status_el else "",
                    "status": "live",
                    "cat": "intl",
                    "series": ""
                }
                matches.append(m)
        except:
            pass
    return matches

async def scrape_cricbuzz_free(session):
    """
    Scrape Cricbuzz match list (no key needed for basic list)
    NOTE: Use only for personal/dev use
    """
    url = "https://www.cricbuzz.com/cricket-match/live-scores"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml"
    }
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status == 200:
                html = await r.text()
                return parse_cricbuzz(html)
    except Exception as e:
        log(f"Cricbuzz scrape error: {e}", "WARN")
    return None

def parse_cricbuzz(html):
    """Parse Cricbuzz live scores"""
    soup = BeautifulSoup(html, "html.parser")
    matches = []
    
    # Cricbuzz match cards
    for card in soup.find_all("div", class_=re.compile(r"cb-mtch-lst|cb-scr-wll-wrp"))[:15]:
        try:
            title = card.find(class_=re.compile(r"cb-lv-scrs-col"))
            teams_el = card.find_all(class_=re.compile(r"cb-hmscg-tm-nm|cb-awyscg-tm-nm"))
            score_els = card.find_all(class_=re.compile(r"cb-lv-scrs-well"))
            status_el = card.find(class_=re.compile(r"cb-text-live|cb-text-complete"))
            
            if len(teams_el) >= 2:
                m = {
                    "id": f"cb_{int(time.time()*1000)}",
                    "t1": teams_el[0].get_text(strip=True),
                    "t2": teams_el[1].get_text(strip=True),
                    "f1": get_flag(teams_el[0].get_text(strip=True)),
                    "f2": get_flag(teams_el[1].get_text(strip=True)),
                    "s1": score_els[0].get_text(strip=True) if score_els else "",
                    "s2": score_els[1].get_text(strip=True) if len(score_els)>1 else "",
                    "note": status_el.get_text(strip=True) if status_el else "",
                    "status": "live" if status_el and "LIVE" in status_el.get_text().upper() else "upcoming",
                    "series": title.get_text(strip=True) if title else "",
                    "cat": "intl",
                }
                matches.append(m)
        except:
            pass
    return matches

# ══════════════════════════════════════════════════════
# NEWS SCRAPERS
# ══════════════════════════════════════════════════════

async def fetch_news_newsapi(session):
    """Fetch cricket news from NewsAPI"""
    if not NEWSAPI_KEY:
        return None
    url = (f"https://newsapi.org/v2/everything"
           f"?q=cricket+IPL&language=en&sortBy=publishedAt"
           f"&pageSize=10&apiKey={NEWSAPI_KEY}")
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
            if r.status == 200:
                data = await r.json()
                articles = data.get("articles", [])
                return [
                    {
                        "id": f"na_{i}",
                        "title": a.get("title",""),
                        "url": a.get("url",""),
                        "source": a.get("source",{}).get("name",""),
                        "time": a.get("publishedAt","")[:10],
                        "icon": "🏏",
                        "tag": "LATEST"
                    }
                    for i, a in enumerate(articles)
                    if a.get("title") and "[Removed]" not in a.get("title","")
                ]
    except Exception as e:
        log(f"NewsAPI error: {e}", "ERR")
    return None

async def scrape_espn_news(session):
    """Scrape ESPNCricinfo cricket news RSS"""
    url = "https://www.espncricinfo.com/rss/content/story/feeds/0.xml"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as r:
            if r.status == 200:
                xml = await r.text()
                return parse_rss(xml, "ESPN")
    except Exception as e:
        log(f"ESPN news error: {e}", "WARN")
    return None

async def scrape_cricbuzz_news(session):
    """Scrape Cricbuzz news RSS"""
    url = "https://www.cricbuzz.com/rss-feeds/latest-cricket-news"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as r:
            if r.status == 200:
                xml = await r.text()
                return parse_rss(xml, "Cricbuzz")
    except Exception as e:
        log(f"Cricbuzz news error: {e}", "WARN")
    return None

def parse_rss(xml, source):
    """Parse RSS XML feed"""
    soup = BeautifulSoup(xml, "xml")
    items = soup.find_all("item")[:10]
    news = []
    for i, item in enumerate(items):
        title = item.find("title")
        link = item.find("link")
        pub = item.find("pubDate")
        if title:
            news.append({
                "id": f"rss_{source}_{i}",
                "title": title.get_text(strip=True),
                "url": link.get_text(strip=True) if link else "",
                "source": source,
                "time": pub.get_text(strip=True)[:16] if pub else "",
                "icon": "🏏",
                "tag": tag_news(title.get_text())
            })
    return news

def tag_news(title):
    t = title.lower()
    if any(w in t for w in ["live","score","update","ball"]): return "LIVE"
    if any(w in t for w in ["win","won","beat","result","final score"]): return "MATCH REPORT"
    if any(w in t for w in ["preview","vs","match","upcoming"]): return "PREVIEW"
    if any(w in t for w in ["stat","record","century","wicket","runs"]): return "STATS"
    return "TRENDING"

# ══════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════

FLAGS = {
    "india": "🇮🇳","australia": "🇦🇺","england": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "pakistan": "🇵🇰","south africa": "🇿🇦","new zealand": "🇳🇿",
    "west indies": "🇯🇲","sri lanka": "🇱🇰","bangladesh": "🇧🇩",
    "afghanistan": "🇦🇫","ireland": "🇮🇪","zimbabwe": "🇿🇼",
    "mi":"🇮🇳","csk":"🇮🇳","rcb":"🇮🇳","kkr":"🇮🇳","dc":"🇮🇳",
    "gt":"🇮🇳","srh":"🇮🇳","lsg":"🇮🇳","rr":"🇮🇳","pbks":"🇮🇳",
}
def get_flag(team):
    t = team.lower().strip()
    for k, v in FLAGS.items():
        if k in t: return v
    return "🏏"

IPL_TEAMS = ["MI","CSK","RCB","KKR","DC","GT","SRH","LSG","RR","PBKS",
             "Mumbai","Chennai","Bangalore","Kolkata","Delhi","Gujarat",
             "Hyderabad","Lucknow","Rajasthan","Punjab"]

def classify_match(series, mtype):
    s = series.upper()
    if any(t.upper() in s for t in IPL_TEAMS) or "IPL" in s: return "ipl"
    if "WOMEN" in s or "WPL" in s: return "women"
    if any(w in s for w in ["RANJI","SHEFFIELD","DOMESTIC","CSA","SYED MUSHTAQ"]): return "domestic"
    return "intl"

# ══════════════════════════════════════════════════════
# MAIN LOOPS
# ══════════════════════════════════════════════════════

async def score_loop():
    """Run every SCORE_INTERVAL seconds"""
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                matches = None
                
                # 1. Try CricAPI first (most reliable with key)
                if CRICAPI_KEY:
                    matches = await fetch_scores_cricapi(session)
                    if matches:
                        log(f"CricAPI: {len(matches)} matches fetched")
                
                # 2. Fallback: Cricbuzz scraper
                if not matches:
                    matches = await scrape_cricbuzz_free(session)
                    if matches:
                        log(f"Cricbuzz scraper: {len(matches)} matches")
                
                # 3. Fallback: ESPN scraper
                if not matches:
                    matches = await scrape_espncricinfo(session)
                    if matches:
                        log(f"ESPN scraper: {len(matches)} matches")
                
                if matches:
                    live_data["matches"] = matches
                    live_data["last_score_update"] = datetime.now().isoformat()
                    save_data()
                    log(f"Data saved → {OUTPUT_FILE}")
                else:
                    log("No score data available", "WARN")
                    
            except Exception as e:
                log(f"Score loop error: {e}", "ERR")
            
            await asyncio.sleep(SCORE_INTERVAL)

async def news_loop():
    """Run every NEWS_INTERVAL seconds"""
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                news = None
                
                # 1. NewsAPI
                if NEWSAPI_KEY:
                    news = await fetch_news_newsapi(session)
                    if news: log(f"NewsAPI: {len(news)} articles")
                
                # 2. Cricbuzz RSS
                if not news:
                    news = await scrape_cricbuzz_news(session)
                    if news: log(f"Cricbuzz RSS: {len(news)} articles")
                
                # 3. ESPN RSS
                if not news:
                    news = await scrape_espn_news(session)
                    if news: log(f"ESPN RSS: {len(news)} articles")
                
                if news:
                    live_data["news"] = news
                    live_data["last_news_update"] = datetime.now().isoformat()
                    save_data()
                    
            except Exception as e:
                log(f"News loop error: {e}", "ERR")
            
            await asyncio.sleep(NEWS_INTERVAL)

async def main():
    log("=" * 50)
    log("CricNow Scraper Starting...")
    log(f"CricAPI key: {'SET ✓' if CRICAPI_KEY else 'NOT SET (using free scrapers)'}")
    log(f"NewsAPI key: {'SET ✓' if NEWSAPI_KEY else 'NOT SET (using RSS)'}")
    log(f"Output: {OUTPUT_FILE}")
    log(f"Score interval: {SCORE_INTERVAL}s | News interval: {NEWS_INTERVAL}s")
    log("=" * 50)
    
    # Run both loops concurrently
    await asyncio.gather(
        score_loop(),
        news_loop()
    )

if __name__ == "__main__":
    asyncio.run(main())
