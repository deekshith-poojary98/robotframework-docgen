"""Matrix tests for Markdown constructs rendered by docgen."""

from robotframework_docgen.parser import RobotFrameworkDocParser


def _html(md: str) -> str:
    return RobotFrameworkDocParser()._parse_docstring(md)[0]


class TestMarkdownFeatureMatrix:
    def test_emphasis_and_code(self):
        html = _html("**bold** *italic* ***both*** ``code``")
        assert "<strong>bold</strong>" in html
        assert "<em>italic</em>" in html
        assert "<code>code</code>" in html

    def test_headings_and_toc_marker(self):
        html = _html("%TOC%\n\n## Alpha\n\n### Beta\n\n#### Gamma\n\nText.")
        assert 'id="alpha"' in html or ">Alpha</h" in html
        assert 'id="beta"' in html or ">Beta</h" in html
        # toc extension emits a TOC list when marker is present; depth must
        # include ### / #### after baselevel shifting.
        assert '<div class="toc">' in html
        assert 'href="#alpha"' in html
        assert 'href="#beta"' in html
        assert 'href="#gamma"' in html

    def test_links_images_and_bare_url(self):
        html = _html(
            "See [RF](https://robotframework.org/) and https://example.com/docs.\n\n"
            "![logo](https://example.com/img/rf_favicon.png)"
        )
        assert 'href="https://robotframework.org/"' in html
        assert 'href="https://example.com/docs"' in html
        assert 'src="https://example.com/img/rf_favicon.png"' in html
        assert "<code>rf_favicon</code>" not in html

    def test_lists_tables_quote_hr(self):
        html = _html(
            """\
- one
    - nested

1. first

| A | B |
|---|---|
| 1 | 2 |

> quoted

---
"""
        )
        assert html.count("<ul>") >= 2
        assert "<ol>" in html
        assert "<table>" in html and "<th>A</th>" in html
        assert "<blockquote>" in html
        assert "<hr" in html

    def test_admonitions(self):
        html = _html(
            '!!! note "Title"\n    Body.\n\n!!! warning\n    Careful.\n\n!!! danger\n    Stop.'
        )
        assert 'class="admonition note"' in html
        assert 'class="admonition warning"' in html
        assert 'class="admonition danger"' in html
        assert "Title" in html

    def test_definition_list(self):
        html = _html("Freeze\n:   Hold time.\n\nAdvance\n:   Move clock.")
        assert "<dl>" in html and "<dt>Freeze</dt>" in html
        assert "Hold time." in html and "<dd>" in html

    def test_footnotes(self):
        html = _html("See note.[^x]\n\n[^x]: Footnote body.")
        assert "footnote" in html
        assert "Footnote body" in html

    def test_abbreviations(self):
        html = _html("*[HTML]: HyperText Markup Language\n\nWrite HTML docs.")
        assert '<abbr title="HyperText Markup Language">HTML</abbr>' in html

    def test_attr_list_heading_id(self):
        html = _html("## Section {: #my-section }\n\nBody.")
        assert 'id="my-section"' in html

    def test_md_in_html(self):
        html = _html('<div markdown="1">\n**inside**\n</div>')
        assert "<strong>inside</strong>" in html

    def test_fenced_robot_still_custom(self):
        html = _html(
            "Intro.\n\n```robotframework\n*** Test Cases ***\nDemo\n    Log    hi\n```\n"
        )
        assert 'class="language-robot"' in html
        assert "Demo" in html and "Log" in html

    def test_kitchen_sink_extended_keyword(self):
        info = RobotFrameworkDocParser().parse_file(
            "sample_libs/DocFormatKitchenSink.py"
        )
        kw = next(k for k in info.keywords if k.name == "Render Extended Markdown")
        d = kw.description
        assert "admonition note" in d
        assert "admonition warning" in d
        assert "<dl>" in d
        assert "<abbr" in d
        assert "footnote" in d
        assert 'id="extended-md-anchor"' in d
        assert "<strong>Bold</strong> inside" in d
