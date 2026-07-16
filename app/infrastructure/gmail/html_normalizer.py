"""Normalização segura de HTML de e-mail para texto simples."""

from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser

_BLOCK_TAGS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "br",
    "div",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "td",
    "th",
    "tr",
    "ul",
}
_IGNORED_TAGS = {"script", "style", "noscript", "svg"}


class _HTMLTextExtractor(HTMLParser):
    """Extrai dados visíveis sem executar ou interpretar conteúdo ativo."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        del attrs
        normalized = tag.lower()
        if normalized in _IGNORED_TAGS:
            self._ignored_depth += 1
        elif normalized in _BLOCK_TAGS and self._ignored_depth == 0:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in _IGNORED_TAGS and self._ignored_depth > 0:
            self._ignored_depth -= 1
        elif normalized in _BLOCK_TAGS and self._ignored_depth == 0:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth == 0:
            self._chunks.append(data)

    def text(self) -> str:
        """Retorna texto normalizado com parágrafos preservados."""

        return normalize_plain_text("".join(self._chunks))


def normalize_plain_text(value: str) -> str:
    """Normaliza espaços sem colapsar completamente as quebras de parágrafo."""

    value = unescape(value).replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[\t\f\v ]+", " ", line).strip() for line in value.split("\n")]
    compact = "\n".join(lines)
    compact = re.sub(r"\n{3,}", "\n\n", compact)
    return compact.strip()


def html_to_text(value: str) -> str:
    """Converte HTML, inclusive malformado, em texto sem conteúdo ativo."""

    parser = _HTMLTextExtractor()
    try:
        parser.feed(value)
        parser.close()
    except Exception:
        # HTMLParser é tolerante; o fallback ainda remove tags de forma conservadora.
        return normalize_plain_text(re.sub(r"<[^>]+>", " ", value))
    return parser.text()
