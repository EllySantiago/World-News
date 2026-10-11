# World-News
# 🤖 Discord News Bot

Bot unificado em Python para monitorar feeds RSS em canais dedicados do Discord, consolidando a lógica de coleta, extração, resumo, deduplicação, tradução e publicação em um único ponto de execução.

---

## 🚀 Canais monitorados

O bot usa o arquivo `feeds.json` para definir os canais e os feeds associados.

1. `cyber`
   - Emoji: 🛡️
   - Webhook: `DISCORD_WEBHOOK_URL`
   - Exemplos de fontes: The Hacker News, BleepingComputer, The Record, SecurityWeek, CISO Advisor.

2. `ia_osint`
   - Emoji: 🤖
   - Webhook: `DISCORD_WEBHOOK_IA_OSINT`
   - Exemplos de fontes: OpenAI Blog, Hugging Face Blog, TechCrunch AI, Google AI Blog, Nmap Releases, KitPloit, Darknet.

3. `front`
   - Emoji: ⚡
   - Webhook: `DISCORD_WEBHOOK_FRONT`
   - Exemplos de fontes: Smashing Magazine, CSS-Tricks, Dev.to, React Blog, LogRocket.

---

## 🧠 Como o bot funciona

- Extrai itens de RSS com `feedparser`.
- Trata HTML com `BeautifulSoup` e `unwrap()` em links para preservar o texto dos links sem manter elementos de ruído.
- Deduplica por ID ou link e mantém estado por canal em `state/<canal>.json`.
- Filtra boilerplate e mantém apenas frases relevantes em um resumo extrativo.
- Tenta resumo em PT-BR via IA quando há `ANTHROPIC_API_KEY` ou `GEMINI_API_KEY` e o texto é longo o suficiente; se falhar, cai para resumo extrativo.
- Tradução automática para PT-BR com `deep-translator` quando o feed não está em português.
- Publica no Discord via webhook com timeout, retry em 429, fallback seguro e exit code 1 se alguma postagem falhar.
- O `dry-run` apenas imprime o payload JSON e não envia nem grava estado.

---

## 📁 Estrutura do repositório

```text
├── .github/
│   └── workflows/
│       ├── _run_channel.yml      # workflow reutilizável por canal
│       ├── cyber_news.yml       # execução do canal cyber
│       ├── ia_osint_news.yml    # execução do canal ia_osint
│       └── front_news.yml       # execução do canal front
├── bot.py                       # entrypoint único do bot
├── feeds.json                   # catálogo de canais, webhooks e feeds
├── requirements.txt             # dependências de runtime
├── requirements-dev.txt         # dependências de teste
├── tests/
│   └── test_bot.py             # testes automatizados
├── state/
│   └── .gitkeep                # arquivo de manutenção do diretório
├── .gitignore                   # ignora state/*.json, preserva .gitkeep
├── README.md
└── ...
```

---

## ⚙️ Dependências

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
```

Dependências principais:
- `feedparser`
- `requests`
- `beautifulsoup4`
- `trafilatura`
- `deep-translator`
- `pytest`

---

## 🧪 Como executar

Executar tudo (todos os canais):

```bash
python bot.py
```

Executar um canal específico:

```bash
python bot.py cyber
python bot.py ia_osint
python bot.py front
```

Modo sem envio (apenas imprime payloads):

```bash
python bot.py --dry-run
python bot.py --dry-run cyber
```

Executar testes:

```bash
python -m pytest -q
```

---

## 🔐 Secrets do GitHub Actions

Os workflows esperam as seguintes variáveis de ambiente/secret do GitHub:

- `DISCORD_WEBHOOK_URL`
- `DISCORD_WEBHOOK_IA_OSINT`
- `DISCORD_WEBHOOK_FRONT`

Além disso, o resumo por IA usa:
- `ANTHROPIC_API_KEY` ou `GEMINI_API_KEY`
- `LLM_MODEL` (opcional)

Nunca comite chaves reais ou webhooks diretamente no código.

---

## 🗂️ Estado e deduplicação

O estado por canal fica em `state/<canal>.json` com uma lista dos IDs processados. Isso evita envio duplicado entre execuções. O diretório `state/` não deve receber arquivos versionados além de `state/.gitkeep`.

---

## 🧩 Workflows do GitHub Actions

Os canais são executados por `workflow_call` no arquivo `.github/workflows/_run_channel.yml`, com a lógica reutilizável centralizada. Os workflows de cada canal apenas invocam o runner com o `channel` correto e o ambiente do webhook correspondente.

Os cronogramas e canais configurados em cada workflow devem ser mantidos de forma consistente ao arquivo `feeds.json`.

---

## ✅ Observações finais

- O projeto foi refatorado para um único bot central.
- Os scripts legados `main.py`, `ia_osint.py` e `front.py` foram removidos da estrutura ativa.
- O dry-run não grava estado nem envia mensagens.
- O bot trata a ausência de webhook real com aviso e continua a execução sem quebrar o restante do processamento.
- O README foi ajustado para refletir a arquitetura final e os comandos válidos do projeto.
