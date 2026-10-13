"""P1 completeness: cross-links, importing section, arg/return docs."""

import re
from pathlib import Path

import pytest

from robotframework_docgen.generator import DocumentationGenerator
from robotframework_docgen.parser import (
    InitInfo,
    KeywordInfo,
    LibraryInfo,
    RobotFrameworkDocParser,
)


def _plain(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html or "")


def _library_with_refs() -> LibraryInfo:
    return LibraryInfo(
        name="LinkLib",
        version="1.0.0",
        scope="GLOBAL",
        description="<p>See [Reset Time] and [Freeze Time] for control.</p>",
        keywords=[
            KeywordInfo(
                name="Freeze Time",
                description="<p>Freeze clock. Related: [Reset Time].</p>",
                example="",
                parameters=[("at", "str")],
                return_type="str",
                line_number=1,
                parameter_docs={"at": "<p>Destination datetime.</p>"},
                return_doc="<p>The simulated datetime.</p>",
            ),
            KeywordInfo(
                name="Reset Time",
                description="<p>Restore real time.</p>",
                example="",
                parameters=[],
                return_type="None",
                line_number=2,
            ),
            KeywordInfo(
                name="Advance Time",
                description=(
                    "<p>Move forward.</p>"
                    "<div class=\"code-block\"><pre class=\"language-robotframework\">"
                    "[Reset Time] should stay plain inside code"
                    "</pre></div>"
                    "<p>Also see [Unknown Keyword] and [markdown](https://example.com).</p>"
                ),
                example="",
                parameters=[
                    ("duration", "str"),
                    ("keep_time", "bool"),
                ],
                return_type="str",
                line_number=3,
                parameter_defaults={"keep_time": "True"},
                parameter_docs={
                    "duration": "<p>Amount to advance.</p>",
                    "keep_time": "<p>Keep time-of-day when <code>True</code>.</p>",
                },
                return_doc="<p>New simulated time.</p>",
            ),
        ],
        source_type="LIBRARY",
        inits=[
            InitInfo(
                description="<p>Initialize the library.</p>",
                parameters=[("auto_reset", "bool")],
                parameter_defaults={"auto_reset": "True"},
                parameter_docs={
                    "auto_reset": "<p>When <code>True</code>, reset after each test.</p>"
                },
            )
        ],
    )


class TestKeywordCrossLinks:
    def test_links_known_keyword_references(self):
        html = DocumentationGenerator(_library_with_refs()).generate_html()
        assert 'href="#reset-time"' in html
        assert 'href="#freeze-time"' in html
        assert 'class="kw-ref"' in html
        # Linked label uses canonical keyword name.
        assert ">Reset Time</a>" in html

    def test_unresolved_and_markdown_links_untouched(self):
        html = DocumentationGenerator(_library_with_refs()).generate_html()
        assert "[Unknown Keyword]" in html
        # Markdown-style [text](url) must not become a keyword link.
        assert 'class="kw-ref" href="#markdown"' not in html
        assert "[markdown](https://example.com)" in html

    def test_references_inside_code_blocks_are_not_linked(self):
        gen = DocumentationGenerator(_library_with_refs())
        linked = gen._link_keyword_references(
            '<pre class="language-robotframework">[Reset Time] stays</pre>'
            "<p>Outside [Reset Time]</p>"
        )
        assert "<pre" in linked and "[Reset Time] stays" in linked
        assert linked.count('href="#reset-time"') == 1

    def test_space_and_underscore_name_variants_resolve(self):
        gen = DocumentationGenerator(_library_with_refs())
        assert 'href="#reset-time"' in gen._link_keyword_references("[reset_time]")
        assert 'href="#freeze-time"' in gen._link_keyword_references("[freeze time]")

    def test_ambiguous_normalized_names_are_not_linked(self):
        info = LibraryInfo(
            name="Ambiguous",
            version="1",
            scope="GLOBAL",
            description="<p>See [Foo Bar].</p>",
            keywords=[
                KeywordInfo(
                    name="Foo Bar",
                    description="",
                    example="",
                    parameters=[],
                    return_type="None",
                    line_number=1,
                ),
                KeywordInfo(
                    name="Foo_Bar",
                    description="",
                    example="",
                    parameters=[],
                    return_type="None",
                    line_number=2,
                ),
            ],
        )
        # Both names normalize identically → do not guess.
        assert DocumentationGenerator.normalize_keyword_key("Foo Bar") == (
            DocumentationGenerator.normalize_keyword_key("Foo_Bar")
        )
        html = DocumentationGenerator(info).generate_html()
        assert "[Foo Bar]" in html
        assert 'href="#foo-bar"' not in html or html.count('class="kw-ref"') == 0


class TestImportingSection:
    def test_library_importing_renders_init_args(self):
        html = DocumentationGenerator(
            _library_with_refs(), RobotFrameworkDocParser()
        ).generate_html()
        assert 'id="importing"' in html
        assert "auto_reset" in html
        assert "default: True" in html
        assert "reset after each test" in _plain(html)
        assert 'href="#importing"' in html
        assert 'class="import-statement"' not in html

    def test_resource_has_no_importing_section(self):
        info = LibraryInfo(
            name="helpers",
            version="",
            scope="GLOBAL",
            description="<p>Helpers</p>",
            keywords=[
                KeywordInfo(
                    name="Do",
                    description="x",
                    example="",
                    parameters=[],
                    return_type="None",
                    line_number=1,
                )
            ],
            source_type="RESOURCE",
        )
        html = DocumentationGenerator(info).generate_html()
        assert 'id="importing"' not in html
        assert "{{IMPORTING" not in html

    def test_library_without_init_metadata_hides_importing(self):
        info = LibraryInfo(
            name="BareLib",
            version="1",
            scope="GLOBAL",
            description="<p>Bare</p>",
            keywords=[
                KeywordInfo(
                    name="Ping",
                    description="x",
                    example="",
                    parameters=[],
                    return_type="None",
                    line_number=1,
                )
            ],
            source_type="LIBRARY",
            inits=[],
        )
        html = DocumentationGenerator(info).generate_html()
        assert 'id="importing"' not in html
        assert "Constructor arguments were not available" not in html
        assert 'href="#importing"' not in html


class TestArgumentAndReturnDocs:
    def test_argument_docs_defaults_and_required_badges(self):
        html = DocumentationGenerator(_library_with_refs()).generate_html()
        assert "Destination datetime." in _plain(html)
        assert "Amount to advance." in _plain(html)
        assert "badge-required" in html
        assert "badge-default" in html
        assert "default: True" in html

    def test_return_docs_rendered(self):
        html = DocumentationGenerator(_library_with_refs()).generate_html()
        assert "The simulated datetime." in _plain(html)
        assert "New simulated time." in _plain(html)
        assert "<h3>Returns</h3>" in html

    def test_missing_arg_and_return_docs_omitted(self):
        info = LibraryInfo(
            name="Sparse",
            version="1",
            scope="GLOBAL",
            description="",
            keywords=[
                KeywordInfo(
                    name="Bare",
                    description="<p>No extras.</p>",
                    example="",
                    parameters=[("x", "str")],
                    return_type="None",
                    line_number=1,
                )
            ],
            source_type="LIBRARY",
            inits=[],
        )
        html = DocumentationGenerator(info).generate_html()
        assert "badge-required" in html
        assert 'class="argument-doc"' not in html
        assert 'class="return-doc"' not in html


class TestLibdocExtractionIntegration:
    def test_timetravel_extracts_arg_return_and_import_docs(self):
        """End-to-end against TimeTravel when the library is importable (RF 7.5+ docs)."""
        import os
        import sys

        tt_src = Path(
            "/Users/deekshithpoojary/Desktop/Projects/robotframework-timetravel/src"
        )
        tt_site = Path(
            "/Users/deekshithpoojary/Desktop/Projects/robotframework-timetravel/"
            ".venv/lib/python3.13/site-packages"
        )
        library = tt_src / "TimeTravel" / "library.py"
        if not library.is_file() or not tt_site.is_dir():
            pytest.skip("TimeTravel library / venv not available")

        sys.path.insert(0, str(tt_src))
        sys.path.insert(0, str(tt_site))
        os.environ.setdefault("PYTHONPATH", f"{tt_src}:{tt_site}")

        try:
            info = RobotFrameworkDocParser().parse_file(str(library))
        except Exception as exc:  # pragma: no cover - env specific
            pytest.skip(f"TimeTravel not importable: {exc}")

        if not info.keywords:
            pytest.skip("TimeTravel produced no keywords in this environment")

        assert info.inits
        assert any(name == "auto_reset" for name, _ in info.inits[0].parameters)
        assert info.inits[0].parameter_defaults.get("auto_reset") == "True"

        freeze = next(kw for kw in info.keywords if kw.name == "Freeze Time")
        # Argument/return prose requires Libdoc metadata (RF 7.5+).
        if freeze.parameter_docs.get("at"):
            assert "datetime" in _plain(freeze.parameter_docs["at"]).lower()
        if freeze.return_doc:
            assert "iso-8601" in _plain(freeze.return_doc).lower()

        html = DocumentationGenerator(
            info, config={"name": "TimeTravel"}
        ).generate_html()
        assert 'id="importing"' in html
        assert "auto_reset" in html
        assert 'href="#reset-time"' in html or 'href="#set-timezone"' in html
        assert "<p>" in info.description
        assert "```" not in info.description


class TestSampleUsagePreference:
    def test_prefers_intro_robot_fence_over_synthetic(self):
        info = LibraryInfo(
            name="DemoLib",
            version="1",
            scope="GLOBAL",
            description=(
                "<p>Intro.</p>"
                '<div class="code-block"><pre class="language-robot">'
                "*** Settings ***\n"
                "Library    DemoLib\n"
                "\n"
                "*** Test Cases ***\n"
                "From Intro\n"
                "    Freeze Time    now\n"
                "</pre></div>"
            ),
            keywords=[
                KeywordInfo(
                    name="Freeze Time",
                    description="<p>Freeze.</p>",
                    example="*** Test Cases ***\nHarvested\n    Freeze Time",
                    parameters=[],
                    return_type="None",
                    line_number=10,
                )
            ],
        )
        html = DocumentationGenerator(info).generate_html()
        assert "From Intro" in html
        assert "# add your keyword calls here" not in html
        # Intro wins over harvested example for the hero Sample Usage card.
        sample = re.search(
            r'hero-card-title">Sample Usage</div>.*?<pre class="language-robot"><code>(.*?)</code></pre>',
            html,
            flags=re.DOTALL,
        )
        assert sample
        sample_plain = _plain(sample.group(1))
        assert "From Intro" in sample_plain
        assert "Harvested" not in sample_plain

    def test_prefers_harvested_example_when_no_intro_fence(self):
        info = LibraryInfo(
            name="DemoLib",
            version="1",
            scope="GLOBAL",
            description="<p>No fence here.</p>",
            keywords=[
                KeywordInfo(
                    name="Freeze Time",
                    description="<p>Freeze the simulated clock.</p>",
                    example="*** Test Cases ***\nHarvested Case\n    Freeze Time",
                    parameters=[],
                    return_type="None",
                    line_number=10,
                    tags=["time", "control"],
                )
            ],
        )
        html = DocumentationGenerator(info).generate_html()
        assert "Harvested Case" in html
        assert "# add your keyword calls here" not in html


class TestSourceLinksAndContentSearch:
    def test_github_source_links_and_tags(self):
        info = LibraryInfo(
            name="DemoLib",
            version="1",
            scope="GLOBAL",
            description="",
            keywords=[
                KeywordInfo(
                    name="Freeze Time",
                    description="<p>Freeze the simulated clock for OTP tests.</p>",
                    example="",
                    parameters=[],
                    return_type="None",
                    line_number=42,
                    tags=["time", "control"],
                )
            ],
            source="src/DemoLib.py",
        )
        html = DocumentationGenerator(
            info,
            config={
                "github_url": "https://github.com/acme/demo",
                "github_branch": "develop",
                "github_file": "src/DemoLib.py",
            },
        ).generate_html()
        assert 'href="https://github.com/acme/demo/blob/develop/src/DemoLib.py#L42"' in html
        assert "Source:L42" in html
        assert "badge-tag" in html
        assert "time" in html
        assert "control" in html

    def test_source_links_can_be_disabled(self):
        info = LibraryInfo(
            name="DemoLib",
            version="1",
            scope="GLOBAL",
            description="",
            keywords=[
                KeywordInfo(
                    name="Freeze Time",
                    description="<p>Freeze.</p>",
                    example="",
                    parameters=[],
                    return_type="None",
                    line_number=42,
                )
            ],
            source="src/DemoLib.py",
        )
        html = DocumentationGenerator(
            info,
            config={
                "github_url": "https://github.com/acme/demo",
                "github_file": "src/DemoLib.py",
                "source_links": False,
            },
        ).generate_html()
        assert "Source:L42" not in html
        assert 'class="kw-source"' not in html
        assert "blob/main/src/DemoLib.py" not in html
        # Repo button still available when github_url is set
        assert 'href="https://github.com/acme/demo"' in html

    def test_source_path_strips_repo_name_prefix_and_uses_git_root(self, tmp_path):
        """Absolute paths outside cwd must resolve relative to the file's git root."""
        repo = tmp_path / "robotframework-timetravel"
        library = repo / "src" / "TimeTravel" / "library.py"
        kw_file = repo / "src" / "TimeTravel" / "keywords" / "clock_control.py"
        kw_file.parent.mkdir(parents=True)
        (repo / ".git").mkdir()
        library.write_text("# library\n")
        kw_file.write_text("# advance_time\n")

        info = LibraryInfo(
            name="TimeTravel",
            version="1",
            scope="GLOBAL",
            description="",
            keywords=[
                KeywordInfo(
                    name="Advance Time",
                    description="<p>Advance.</p>",
                    example="",
                    parameters=[],
                    return_type="None",
                    line_number=163,
                    source=str(kw_file),
                )
            ],
            source=str(library),
        )
        gen = DocumentationGenerator(
            info,
            config={
                "github_url": "https://github.com/acme/robotframework-timetravel",
                "source": str(library),
            },
        )
        # Per-keyword Libdoc source wins over the library entrypoint file.
        assert (
            gen._resolve_github_source_path(str(kw_file))
            == "src/TimeTravel/keywords/clock_control.py"
        )
        assert (
            gen._source_url(163, source_path=str(kw_file))
            == "https://github.com/acme/robotframework-timetravel/blob/main/"
            "src/TimeTravel/keywords/clock_control.py#L163"
        )
        html = gen.generate_html()
        assert (
            'href="https://github.com/acme/robotframework-timetravel/blob/main/'
            'src/TimeTravel/keywords/clock_control.py#L163"'
        ) in html
        assert "library.py#L163" not in html

        # Paths that wrongly include the repo folder name are cleaned up.
        gen2 = DocumentationGenerator(
            LibraryInfo(
                name="TimeTravel",
                version="1",
                scope="GLOBAL",
                description="",
                keywords=info.keywords,
                source="",
            ),
            config={
                "github_url": "https://github.com/acme/robotframework-timetravel",
                "source": "robotframework-timetravel/src/TimeTravel/library.py",
            },
        )
        assert gen2._resolve_github_source_path() == "src/TimeTravel/library.py"

    def test_sidebar_search_includes_docs_and_tags(self):
        info = LibraryInfo(
            name="DemoLib",
            version="1",
            scope="GLOBAL",
            description="",
            keywords=[
                KeywordInfo(
                    name="Freeze Time",
                    description="<p>Freeze the simulated clock for OTP tests.</p>",
                    example="",
                    parameters=[],
                    return_type="None",
                    line_number=1,
                    tags=["time"],
                ),
                KeywordInfo(
                    name="Other",
                    description="<p>Unrelated.</p>",
                    example="",
                    parameters=[],
                    return_type="None",
                    line_number=2,
                ),
            ],
        )
        html = DocumentationGenerator(info).generate_html()
        assert 'data-search="' in html
        # Doc prose and tags land in the search blob even though the visible
        # sidebar label is only the keyword name.
        freeze_li = re.search(
            r'<li data-search="([^"]*)"><a href="#freeze-time">',
            html,
        )
        assert freeze_li
        blob = freeze_li.group(1)
        assert "freeze time" in blob
        assert "otp" in blob
        assert "time" in blob
