*** Settings ***
Documentation
...    Test suite for the registry view handler API
Suite Setup    Setup suite
Suite Teardown    Teardown suite
Library    DateTime
Library    RequestsLibrary
Library    JSONLibrary
Test Timeout    2 minutes

*** Variables ***

${VIEW_HANDLERS_API}    http://127.0.0.1:11000/views

*** Test Cases ***

Check applications API returns applications
    ${response}=    Call GET API    /applications
    Should Contain    ${response.content}    QCrBox Registered Applications
    Should Contain    ${response.content}    QCrBoxTools
    Should Contain    ${response.content}    Crystal Explorer
    Should Contain    ${response.content}    Olex2 (Linux)

Check data_files API returns data_files
    Call GET API    /data_files

Check index API returns index
    ${response}=    Call GET API    /index
    ${html}=    Convert To String    ${response.content}
    Should Match Regexp    ${html}    (?i)<form[^>]*id=["']file_upload_form["']

Check restart API returns the restart screen
    Call GET API    /restart

Check restart_docker_containers API restarts the containers
    Call POST API    /restart_docker_containers

*** Keywords ***

Setup suite
    Create Session    view_handlers    ${VIEW_HANDLERS_API}
    Log datetime information
    Log    Starting test suite

Teardown suite
    Log datetime information
    Log    Test suite completed

Log datetime information
    ${date}=    Get Current Date
    Log    ${date}

Call GET API
    [Arguments]    ${api}
	${response}=    GET On Session    view_handlers    ${api}
    Status Should Be    200    ${response}
    Log    ${response}
    Log    ${response.content}
    RETURN    ${response}

Call POST API
    [Arguments]    ${api}
    ${response}=    POST On Session    view_handlers    ${api}
    Status Should Be    200    ${response}
    Log    ${response}
    Log    ${response.content}
    RETURN    ${response}
