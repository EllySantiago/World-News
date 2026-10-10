import os
import requests
import feedparser
from html2text import html2text

# URL do Webhook do Discord (salva nos Secrets do GitHub)
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Feeds confiáveis de cibersegurança
FEEDS = [
    {"name": "The Hacker News", "url": "https://feeds.feedburner.com/TheHackersNews"},
    {"name": "BleepingComputer", "url": "https://www.bleepingcomputer.com/feed/"},
    {"name": "The Record", "url": "https://therecord.media/feed"}
]

def clean_summary(raw_html, max_length=280):
    """Converte HTML do feed em texto limpo e limita o tamanho."""
    text = html2text(raw_html).strip()
    text = text.replace("\n", " ")
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text

def send_discord_embed(title, link, summary, source_name):
    """Envia o resumo formatado via Embed no Discord."""
    payload = {
        "username": "Cyber Intel Bot",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/2092/2092663.png",
        "embeds": [
            {
                "title": title,
                "url": link,
                "description": summary,
                "color": 15158332,  # Cor vermelha/alerta em Hex (decimal)
                "footer": {
                    "text": f"Fonte: {source_name} • Atualização Diária"
                }
            }
        ]
    }
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def fetch_latest_news():
    for source in FEEDS:
        feed = feedparser.parse(source["url"])
        if feed.entries:
            # Pega apenas a notícia mais recente de cada feed
            latest = feed.entries[0]
            
            title = latest.title
            link = latest.link
            summary_raw = getattr(latest, 'summary', getattr(latest, 'description', 'Sem resumo disponível.'))
            summary = clean_summary(summary_raw)
            
            send_discord_embed(title, link, summary, source["name"])

if __name__ == "__main__":
    if DISCORD_WEBHOOK_URL:
        fetch_latest_news()
    else:
        print("Erro: DISCORD_WEBHOOK_URL não configurada.")
