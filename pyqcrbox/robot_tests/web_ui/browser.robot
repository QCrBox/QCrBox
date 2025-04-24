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
${WEB_URL}    http://127.0.0.1:11000/views/index
${TEST_CIF_FILE}    ${CURDIR}/test_data/robot_test_cif.cif

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
    
    # Check if the CIF file is uploaded
    ${response}=    Call GET API    /datasets
    ${datasets}=    Evaluate    [d for d in ${response.json()} if "robot_test_cif.cif" in d["data_files"]]    json
    Length Should Be    ${datasets}    1
    ${dataset_id}=    Set Variable    ${datasets[0]["dataset_id"]}

    # Delete the CIF file
    Call DELETE API    /datasets/delete/${dataset_id}
    
    # Check if the CIF file is deleted
    ${response}=    Call GET API    /datasets
    ${datasets}=    Evaluate    [d for d in ${response.json()} if "robot_test_cif.cif" in d["data_files"]]    json
    Length Should Be    ${datasets}    0

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

Call DELETE API
    [Arguments]    ${api}
    ${response}=    DELETE On Session    api_endpoints    ${api}
    Status Should Be    204    ${response}
    Log    ${response}
    Log    ${response.content}
    RETURN    ${response}
