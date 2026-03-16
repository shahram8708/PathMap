"""Markdown rendering and sanitization utilities for PathMap."""

import re
from typing import List

import bleach
import markdown
from markupsafe import Markup


MARKDOWN_EXTENSIONS: List[str] = [
	"extra",
	"codehilite",
	"fenced_code",
	"toc",
	"nl2br",
	"sane_lists",
	"smarty",
]

EXTENSION_CONFIGS = {
	"codehilite": {"guess_lang": False, "css_class": "highlight", "linenums": False},
	"toc": {"permalink": True},
}

ALLOWED_TAGS = [
	"p",
	"br",
	"strong",
	"em",
	"b",
	"i",
	"u",
	"s",
	"del",
	"ins",
	"h1",
	"h2",
	"h3",
	"h4",
	"h5",
	"h6",
	"ul",
	"ol",
	"li",
	"blockquote",
	"pre",
	"code",
	"table",
	"thead",
	"tbody",
	"tr",
	"th",
	"td",
	"a",
	"img",
	"hr",
	"div",
	"span",
	"figure",
	"figcaption",
]

ALLOWED_ATTRIBUTES = {
	"a": ["href", "title", "target"],
	"img": ["src", "alt", "title", "width", "height"],
	"code": ["class"],
	"pre": ["class"],
	"div": ["class"],
	"span": ["class"],
	"table": ["class", "id"],
	"th": ["class", "id"],
	"td": ["class", "id"],
	"h1": ["id"],
	"h2": ["id"],
	"h3": ["id"],
	"h4": ["id"],
	"h5": ["id"],
	"h6": ["id"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


MARKDOWN_PATTERNS = [
	re.compile(r"^\s{0,3}#{1,6}\s", re.MULTILINE),
	re.compile(r"(\*\*.+?\*\*|__.+?__)", re.DOTALL),
	re.compile(r"(?<!\w)(\*[^*]+\*|_[^_]+_)", re.DOTALL),
	re.compile(r"^\s{0,3}[-+*]\s", re.MULTILINE),
	re.compile(r"^\s{0,3}\d+\.\s", re.MULTILINE),
	re.compile(r"`{1,3}[^`]+`{1,3}", re.DOTALL),
	re.compile(r"^\s{0,3}>\s", re.MULTILINE),
	re.compile(r"\[[^\]]+\]\([^)]+\)"),
	re.compile(r"^\s*(---|===)\s*$", re.MULTILINE),
	re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE),
]

HTML_START_PATTERN = re.compile(r"^\s*<\s*(p|h[1-6]|ul|ol|div|table|blockquote|pre)\b", re.IGNORECASE)
CLASS_PATTERN = re.compile(r"class\s*=\s*\"([^\"]*)\"", re.IGNORECASE)
STYLE_PATTERN = re.compile(r"style\s*=\s*\"([^\"]*)\"", re.IGNORECASE)


def is_markdown(text: str) -> bool:
	"""Return True if text appears to contain Markdown syntax."""

	if not text or not isinstance(text, str):
		return False
	return any(pattern.search(text) for pattern in MARKDOWN_PATTERNS)


def _markdown_to_html(raw: str) -> str:
	return markdown.markdown(
		raw,
		extensions=MARKDOWN_EXTENSIONS,
		extension_configs=EXTENSION_CONFIGS,
		output_format="html5",
	)


def convert_markdown(text: str) -> str:
	"""Convert Markdown to sanitized HTML."""

	if not text:
		return ""
	cleaned = text.strip()
	if not cleaned:
		return ""
	try:
		html = _markdown_to_html(cleaned)
	except Exception:
		safe_text = bleach.clean(cleaned, tags=[], attributes={}, strip=True)
		parts = [seg.strip() for seg in re.split(r"\n{2,}", safe_text) if seg.strip()]
		return "".join(f"<p>{seg.replace('\n', '<br>')}</p>" for seg in parts)
	return bleach.clean(
		html,
		tags=ALLOWED_TAGS,
		attributes=ALLOWED_ATTRIBUTES,
		protocols=ALLOWED_PROTOCOLS,
		strip=True,
	)


def convert_markdown_unsafe(text: str) -> str:
	"""Convert Markdown to HTML without sanitization (trusted sources only)."""

	if not text:
		return ""
	cleaned = text.strip()
	if not cleaned:
		return ""
	try:
		return _markdown_to_html(cleaned)
	except Exception:
		parts = [seg.strip() for seg in re.split(r"\n{2,}", cleaned) if seg.strip()]
		return "".join(f"<p>{seg.replace('\n', '<br>')}</p>" for seg in parts)


def render_content(text: str, force_markdown: bool = False) -> str:
	"""Render text as Markdown when present; otherwise wrap plain text in paragraphs."""

	if not text:
		return ""
	cleaned = text.strip()
	if not cleaned:
		return ""
	if force_markdown or is_markdown(cleaned):
		return convert_markdown(cleaned)

	paragraphs = [segment.strip() for segment in re.split(r"\n{2,}", cleaned) if segment.strip()]
	if not paragraphs:
		return ""

	rendered_parts = []
	for segment in paragraphs:
		safe_text = bleach.clean(segment, tags=[], attributes={}, strip=True)
		safe_text = safe_text.replace("\n", "<br>")
		rendered_parts.append(f"<p>{safe_text}</p>")
	return "".join(rendered_parts)


def render_content_unsafe(text: str, force_markdown: bool = False) -> str:
	"""Render text without sanitization; use only for trusted admin-authored content."""

	if not text:
		return ""
	cleaned = text.strip()
	if not cleaned:
		return ""
	if force_markdown or is_markdown(cleaned):
		return convert_markdown_unsafe(cleaned)

	paragraphs = [segment.strip() for segment in re.split(r"\n{2,}", cleaned) if segment.strip()]
	if not paragraphs:
		return ""
	rendered_parts = []
	for segment in paragraphs:
		rendered_parts.append(f"<p>{segment.replace('\n', '<br>')}</p>")
	return "".join(rendered_parts)


def _append_class_attr(attrs: str, classes: str) -> str:
	attrs = attrs or ""
	attrs = f" {attrs.strip()}" if attrs.strip() else ""
	if CLASS_PATTERN.search(attrs):
		return CLASS_PATTERN.sub(lambda m: f'class="{m.group(1)} {classes}"', attrs, count=1)
	return f"{attrs} class=\"{classes}\""


def _append_style_attr(attrs: str, style: str) -> str:
	attrs = attrs or ""
	attrs = f" {attrs.strip()}" if attrs.strip() else ""
	if STYLE_PATTERN.search(attrs):
		return STYLE_PATTERN.sub(lambda m: f'style="{m.group(1)} {style}"', attrs, count=1)
	return f"{attrs} style=\"{style}\""


def _add_classes(html: str, tag: str, classes: str, extra_style: str | None = None) -> str:
	pattern = re.compile(rf"<{tag}([^>]*)>", re.IGNORECASE)

	def repl(match: re.Match[str]) -> str:
		attrs = match.group(1) or ""
		attrs = _append_class_attr(attrs, classes)
		if extra_style:
			attrs = _append_style_attr(attrs, extra_style)
		return f"<{tag}{attrs}>"

	return pattern.sub(repl, html)


def apply_bootstrap_classes(html_string: str) -> str:
	"""Apply Bootstrap-friendly classes to rendered Markdown HTML."""

	if not html_string:
		return ""

	html = html_string
	html = _add_classes(html, "table", "table table-bordered table-hover")
	html = _add_classes(html, "blockquote", "blockquote border-start border-4 ps-3 text-muted")
	html = _add_classes(html, "pre", "bg-dark text-light p-3 rounded", "overflow-x: auto;")
	html = _add_classes(html, "ul", "mb-3")
	html = _add_classes(html, "ol", "mb-3")
	html = _add_classes(html, "img", "img-fluid rounded")
	html = _add_classes(html, "h2", "mt-4 mb-3", "color: #1A5276;")
	html = _add_classes(html, "h3", "mt-3 mb-2", "color: #1A5276;")
	html = _add_classes(html, "h4", "mt-3 mb-2")
	html = _add_classes(html, "h5", "mt-2 mb-2")
	html = _add_classes(html, "h6", "mt-2 mb-2")
	html = _add_classes(html, "hr", "my-4")

	code_pattern = re.compile(r"<code([^>]*)>", re.IGNORECASE)

	def code_repl(match: re.Match[str]) -> str:
		attrs = _append_class_attr(match.group(1) or "", "bg-light px-1 rounded")
		attrs = _append_style_attr(attrs, "font-family: monospace; font-size: 0.9em; color: #c7254e;")
		return f"<code{attrs}>"

	html = code_pattern.sub(code_repl, html)

	link_pattern = re.compile(r"<a([^>]*)href=\"([^\"]+)\"([^>]*)>", re.IGNORECASE)

	def link_repl(match: re.Match[str]) -> str:
		before, href, after = match.group(1) or "", match.group(2) or "", match.group(3) or ""
		attrs = f"{before} href=\"{href}\"{after}"
		attrs = _append_class_attr(attrs, "text-decoration-underline")
		if href.lower().startswith("http"):
			if not re.search(r"target=", attrs, re.IGNORECASE):
				attrs += " target=\"_blank\""
			if not re.search(r"rel=", attrs, re.IGNORECASE):
				attrs += " rel=\"noopener noreferrer\""
		return f"<a{attrs}>"

	html = link_pattern.sub(link_repl, html)

	return html


def markdown_to_html(text: str, trusted_source: bool = False, force_markdown: bool = False) -> Markup:
	"""Convert text to HTML with Markdown support, styling, and optional sanitization."""

	if not text:
		return Markup("")

	if HTML_START_PATTERN.match(text):
		return Markup(text)

	if trusted_source:
		rendered = render_content_unsafe(text, force_markdown=force_markdown)
	else:
		rendered = render_content(text, force_markdown=force_markdown)

	rendered = apply_bootstrap_classes(rendered)

	return Markup(rendered)


if __name__ == "__main__":
	# Basic self-tests for quick verification
	def _print_result(name: str, condition: bool, output: str | None = None) -> None:
		status = "PASS" if condition else "FAIL"
		print(f"{name}: {status}")
		if output is not None:
			print(output)

	plain_text = "This is plain text with zero markdown syntax."
	_print_result("Test 1 - Plain text detection", not is_markdown(plain_text))

	md_text = "## Heading\nSome **bold** text and:\n- item one"
	_print_result("Test 2 - Markdown detection", is_markdown(md_text))

	md_full = """## Title\n\nHere is a **bold** word, an _italic_ word, and a list:\n\n- First\n- Second\n\n`code` snippet."""
	html_output = markdown_to_html(md_full)
	_print_result(
		"Test 3 - Markdown conversion",
		all(token in html_output for token in ["<h2", "<strong>", "<ul>"]),
		str(html_output),
	)

	table_html = apply_bootstrap_classes("<table><tr><td>Cell</td></tr></table>")
	_print_result("Test 4 - Bootstrap classes on table", "table table-bordered table-hover" in table_html, table_html)

	xss_attempt = "<script>alert('xss')</script> **bold**"
	sanitized = markdown_to_html(xss_attempt)
	_print_result("Test 5 - XSS sanitization", "<script" not in sanitized, str(sanitized))

	paragraphs = "First paragraph.\n\nSecond line."
	rendered_plain = render_content(paragraphs)
	_print_result(
		"Test 6 - Plain text paragraphs",
		"<p>First paragraph." in rendered_plain and "<p>Second line." in rendered_plain,
		rendered_plain,
	)

