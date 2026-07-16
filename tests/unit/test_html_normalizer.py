"""Testes da normalização de HTML de e-mail."""

from app.infrastructure.gmail.html_normalizer import html_to_text, normalize_plain_text


def test_html_to_text_removes_active_content_and_preserves_blocks() -> None:
    html = """
    <html><head><style>.hidden{display:none}</style><script>alert('x')</script></head>
    <body><h1>Título</h1><p>Primeiro&nbsp;parágrafo.</p><div>Segundo<br>linha</div></body>
    </html>
    """

    result = html_to_text(html)

    assert "alert" not in result
    assert "display:none" not in result
    assert "Título" in result
    assert "Primeiro parágrafo." in result
    assert "Segundo" in result
    assert "linha" in result


def test_normalize_plain_text_collapses_spaces_and_excess_blank_lines() -> None:
    value = "  primeira   linha  \r\n\r\n\r\n segunda\tlinha  "
    assert normalize_plain_text(value) == "primeira linha\n\nsegunda linha"


def test_html_to_text_tolerates_malformed_html() -> None:
    assert "Conteúdo" in html_to_text("<div><b>Conteúdo")
