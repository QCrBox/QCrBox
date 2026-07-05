*** Settings ***
Documentation
...    Test suite for the management API endpoints unrelated to commands

Resource    resources/keywords.resource

Suite Setup         Setup Suite
Suite Teardown      Teardown Suite
Test Timeout        2 minutes

*** Variables ***
${REGISTRY_ADDRESS}         %{QCRBOX_BIND_ADDRESS=127.0.0.1}
${REGISTRY_PORT}            %{QCRBOX_REGISTRY_PORT=11000}
${ENDPOINTS_API}            http://${REGISTRY_ADDRESS}:${REGISTRY_PORT}/api
${SESSION_ALIAS}            QCRBOX_REGISTRY_API_ENDPOINTS

${TEST_CIF_FILE_NAME}       robot_test_cif.cif
${TEST_JSON_FILE_NAME}      robot_test_json.json
${TEST_CIF_FILE}            ${CURDIR}/test_data/${TEST_CIF_FILE_NAME}
${TEST_JSON_FILE}           ${CURDIR}/test_data/${TEST_JSON_FILE_NAME}

${TEST_JSON_FILE_ID}        ${EMPTY}
${TEST_DATASET_ID}          ${EMPTY}


*** Test Cases ***
Check that registered applications can be requested in the correct format
    [Documentation]    The applications API should return the registered applications

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /applications    200
    ${payload}=    Check Response Structure And Get Payload    ${response}
    Check Response Content Has Attributes    ${payload}    applications
    VAR    ${applications}=    ${payload["applications"]}

    ${n_applications}=    Get Length    ${applications}
    Should Be True    ${n_applications} > 0    "No registered applications, which is unexpected"
    FOR    ${application}    IN    @{applications}
        Check Application Response Structure    ${application}
    END

Check that container instances can be requested in the correct format
    [Documentation]    The container-instances API should return the tracked live application containers

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /container-instances    200
    ${payload}=    Check Response Structure And Get Payload    ${response}
    Check Response Content Has Attributes    ${payload}    container_instances
    VAR    ${instances}=    ${payload["container_instances"]}

    ${n_instances}=    Get Length    ${instances}
    Should Be True    ${n_instances} > 0    "No tracked container instances, which is unexpected"
    FOR    ${instance}    IN    @{instances}
        Dictionary Should Contain Key    ${instance}    client_id
        Dictionary Should Contain Key    ${instance}    application_slug
        Dictionary Should Contain Key    ${instance}    application_version
        Dictionary Should Contain Key    ${instance}    status
        Dictionary Should Contain Key    ${instance}    last_seen
        Should Be True    "${instance['status']}" in ("idle", "busy", "gone")    "Unexpected instance status"
    END

It should be possible to create a dataset by uploading a cif
    [Documentation]    Check that the datasets API will create a dataset

    ${datasets}=    Upload Cif    ${TEST_CIF_FILE}    ${TEST_CIF_FILE_NAME}
    VAR    ${test_dataset_id}=    ${datasets[0]["qcrbox_dataset_id"]}
    VAR    ${TEST_DATASET_ID}=    ${test_dataset_id}    scope=SUITE

    Check Datasets Structure    @{datasets}

Append a generic data file to a dataset
    [Documentation]    Append a JSON file to the dataset from the previous test case

    ${file_contents}=    Get Binary File    ${TEST_JSON_FILE}
    VAR    &{files}=    ${TEST_JSON_FILE_NAME}=${file_contents}

    Send API Request    POST    ${SESSION_ALIAS}    /data-files    201    files=${files}
    ${response}=    Send API Request
    ...    POST
    ...    ${SESSION_ALIAS}
    ...    /datasets/${TEST_DATASET_ID}/append
    ...    201
    ...    files=${files}
    ${payload}=    Check Response Structure And Get Payload    ${response}
    Check Response Content Has Attributes    ${payload}    datasets    data_files    appended_file

    ${n_data_files}=    Get Length    ${payload["datasets"][0]["data_files"]}
    Should Be Equal As Integers    ${n_data_files}    2    "Incorrect number of files in appended dataset"
    VAR    ${TEST_JSON_FILE_ID}=
    ...    ${payload["datasets"][0]["data_files"]["${TEST_JSON_FILE_NAME}"]["qcrbox_file_id"]}
    ...    scope=SUITE

Get all datasets in the QCrBox data manager
    [Documentation]    Query the datasets API to get a list of uploaded datasets

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /datasets    200
    ${payload}=    Check Response Structure And Get Payload    ${response}

    Check Response Content Has Attributes    ${payload}    datasets
    VAR    ${datasets}=    ${payload["datasets"]}
    ${n_datasets}=    Get Length    ${datasets}
    Should Be True    ${n_datasets} > 0    No datasets retrieved, even though at least one has been uploaded
    Check Datasets Structure    @{datasets}

Query the details about a single dataset
    [Documentation]    Send a request for a single dataset

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /datasets/${TEST_DATASET_ID}    200
    ${payload}=    Check Response Structure And Get Payload    ${response}
    Check Response Content Has Attributes    ${payload}    datasets    data_files

    ${n_datasets}=    Get Length    ${payload["datasets"]}
    Should Be Equal As Integers
    ...    ${n_datasets}
    ...    1
    ...    Incorrect number of datasets returned from the API
    Should Be Equal
    ...    ${TEST_DATASET_ID}
    ...    ${payload["datasets"][0]["qcrbox_dataset_id"]}
    ...    Incorrect dataset returned from API

Delete the appended data file from the dataset
    [Documentation]    Check we can delete only the data file and not the dataset

    Send API Request    DELETE    ${SESSION_ALIAS}    /data-files/${TEST_JSON_FILE_ID}    204
    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /datasets/${TEST_DATASET_ID}    200

    ${payload}=    Check Response Structure And Get Payload    ${response}
    Check Response Content Has Attributes    ${payload}    datasets
    ${n_data_files}=    Get Length    ${payload["datasets"][0]["data_files"]}
    Should Be Equal As Integers    ${n_data_files}    1    The requested data file was not removed from the dataset

Download the cif file from the dataset
    [Documentation]    Download the dataset which contains only a cif. This test will fail if a .zip is downloaded

    ${dataset_contents}=    Get Dataset File Contents    ${TEST_DATASET_ID}
    ${original_file_content}=    Get Binary File    ${TEST_CIF_FILE}
    ${original_file_content}=    Convert To String    ${original_file_content}
    Should Be Equal    ${original_file_content}    ${dataset_contents}

Get a list of registered commands
    [Documentation]    Check the commands endpoint returns a correctly structured list

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /commands    200
    ${payload}=    Check Response Structure And Get Payload    ${response}
    Check Response Content Has Attributes    ${payload}    commands

    VAR    ${commands}=    ${payload["commands"]}
    ${n_commands}=    Get Length    ${commands}
    Should Be True    ${n_commands} > 0    No commands registered, which is unexpected
    FOR    ${command}    IN    @{commands}
        Check Command Response Structure    ${command}
    END

Check a specific command can be queried
    [Documentation]    Check the commands endpoint returns a correctly structured response for a query about a command

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /commands/1    200
    ${payload}=    Check Response Structure And Get Payload    ${response}
    Check Response Content Has Attributes    ${payload}    commands

    VAR    ${commands}=    ${payload["commands"]}
    ${n_commands}=    Get Length    ${commands}
    Should Be True    ${n_commands} == 1    Multiple commands have been returned when expecting only one
    Check Command Response Structure    ${commands[0]}

A 404 should be returned for an invalid command id
    [Documentation]    Check that the commands endpoints returns a 404 when an incorrect id is used

    Send API Request    GET    ${SESSION_ALIAS}    /commands/0    404

Delete a dataset
    [Documentation]    We should be able to delete a dataset from the data manager

    Delete Cif Dataset    ${TEST_DATASET_ID}

Expect a 404 response when trying to delete a non-existing dataset
    [Documentation]    If we try re-deleting the last dataset it should return a 404

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /datasets/${TEST_DATASET_ID}    404
    ${content}=    Decode Response Content    ${response}
    Check Response Content Has Attributes    ${content}    status    error

    Should Be Equal    ${content["status"]}    error
    VAR    ${error_payload}=    ${content["error"]}
    Check Response Content Has Attributes    ${error_payload}    code    message    details
    Should Be Equal As Integers    ${error_payload["code"]}    404

Expect a 404 response when trying to download a non-existing dataset
    [Documentation]    If we try downloading the deleted dataset it should return a 404

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /datasets/${TEST_DATASET_ID}/download    404
    ${content}=    Decode Response Content    ${response}
    Check Response Content Has Attributes    ${content}    status    error

    Should Be Equal    ${content["status"]}    error
    VAR    ${error_payload}=    ${content["error"]}
    Check Response Content Has Attributes    ${error_payload}    code    message    details
    Should Be Equal As Integers    ${error_payload["code"]}    404


*** Keywords ***
Setup Suite
    [Documentation]    Setup the test environment for this suite

    Create API Session    ${SESSION_ALIAS}    ${ENDPOINTS_API}
    Check Suite Can Run
    Log Datetime Information
    Log    Starting test suite

Teardown Suite
    [Documentation]    Teardown the test environment for this suite

    Log Datetime Information
    Log    Test suite completed
