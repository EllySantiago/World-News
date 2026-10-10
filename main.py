import os
import requests
import feedparser
from html2text import html2text
from deep_translator import GoogleTranslator

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Feeds de vários países (EUA, Europa, Brasil)
FEEDS = [
    {"name": "The Hacker News (EUA)", "url": "https://feeds.feedburner.com/TheHackersNews"},
    {"name": "BleepingComputer (EUA)", "url": "https://www.bleepingcomputer.com/feed/"},
    {"name": "The Record (EUA)", "url": "https://therecord.media/feed"},
    {"name": "SecurityWeek (EUA)", "url": "https://www.securityweek.com/feed/"},
    {"name": "CISO Advisor (Brasil)", "url": "https://www.cisoadvisor.com.br/feed/"}
]

def translate_to_pt(text):
    """Traduz textos de qualquer idioma para o Português."""
    try:
        if not text.strip():
            return "Sem resumo disponível."
        # Traduz automaticamente detectando o idioma de origem
        translated = GoogleTranslator(source='auto', target='pt').translate(text)
        return translated
    except Exception:
        return text  # Retorna o texto original caso ocorra falha na tradução

def clean_and_format_summary(raw_html, max_length=300):
    """Remove tags HTML e converte para texto limpo."""
    text = html2text(raw_html).strip()
    text = text.replace("\n", " ")
    if len(text) > max_length:
        text = text[:max_length] + "..."
    return text

def send_discord_embed(title, link, summary_pt, source_name):
    """Formata e envia a notícia para o Discord via Webhook."""
    payload = {
        "username": "Global Cyber Intel",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/2092/2092663.png",
        "embeds": [
            {
                "title": f"🛡️ {title}",
                "url": link,
                "description": summary_pt,
                "color": 3447003, # Cor azul-escuro/cyber
                "footer": {
                    "text": f"Fonte Original: {source_name} • Traduzido para PT-BR"
                }
            }
        ]
    }
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def fetch_latest_news():
    for source in FEEDS:
        feed = feedparser.parse(source["url"])
        if feed.entries:
            latest = feed.entries[0]
            
            raw_title = latest.title
            link = latest.link
            raw_summary = getattr(latest, 'summary', getattr(latest, 'description', ''))
            
            # Limpa o HTML e traduz título e resumo
            clean_summary = clean_and_format_summary(raw_summary)
            title_pt = translate_to_pt(raw_title)
            summary_pt = translate_to_pt(clean_summary)
            
            send_discord_embed(title_pt, link, summary_pt, source["name"])

if __name__ == "__main__":
    if DISCORD_WEBHOOK_URL:
        fetch_latest_news()
    else:
        print("Erro: DISCORD_WEBHOOK_URL não encontrada.")
