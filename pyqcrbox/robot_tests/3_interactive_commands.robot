*** Settings ***
Documentation
...                 Test suite for the API endpoints of the QCrBox registry

Library    Collections
Library    DateTime
Library    OperatingSystem
Library    JSONLibrary
Resource    resources/api.resource
Resource    resources/keywords.resource
Resource    resources/responses.resource

Suite Setup         Setup Suite
Suite Teardown      Teardown Suite
Test Timeout        2 minutes

*** Variables ***
${REGISTRY_ADDRESS}                 %{QCRBOX_BIND_ADDRESS=127.0.0.1}
${REGISTRY_PORT}                    %{QCRBOX_REGISTRY_PORT=11000}
${ENDPOINTS_API}                    http://${REGISTRY_ADDRESS}:${REGISTRY_PORT}/api
${SESSION_ALIAS}                    QCRBOX_REGISTRY_API_ENDPOINTS

${TEST_CIF_FILE_NAME}               robot_test_cif.cif
${TEST_CIF_FILE}                    ${CURDIR}/test_data/${TEST_CIF_FILE_NAME}

${TEST_INTERACTIVE_SESSION_ID}      ${EMPTY}
${TEST_DATA_FILE_ID}                ${EMPTY}
${TEST_DATASET_ID}                  ${EMPTY}
${TEST_OUTPUT_DATSET_ID_1}          ${EMPTY}
${TEST_OUTPUT_DATSET_ID_2}          ${EMPTY}


*** Test Cases ***
Check /interactive-sessions can create an interactive session
    # Create request body for interactive session
    ${input_file}=    Create Dictionary    data_file_id=${TEST_DATA_FILE_ID}
    ${arguments}=    Create Dictionary    input_file=${input_file}
    ${request_body}=    Create Dictionary
    ...    application_slug=dummy_gui
    ...    application_version=0.1.0
    ...    command_arguments=${arguments}

    ${response}=    Send API Request
    ...    POST
    ...    ${SESSION_ALIAS}
    ...    /interactive-sessions
    ...    201
    ...    json_data=${request_body}
    ${payload}=    Check Response Structure And Get Payload    ${response}

    Sleep    1s    "Waiting for interactive session to be submitted to registry"

    Check Response Content Has Attributes    ${payload}    interactive_session_id
    Set Suite Variable    ${TEST_INTERACTIVE_SESSION_ID}    ${payload["interactive_session_id"]}

Check that interactive session is still running
    Sleep    2s    "Waiting for interactive session to start running"
    ${status}=    Get Calculation Status    ${TEST_INTERACTIVE_SESSION_ID}
    Should Be Equal
    ...    ${status}
    ...    running
    ...    "Interactive session is not running, probably due to a launch failure after submission"

Check /interactive-sessions returns a list of sessions
    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /interactive-sessions    200
    ${payload}=    Check Response Structure And Get Payload    ${response}

    Check Response Content Has Attributes    ${payload}    interactive_sessions
    ${interactive_sessions}=    Set Variable    ${payload["interactive_sessions"]}
    Check Interactive Sessions Structure    @{interactive_sessions}

Check /interactive-sessions returns an error when client is busy
    ${input_file}=    Create Dictionary    data_file_id=${TEST_DATA_FILE_ID}
    ${arguments}=    Create Dictionary    input_file=${input_file}
    ${request_body}=    Create Dictionary
    ...    application_slug=dummy_gui
    ...    application_version=0.1.0
    ...    command_arguments=${arguments}

    ${response}=    Send API Request
    ...    POST
    ...    ${SESSION_ALIAS}
    ...    /interactive-sessions
    ...    500
    ...    json_data=${request_body}

Check /interactive-sessions/id can close an interactive session
   Should Not Be Empty
   ...    ${TEST_INTERACTIVE_SESSION_ID}
   ...    Earlier test to start an interactive session failed. Cannot run this test.
   ${response}=    Send API Request
   ...    POST
   ...    ${SESSION_ALIAS}
   ...    /interactive-sessions/${TEST_INTERACTIVE_SESSION_ID}/close
   ...    200
   ${payload}=    Check Response Structure And Get Payload    ${response}

   Check Response Content Has Attributes    ${payload}    interactive_sessions
   ${interactive_sessions}=    Set Variable    ${payload["interactive_sessions"]}
   ${n_sessions}=    Get Length    ${interactive_sessions}
   Should Be Equal As Integers    ${n_sessions}    1    "Close interactive session should return the closed session"

   ${closed_session}=    Set Variable    ${interactive_sessions[0]}
   Check Response Content Has Attributes    ${closed_session}    session_id    status    output_dataset_id    error_msg
   Should Be Equal    ${closed_session["session_id"]}    ${TEST_INTERACTIVE_SESSION_ID}
   Set Suite Variable    ${TEST_OUTPUT_DATSET_ID_1}    ${closed_session["output_dataset_id"]}

Check /interactive-sessions can open a new session after the last was closed
   ${input_file}=    Create Dictionary    data_file_id=${TEST_DATA_FILE_ID}
   ${arguments}=    Create Dictionary    input_file=${input_file}
   ${request_body}=    Create Dictionary
   ...    application_slug=dummy_gui
   ...    application_version=0.1.0
   ...    command_arguments=${arguments}

   ${response}=    Send API Request
   ...    POST
   ...    ${SESSION_ALIAS}
   ...    /interactive-sessions
   ...    201
   ...    json_data=${request_body}
   ${invoke_payload}=    Check Response Structure And Get Payload    ${response}

   Sleep    1s    "Waiting for interactive session to be registered and start"

   Check Response Content Has Attributes    ${invoke_payload}    interactive_session_id

   ${response}=    Send API Request
   ...    POST
   ...    ${SESSION_ALIAS}
   ...    /interactive-sessions/${invoke_payload['interactive_session_id']}/close
   ...    200
   ${close_payload}=    Check Response Structure And Get Payload    ${response}

   Check Response Content Has Attributes    ${close_payload}    interactive_sessions
   ${interactive_sessions}=    Set Variable    ${close_payload["interactive_sessions"]}
   ${n_sessions}=    Get Length    ${interactive_sessions}
   Should Be Equal As Integers    ${n_sessions}    1    "Close interactive session should return the closed session"

   ${closed_session}=    Set Variable    ${interactive_sessions[0]}
   Check Response Content Has Attributes    ${closed_session}    session_id    status    output_dataset_id    error_msg
   Should Be Equal    ${closed_session["session_id"]}    ${invoke_payload['interactive_session_id']}
   Set Suite Variable    ${TEST_OUTPUT_DATSET_ID_2}    ${closed_session["output_dataset_id"]}

Check /interactive-sessions fails for incorrect application
   ${input_file}=    Create Dictionary    data_file_id=${TEST_DATA_FILE_ID}
   ${arguments}=    Create Dictionary    input_file=${input_file}
   ${request_body}=    Create Dictionary
   ...    application_slug=olex-999
   ...    application_version=1.5-alpha
   ...    command_arguments=${arguments}
   ${response}=    Send API Request
   ...    POST
   ...    ${SESSION_ALIAS}
   ...    /interactive-sessions
   ...    400
   ...    json_data=${request_body}
   ${content}=    Decode Response Content    ${response}

   Check Response Content Has Attributes    ${content}    status    error
   Should Be Equal    ${content["status"]}    error

Check /interactive-sessions/id returns interactive session
   Should Not Be Empty
   ...    ${TEST_INTERACTIVE_SESSION_ID}
   ...    Earlier test to start an interactive session failed. Cannot run this test.
   ${response}=    Send API Request
   ...    GET
   ...    ${SESSION_ALIAS}
   ...    /interactive-sessions/${TEST_INTERACTIVE_SESSION_ID}
   ...    200
   ${payload}=    Check Response Structure And Get Payload    ${response}

   Check Response Content Has Attributes    ${payload}    interactive_sessions
   ${interactive_sessions}=    Set Variable    ${payload["interactive_sessions"]}
   ${n_sessions}=    Get Length    ${interactive_sessions}
   Should Be Equal As Integers
   ...    ${n_sessions}
   ...    1
   ...    "/interactive-sessions/id response returned an incorrect number of sessions when it should return only the requested session"

   Check Interactive Sessions Structure    @{interactive_sessions}

Check /interactive-sessions/id returns 404 for incorrect id
   ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /interactive-sessions/999999    404
   ${content}=    Decode Response Content    ${response}

   Check Response Content Has Attributes    ${content}    status    error
   Should Be Equal    ${content["status"]}    error

   ${error_payload}=    Set Variable    ${content["error"]}
   Check Response Content Has Attributes    ${error_payload}    code    message    details
   Should Be Equal As Integers    ${error_payload["code"]}    404

Check /commands can open an interactive session instead of /interactive-sessions
   ${input_file}=    Create Dictionary    data_file_id=${TEST_DATA_FILE_ID}
   ${arguments}=    Create Dictionary    input_file=${input_file}
   ${request_body}=    Create Dictionary
   ...    application_slug=dummy_gui
   ...    application_version=0.1.0
   ...    command_name=interactive_session
   ...    command_arguments=${arguments}

   ${response}=    Send API Request
   ...    POST
   ...    ${SESSION_ALIAS}
   ...    /commands
   ...    201
   ...    json_data=${request_body}
   ${invoke_payload}=    Check Response Structure And Get Payload    ${response}

   Sleep    1s    "Waiting for interactive session to be registered and start"

   Check Response Content Has Attributes    ${invoke_payload}    calculation_id

   ${response}=    Send API Request
   ...    POST
   ...    ${SESSION_ALIAS}
   ...    /interactive-sessions/${invoke_payload['calculation_id']}/close
   ...    200
   ${close_payload}=    Check Response Structure And Get Payload    ${response}

   Check Response Content Has Attributes    ${close_payload}    interactive_sessions
   ${interactive_sessions}=    Set Variable    ${close_payload["interactive_sessions"]}
   ${n_sessions}=    Get Length    ${interactive_sessions}
   Should Be Equal As Integers    ${n_sessions}    1    "Close interactive session should return the closed session"

   ${closed_session}=    Set Variable    ${interactive_sessions[0]}
   Check Response Content Has Attributes    ${closed_session}    session_id    status    output_dataset_id    error_msg
   Should Be Equal    ${closed_session["session_id"]}    ${invoke_payload['calculation_id']}


*** Keywords ***
Get Calculation Status
    [Arguments]    ${calculation_id}

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /calculations/${calculation_id}    200
    ${payload}=    Check Response Structure And Get Payload    ${response}

    Check Response Content Has Attributes    ${payload}    calculations
    ${calculations}=    Set Variable    ${payload["calculations"]}
    ${n_calculations}=    Get Length    ${calculations}
    Should Be Equal As Integers    ${n_calculations}    1    "Multiple calculations retrieved, when only one requested"

    Check Calculations Structure    ${calculations}
    ${calculation_status}=    Set Variable    ${calculations[0]}

    RETURN    ${calculation_status['status']}

Setup Suite
    Create API Session    ${SESSION_ALIAS}    ${ENDPOINTS_API}
    Log Datetime Information
    Upload Test Dataset
    Log    Starting test suite

Teardown Suite
    Log Datetime Information
    Delete Test Dataset
    Log    Test suite completed

Upload Test Dataset
    ${file_contents}=    Get Binary File    ${TEST_CIF_FILE}
    ${files}=    Create Dictionary    ${TEST_CIF_FILE_NAME}=${file_contents}

    ${response}=    Send API Request    POST    ${SESSION_ALIAS}    /datasets    201    files=${files}
    ${payload}=    Check Response Structure And Get Payload    ${response}

    Check Response Content Has Attributes    ${payload}    datasets
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
    ${response}=    Send API Request    DELETE    ${SESSION_ALIAS}    /datasets/${TEST_OUTPUT_DATSET_ID_1}    204
    ${response}=    Send API Request    DELETE    ${SESSION_ALIAS}    /datasets/${TEST_OUTPUT_DATSET_ID_2}    204
