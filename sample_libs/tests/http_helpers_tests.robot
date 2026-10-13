*** Settings ***
Resource    ../sample_libs/http_helpers.resource

*** Test Cases ***
Extract Nested Value
    [Documentation]    Ensures Get Json Value reads values from a dictionary payload.
    &{payload}=    Create Dictionary    a=1    b=2
    ${value}=    Get Json Value    ${payload}    a
    Should Be Equal    ${value}    1

Build Authorization Headers
    [Documentation]    Create Session Headers includes the bearer token.
    &{headers}=    Create Session Headers    token=secret-token
    Should Contain    ${headers}    Authorization
