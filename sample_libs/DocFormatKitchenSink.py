"""
DocFormatKitchenSink — exhausts Robot Framework / Libdoc documentation constructs.

Libdoc source formats (ROBOT_LIBRARY_DOC_FORMAT): ROBOT | MARKDOWN | HTML | TEXT | REST.
This library uses MARKDOWN (RF 7.5+ / docgen's primary path) and covers the formatting
features documented for both Markdown and the classic ROBOT doc syntax.
"""

from __future__ import annotations

from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional, Union

from robot.api.deco import keyword, library


class Severity(Enum):
    """String-valued severity levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HttpMethod(Enum):
    """HTTP verbs as enum members."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class Priority(IntEnum):
    """Integer-valued priority."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class Region(Enum):
    """Deployment region codes."""

    US_EAST = "us-east-1"
    EU_WEST = "eu-west-1"
    AP_SOUTH = "ap-south-1"


@library(
    scope="GLOBAL",
    version="1.0.0",
    doc_format="MARKDOWN",
    auto_keywords=False,
)
class DocFormatKitchenSink:
    """Kitchen-sink library for documentation formatting and Enum arguments.

`DocFormatKitchenSink` exercises Markdown constructs that Libdoc / docgen should
render: emphasis, links, images, lists, tables, headings, quotes, rules, fenced
code, and in-doc keyword references like [Render Inline Styles].

It also demonstrates Enum / IntEnum typed arguments with defaults.

Supported formats elsewhere in RF (set via ``ROBOT_LIBRARY_DOC_FORMAT`` or
``@library(doc_format=...)``):

| Format | Notes |
|--------|-------|
| ROBOT | Classic Libdoc syntax (`*bold*`, ``code``, custom `[link|label]`) |
| MARKDOWN | This library (RF 7.5+) |
| HTML | Raw HTML fragments in docstrings |
| TEXT | Plain text, whitespace preserved |
| REST | reStructuredText (needs ``docutils``) |

Examples:

```robotframework
*** Settings ***
Library    DocFormatKitchenSink

*** Test Cases ***
Smoke
    Render Inline Styles
    Apply Severity    ERROR
```
"""

    def __init__(
        self,
        default_severity: Severity = Severity.INFO,
        region: Region = Region.US_EAST,
    ):
        """Construct the library with defaults used by later keywords.

        **Arguments:**
        - `default_severity`: Initial [Apply Severity] level (default ``INFO``)
        - `region`: Default [Select Region] value (default ``US_EAST``)

        **Example:**

        ```robotframework
        *** Settings ***
        Library    DocFormatKitchenSink    default_severity=WARNING    region=EU_WEST
        ```
        """
        self.default_severity = default_severity
        self.region = region

    @keyword
    def render_inline_styles(self) -> str:
        """Show **bold**, *italic*, ***bold italic***, and ``inline code``.

        Soft-wrapped prose continues on the next line so paragraph joining
        can be verified without breaking surrounding blocks.

        Mix of punctuation and code: use ``${variable}``, keep *emphasis*,
        and prefer **strong** labels.

        Autolink: https://robotframework.org/

        Explicit markdown link: [Robot Framework](https://robotframework.org/)

        Image (decorative): ![RF logo](https://docs.robotframework.org/img/rf_favicon.png)

        See also [Render Lists And Quotes] and [Render Markdown Table].
        """
        return "ok"

    @keyword
    def render_extended_markdown(self) -> None:
        """Exercise extended Markdown: admonitions, definitions, footnotes, abbr, TOC.

        %TOC%

        ## Overview

        This keyword covers constructs beyond basic emphasis / lists / tables.

        ### Admonitions

        !!! note "Friendly tip"
            Prefer Markdown docstrings with ``ROBOT_LIBRARY_DOC_FORMAT = "MARKDOWN"``.

        !!! warning
            Nested lists need **four spaces** of indent for Python-Markdown.

        !!! danger "Breaking change"
            Reset travelers in teardown or clocks leak across tests.

        ### Definition list

        Freeze Time
        :   Hold perceived time at an instant.

        Advance Time
        :   Move the simulated clock forward by a duration.

        ### Abbreviations

        *[HTML]: HyperText Markup Language
        *[JSON]: JavaScript Object Notation

        Docs are emitted as HTML; payloads are often JSON.

        ### Footnotes

        Cross-references use ``[Keyword Name]`` links.[^kw-ref]

        [^kw-ref]: Resolved later to in-page anchors when the target exists.

        ### Attribute list heading

        #### Custom anchor {: #extended-md-anchor }

        Jump target for ``#extended-md-anchor``.

        ### HTML with nested Markdown

        <div markdown="1" class="md-in-html">

        **Bold** inside an HTML wrapper via ``md_in_html``.

        </div>
        """

    @keyword
    def render_lists_and_quotes(self) -> None:
        """Unordered, ordered, nested lists, and a block quote.

        Bullet list:

        - Alpha item with ``code``
        - Beta item with **bold**
            - child one
            - child two
        - Gamma item

        Numbered list:

        1. First step
        2. Second step with a [Render Inline Styles] reference
        3. Third step

        Quote:

        > Documentation should be readable in source *and* in HTML.
        >
        > — Kitchen sink

        Horizontal rule below.

        ---

        Trailing note after the rule.
        """

    @keyword
    def render_markdown_table(self) -> Dict[str, str]:
        """Markdown pipe table with inline formatting inside cells.

        **Schema:**

        | Field | Type | Required | Notes |
        |-------|------|----------|-------|
        | `name` | str | yes | Display name |
        | `severity` | Severity | no | See [Apply Severity] |
        | `region` | Region | no | See [Select Region] |
        | `active` | bool | no | Defaults to ``True`` |

        **Returns:** A small dictionary echoing the schema keys.
        """
        return {"name": "demo", "severity": "INFO", "region": "US_EAST", "active": "True"}

    @keyword
    def render_headings_and_toc_style(self) -> None:
        """Section headings at multiple levels.

        ## Level two

        Body under level two with a soft
        wrapped continuation line.

        ### Level three

        - still a list under h3
        - second bullet

        #### Level four

        Closing paragraph with ``code`` and a link to
        [https://example.com/docs](https://example.com/docs).
        """

    @keyword
    def render_fenced_code_samples(self, payload: str = "{}") -> str:
        """Fenced code in Robot, Python, and plain text.

        Robot example:

        ```robotframework
        *** Settings ***
        Library    DocFormatKitchenSink

        *** Test Cases ***
        Demo Fence
            ${out}=    Render Fenced Code Samples    {"ok": true}
            Should Contain    ${out}    ok
        ```

        Python example:

        ```python
        def echo(payload: str) -> str:
            return payload or "{}"
        ```

        Plain fence:

        ```text
        line one
        line two
        ```

        **Arguments:**
        - `payload`: JSON-ish string passed through unchanged

        **Returns:** The same `payload` (or ``{}`` when empty).
        """
        return payload or "{}"

    @keyword
    def apply_severity(
        self,
        level: Severity = Severity.INFO,
        notify: bool = True,
    ) -> str:
        """Apply a ``Severity`` enum level.

        **Arguments:**
        - `level`: One of ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``
        - `notify`: When ``True``, pretend to emit a notification

        **Returns:** The severity *value* string (not the enum name).

        | Level | Value |
        |-------|-------|
        | DEBUG | debug |
        | INFO | info |
        | WARNING | warning |
        | ERROR | error |
        | CRITICAL | critical |

        ```robotframework
        *** Test Cases ***
        Set Error
            ${v}=    Apply Severity    ERROR
            Should Be Equal    ${v}    error
            Apply Severity    level=WARNING    notify=${False}
        ```
        """
        _ = notify
        return level.value

    @keyword
    def select_region(self, region: Region = Region.US_EAST) -> str:
        """Select a deployment ``Region`` enum.

        **Arguments:**
        - `region`: ``US_EAST``, ``EU_WEST``, or ``AP_SOUTH``

        **Returns:** Region code string such as ``us-east-1``.
        """
        return region.value

    @keyword
    def schedule_work(
        self,
        title: str,
        priority: Priority = Priority.MEDIUM,
        severity: Severity = Severity.INFO,
        method: HttpMethod = HttpMethod.POST,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Combine IntEnum, Enum, and regular arguments.

        **Arguments:**
        - `title`: Work item title (required)
        - `priority`: ``Priority`` IntEnum (default ``MEDIUM`` / ``2``)
        - `severity`: ``Severity`` (default ``INFO``)
        - `method`: ``HttpMethod`` (default ``POST``)
        - `tags`: Optional list of string tags

        **Returns:** Dict with normalized fields.

        **Priority table:**

        | Name | Int |
        |------|-----|
        | LOW | 1 |
        | MEDIUM | 2 |
        | HIGH | 3 |
        | CRITICAL | 4 |

        ```robotframework
        *** Test Cases ***
        Schedule
            ${job}=    Schedule Work    Deploy    priority=HIGH    method=PUT
            Should Be Equal As Integers    ${job}[priority]    3
        ```
        """
        return {
            "title": title,
            "priority": int(priority),
            "severity": severity.value,
            "method": method.value,
            "tags": list(tags or ()),
        }

    @keyword
    def mixed_optional_union(
        self,
        value: Union[str, int, None] = None,
        severity: Optional[Severity] = None,
    ) -> str:
        """Optional / Union typing next to an optional Enum.

        **Arguments:**
        - `value`: ``str``, ``int``, or ``None``
        - `severity`: Optional ``Severity``; falls back to library default

        **Returns:** A short status string.
        """
        sev = severity or self.default_severity
        return f"{value!r}@{sev.value}"

    @keyword("Echo With HTML-ish Name")
    def echo_with_special_name(self, text: str = "") -> str:
        """Keyword name contains characters that must stay escaped in HTML.

        Includes literal angle brackets in prose: use values like ``<raw>``
        carefully. Ampersands & quotes "like this" should not break markup.

        Cross-ref back to [Render Markdown Table].
        """
        return text
