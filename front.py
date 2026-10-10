import os
import requests
import feedparser
from html2text import html2text
from deep_translator import GoogleTranslator

DISCORD_WEBHOOK_FRONT = os.getenv("DISCORD_WEBHOOK_FRONT")

# Feeds do Ecossistema Frontend
FEEDS_FRONTEND = [
    {"name": "Smashing Magazine", "url": "https://www.smashingmagazine.com/feed/"},
    {"name": "CSS-Tricks", "url": "https://css-tricks.com/feed/"},
    {"name": "Dev.to (Frontend)", "url": "https://dev.to/feed/tag/frontend"},
    {"name": "React Blog", "url": "https://react.dev/rss.xml"},
    {"name": "LogRocket Blog", "url": "https://blog.logrocket.com/feed/"}
]

def translate_to_pt(text):
    try:
        if not text.strip():
            return "Sem resumo disponível."
        return GoogleTranslator(source='auto', target='pt').translate(text)
    except Exception:
        return text

def clean_summary(raw_html, max_length=280):
    text = html2text(raw_html).strip()
    text = text.replace("\n", " ")
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text

def send_discord_embed(title, link, summary, source_name):
    """Envia as novidades para o canal de Frontend do Discord."""
    payload = {
        "username": "Frontend Pulse Bot",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/1055/1055687.png",
        "embeds": [
            {
                "title": f"⚡ {title}",
                "url": link,
                "description": summary,
                "color": 1752220, # Cor turquesa/frontend
                "footer": {
                    "text": f"Fonte: {source_name} • Tendências Frontend"
                }
            }
        ]
    }
    requests.post(DISCORD_WEBHOOK_FRONT, json=payload)

def main():
    for source in FEEDS_FRONTEND:
        feed = feedparser.parse(source["url"])
        if feed.entries:
            latest = feed.entries[0]
            
            raw_title = latest.title
            link = latest.link
            raw_summary = getattr(latest, 'summary', getattr(latest, 'description', ''))
            
            clean_text = clean_summary(raw_summary)
            title_pt = translate_to_pt(raw_title)
            summary_pt = translate_to_pt(clean_text)
            
            send_discord_embed(title_pt, link, summary_pt, source["name"])

if __name__ == "__main__":
    if DISCORD_WEBHOOK_FRONT:
        main()
    else:
        print("Erro: Variável DISCORD_WEBHOOK_FRONT não configurada.")
