import os
import requests
import feedparser
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

FEEDS_CYBER = [
    {"name": "The Hacker News", "url": "https://feeds.feedburner.com/TheHackersNews"},
    {"name": "BleepingComputer", "url": "https://www.bleepingcomputer.com/feed/"},
    {"name": "The Record", "url": "https://therecord.media/feed"},
    {"name": "SecurityWeek", "url": "https://www.securityweek.com/feed/"},
    {"name": "CISO Advisor", "url": "https://www.cisoadvisor.com.br/feed/"}
]

def clean_html_to_pure_text(raw_html, max_length=350):
    """Remove tags HTML, scripts, imagens e links para deixar apenas texto limpo."""
    if not raw_html:
        return "Sem resumo disponível."
    
    soup = BeautifulSoup(raw_html, "html.parser")
    
    # Remove tags que poluem a tradução
    for element in soup(["script", "style", "img", "figure", "a"]):
        element.decompose()
        
    text = soup.get_text(separator=" ").strip()
    text = " ".join(text.split()) # Remove múltiplos espaços e quebras de linha
    
    if len(text) > max_length:
        text = text[:max_length] + "..."
    return text if text else "Sem resumo disponível."

def translate_to_pt(text):
    """Traduz texto puro para Português."""
    if not text or text == "Sem resumo disponível.":
        return text
    try:
        return GoogleTranslator(source='auto', target='pt').translate(text)
    except Exception as e:
        print(f"Erro na tradução: {e}")
        return text

def send_discord_embed(title, link, summary, source_name):
    """
    Envia a mensagem para o Discord.
    (Sem enviar 'username' para respeitar o nome/avatar definidos no seu Webhook)
    """
    payload = {
        "embeds": [
            {
                "title": f"🛡️ {title}",
                "url": link,
                "description": summary,
                "color": 3447003, # Cor Azul/Cyber
                "footer": {
                    "text": f"Fonte: {source_name} • Traduzido para PT-BR"
                }
            }
        ]
    }
    
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if response.status_code not in [200, 204]:
        print(f"Erro ao enviar para Discord: {response.status_code} - {response.text}")

def main():
    for source in FEEDS_CYBER:
        feed = feedparser.parse(source["url"])
        if feed.entries:
            latest = feed.entries[0]
            
            raw_title = latest.title
            link = latest.link
            raw_summary = getattr(latest, 'summary', getattr(latest, 'description', ''))
            
            clean_text = clean_html_to_pure_text(raw_summary)
            title_pt = translate_to_pt(raw_title)
            summary_pt = translate_to_pt(clean_text)
            
            send_discord_embed(title_pt, link, summary_pt, source["name"])

if __name__ == "__main__":
    if DISCORD_WEBHOOK_URL:
        main()
    else:
        print("Erro: Variável DISCORD_WEBHOOK_URL não configurada.")
