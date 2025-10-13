*** Settings ***
Documentation
...                 Test suite for the CIF2CIF translation and merging

Library             Collections
Library             DateTime
Library             OperatingSystem
Library             JSONLibrary
Resource            resources/api.resource
Resource            resources/keywords.resource

Suite Setup         Setup Suite
Suite Teardown      Teardown Suite
Test Timeout        2 minutes


*** Variables ***
${REGISTRY_ADDRESS}         %{QCRBOX_BIND_ADDRESS=127.0.0.1}
${REGISTRY_PORT}            %{QCRBOX_REGISTRY_PORT=11000}
${ENDPOINTS_API}            http://${REGISTRY_ADDRESS}:${REGISTRY_PORT}/api
${SESSION_ALIAS}            QCRBOX_REGISTRY_API_ENDPOINTS

${TEST_CIF_FILE_NAME}       lalanine8_200k.cif
${TEST_CIF_FILE}            ${CURDIR}/test_data/${TEST_CIF_FILE_NAME}
${TEST_DATA_FILE_ID}        ${EMPTY}
${TEST_DATASET_ID}          ${EMPTY}


*** Test Cases ***
Check that returned cif is unmodified
    [Documentation]    If no cif entries are set in the parameter yaml, an unmodified cif is expected to be returned

    VAR    &{input_cif}=    data_file_id=${TEST_DATA_FILE_ID}
    VAR    &{command_arguments}=    input_cif=${input_cif}    print_times=3

    ${invoke_response}=    Invoke Command With Arguments    print_cif    ${command_arguments}
    ${calculation_id}=    Get Calculation ID    ${invoke_response}
    ${output_dataset_id}=    Get Output Dataset    ${calculation_id}

    ${original_cif}=    Get Binary File    ${TEST_CIF_FILE}
    ${processed_cif}=    Get Dataset File Contents    ${output_dataset_id}
    Log    Original cif file: ${original_cif}
    Log    Processed cif file: ${processed_cif}
    Should Be Equal    ${processed_cif}    ${original_cif}

Check that returned cif has additional entries
    [Documentation]    We should expect some additional entries to be in the cif after command execution

    Log    Completed

Check that returned cif has invalidated entries
    [Documentation]    We should expect a cif not to have certain entries which were removed by QCrBox

    Log    Completed


*** Keywords ***
Setup Suite
    [Documentation]    Setup the test environment for this suite

    Create API Session    ${SESSION_ALIAS}    ${ENDPOINTS_API}
    Log Datetime Information
    Upload Test Cif
    Log    Starting test suite

Teardown Suite
    [Documentation]    Teardown the test environment for this suite

    Log Datetime Information
    Delete Cif Dataset    ${TEST_DATASET_ID}
    Log    Test suite completed

Upload Test Cif
    [Documentation]    Upload a cif file for testing purposes

    ${file_contents}=    Get Binary File    ${TEST_CIF_FILE}
    VAR    &{files}=    ${TEST_CIF_FILE_NAME}=${file_contents}

    ${response}=    Send API Request    POST    ${SESSION_ALIAS}    /datasets    201    files=${files}
    ${payload}=    Check Response And Get Payload    ${response}

    Check Response Has Attributes    ${payload}    datasets
    VAR    ${datasets}=    ${payload["datasets"]}
    VAR    ${test_dataset_id}=    ${datasets[0]["qcrbox_dataset_id"]}
    VAR    ${TEST_DATASET_ID}=    ${test_dataset_id}    scope=suite
    VAR    ${TEST_DATA_FILE_ID}=
    ...    ${datasets[0]["data_files"]["${TEST_CIF_FILE_NAME}"]["qcrbox_file_id"]}
    ...    scope=suite

Delete Cif Dataset
    [Documentation]    Remove a dataset containing a test cif file
    [Arguments]    ${dataset_id}

    Send API Request    DELETE    ${SESSION_ALIAS}    /datasets/${dataset_id}    204

Invoke Command With Arguments
    [Documentation]    Invoke a command with the provided arguments
    [Arguments]    ${command_name}    ${command_arguments}

    VAR    &{command_request}=
    ...    application_slug=dummy_cli
    ...    application_version=0.1.0
    ...    command_name=${command_name}
    ...    command_arguments=${command_arguments}
    Log    Command invocation request: ${command_request}

    ${response}=    Send API Request    POST    ${SESSION_ALIAS}    /commands    201    json_data=${command_request}
    VAR    ${response_json}=    ${response.json()}
    Log    Command invocation response: ${response_json}

    RETURN    ${response_json}

Get Calculation ID
    [Documentation]    Get the calculation ID from a command invocation response
    [Arguments]    ${invocation_response}

    RETURN    ${invocation_response["payload"]["calculation_id"]}

Get Calculation Status
    [Documentation]    Get the status of a calculation
    [Arguments]    ${calculation_id}

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /calculations/${calculation_id}    200
    ${payload}=    Check Response And Get Payload    ${response}

    Check Response Has Attributes    ${payload}    calculations
    VAR    ${calculations}=    ${payload["calculations"]}
    ${n_calculations}=    Get Length    ${calculations}
    Should Be Equal As Integers    ${n_calculations}    1    "Multiple calculations retrieved, when only one requested"
    VAR    ${calculation_status}=    ${calculations[0]}

    RETURN    ${calculation_status}

Check Calculation Successful
    [Documentation]    Check if a calculation has executed successfully
    [Arguments]    ${calculation_id}

    ${calculation_response}=    Get Calculation Status    ${calculation_id}
    Should Be Equal    ${calculation_response["status"]}    successful

    RETURN    ${calculation_response}

Wait Until Calculation Successful
    [Documentation]    Wait until a calculation has been succesfully executed
    [Arguments]    ${calculation_id}

    ${calculation_response}=    Wait Until Keyword Succeeds
    ...    10s
    ...    2s
    ...    Check Calculation Successful
    ...    ${calculation_id}

    Log    Calculation response: ${calculation_response}

    RETURN    ${calculation_response}

Get Output Dataset
    [Documentation]    Get the output dataset for a finished calculation
    [Arguments]    ${calculation_id}

    ${calculation_response}=    Wait Until Calculation Successful    ${calculation_id}

    RETURN    ${calculation_response["output_dataset_id"]}

Get Dataset File Contents
    [Documentation]    Get the contents of a dataset
    [Arguments]    ${dataset_id}

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /datasets/${dataset_id}/download    200
    Should Not Be Empty    ${response.content}

    RETURN    ${response.content}
