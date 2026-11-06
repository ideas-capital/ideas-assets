from pwass.ai import documents, openrouter


def test_payload_with_web_search_and_images():
    msg = openrouter.user_message("analise", ["data:image/png;base64,AAAA"])
    assert msg["content"][1]["type"] == "image_url"
    p = openrouter.build_payload("anthropic/claude-haiku-5.5", [msg], web_search=True)
    assert p["plugins"] == [{"id": "web"}]
    assert "plugins" not in openrouter.build_payload("x/y", [msg])


def test_chat_requires_key():
    try:
        openrouter.chat("", "x/y", [])
    except openrouter.OpenRouterError as e:
        assert "chave" in str(e)
    else:
        raise AssertionError("deveria exigir chave")


def test_html_to_text_skips_scripts_and_xbrl_header():
    html = ("<html><head><title>x</title></head><body><ix:header>oculto</ix:header>"
            "<script>var a=1</script><p>Receita cresceu&nbsp;12%</p><table><tr><td>A</td><td>B</td></tr></table></body></html>")
    t = documents.html_to_text(html)
    assert "Receita cresceu 12%" in t and "oculto" not in t and "var a" not in t and "A | B" in t


def test_truncate():
    t, cut = documents.truncate("a" * 10, 5)
    assert cut and t.startswith("aaaaa")
