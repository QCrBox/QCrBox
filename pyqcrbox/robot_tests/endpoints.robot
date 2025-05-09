*** Settings ***
Documentation
...    Test suite for the registry API endpoints
Suite Setup    Setup suite
Suite Teardown    Teardown suite
Resource    resources/api.resource
Library    DateTime
Library    Collections
Library    JSONLibrary
Test Timeout    2 minutes

*** Variables ***

${ENDPOINTS_API}    http://127.0.0.1:11000/api
${TEST_CIF_FILE_NAME}    robot_test_cif.cif
${TEST_CIF_FILE}    ${CURDIR}/test_data/${TEST_CIF_FILE_NAME}

*** Test Cases ***

Check healthz API returns healthz
    Call GET API    api_endpoints    /healthz

Check applications API returns list of registered applications
    ${response}=    Call GET API    api_endpoints    /applications
    ${applications}=    Set Variable    ${response.json()['payload']['applications']}
    FOR    ${app}    IN    @{applications}
        Verify Application Data    ${app}
    END

Check interactive sessions API returns interactive sessions
    Call GET API    api_endpoints     /interactive-sessions

Check calculations API returns calculations
    Call GET API    api_endpoints    /calculations

Check commands API returns commands
    Call GET API    api_endpoints    /commands

Check data_files API returns data_files
    Call GET API    api_endpoints    /data-files

Check dataset can be uploaded via API
    ${dataset_id}=    Upload Test Dataset
    Set Global Variable    ${dataset_id}

Check datasets API returns datasets
    ${response}=    Call GET API    api_endpoints    /datasets
    ${length}=    Get Length    ${response.json()}
    Should Be True    ${length} > 0

Check a dataset can be retrieved via API
    ${response}=    Call GET API    api_endpoints    /datasets/${dataset_id}
    ${dataset}=    Set Variable    ${response.json()['payload']}

    Should Contain    ${dataset}    dataset_id
    Should Contain    ${dataset}    data_files
    ${data_files}=    Get From Dictionary    ${dataset}    data_files

    FOR    ${file_key}    IN    @{data_files.keys()}
        ${file_data}=    Get From Dictionary    ${data_files}    ${file_key}
        Should Contain    ${file_data}    qcrbox_file_id
        Should Contain    ${file_data}    filename
        Should Contain    ${file_data}    filetype
    END

Check an interactive session can be created
    # We need to get the data_file_id from the test dataset
    ${response}=    Call GET API   api_endpoints    /datasets/${dataset_id}
    ${data_files}=    Set Variable    ${response.json()['payload']['data_files']}
    ${data_file}=    Get From Dictionary    ${data_files}    ${TEST_CIF_FILE_NAME}
    ${data_file_id}=    Set Variable    ${data_file['qcrbox_file_id']}

    # Call the API to create a session, which should return the calculation id
    ${payload}=     Create Dictionary
    ...             application_slug=olex2
    ...             application_version=1.5-alpha
    ...             data_file_id=${data_file_id}
    ${response}=    Call POST API with json    api_endpoints    /interactive-sessions    ${payload}
    ${interactive_session_id}=    Set Variable    ${response.json()['payload']['calculation_id']}
    Set Global Variable    ${interactive_session_id}
    Sleep    5s    "Wait for the interactive session to be added to the database"

Check interactive session can be retrieved via API
    ${response}=    Call GET API    api_endpoints    /interactive-sessions/${interactive_session_id}
    ${interactive_session}=    Set Variable    ${response.json()['payload']}
    Should Contain    ${interactive_session}    calculation_id
    Should Contain    ${interactive_session}    application
    Should Contain    ${interactive_session}    data_file
    Should Contain    ${interactive_session}    status
    Should Contain    ${interactive_session}    created_at

Check an interactive session can be closed
    Call DELETE API    api_endpoints    /interactive-sessions/${interactive_session_id}

Check dataset can be deleted via API
    Call DELETE API    api_endpoints    /datasets/${dataset_id}

*** Keywords ***

Setup suite
    ${api_session}=    Create API Session    api_endpoints    ${ENDPOINTS_API}
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

*** Keywords ***
Upload Test Dataset
    ${files}=    Create Dictionary    ${TEST_CIF_FILE_NAME}=${TEST_CIF_FILE}
    ${response}=    Call POST API With File    api_endpoints    /datasets    files=${files}
    ${dataset_id}=    Set Variable    ${response.json()['payload']['qcrbox_dataset_id']}
    Log    "Response: ${response.json()}"
    Log    "Dataset ID: ${dataset_id}"
    RETURN    ${dataset_id}
