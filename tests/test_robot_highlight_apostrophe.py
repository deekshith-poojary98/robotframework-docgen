"""Regression: quoted Robot values must not become fake rf-comment spans."""

from robotframework_docgen.parser import RobotFrameworkDocParser


def test_single_quoted_value_is_not_highlighted_as_comment():
    parser = RobotFrameworkDocParser({})
    html = parser._highlight_robot_framework(
        "    Should Be Equal    ${status}    'SUBMITTED'"
    )
    assert "#x27" not in html
    assert "&#x27;" not in html
    assert "'SUBMITTED'" in html
    assert "rf-comment" not in html


def test_real_trailing_comment_still_highlighted():
    parser = RobotFrameworkDocParser({})
    html = parser._highlight_robot_framework(
        "    Log    'SUBMITTED'    # expected status"
    )
    assert "'SUBMITTED'" in html
    assert 'class="rf-comment"' in html
    assert "# expected status" in html
