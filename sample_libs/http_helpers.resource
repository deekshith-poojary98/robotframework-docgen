*** Settings ***
Documentation    Shared HTTP helper keywords for Robot Framework suites.
Library          Collections

*** Keywords ***
Get Json Value
    [Documentation]    Extract a value by key from a JSON dictionary.
    ...
    ...    Returns ``${NONE}`` when the key is missing and no default is given.
    [Arguments]    ${payload}    ${key}    ${default}=${NONE}
    ${value}=    Get From Dictionary    ${payload}    ${key}    ${default}
    RETURN    ${value}

Create Session Headers
    [Documentation]    Build a headers dictionary for API calls.
    [Arguments]    ${token}    ${content_type}=application/json
    &{headers}=    Create Dictionary
    ...    Authorization=Bearer ${token}
    ...    Content-Type=${content_type}
    RETURN    &{headers}

Do Something With
    [Documentation]    Accept a list and optional named options.
    [Arguments]    @{items}    &{options}
    Log    ${items}
    Log    ${options}

Undocumented Keyword
    [Arguments]    ${x}
    No Operation
