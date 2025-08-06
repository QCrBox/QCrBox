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
Check a non-interactive command can be invoked
    ${input_file}=    Create Dictionary    data_file_id=${TEST_DATA_FILE_ID}
    ${arguments}=    Create Dictionary    input_cif=${input_file}    output_cif_path=/opt/qcrbox/test_cif.cif
    ${request_body}=    Create Dictionary
    ...    application_slug=qcrboxtools
    ...    application_version=0.0.5
    ...    command_name=to_unified_cif
    ...    arguments=${arguments}

    ${response}=    Send API Request
    ...    POST
    ...    ${SESSION_ALIAS}
    ...    /commands
    ...    201
    ...    json_data=${request_body}
    ${invoke_payload}=    Check Response And Get Payload    ${response}

    Sleep    2s    "Waiting for non-interactive session to be registered and start"

    Check Response Has Attributes    ${invoke_payload}    calculation_id
    Set Suite Variable    ${TEST_CALCULATION_ID}    ${invoke_payload["calculation_id"]}

Check that long running non-interactive commands can be stopped
    ${response}=    Send API Request    POST    ${SESSION_ALIAS}    /calculations/${TEST_CALCULATION_ID}/stop    200
    ${payload}=    Check Response And Get Payload    ${response}
    Check Response Has Attributes    ${payload}   calculations

Check that the non-interactive command has stopped
    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /calculations/${TEST_CALCULATION_ID}    200
    ${payload}=    Check Response And Get Payload    ${response}

    Check Response Has Attributes    ${payload}    calculations
    ${calculations}=    Set Variable    ${payload["calculations"]}
    ${n_calculations}=    Get Length    ${calculations}
    Should Be Equal As Integers    ${n_calculations}    1    "Multiple calculations retrieved, when only one requested"

    Check Calculations Structure    ${calculations}
    Should Not Be Equal    ${calculations[0]["status"]}    running

# Check that the calculation entry contains the output dataset id
#     ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /calculations/${TEST_CALCULATION_ID}    200
#     ${payload}=    Check Response And Get Payload    ${response}

#     Check Response Has Attributes    ${payload}    calculations
#     ${calculations}=    Set Variable    ${payload["calculations"]}
#     ${n_calculations}=    Get Length    ${calculations}
#     Should Be Equal As Integers    ${n_calculations}    1    "Multiple calculations retrieved, when only one requested"

#     Check Calculations Structure    ${calculations}
#     Set Suite Variable    ${TEST_OUTPUT_DATASET_ID}    ${calculations[0]["output_dataset_id"]}

# Check it's possible to download the non-interactive command's output dataset
#     ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /datasets/${TEST_OUTPUT_DATASET_ID}    200
#     Should Not Be Empty    ${response.content}


*** Keywords ***
Setup suite
    Create API Session    ${SESSION_ALIAS}    ${ENDPOINTS_API}
    Log datetime information
    Upload Test Dataset
    Log    Starting test suite

Teardown suite
    Log datetime information
    # Delete Test Dataset
    # Delete Output Dataset
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
        ...    arguments
        ...    output_dataset_id
    END
