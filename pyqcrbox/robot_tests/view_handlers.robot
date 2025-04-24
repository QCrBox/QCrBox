*** Settings ***
Documentation
...    Test suite for the registry view handler API
Suite Setup    Setup suite
Suite Teardown    Teardown suite
Resource    ../api_keywords.resource
Library    DateTime
Test Timeout    2 minutes

*** Variables ***

${VIEW_HANDLERS_API}    http://127.0.0.1:11000/views

*** Test Cases ***

Check applications API returns applications
    ${response}=    Call GET API    view_handlers    /applications
    Should Contain    ${response.content}    QCrBox Registered Applications
    Should Contain    ${response.content}    QCrBoxTools
    Should Contain    ${response.content}    Crystal Explorer
    Should Contain    ${response.content}    Olex2 (Linux)

Check data_files API returns data_files
    Call GET API    view_handlers    /data_files

Check index API returns index
    ${response}=    Call GET API    view_handlers    /index
    ${html}=    Convert To String    ${response.content}
    Should Match Regexp    ${html}    (?i)<form[^>]*id=["']file_upload_form["']

Check restart API returns the restart screen
    Call GET API    view_handlers    /restart

Check restart_docker_containers API restarts the containers
    Call POST API    view_handlers    /restart_docker_containers

*** Keywords ***

Setup suite
    ${api_session}=    Create API Session    view_handlers    ${VIEW_HANDLERS_API}
    Log datetime information
    Log    Starting test suite

Teardown suite
    Log datetime information
    Log    Test suite completed

Log datetime information
    ${date}=    Get Current Date
    Log    ${date}
