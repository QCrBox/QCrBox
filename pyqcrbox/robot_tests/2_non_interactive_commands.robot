*** Settings ***
Documentation
...                 Test suite for the API endpoints of the QCrBox registry

# Standard libraries
Library             DateTime
Library             Collections
Library             JSONLibrary
Library             OperatingSystem
# Keywords implemented in Robot
Resource            resources/api.resource
Resource            resources/keywords.resource

Suite Setup         Setup suite
Suite Teardown      Teardown suite
Test Timeout        2 minutes


*** Variables ***
${REGISTRY_ADDRESS}             %{QCRBOX_BIND_ADDRESS=127.0.0.1}
${REGISTRY_PORT}                %{QCRBOX_REGISTRY_PORT=11000}
${ENDPOINTS_API}                http://${REGISTRY_ADDRESS}:${REGISTRY_PORT}/api
${SESSION_ALIAS}                QCRBOX_REGISTRY_API_ENDPOINTS

${TEST_CIF_FILE_NAME}           robot_test_cif.cif
${TEST_CIF_FILE}                ${CURDIR}/test_data/${TEST_CIF_FILE_NAME}

${TEST_CALCULATION_ID}          ${EMPTY}
${TEST_DATA_FILE_ID}            ${EMPTY}
${TEST_DATASET_ID}              ${EMPTY}
${TEST_OUTPUT_DATASET_ID}       ${EMPTY}


*** Test Cases ***
Invoke a short running non-interactive command
    ${input_file}=    Create Dictionary    data_file_id=${TEST_DATA_FILE_ID}
    ${arguments}=    Create Dictionary    input_cif=${input_file}    print_times=3
    ${request_body}=    Create Dictionary
    ...    application_slug=dummy_cli
    ...    application_version=0.1.0
    ...    command_name=print_cif
    ...    command_arguments=${arguments}

    ${response}=    Send API Request
    ...    POST
    ...    ${SESSION_ALIAS}
    ...    /commands
    ...    201
    ...    json_data=${request_body}
    ${invoke_payload}=    Check Response And Get Payload    ${response}
    Check Response Has Attributes    ${invoke_payload}    calculation_id
    Set Suite Variable    ${TEST_CALCULATION_ID}    ${invoke_payload["calculation_id"]}

Check that short command status is successful
    ${calculation}=    Wait Until Keyword Succeeds
    ...    10s
    ...    2s
    ...    Check Calculation Successful
    ...    ${TEST_CALCULATION_ID}

    # Use the output from this command as the output dataset which should be downloadable
    Set Suite Variable    ${TEST_OUTPUT_DATASET_ID}    ${calculation["output_dataset_id"]}
    Should Not Be None    ${TEST_OUTPUT_DATASET_ID}

Download the output dataset from the short running command
    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /datasets/${TEST_OUTPUT_DATASET_ID}    200
    Should Not Be Empty    ${response.content}

Invoke a long running non-interactive command
    ${arguments}=    Create Dictionary    dummy="hello"
    ${request_body}=    Create Dictionary
    ...    application_slug=dummy_cli
    ...    application_version=0.1.0
    ...    command_name=infinite_loop
    ...    command_arguments=${arguments}

    ${response}=    Send API Request
    ...    POST
    ...    ${SESSION_ALIAS}
    ...    /commands
    ...    201
    ...    json_data=${request_body}
    ${invoke_payload}=    Check Response And Get Payload    ${response}
    Check Response Has Attributes    ${invoke_payload}    calculation_id
    Set Suite Variable    ${TEST_CALCULATION_ID}    ${invoke_payload["calculation_id"]}

Check that a long running non-interactive command is still running
    Sleep    5s    "Letting the long running command run for a while"
    ${calculation_status}=    Get Calculation Status    ${TEST_CALCULATION_ID}
    Should Be Equal    ${calculation_status["status"]}    running

Check that long running non-interactive command can be stopped
   ${response}=    Send API Request    POST    ${SESSION_ALIAS}    /calculations/${TEST_CALCULATION_ID}/stop    200
   ${payload}=    Check Response And Get Payload    ${response}
   Check Response Has Attributes    ${payload}    calculations

Check that the non-interactive command has stopped
    ${calculation_status}=    Check Calculation Successful    ${TEST_CALCULATION_ID}
    Should Be None    ${calculation_status["output_dataset_id"]}

Check that an error is returned if a dataset ID is used instead of a data file ID
    ${input_file}=    Create Dictionary    data_file_id=${TEST_DATASET_ID}
    ${arguments}=    Create Dictionary    input_cif=${input_file}    print_times=3
    ${request_body}=    Create Dictionary
    ...    application_slug=dummy_cli
    ...    application_version=0.1.0
    ...    command_name=print_cif
    ...    command_arguments=${arguments}

    ${response}=    Send API Request
    ...    POST
    ...    ${SESSION_ALIAS}
    ...    /commands
    ...    201
    ...    json_data=${request_body}
    ${invoke_payload}=    Check Response And Get Payload    ${response}
    Check Response Has Attributes    ${invoke_payload}    calculation_id
    ${calculation_id}=    Set Variable    ${invoke_payload["calculation_id"]}

    Sleep    2s    "Waiting for command to fail"

    ${calculation_status}=    Get Calculation Status    ${calculation_id}
    Should Be Equal    ${calculation_status["status"]}    failed
    ${error_msg}=    Set Variable    ${calculation_status["status_events"][-1]["extra_info"]["error_msg"]}
    Should Contain    ${error_msg}    is a `dataset_id`


*** Keywords ***
Get Calculation Status
    [Arguments]    ${calculation_id}

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /calculations/${calculation_id}    200
    ${payload}=    Check Response And Get Payload    ${response}

    Check Response Has Attributes    ${payload}    calculations
    ${calculations}=    Set Variable    ${payload["calculations"]}
    ${n_calculations}=    Get Length    ${calculations}
    Should Be Equal As Integers    ${n_calculations}    1    "Multiple calculations retrieved, when only one requested"

    Check Calculations Structure    ${calculations}
    ${calculation_status}=    Set Variable    ${calculations[0]}

    RETURN    ${calculation_status}

Check Calculation Successful
    [Arguments]    ${calculation_id}
    ${calculation_status}=    Get Calculation Status    ${calculation_id}
    Should Be Equal    ${calculation_status["status"]}    successful

    RETURN    ${calculation_status}

Check Calculations Structure
    [Arguments]    ${calculations}
    FOR    ${calculation}    IN    @{calculations}
        Check Response Has Attributes
        ...    ${calculation}
        ...    calculation_id
        ...    application_slug
        ...    application_version
        ...    command_name
        ...    status
        ...    command_arguments
        ...    output_dataset_id
    END

Setup suite
    Create API Session    ${SESSION_ALIAS}    ${ENDPOINTS_API}
    Log datetime information
    Upload Test Dataset
    Log    Starting test suite

Teardown suite
    Log datetime information
    Delete Test Dataset
    Delete Output Dataset
    Log    Test suite completed

Upload Test Dataset
    ${file_contents}=    Get Binary File    ${TEST_CIF_FILE}
    ${files}=    Create Dictionary    ${TEST_CIF_FILE_NAME}=${file_contents}

    ${response}=    Send API Request    POST    ${SESSION_ALIAS}    /datasets    201    files=${files}
    ${payload}=    Check Response And Get Payload    ${response}

    Check Response Has Attributes    ${payload}    datasets
    ${datasets}=    Set Variable    ${payload["datasets"]}
    ${n_datasets}=    Get Length    ${datasets}
    Should Be Equal As Integers
    ...    ${n_datasets}
    ...    1
    ...    "/datasets response returned an incorrect number of datasets when it should return only the created dataset"

    ${test_dataset_id}=    Set Variable    ${datasets[0]["qcrbox_dataset_id"]}
    Set Suite Variable    ${TEST_DATASET_ID}    ${test_dataset_id}
    Set Suite Variable
    ...    ${TEST_DATA_FILE_ID}
    ...    ${datasets[0]["data_files"]["${TEST_CIF_FILE_NAME}"]["qcrbox_file_id"]}

Delete Test Dataset
    ${response}=    Send API Request    DELETE    ${SESSION_ALIAS}    /datasets/${TEST_DATASET_ID}    204

Delete Output Dataset
    ${response}=    Send API Request    DELETE    ${SESSION_ALIAS}    /datasets/${TEST_OUTPUT_DATASET_ID}    204
