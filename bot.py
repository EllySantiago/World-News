#!/usr/bin/env python3
import argparse
import json
import math
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import feedparser
import requests
import trafilatura
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

PROJECT_ROOT = Path(__file__).resolve().parent
STATE_DIR = PROJECT_ROOT / "state"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
DEFAULT_CHANNELS = {
    "cyber": "DISCORD_WEBHOOK_URL",
    "ia_osint": "DISCORD_WEBHOOK_IA_OSINT",
    "front": "DISCORD_WEBHOOK_FRONT",
}
BOILERPLATE_PATTERNS = (
    "subscribe",
    "newsletter",
    "follow us",
    "click here",
    "found this article interesting",
    "read more",
    "inscreva-se",
    "siga-nos",
    "leia mais",
    "seguir",
    "assine",
)
ABBREVIATIONS = (
    "U.S.", "U.K.", "e.g.", "i.e.", "Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "Sr.", "Jr.", "Inc.", "Ltd.", "Corp.", "vs.", "etc.", "No.", "Fig.", "Jan.", "Feb.", "Mar.", "Apr.", "Jun.", "Jul.", "Aug.", "Sep.", "Sept.", "Oct.", "Nov.", "Dec.", "Ex.")
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "as", "at", "be", "because", "been",
    "before", "being", "below", "between", "both", "but", "by", "can", "cannot", "could", "did", "do", "does", "doing", "down",
    "during", "each", "few", "for", "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me", "more", "most", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "same",
    "she", "should", "so", "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves", "then", "there", "these",
    "they", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "we", "were", "what", "when", "where",
    "which", "while", "who", "whom", "why", "with", "you", "your", "yours", "yourself", "yourselves",
    "o", "a", "de", "da", "do", "das", "dos", "e", "em", "para", "por", "com", "como", "uma", "um", "na", "nas", "nos", "se", "que", "mais",
    "menos", "entre", "sobre", "também", "onde", "quando", "porque", "senão", "após", "antes", "entre", "ainda", "ao", "à", "às", "sua",
    "suas", "seu", "seus", "este", "esta", "estes", "estas", "esse", "essa", "esses", "essas", "aquilo", "neste", "nessa", "deste", "dessa",
    "disse", "diz", "dizem", "deve", "devem", "entre", "sem", "uma", "uns", "umas"
}


def load_channel_config(path: Path = PROJECT_ROOT / "feeds.json") -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("channels", {})


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def read_state(channel: str) -> List[str]:
    path = STATE_DIR / f"{channel}.json"
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(payload, list):
        return [str(item) for item in payload[-600:]]
    return []


def write_state(channel: str, ids: List[str]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = STATE_DIR / f"{channel}.json"
    trimmed = [str(item) for item in ids[-600:]]
    with path.open("w", encoding="utf-8") as fh:
        json.dump(trimmed, fh, ensure_ascii=False)


def get_entry_value(entry: Any, *names: str) -> Any:
    for name in names:
        value = getattr(entry, name, None)
        if value is not None and value != "":
            return value
        if isinstance(entry, dict):
            value = entry.get(name)
            if value is not None and value != "":
                return value
    return None


def get_entry_id(entry: Any) -> Optional[str]:
    entry_id = get_entry_value(entry, "id")
    if entry_id:
        return str(entry_id)
    link = get_entry_value(entry, "link")
    if isinstance(link, list) and link:
        link = link[0].get("href") if isinstance(link[0], dict) else str(link[0])
    if link:
        return str(link)
    title = get_entry_value(entry, "title")
    return str(title) if title else None


def parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (list, tuple)) and len(value) >= 9:
        try:
            dt = datetime(*value[:6], tzinfo=timezone.utc)
            return dt
        except (TypeError, ValueError):
            return None
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        try:
            if cleaned.endswith("Z"):
                cleaned = cleaned[:-1] + "+00:00"
            return datetime.fromisoformat(cleaned).astimezone(timezone.utc)
        except ValueError:
            try:
                return parsedate_to_datetime(cleaned).astimezone(timezone.utc)
            except (TypeError, ValueError, IndexError):
                return None
    return None


def get_entry_published_at(entry: Any) -> Optional[datetime]:
    for field in ("published_parsed", "updated_parsed", "created_parsed"):
        value = get_entry_value(entry, field)
        dt = parse_datetime(value)
        if dt:
            return dt
    for field in ("published", "updated", "created"):
        value = get_entry_value(entry, field)
        dt = parse_datetime(value)
        if dt:
            return dt
    return None


def normalize_article_text(value: str) -> str:
    if not value:
        return ""
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\s+([.,;:!?%])", r"\1", value)
    return value.strip()


def html_to_text(raw_html: str) -> str:
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup(["script", "style", "img", "figure", "iframe", "svg", "noscript"]):
        tag.decompose()
    for anchor in soup.find_all("a"):
        anchor.unwrap()
    text = soup.get_text(" ")
    return normalize_article_text(text) or ""


def safe_extract_text(entry: Any) -> str:
    extracted = []
    for field in ("content", "summary", "description"):
        value = get_entry_value(entry, field)
        if value is None:
            continue
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    extracted.append(item.get("value",""))
                else:
                    extracted.append(str(item))
        elif isinstance(value, dict):
            extracted.append(value.get("value", ""))
        else:
            extracted.append(str(value))
    combined = " ".join(part for part in extracted if part)
    text = html_to_text(combined)
    return text


def split_sentences(text: str) -> List[str]:
    if not text:
        return []
    normalized = text.replace("\r\n", "\n").replace("\n", " ")
    placeholders = {abbr: abbr.replace(".", "§") for abbr in ABBREVIATIONS}
    for key, value in placeholders.items():
        normalized = normalized.replace(key, value)
    chunks = re.split(r"(?<=[.!?])\s+", normalized)
    sentences = []
    for chunk in chunks:
        sentence = normalize_space(chunk)
        if not sentence:
            continue
        sentence = sentence.replace("§", ".")
        sentences.append(sentence)
    return [s for s in sentences if s]


def build_extractive_summary(title: str, text: str, max_chars: int = 900, max_sentences: int = 7) -> str:
    if not text:
        return ""
    title_lower = title.lower().strip()
    sentences = []
    for sentence in split_sentences(text):
        clean = normalize_space(sentence)
        if not clean:
            continue
        if clean.lower() == title_lower:
            continue
        if len(clean) < 40:
            continue
        if len(clean) > 450:
            continue
        if any(phrase in clean.lower() for phrase in BOILERPLATE_PATTERNS):
            continue
        if len(clean) < 100 and not clean.endswith((".", "!", "?", '"', "'")):
            continue
        sentences.append(clean)
    if not sentences:
        return text[:max_chars].strip()
    if len(" ".join(sentences)) <= max_chars:
        summary = " ".join(sentences)
        return summary[:max_chars].strip()

    title_tokens = {token for token in re.findall(r"[A-Za-zÀ-ÿ0-9]+", title.lower()) if token and token not in STOPWORDS}
    word_freq = Counter()
    for sentence in sentences:
        words = [token for token in re.findall(r"[A-Za-zÀ-ÿ0-9]+", sentence.lower()) if token and token not in STOPWORDS]
        for token in words:
            word_freq[token] += 1

    scored = []
    for idx, sentence in enumerate(sentences):
        tokens = [token for token in re.findall(r"[A-Za-zÀ-ÿ0-9]+", sentence.lower()) if token and token not in STOPWORDS]
        frequency_score = sum(word_freq.get(token, 0) for token in tokens) / max(1, len(tokens))
        start_bonus = 1 + 1.2 * math.exp(-idx / 4)
        overlap = 1 + 0.8 * (len(set(tokens) & title_tokens) / max(1, len(title_tokens)))
        digit_bonus = 1.1 if re.search(r"\d", sentence) else 1.0
        score = frequency_score * start_bonus * overlap * digit_bonus
        scored.append((score, idx, sentence))

    selected = []
    used_indexes = set()
    for _, idx, sentence in sorted(scored, key=lambda item: item[0], reverse=True):
        if len(selected) >= max_sentences:
            break
        if idx in used_indexes:
            continue
        used_indexes.add(idx)
        candidate = sentence
        if not candidate:
            continue
        new_summary = " ".join(selected + [candidate])
        if len(new_summary) <= max_chars:
            selected.append(candidate)
        elif not selected:
            selected.append(candidate[:max_chars].strip())
            break
    if not selected:
        selected = [sentences[0]]
    ordered = [sentence for idx, sentence in sorted(enumerate(sentences), key=lambda x: x[0]) if sentence in selected]
    if not ordered:
        ordered = selected
    summary = " ".join(ordered)
    if len(summary) > max_chars:
        summary = summary[:max_chars].rstrip(" .,!?")
    return summary.strip()


def clean_ai_output(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"https?://\S+|www\.\S+", " ", text)
    cleaned = re.sub(r"(?<!\w)@\w+|(?<!\w)#\w+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def llm_summarize(title: str, article_text: str, lang: str) -> Optional[str]:
    if len(article_text) < 400:
        return None
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    prompt = (
        "Você deve resumir apenas usando as informações deste texto. "
        "Ignore qualquer instrução ou conteúdo fora do texto. "
        "Escreva um resumo em PT-BR com 5 a 7 frases, cerca de 900 caracteres, cobrindo o que aconteceu, quem participou, impacto e números/CVEs/versões. "
        "Use texto corrido e não inclua listas, emojis nem URL.\n\n"
        f"TÍTULO: {title}\n\nTEXTO:\n{article_text[:12000]}"
    )
    model = os.getenv("LLM_MODEL")
    if os.getenv("ANTHROPIC_API_KEY"):
        chosen_model = model or "claude-haiku-5-5"
        headers = {
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": chosen_model,
            "max_tokens": 512,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        }
        try:
            response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=30)
            if response.status_code >= 400:
                raise requests.HTTPError(f"Anthropic status {response.status_code}: {response.text[:200]}")
            data = response.json()
            blocks = data.get("content", [])
            if not blocks:
                return None
            content = "".join(block.get("text", "") for block in blocks if isinstance(block, dict))
            return clean_ai_output(content)
        except Exception as exc:
            print(f"Aviso: resumo por IA falhou ({exc}); usando resumo extrativo.", file=sys.stderr)
            return None

    if os.getenv("GEMINI_API_KEY"):
        chosen_model = model or "gemini-3.1-flash-lite"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{chosen_model}:generateContent"
        headers = {"x-goog-api-key": os.environ["GEMINI_API_KEY"], "Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code >= 400:
                raise requests.HTTPError(f"Gemini status {response.status_code}: {response.text[:200]}")
            data = response.json()
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            if not text:
                return None
            content = "".join(part.get("text", "") for part in text if isinstance(part, dict))
            return clean_ai_output(content)
        except Exception as exc:
            print(f"Aviso: resumo por IA falhou ({exc}); usando resumo extrativo.", file=sys.stderr)
            return None
    return None


def choose_summary(title: str, article_text: str, lang: str, max_chars: int, max_sentences: int) -> Tuple[str, str]:
    if len(article_text) >= 400 and (os.getenv("ANTHROPIC_API_KEY") or os.getenv("GEMINI_API_KEY")):
        ai_summary = llm_summarize(title, article_text, lang)
        if ai_summary:
            return ai_summary, "ai"
    summary = build_extractive_summary(title, article_text, max_chars=max_chars, max_sentences=max_sentences)
    return summary, "extractive"


def translate_text(text: str, lang: str) -> str:
    if not text or lang == "pt":
        return text
    try:
        translator = GoogleTranslator(source="auto", target="pt")
        blocks = []
        current = ""
        for sentence in split_sentences(text):
            candidate = f"{current} {sentence}".strip()
            if len(candidate) > 4500:
                if current:
                    blocks.append(current)
                    current = sentence
                else:
                    blocks.append(sentence[:4500].strip())
                    current = sentence[4500:].strip()
            else:
                current = candidate
        if current:
            blocks.append(current)
        translated = []
        for block in blocks:
            translated.append(translator.translate(block))
        return normalize_space(" ".join(translated))
    except Exception as exc:
        print(f"Aviso: tradução falhou: {exc}, mantendo o texto original.", file=sys.stderr)
        return text


def build_footer(source_name: str, lang: str, summary_source: str, translation_ok: bool) -> str:
    if summary_source == "ai":
        return "resumo por IA"
    if lang == "pt":
        return "trechos da matéria"
    if translation_ok:
        return "trechos da matéria traduzidos para PT-BR"
    return "trechos da matéria (original)"


def fetch_article(url: str) -> Tuple[str, Optional[str]]:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
    response.raise_for_status()
    html = response.text
    metadata = trafilatura.extract_metadata(html)
    image_url = None
    if metadata is not None:
        image_url = getattr(metadata, "image", None) or getattr(metadata, "image_url", None)
    text = trafilatura.extract(
        html,
        output_format="txt",
        include_comments=False,
        include_tables=False,
        include_formatting=False,
        favor_precision=True,
        fast=True,
    )
    if not text or len(text) < 300:
        # fallback: use the best available feed text payload
        return html_to_text(html) or "", image_url
    return text, image_url


def entry_watch_flag(entry: Any, watch_terms: Iterable[str]) -> bool:
    if not watch_terms:
        return False
    haystack = " ".join(filter(None, [get_entry_value(entry, "title"), safe_extract_text(entry)]))
    if not haystack:
        return False
    lowered = haystack.lower()
    for term in watch_terms:
        if term and term.lower() in lowered:
            return True
    return False


def channel_entry_candidates(channel_name: str, channel_cfg: Dict[str, Any], state_ids: Optional[List[str]] = None) -> List[Any]:
    if state_ids is None:
        state_ids = read_state(channel_name)
    max_hours = int(os.getenv("MAX_AGE_HOURS", "30"))
    max_per_feed = int(os.getenv("MAX_PER_FEED", "2"))
    watch_terms = channel_cfg.get("watch", [])
    candidates: List[Any] = []
    for feed in channel_cfg.get("feeds", []):
        feed_url = feed.get("url")
        print(f"[feed] {channel_name} :: {feed.get('name')} :: {feed_url}")
        try:
            response = requests.get(feed_url, headers={"User-Agent": USER_AGENT}, timeout=20)
            response.raise_for_status()
        except Exception as exc:
            print(f"Aviso: falha ao baixar feed {feed.get('name')}: {exc}", file=sys.stderr)
            continue
        feed_data = feedparser.parse(response.text)
        if not getattr(feed_data, "entries", None):
            continue
        ordered = sorted(feed_data.entries, key=lambda entry: get_entry_published_at(entry) or datetime.min.replace(tzinfo=timezone.utc))
        watch_hits = []
        regular = []
        for entry in ordered:
            entry_id = get_entry_id(entry)
            if entry_id in state_ids:
                continue
            dt = get_entry_published_at(entry)
            if dt is not None:
                age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
                if age_hours > max_hours:
                    continue
            if entry_watch_flag(entry, watch_terms):
                watch_hits.append(entry)
            else:
                regular.append(entry)
        selected = watch_hits + regular[: max(0, max_per_feed - len(watch_hits))]
        if len(watch_hits) > max_per_feed:
            selected = watch_hits
        for entry in selected:
            candidates.append({"channel": channel_name, "feed": feed, "entry": entry})
    return candidates


def build_payload(channel: str, channel_cfg: Dict[str, Any], entry_data: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    feed = entry_data["feed"]
    entry = entry_data["entry"]
    feed_name = feed.get("name")
    source_lang = str(feed.get("lang", "en")).lower()
    title = normalize_space(str(get_entry_value(entry, "title") or "Sem título"))
    entry_id = get_entry_id(entry) or f"{feed_name}:{title}"
    url = get_entry_value(entry, "link")
    text = safe_extract_text(entry)
    article_text, image_url = fetch_article(url) if url else (text, None)
    if len(article_text) < 300 and text:
        article_text = max([article_text, text], key=len)
    if len(article_text) < 300:
        article_text = title
    summary_chars = int(os.getenv("SUMMARY_CHARS", "900"))
    summary_sentences = int(os.getenv("SUMMARY_SENTENCES", "7"))
    summary, summary_source = choose_summary(title, article_text, source_lang, summary_chars, summary_sentences)
    translation_ok = False
    if source_lang != "pt" and summary_source != "ai":
        translated_title = translate_text(title, source_lang)
        translated_summary = translate_text(summary, source_lang)
        title = translated_title
        summary = translated_summary
        translation_ok = True
    elif source_lang != "pt" and summary_source == "ai":
        title = title
    if source_lang == "pt":
        title = title
    feed_prefix = str(feed.get("emoji") or channel_cfg.get("emoji") or "")
    if entry_watch_flag(entry, channel_cfg.get("watch", [])):
        title = f"🚨 {feed_prefix} {title}".strip()
    elif feed_prefix:
        title = f"{feed_prefix} {title}".strip()
    footer = build_footer(feed_name, source_lang, summary_source, translation_ok)
    payload = {
        "embeds": [{
            "title": title,
            "url": url,
            "description": summary[:2000],
            "color": int(feed.get("color") or channel_cfg.get("color") or 0),
            "footer": {"text": f"Fonte: {feed_name} • {footer}"},
        }]
    }
    if image_url:
        payload["embeds"][0]["image"] = {"url": image_url}
    if "username" in payload:
        payload.pop("username")
    return {"channel": channel, "entry_id": entry_id, "payload": payload}


def post_payload(channel: str, channel_cfg: Dict[str, Any], payload: Dict[str, Any], webhook_url: str) -> bool:
    attempts = 0
    while attempts < 4:
        try:
            response = requests.post(webhook_url, json=payload["payload"], headers={"User-Agent": USER_AGENT}, timeout=20)
            if response.status_code in (200, 204):
                return True
            if response.status_code == 429:
                retry_after = min(30, int(response.headers.get("Retry-After", "1")))
                print(f"Aviso: rate limit do Discord em {channel}. Esperando {retry_after}s antes de tentar novamente.", file=sys.stderr)
                time.sleep(retry_after)
                attempts += 1
                continue
            raise RuntimeError(f"Discord respondeu {response.status_code}: {response.text[:200]}")
        except Exception as exc:
            if attempts >= 3:
                print(f"Erro ao enviar embed para {channel}: {exc}", file=sys.stderr)
                return False
            time.sleep(1 + attempts * 2)
            attempts += 1
    return False


def process_channel(channel: str, dry_run: bool = False) -> bool:
    config = load_channel_config()
    channel_cfg = config.get(channel)
    if not channel_cfg:
        raise KeyError(f"Canal desconhecido: {channel}")
    if dry_run:
        for item in channel_entry_candidates(channel, channel_cfg):
            payload = build_payload(channel, channel_cfg, item, dry_run=True)
            encoded = json.dumps(payload["payload"], ensure_ascii=False).encode("utf-8")
            sys.stdout.buffer.write(encoded + b"\n")
        return True
    webhook_var = channel_cfg.get("webhook_env")
    webhook_url = os.getenv(webhook_var)
    if not webhook_url:
        print(f"Canal {channel} ignorado: variável {webhook_var} não configurada.", file=sys.stderr)
        return True
    state_ids = read_state(channel)
    failed = False
    for item in channel_entry_candidates(channel, channel_cfg, state_ids):
        payload = build_payload(channel, channel_cfg, item, dry_run=False)
        if not post_payload(channel, channel_cfg, payload, webhook_url):
            failed = True
            continue
        entry_id = payload["entry_id"]
        state_ids.append(entry_id)
        state_ids = list(dict.fromkeys(state_ids))[-600:]
        write_state(channel, state_ids)
    return not failed


def list_channels() -> List[str]:
    return sorted(load_channel_config().keys())


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Bot de notícias para Discord.")
    parser.add_argument("channels", nargs="*", help="Canais a processar. Se omitido, processa todos.")
    parser.add_argument("--channel", "-c", dest="channel", action="append", help="Canal a processar. Pode ser informado múltiplas vezes.")
    parser.add_argument("--dry-run", action="store_true", help="Mostra o payload JSON de cada item sem enviar ou gravar estado.")
    args = parser.parse_args(argv)
    config = load_channel_config()
    requested = list(args.channel or [])
    requested.extend(args.channels)
    channels = requested or sorted(config.keys())
    seen = set()
    ordered = []
    for channel in channels:
        if channel in seen:
            continue
        seen.add(channel)
        ordered.append(channel)
    unknown = [name for name in ordered if name not in config]
    if unknown:
        print(f"Canal desconhecido: {', '.join(unknown)}", file=sys.stderr)
        return 2
    failed = False
    for channel in ordered:
        try:
            result = process_channel(channel, dry_run=args.dry_run)
            if not result:
                failed = True
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
