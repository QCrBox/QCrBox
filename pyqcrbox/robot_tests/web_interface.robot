*** Settings ***
Documentation
...                 Test suite for the Web UI

Resource            resources/api.resource
Library             DateTime
Library             SeleniumLibrary

Suite Setup         Setup suite
Suite Teardown      Teardown suite
Test Timeout        2 minutes


*** Variables ***
${ENDPOINTS_API}            http://127.0.0.1:11000/api
${WEB_URL}                  http://127.0.0.1:11000/views/index
${TEST_CIF_FILE_NAME}       robot_test_cif.cif
${TEST_CIF_FILE}            ${CURDIR}/test_data/${TEST_CIF_FILE_NAME}


*** Test Cases ***
Test user can upload a CIF file
    # Test that a user can upload a CIF file using the web UI upload form
    Wait Until Element Is Visible    id=open-modal    timeout=5s
    Click Element    id=open-modal
    Wait Until Element Is Visible    id=file_upload_form    timeout=2s
    Choose File    id=file_selector    ${TEST_CIF_FILE}
    Wait Until Element Is Enabled    id=btn_data_file_upload    timeout=5s
    Click Button    id=btn_data_file_upload
    Wait Until Element Is Not Visible    id=btn_data_file_upload    timeout=5s

    # Now check that the file has been uploaded and delete it
    ${dataset_id}=    Check that file uploaded to dataset    ${TEST_CIF_FILE_NAME}
    Call DELETE API    api_endpoints    /datasets/delete/${dataset_id}


*** Keywords ***
Setup suite
    Log datetime information
    ${api_session}=    Create API Session    api_endpoints    ${ENDPOINTS_API}
    Open Browser    ${WEB_URL}    Chrome
    Log    Starting the test

Teardown suite
    Log datetime information
    Close Browser
    Log    Test execution completed

Log datetime information
    ${date}=    Get Current Date
    Log    ${date}

Check that file uploaded to dataset
    [Arguments]    ${filename}
    ${response}=    Call GET API    api_endpoints    /datasets
    ${data}=    Set Variable    ${response.json()['payload']['datasets']}
    ${datasets}=    Evaluate    [d for d in ${data} if "${filename}" in d["data_files"]]    json
    Length Should Be    ${datasets}    1
    ${dataset_id}=    Set Variable    ${datasets[0]["dataset_id"]}
    RETURN    ${dataset_id}
