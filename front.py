import os
import requests
import feedparser
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

DISCORD_WEBHOOK_FRONT = os.getenv("DISCORD_WEBHOOK_FRONT")

FEEDS_FRONTEND = [
    {"name": "Smashing Magazine", "url": "https://www.smashingmagazine.com/feed/"},
    {"name": "CSS-Tricks", "url": "https://css-tricks.com/feed/"},
    {"name": "Dev.to (Frontend)", "url": "https://dev.to/feed/tag/frontend"},
    {"name": "React Blog", "url": "https://react.dev/rss.xml"},
    {"name": "LogRocket Blog", "url": "https://blog.logrocket.com/feed/"}
]

def clean_html_to_pure_text(raw_html, max_length=350):
    """Remove tags HTML, imagens e links para deixar texto limpo."""
    if not raw_html:
        return "Sem resumo disponível."
    
    soup = BeautifulSoup(raw_html, "html.parser")
    
    # Remove elementos que poluem a tradução
    for element in soup(["script", "style", "img", "figure", "a"]):
        element.decompose()
        
    text = soup.get_text(separator=" ").strip()
    text = " ".join(text.split())
    
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
    Envia o Embed respeitando o NOME e AVATAR configurados no Discord.
    (Sem enviar 'username' para não sobrescrever o que você escolheu)
    """
    payload = {
        "embeds": [
            {
                "title": f"⚡ {title}",
                "url": link,
                "description": summary,
                "color": 1752220,  # Cor Turquesa
                "footer": {
                    "text": f"Fonte: {source_name} • Traduzido para PT-BR"
                }
            }
        ]
    }
    
    response = requests.post(DISCORD_WEBHOOK_FRONT, json=payload)
    if response.status_code not in [200, 204]:
        print(f"Erro ao enviar para Discord: {response.status_code} - {response.text}")

def main():
    for source in FEEDS_FRONTEND:
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
    if DISCORD_WEBHOOK_FRONT:
        main()
    else:
        print("Erro: Variável DISCORD_WEBHOOK_FRONT não configurada.")
