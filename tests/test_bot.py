import json

from bot import (
    build_extractive_summary,
    build_payload,
    channel_entry_candidates,
    entry_watch_flag,
    html_to_text,
    read_state,
    write_state,
)


SAMPLE_HTML = """
<html>
  <body>
    <p>We tested <a href='https://example.com'>this link</a> and it kept the text.</p>
    <script>do not keep me</script>
    <style>hide me</style>
  </body>
</html>
"""

SAMPLE_TEXT = (
    "A zero-day issue was disclosed by a vendor after exploitation in the wild. "
    "Security teams began patching vulnerable endpoints across a large customer base. "
    "The company published a fix and urged administrators to update immediately. "
    "The update includes migration guidance and a patch note for affected versions. "
    "The advisory explains the blast radius, impact and remediation steps for all customers."
)


def test_html_to_text_keeps_link_text():
    assert "this link" in html_to_text(SAMPLE_HTML)
    assert "do not keep me" not in html_to_text(SAMPLE_HTML)


def test_build_extractive_summary_filters_boilerplate():
    summary = build_extractive_summary("Security advisory update", SAMPLE_TEXT, max_chars=300, max_sentences=6)
    assert len(summary) <= 300
    assert "follow us" not in summary.lower()
    assert "click here" not in summary.lower()


def test_entry_watch_flag_detects_term():
    entry = {"title": "ShinyHunters alert", "content": [{"value": "Some details here"}]}
    assert entry_watch_flag(entry, ["ShinyHunters"])


def test_channel_candidates_are_deduplicated_by_state():
    entry = {"id": "abc123", "title": "Example", "link": "https://example.com/abc", "published": "2024-01-01T00:00:00Z"}
    assert channel_entry_candidates("cyber", {"watch": [], "feeds": []}) == []
    write_state("cyber", ["abc123"])
    try:
        assert read_state("cyber") == ["abc123"]
    finally:
        write_state("cyber", [])


def test_payload_omits_username_key():
    channel_cfg = {"emoji": "🛡️", "color": 123, "watch": []}
    payload = build_payload("cyber", channel_cfg, {"feed": {"name": "Example", "color": 123}, "entry": {"title": "Test title", "link": "https://example.com", "content": [{"value": SAMPLE_TEXT}]}})
    assert "username" not in json.dumps(payload["payload"])


def test_watch_prefix_added_for_triggered_terms():
    channel_cfg = {"emoji": "🚨", "color": 123, "watch": ["ShinyHunters"]}
    entry = {"title": "ShinyHunters breach disclosed", "link": "https://example.com", "content": [{"value": SAMPLE_TEXT}]}
    payload = build_payload("cyber", channel_cfg, {"feed": {"name": "Example", "lang": "en", "color": 123}, "entry": entry})
    assert payload["payload"]["embeds"][0]["title"].startswith("🚨")
