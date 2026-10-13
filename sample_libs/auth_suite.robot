*** Settings ***
Documentation    Suite with reusable keywords and an example test.

*** Test Cases ***
Login Example
    Login User    alice    secret
    Logout User

*** Keywords ***
Login User
    [Documentation]    Log in with username and password.
    [Arguments]    ${username}    ${password}
    Log    Logging in as ${username}
    No Operation

Logout User
    [Documentation]    Log the current user out.
    Log    Logging out
