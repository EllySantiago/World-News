import os
import requests
import feedparser
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

DISCORD_WEBHOOK_IA_OSINT = os.getenv("DISCORD_WEBHOOK_IA_OSINT")

FEEDS_IA_OSINT = [
    # --- INTELIGÊNCIA ARTIFICIAL ---
    {"name": "OpenAI Blog", "url": "https://openai.com/news/rss.xml", "category": "🤖 IA"},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml", "category": "🤖 IA"},
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "category": "🤖 IA"},
    {"name": "Google AI Blog", "url": "https://blog.research.google/feeds/posts/default", "category": "🤖 IA"},
    
    # --- FERRAMENTAS OPEN SOURCE & OSINT ---
    {"name": "Nmap Releases", "url": "https://seclists.org/rss/nmap-hackers.rss", "category": "🛠️ OSINT & Tools"},
    {"name": "KitPloit (Hacking & OSINT)", "url": "https://feeds.feedburner.com/pentesttools", "category": "🛠️ OSINT & Tools"},
    {"name": "Darknet (Security Tools)", "url": "https://www.darknet.org.uk/feed/", "category": "🛠️ OSINT & Tools"}
]

def clean_html_to_pure_text(raw_html, max_length=350):
    """Remove todas as tags HTML, imagens, links e deixa apenas texto puro para tradução."""
    if not raw_html:
        return "Sem resumo disponível."
    
    soup = BeautifulSoup(raw_html, "html.parser")
    
    # Remove tags de imagens, scripts e estilos que poluem o texto
    for element in soup(["script", "style", "img", "figure", "a"]):
        element.decompose()
        
    text = soup.get_text(separator=" ").strip()
    text = " ".join(text.split()) # Remove múltiplos espaços e quebras de linha
    
    if len(text) > max_length:
        text = text[:max_length] + "..."
    return text if text else "Sem resumo disponível."

def translate_to_pt(text):
    """Traduz texto puro do Inglês para o Português."""
    if not text or text == "Sem resumo disponível.":
        return text
    try:
        translated = GoogleTranslator(source='auto', target='pt').translate(text)
        return translated
    except Exception as e:
        print(f"Erro na tradução: {e}")
        return text

def send_discord_embed(title, link, summary, source_name, category):
    """Envia o Embed formatado com o nome do Bot correto."""
    payload = {
        "username": "IA & OSINT Intel",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/2103/2103633.png",
        "embeds": [
            {
                "title": f"[{category}] {title}",
                "url": link,
                "description": summary,
                "color": 10181046 if "IA" in category else 15844367,
                "footer": {
                    "text": f"Fonte: {source_name} • Traduzido para PT-BR"
                }
            }
        ]
    }
    
    response = requests.post(DISCORD_WEBHOOK_IA_OSINT, json=payload)
    if response.status_code not in [200, 204]:
        print(f"Erro ao enviar para Discord: {response.status_code} - {response.text}")

def main():
    for source in FEEDS_IA_OSINT:
        feed = feedparser.parse(source["url"])
        if feed.entries:
            latest = feed.entries[0]
            
            raw_title = latest.title
            link = latest.link
            raw_summary = getattr(latest, 'summary', getattr(latest, 'description', ''))
            
            # 1. Limpa o texto completamente primeiro
            clean_text = clean_html_to_pure_text(raw_summary)
            
            # 2. Traduz título e resumo já limpo
            title_pt = translate_to_pt(raw_title)
            summary_pt = translate_to_pt(clean_text)
            
            # 3. Dispara para o Discord
            send_discord_embed(title_pt, link, summary_pt, source["name"], source["category"])

if __name__ == "__main__":
    if DISCORD_WEBHOOK_IA_OSINT:
        main()
    else:
        print("Erro: Variável DISCORD_WEBHOOK_IA_OSINT não configurada.")
