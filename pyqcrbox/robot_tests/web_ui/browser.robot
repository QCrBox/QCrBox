*** Settings ***
Documentation
...  Test suite for the Web UI
Suite Setup    Setup suite
Suite Teardown    Teardown suite
Library    DateTime
Library    SeleniumLibrary
Library    RequestsLibrary
Library    JSONLibrary
Test Timeout    2 minutes

*** Variables ***

${ENDPOINTS_API}    http://127.0.0.1:11000/api
${WEB_URL}  http://127.0.0.1:11000/views/index
${TEST_CIF_FILE}  ${CURDIR}/test_data/test.cif

*** Test Cases ***

Test user can upload a CIF file
    Open Browser    ${WEB_URL}    Chrome
    Wait Until Element Is Visible    id=open-modal    timeout=5s
    Click Element    id=open-modal
    Wait Until Element Is Visible    id=file_upload_form    timeout=2s
    Choose File    id=file_selector    ${TEST_CIF_FILE}
    Wait Until Element Is Enabled    id=btn_data_file_upload    timeout=5s
    Click Button    id=btn_data_file_upload
    Close Browser
    Call GET API   /datasets

*** Keywords ***

Setup suite
    Create Session    api_endpoints    ${ENDPOINTS_API}
    Log datetime information
    Log    Starting the test

Teardown suite
    Log datetime information
    Log    Test execution completed

Log datetime information
    ${date}=    Get Current Date
    Log    ${date}

Call GET API
    [Arguments]    ${api}
	${response}=    GET On Session    api_endpoints    ${api}
    Status Should Be    200    ${response}
    Log    ${response}
    Log    ${response.content}
    RETURN    ${response}
