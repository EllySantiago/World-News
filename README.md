# World-News
# 🤖 Discord Intel & Tech News Bots

Automatizações em Python executadas via **GitHub Actions** que buscam os feeds RSS mais recentes de portais globais de Cibersegurança, Inteligência Artificial, Ferramentas Open Source/OSINT e Frontend, traduzem os resumos para o Português (PT-BR) e publicam automaticamente em canais dedicados do **Discord** usando Webhooks.

---

## 🚀 Canais e Fontes Monitoradas

1. **🛡️ Cibersegurança (`main.py`)**
   - *Fontes:* The Hacker News, BleepingComputer, The Record, SecurityWeek, CISO Advisor.
2. **🤖 IA & OSINT (`ia_osint.py`)**
   - *Fontes:* OpenAI Blog, Hugging Face Blog, TechCrunch AI, Google AI Blog, Nmap, KitPloit, Darknet.
3. **⚡ Frontend (`front.py`)**
   - *Fontes:* Smashing Magazine, CSS-Tricks, Dev.to, React Blog, LogRocket.

---

## 🛠️ Tecnologias Utilizadas

- **Python 3.10+**
- **GitHub Actions** (Automação e agendamento diário sem servidor)
- **BeautifulSoup4** (Limpeza de tags HTML e imagens)
- **Deep-Translator** (Tradução automática para PT-BR)
- **Feedparser** (Leitura de RSS)
- **Discord Webhooks**

---

## 📁 Estrutura do Repositório

```text
├── .github/
│   └── workflows/
│       ├── cyber_news.yml      # Workflow diário de Cyber
│       ├── ia_osint_news.yml   # Workflow diário de IA & OSINT
│       └── front_news.yml      # Workflow diário de Frontend
├── main.py                     # Script de Cibersegurança
├── ia_osint.py                 # Script de IA & Ferramentas OSINT
├── front.py                    # Script de Frontend
├── requirements.txt            # Dependências compartilhadas
└── README.md
