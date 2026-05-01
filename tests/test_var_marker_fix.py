from robotframework_docgen.parser import RobotFrameworkDocParser


def test_fenced_robot_code_no_marker_tokens():
    parser = RobotFrameworkDocParser()
    md = """
    ```robot
    ${url}=    Assert    Get Url
    ${text}=   Assert    Get Text    ${HEADING}
    ```
    """
    out = parser._render_docstring_with_markdown(md)

    # Assert no leftover marker tokens in the rendered HTML
    assert "__VAR_MARKER" not in out
    assert "::VAR_MARKER" not in out

    # Variables should be present and highlighted (inside span tags)
    assert '<span' in out
    assert '${url}' in out
