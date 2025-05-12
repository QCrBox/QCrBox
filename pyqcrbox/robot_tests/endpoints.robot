*** Settings ***
Documentation
...    Test suite for the registry API endpoints
Suite Setup    Setup suite
Suite Teardown    Teardown suite
Resource    resources/api.resource
Library    DateTime
Library    Collections
Library    JSONLibrary
Library    OperatingSystem
Test Timeout    2 minutes

*** Variables ***

${ENDPOINTS_API}    http://127.0.0.1:11000/api
${TEST_CIF_FILE_NAME}    robot_test_cif.cif
${TEST_CIF_FILE}    ${CURDIR}/test_data/${TEST_CIF_FILE_NAME}
${SESSION_ALIAS}    api_endpoints

*** Test Cases ***

Check healthz API returns healthz
    Call GET API    ${SESSION_ALIAS}    /healthz

Check applications API returns list of registered applications
    ${response}=    Call GET API    ${SESSION_ALIAS}    /applications
    ${applications}=    Set Variable    ${response.json()['payload']['applications']}
    FOR    ${app}    IN    @{applications}
        Verify Application Data    ${app}
    END

Check calculations API returns calculations
    Call GET API    ${SESSION_ALIAS}    /calculations

Check commands API returns commands
    Call GET API    ${SESSION_ALIAS}    /commands

Check data_files API returns data_files
    Call GET API    ${SESSION_ALIAS}    /data-files

Check dataset can be uploaded via API
    ${dataset_id}=    Upload Test Dataset
    Set Global Variable    ${dataset_id}

Check datasets API returns datasets
    ${response}=    Call GET API    ${SESSION_ALIAS}    /datasets
    ${length}=    Get Length    ${response.json()}
    Should Be True    ${length} > 0

Check a dataset metadata can be retrieved via API
    ${response}=    Call GET API    ${SESSION_ALIAS}    /datasets/${dataset_id}
    ${dataset}=    Set Variable    ${response.json()['payload']}

    Should Contain    ${dataset}    dataset_id
    Should Contain    ${dataset}    data_files
    ${data_files}=    Get From Dictionary    ${dataset}    data_files

    FOR    ${file_key}    IN    @{data_files.keys()}
        ${file_data}=    Get From Dictionary    ${data_files}    ${file_key}
        Should Contain    ${file_data}    qcrbox_file_id
        Should Contain    ${file_data}    filename
        Should Contain    ${file_data}    filetype
        Set Global Variable    ${data_file_id}    ${file_data['qcrbox_file_id']}
    END
    
Check data file can be downloaded via API
    ${response}=    Call GET API    ${SESSION_ALIAS}    /data-files/${data_file_id}/download
    Compare Downloaded File With Uploaded    ${response.content}    ${response}

Check dataset can be downloaded via API
    ${response}=    Call GET API    ${SESSION_ALIAS}    /datasets/${dataset_id}/download
    Compare Downloaded File With Uploaded    ${response.content}    ${response}


Check an interactive session can be created
    # We need to get the data_file_id from the test dataset
    ${response}=    Call GET API   ${SESSION_ALIAS}    /datasets/${dataset_id}
    ${data_files}=    Set Variable    ${response.json()['payload']['data_files']}
    ${data_file}=    Get From Dictionary    ${data_files}    ${TEST_CIF_FILE_NAME}
    ${data_file_id}=    Set Variable    ${data_file['qcrbox_file_id']}
    Set Global Variable    ${data_file_id}

    # Call the API to create a session, which should return the calculation id
    ${payload}=     Create Dictionary
    ...             application_slug=olex2
    ...             application_version=1.5-alpha
    ...             data_file_id=${data_file_id}
    ${response}=    Call POST API with json    ${SESSION_ALIAS}    /interactive-sessions    ${payload}
    ${interactive_session_id}=    Set Variable    ${response.json()['payload']['calculation_id']}
    Log    "Interactive session ID: ${interactive_session_id}"
    Set Global Variable    ${interactive_session_id}
    Sleep    5s    "Wait for the interactive session to be added to the database"
    
Check interactive sessions API returns interactive sessions 
    Call GET API    ${SESSION_ALIAS}    /interactive-sessions

Check interactive session can be retrieved via API
    ${response}=    Call GET API    ${SESSION_ALIAS}    /interactive-sessions/${interactive_session_id}
    ${payload}=    Set Variable    ${response.json()['payload']}
    Should Contain    ${payload}    interactive_session
    ${interactive_session}=    Get From Dictionary    ${payload}    interactive_session
    Should Contain    ${interactive_session}    session_id
    Should Contain    ${interactive_session}    client_private_inbox
    Should Contain    ${interactive_session}    application_slug
    Should Contain    ${interactive_session}    application_version
    Should Contain    ${interactive_session}    command_name
    Should Contain    ${interactive_session}    arguments

    Should Be Equal    ${interactive_session['session_id']}    ${interactive_session_id}
    Should Be Equal    ${interactive_session['command_name']}    interactive_session
    Should Be Equal    ${interactive_session['application_slug']}    olex2
    Should Be Equal    ${interactive_session['application_version']}    1.5-alpha
    Should Be Equal    ${interactive_session['arguments']['input_file']['data_file_id']}    ${data_file_id}

Check an interactive session can be closed
    Call DELETE API    ${SESSION_ALIAS}    /interactive-sessions/${interactive_session_id}

Check dataset can be deleted via API
    Call DELETE API    ${SESSION_ALIAS}    /datasets/${dataset_id}

*** Keywords ***

Setup suite
    ${api_session}=    Create API Session    ${SESSION_ALIAS}    ${ENDPOINTS_API}
    Log datetime information
    Log    Starting test suite

Teardown suite
    Log datetime information
    Log    Test suite completed

Log datetime information
    ${date}=    Get Current Date
    Log    ${date}

Verify Application Data
    [Arguments]    ${app}
    Should Contain    ${app}    name
    Should Contain    ${app}    slug
    Should Contain    ${app}    version
    Should Contain    ${app}    description
    Should Contain    ${app}    url
    Should Contain    ${app}    registered_at
    Should Contain    ${app}    commands
    FOR    ${command}    IN    @{app['commands']}
        Should Contain    ${command}    name
        Should Contain    ${command}    description
        Should Contain    ${command}    implemented_as
        Should Contain    ${command}    parameters
    END

Upload Test Dataset
    ${file_content}=    Get Binary File    ${TEST_CIF_FILE}
    
    ${files}=    Create Dictionary    ${TEST_CIF_FILE_NAME}=${file_content}
    ${response}=    Call POST API With File    ${SESSION_ALIAS}    /datasets    files=${files}
    ${dataset_id}=    Set Variable    ${response.json()['payload']['qcrbox_dataset_id']}
    Log    "Response: ${response.json()}"
    Log    "Dataset ID: ${dataset_id}"
    RETURN    ${dataset_id}

Compare Downloaded File With Uploaded
    [Arguments]    ${downloaded_bytes}    ${response}
    ${original_bytes}=    Get Binary File    ${TEST_CIF_FILE}
    Should Be Equal As Strings    ${downloaded_bytes}    ${original_bytes}
    ${content_disposition}=    Get From Dictionary    ${response.headers}    content-disposition
    Should Contain    ${content_disposition}    filename='${TEST_CIF_FILE_NAME}'
