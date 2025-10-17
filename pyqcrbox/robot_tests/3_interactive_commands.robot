*** Settings ***
Documentation
...    Test suite for interactive commands

Resource    resources/keywords.resource

Suite Setup         Setup Suite
Suite Teardown      Teardown Suite
Test Timeout        2 minutes

*** Variables ***
${REGISTRY_ADDRESS}                 %{QCRBOX_BIND_ADDRESS=127.0.0.1}
${REGISTRY_PORT}                    %{QCRBOX_REGISTRY_PORT=11000}
${ENDPOINTS_API}                    http://${REGISTRY_ADDRESS}:${REGISTRY_PORT}/api
${SESSION_ALIAS}                    QCRBOX_REGISTRY_API_ENDPOINTS

${TEST_CIF_FILE_NAME}               robot_test_cif.cif
${TEST_CIF_FILE}    ${CURDIR}/test_data/${TEST_CIF_FILE_NAME}
${TEST_INTERACTIVE_SESSION_ID}      ${EMPTY}
${TEST_DATA_FILE_ID}                ${EMPTY}
${TEST_DATASET_ID}      ${EMPTY}


*** Test Cases ***
Check an interactive session can be launched
    [Documentation]    Check that an interactive session can be created

    ${payload}=    Invoke Interactive Dummy GUI
    Check Response Content Has Attributes    ${payload}    interactive_session_id
    VAR    ${TEST_INTERACTIVE_SESSION_ID}=    ${payload["interactive_session_id"]}    scope=SUITE

Check that interactive session is still running
    [Documentation]    The calculation status for a running interactive session should be 'running'

    ${status}=    Get Calculation Status    ${TEST_INTERACTIVE_SESSION_ID}
    Should Be Equal
    ...    ${status["status"]}
    ...    running
    ...    "Interactive session is not running, probably due to a launch failure after submission"

Check that you cn get a a list of interactive sessions
    [Documentation]    The /interactive-sessions endpoint should return a list of interactive sessions (past and present)

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /interactive-sessions    200
    ${payload}=    Check Response Structure And Get Payload    ${response}
    Check Response Content Has Attributes    ${payload}    interactive_sessions
    VAR    ${interactive_sessions}=    ${payload["interactive_sessions"]}
    Check Interactive Sessions Structure    @{interactive_sessions}

Make sure two interactive sessions can't run at once
    [Documentation]    The application should report itself as being busy and reject a command request

    VAR    &{input_file}=    data_file_id=${TEST_DATA_FILE_ID}
    VAR    &{arguments}=    input_file=${input_file}
    VAR    &{request_body}=
    ...    application_slug=dummy_gui
    ...    application_version=0.1.0
    ...    command_arguments=${arguments}
    Send API Request
    ...    POST
    ...    ${SESSION_ALIAS}
    ...    /interactive-sessions
    ...    500
    ...    json_data=${request_body}

Ensure an interactive session can be quit and return an output
    [Documentation]    An interactive session should be killable and return some form of output

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
    VAR    ${interactive_sessions}=    ${payload["interactive_sessions"]}
    ${n_sessions}=    Get Length    ${interactive_sessions}
    Should Be Equal As Integers    ${n_sessions}    1    "Close interactive session should return the closed session"

    Check Response Content Has Attributes
    ...    ${interactive_sessions[0]}
    ...    session_id
    ...    status
    ...    output_dataset_id
    ...    error_msg
    Should Be Equal    ${interactive_sessions[0]["session_id"]}    ${TEST_INTERACTIVE_SESSION_ID}
    Delete Cif Dataset    ${interactive_sessions[0]["output_dataset_id"]}

We should be able to invoke a new interactive session
    [Documentation]    An new interactive session should be invokable after the other is closed

    ${payload}=    Invoke Interactive Dummy GUI
    Check Response Content Has Attributes    ${payload}    interactive_session_id

    ${response}=    Send API Request
    ...    POST
    ...    ${SESSION_ALIAS}
    ...    /interactive-sessions/${payload['interactive_session_id']}/close
    ...    200
    ${close_payload}=    Check Response Structure And Get Payload    ${response}
    Check Response Content Has Attributes    ${close_payload}    interactive_sessions
    VAR    ${interactive_sessions}=    ${close_payload["interactive_sessions"]}
    Delete Cif Dataset    ${interactive_sessions[0]["output_dataset_id"]}

Requests for incorrect applications and/or commands should fail
    [Documentation]    If an incorrect application/command/parameter is sent to the API, it should return a failure

    VAR    &{input_file}=    data_file_id=${TEST_DATA_FILE_ID}
    VAR    &{arguments}=    input_file=${input_file}
    VAR    &{request_body}=    application_slug=olex-999
    ...    application_version=1.5-alpha
    ...    command_arguments=${arguments}
    ${response}=    Send API Request
    ...    POST
    ...    ${SESSION_ALIAS}
    ...    /interactive-sessions
    ...    400
    ...    json_data=${request_body}

    # We do this a little differently because we are expecting an error. If we
    # follow the other tests, then the error will fail this test when it should pass
    ${content}=    Decode Response Content    ${response}
    Check Response Content Has Attributes    ${content}    status    error
    Should Be Equal    ${content["status"]}    error

Check that details about a specific interactive session can be gotten
    [Documentation]    Check that the interactive-sessions endpoint can return a specific interactive session

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
    VAR    ${interactive_sessions}=    ${payload["interactive_sessions"]}
    ${n_sessions}=    Get Length    ${interactive_sessions}
    Should Be Equal As Integers
    ...    ${n_sessions}
    ...    1
    ...    "Interactive sessions response returned multiple sessions when it should return only one"
    Check Interactive Sessions Structure    @{interactive_sessions}

Check that an incorrect session id returns a 404
    [Documentation]    The interactive session API should return 404 for an incorrect id

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /interactive-sessions/999999    404
    ${content}=    Decode Response Content    ${response}
    Check Response Content Has Attributes    ${content}    status    error
    Should Be Equal    ${content["status"]}    error

    VAR    ${error_payload}=    ${content["error"]}
    Check Response Content Has Attributes    ${error_payload}    code    message    details
    Should Be Equal As Integers    ${error_payload["code"]}    404

The commands API should also be able to launch an interactive session
    [Documentation]    This checks that an interactive sessions can be started with the commands endpoint

    VAR    &{input_file}=    data_file_id=${TEST_DATA_FILE_ID}
    VAR    &{arguments}=    input_file=${input_file}
    ${response}=    Invoke Command With Arguments    dummy_gui    0.1.0    interactive_session    ${arguments}
    ${invoke_payload}=    Check Response Structure And Get Payload    ${response}
    Check Response Content Has Attributes    ${invoke_payload}    calculation_id
    Sleep    5s    "Waiting for interactive session to be registered and start"

    ${response}=    Send API Request
    ...    POST
    ...    ${SESSION_ALIAS}
    ...    /interactive-sessions/${invoke_payload['calculation_id']}/close
    ...    200
    ${close_payload}=    Check Response Structure And Get Payload    ${response}
    Check Response Content Has Attributes    ${close_payload}    interactive_sessions
    VAR    ${interactive_sessions}=    ${close_payload["interactive_sessions"]}
    Should Be Equal    ${interactive_sessions[0]["session_id"]}    ${invoke_payload['calculation_id']}


Interactive sessions should be closable if they don't return an output dataset
    [Documentation]    This checks that an interactive sessions closes properly when there is no output to return

    VAR    &{input_file}=    data_file_id=${TEST_DATA_FILE_ID}
    VAR    &{arguments}=    input_file=${input_file}
    ${response}=    Invoke Command With Arguments    dummy_gui    0.1.0    no_output    ${arguments}
    ${invoke_payload}=    Check Response Structure And Get Payload    ${response}
    Check Response Content Has Attributes    ${invoke_payload}    calculation_id
    Sleep    5s    "Waiting for interactive session to be registered and start"

    ${response}=    Send API Request
    ...    POST
    ...    ${SESSION_ALIAS}
    ...    /interactive-sessions/${invoke_payload['calculation_id']}/close
    ...    200
    ${close_payload}=    Check Response Structure And Get Payload    ${response}
    Check Response Content Has Attributes    ${close_payload}    interactive_sessions
    VAR    ${interactive_sessions}=    ${close_payload["interactive_sessions"]}
    Should Be Equal    ${interactive_sessions[0]["session_id"]}    ${invoke_payload['calculation_id']}

*** Keywords ***
Setup Suite
    [Documentation]    Setup the test environment for this suite

    Create API Session    ${SESSION_ALIAS}    ${ENDPOINTS_API}
    Check Suite Can Run
    Log Datetime Information

    ${dataset}=    Upload Cif    ${TEST_CIF_FILE}    ${TEST_CIF_FILE_NAME}
    VAR    ${TEST_DATASET_ID}=    ${dataset[0]["qcrbox_dataset_id"]}    scope=SUITE
    VAR    ${TEST_DATA_FILE_ID}=
    ...    ${dataset[0]["data_files"]["${TEST_CIF_FILENAME}"]["qcrbox_file_id"]}
    ...    scope=SUITE

    Log    Starting test suite

Teardown Suite
    [Documentation]    Teardown the test environment for this suite

    Log Datetime Information
    Delete Cif Dataset    ${TEST_DATASET_ID}
    Log    Test suite completed

Invoke Interactive Dummy GUI
    [Documentation]    Invoke an interactive session for the Dummy GUI application

    VAR    &{input_file}=    data_file_id=${TEST_DATA_FILE_ID}
    VAR    &{arguments}=    input_file=${input_file}
    ${response}=    Invoke Command With Arguments
    ...    dummy_gui
    ...    0.1.0
    ...    interactive_session
    ...    ${arguments}
    ...    endpoint=/interactive-sessions
    ${payload}=    Check Response Structure And Get Payload    ${response}
    Sleep    5s    "Waiting for interactive session to be submitted to registry and run"

    RETURN    ${payload}
