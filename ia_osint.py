import os
import requests
import feedparser
from html2text import html2text
from deep_translator import GoogleTranslator

DISCORD_WEBHOOK_IA_OSINT = os.getenv("DISCORD_WEBHOOK_IA_OSINT")

FEEDS_IA_OSINT = [
    # --- INTELIGÊNCIA ARTIFICIAL ---
    {"name": "OpenAI Blog", "url": "https://openai.com/news/rss.xml", "category": "🤖 IA"},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml", "category": "🤖 IA"},
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "category": "🤖 IA"},
    {"name": "Google AI Blog", "url": "https://blog.research.google/feeds/posts/default", "category": "🤖 IA"},
    
    # --- FERRAMENTAS OPEN SOURCE & OSINT ---
    {"name": "Nmap Releases / News", "url": "https://seclists.org/rss/nmap-hackers.rss", "category": "🛠️ OSINT & Tools"},
    {"name": "KitPloit (Ferramentas Hacking & OSINT)", "url": "https://feeds.feedburner.com/pentesttools", "category": "🛠️ OSINT & Tools"},
    {"name": "Darknet (Security Tools)", "url": "https://www.darknet.org.uk/feed/", "category": "🛠️ OSINT & Tools"}
]

def translate_to_pt(text):
    try:
        if not text.strip():
            return "Sem descrição disponível."
        return GoogleTranslator(source='auto', target='pt').translate(text)
    except Exception:
        return text

def clean_summary(raw_html, max_length=280):
    text = html2text(raw_html).strip().replace("\n", " ")
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text

def send_discord_embed(title, link, summary, source_name, category):
    payload = {
        "username": "IA & OSINT Intel Bot",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/2103/2103633.png",
        "embeds": [
            {
                "title": f"[{category}] {title}",
                "url": link,
                "description": summary,
                "color": 10181046 if "IA" in category else 15844367,
                "footer": {
                    "text": f"Fonte: {source_name} • Traduzido via Google Translate"
                }
            }
        ]
    }
    requests.post(DISCORD_WEBHOOK_IA_OSINT, json=payload)

def main():
    for source in FEEDS_IA_OSINT:
        feed = feedparser.parse(source["url"])
        if feed.entries:
            latest = feed.entries[0]
            raw_title = latest.title
            link = latest.link
            raw_summary = getattr(latest, 'summary', getattr(latest, 'description', ''))
            
            clean_text = clean_summary(raw_summary)
            title_pt = translate_to_pt(raw_title)
            summary_pt = translate_to_pt(clean_text)
            
            send_discord_embed(title_pt, link, summary_pt, source["name"], source["category"])

if __name__ == "__main__":
    if DISCORD_WEBHOOK_IA_OSINT:
        main()
    else:
        print("Erro: Variável DISCORD_WEBHOOK_IA_OSINT não configurada.")
