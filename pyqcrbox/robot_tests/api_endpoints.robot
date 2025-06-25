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
${ENDPOINTS_API}                    http://127.0.0.1:11000/api
${SESSION_ALIAS}                    QCRBOX_REGISTRY_API_ENDPOINTS

${TEST_CIF_FILE_NAME}               robot_test_cif.cif
${TEST_CIF_FILE}                    ${CURDIR}/test_data/${TEST_CIF_FILE_NAME}

${TEST_INTERACTIVE_SESSION_ID}      ${EMPTY}
${TEST_CALCULATION_ID}              ${EMPTY}
${TEST_DATA_FILE_ID}                ${EMPTY}
${TEST_DATASET_ID}                  ${EMPTY}


*** Test Cases ***
#
#    Admin
#

Check healthz returns health status
    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /healthz    200
    ${content}=    Get Response Content    ${response}
    Check Response Has Attributes    ${content}    status    timestamp
    Should Be Equal    ${content["status"]}    ok

#
#    Applications
#

Check /applications returns list of registered applications
   ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /applications    200
   ${payload}=    Check Response And Get Payload    ${response}

   Check Response Has Attributes    ${payload}    applications
   ${applications}=    Set Variable    ${payload["applications"]}

   ${n_applications}=    Get Length    ${applications}
   Should Be True    ${n_applications} > 0    "No registered applications, which is unexpected"

   FOR    ${application}    IN    @{applications}
   Check Application Response Structure    ${application}
   END

#
#    Commands
#

Check /commands returns a list of commands
   ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /commands    200
   ${payload}=    Check Response And Get Payload    ${response}

   Check Response Has Attributes    ${payload}    commands
   ${commands}=    Set Variable    ${payload["commands"]}
   ${n_commands}=    Get Length    ${commands}
   Should Be True    ${n_commands} > 0    "No commands registered, which is unexpected"

   FOR    ${command}    IN    @{commands}
   Check Command Response Structure    ${command}
   END

Check /commands/id returns a command
   ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /commands/1    200
   ${payload}=    Check Response And Get Payload    ${response}

   Check Response Has Attributes    ${payload}    commands
   ${commands}=    Set Variable    ${payload["commands"]}
   ${n_commands}=    Get Length    ${commands}
   Should Be True    ${n_commands} == 1    "/commands/id returned multiple commands"

   Check Command Response Structure    ${commands[0]}

Check /commands/id returns 404 for invalid id
   ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /commands/0    404

#
#    Datasets
#

Check /datasets can upload a data file to a dataset
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
    Check Datasets Structure    @{datasets}

Check /datasets returns a list of datasets
   ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /datasets    200
   ${payload}=    Check Response And Get Payload    ${response}

   Check Response Has Attributes    ${payload}    datasets
   ${datasets}=    Set Variable    ${payload["datasets"]}
   ${n_datasets}=    Get Length    ${datasets}
   Should Be True    ${n_datasets} > 0    "No datasets retrieved, even though at least one has been uploaded"

   Check Datasets Structure    @{datasets}

Check /datasets/id returns the correct dataset
   ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /datasets/${TEST_DATASET_ID}    200
   ${payload}=    Check Response And Get Payload    ${response}

   Check Response Has Attributes    ${payload}    datasets
   ${datasets}=    Set Variable    ${payload["datasets"]}
   ${n_datasets}=    Get Length    ${datasets}
   Should Be Equal As Integers
   ...    ${n_datasets}
   ...    1
   ...    "/datasets/id response returned an incorrect number of datasets when it should return only the requested dataset"

   ${dataset_id}=    Set Variable    ${datasets[0]["qcrbox_dataset_id"]}
   Should Be Equal    ${TEST_DATASET_ID}    ${dataset_id}    "/datasets/id returned the wrong dataset"

Check /datasets/id/download downloads the dataset
   ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /datasets/${TEST_DATASET_ID}/download    200
   Should Not Be Empty    ${response.content}

   # Compare with original file content
   ${original_file_content}=    Get Binary File    ${TEST_CIF_FILE}
   Should Be Equal    ${original_file_content}    ${response.content}

#
# Interactive sessions
#

Check /interactive-sessions returns a list of sessions
   ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /interactive-sessions    200
   ${payload}=    Check Response And Get Payload    ${response}

   Check Response Has Attributes    ${payload}    interactive_sessions
   ${interactive_sessions}=    Set Variable    ${payload["interactive_sessions"]}
   Check Interactive Sessions Structure    @{interactive_sessions}

Check /interactive-sessions can create an interactive session
    # Create request body for interactive session
    ${input_file}=    Create Dictionary    data_file_id=${TEST_DATA_FILE_ID}
    ${arguments}=    Create Dictionary    input_file=${input_file}
    ${request_body}=    Create Dictionary
    ...    application_slug=olex2
    ...    application_version=1.5-alpha
    ...    arguments=${arguments}

    ${response}=    Send API Request
    ...    POST
    ...    ${SESSION_ALIAS}
    ...    /interactive-sessions
    ...    201
    ...    json_data=${request_body}
    ${payload}=    Check Response And Get Payload    ${response}

    Sleep    5s    "Waiting for interactive session to be registered and start"

    Check Response Has Attributes    ${payload}    interactive_session_id
    Set Suite Variable    ${TEST_INTERACTIVE_SESSION_ID}    ${payload["interactive_session_id"]}

Check /interactive-sessions returns an error when client is busy
   ${input_file}=    Create Dictionary    data_file_id=${TEST_DATA_FILE_ID}
   ${arguments}=    Create Dictionary    input_file=${input_file}
   ${request_body}=    Create Dictionary
   ...    application_slug=olex2
   ...    application_version=1.5-alpha
   ...    arguments=${arguments}

   ${response}=    Send API Request
   ...    POST
   ...    ${SESSION_ALIAS}
   ...    /interactive-sessions
   ...    500
   ...    json_data=${request_body}

Check /interactive-sessions fails for incorrect application
   ${input_file}=    Create Dictionary    data_file_id=${TEST_DATA_FILE_ID}
   ${arguments}=    Create Dictionary    input_file=${input_file}
   ${request_body}=    Create Dictionary
   ...    application_slug=olex-999
   ...    application_version=1.5-alpha
   ...    arguments=${arguments}
   ${response}=    Send API Request
   ...    POST
   ...    ${SESSION_ALIAS}
   ...    /interactive-sessions
   ...    400
   ...    json_data=${request_body}
   ${content}=    Get Response Content    ${response}

   Check Response Has Attributes    ${content}    status    error
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
   ${payload}=    Check Response And Get Payload    ${response}

   Check Response Has Attributes    ${payload}    interactive_sessions
   ${interactive_sessions}=    Set Variable    ${payload["interactive_sessions"]}
   ${n_sessions}=    Get Length    ${interactive_sessions}
   Should Be Equal As Integers
   ...    ${n_sessions}
   ...    1
   ...    "/interactive-sessions/id response returned an incorrect number of sessions when it should return only the requested session"

   Check Interactive Sessions Structure    @{interactive_sessions}

Check /interactive-sessions/id returns 404 for incorrect id
   ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /interactive-sessions/999999    404
   ${content}=    Get Response Content    ${response}

   Check Response Has Attributes    ${content}    status    error
   Should Be Equal    ${content["status"]}    error

   ${error_payload}=    Set Variable    ${content["error"]}
   Check Response Has Attributes    ${error_payload}    code    message    details
   Should Be Equal As Integers    ${error_payload["code"]}    404

Check /interactive-sessions/id can close an interactive session
    Should Not Be Empty
    ...    ${TEST_INTERACTIVE_SESSION_ID}
    ...    Earlier test to start an interactive session failed. Cannot run this test.
    ${response}=    Send API Request
    ...    POST
    ...    ${SESSION_ALIAS}
    ...    /interactive-sessions/${TEST_INTERACTIVE_SESSION_ID}/close
    ...    200
    ${payload}=    Check Response And Get Payload    ${response}

    Check Response Has Attributes    ${payload}    interactive_sessions
    ${interactive_sessions}=    Set Variable    ${payload["interactive_sessions"]}
    ${n_sessions}=    Get Length    ${interactive_sessions}
    Should Be Equal As Integers    ${n_sessions}    1    "Close interactive session should return the closed session"

    ${closed_session}=    Set Variable    ${interactive_sessions[0]}
    Check Response Has Attributes    ${closed_session}    session_id    status    output_dataset_id
    Should Be Equal    ${closed_session["session_id"]}    ${TEST_INTERACTIVE_SESSION_ID}

#
#    Calculations
#

Check /calculations returns a list of calculations
   ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /calculations    200
   ${payload}=    Check Response And Get Payload    ${response}

   Check Response Has Attributes    ${payload}    calculations
   ${calculations}=    Set Variable    ${payload["calculations"]}
   ${n_calculations}=    Get Length    ${calculations}
   Should Be True    ${n_calculations} > 0    "No calculations retrieved, when we are expecting at least 1"

   Check Calculations Structure    ${calculations}
   ${test_calculation_id}=    Set Variable    ${calculations[0]["calculation_id"]}
   Set Suite Variable    ${TEST_CALCULATION_ID}    ${test_calculation_id}

Check /calculation/id returns a calculation
   ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /calculations/${TEST_CALCULATION_ID}    200
   ${payload}=    Check Response And Get Payload    ${response}

   Check Response Has Attributes    ${payload}    calculations
   ${calculations}=    Set Variable    ${payload["calculations"]}
   ${n_calculations}=    Get Length    ${calculations}
   Should Be Equal As Integers    ${n_calculations}    1    "Multiple calculations retrieved, when only one requested"

   Check Calculations Structure    ${calculations}

Check /calculations/id returns 404 for incorrect id
   ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /calculations/-1    404
   ${content}=    Get Response Content    ${response}

   Check Response Has Attributes    ${content}    status    error
   Should Be Equal    ${content["status"]}    error

   ${error_payload}=    Set Variable    ${content["error"]}
   Check Response Has Attributes    ${error_payload}    code    message    details
   Should Be Equal As Integers    ${error_payload["code"]}    404

#
# Datasets -- check we can delete the file
#

Check /datasets/id can delete a dataset
    ${response}=    Send API Request    DELETE    ${SESSION_ALIAS}    /datasets/${TEST_DATASET_ID}    204

Check /datasets/id returns 404 for deleted dataset
   ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /datasets/${TEST_DATASET_ID}    404
   ${content}=    Get Response Content    ${response}

   Check Response Has Attributes    ${content}    status    error
   Should Be Equal    ${content["status"]}    error

   ${error_payload}=    Set Variable    ${content["error"]}
   Check Response Has Attributes    ${error_payload}    code    message    details
   Should Be Equal As Integers    ${error_payload["code"]}    404

Check /datasets/id/download returns 404 for deleted dataset
   ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /datasets/${TEST_DATASET_ID}/download    404
   ${content}=    Get Response Content    ${response}

   Check Response Has Attributes    ${content}    status    error
   Should Be Equal    ${content["status"]}    error

   ${error_payload}=    Set Variable    ${content["error"]}
   Check Response Has Attributes    ${error_payload}    code    message    details
   Should Be Equal As Integers    ${error_payload["code"]}    404


*** Keywords ***
Setup suite
    Create API Session    ${SESSION_ALIAS}    ${ENDPOINTS_API}
    Log datetime information
    Log    Starting test suite

Teardown suite
    Log datetime information
    Log    Test suite completed

Check Application Response Structure
    [Arguments]    ${application}

    Log    ${application}

    Check Response Has Attributes
    ...    ${application}
    ...    name
    ...    slug
    ...    version
    ...    description
    ...    email
    ...    doi
    ...    gui_port
    ...    url
    ...    registered_at
    ...    commands
    FOR    ${command}    IN    @{application['commands']}
        Check Command Response Structure    ${command}
    END

Check Command Response Structure
    [Arguments]    ${command}

    Log    ${command}

    Check Response Has Attributes
    ...    ${command}
    ...    name
    ...    description
    ...    implemented_as
    ...    parameters
    ...    id
    ...    application_id
    ...    application
    ...    version
    ...    cmd_name
    ...    merge_cif_su
    ...    doi

Check Datasets Structure
    [Arguments]    @{datasets}
    FOR    ${dataset}    IN    @{datasets}
        Check Response Has Attributes    ${dataset}    qcrbox_dataset_id    data_files
    END

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
    END

Check Interactive Sessions Structure
    [Arguments]    @{interactive_sessions}

    FOR    ${interactive_session}    IN    @{interactive_sessions}
        Check Response Has Attributes
        ...    ${interactive_session}
        ...    session_id
        ...    client_private_inbox
        ...    application_slug
        ...    application_version
        ...    command_name
        ...    arguments
    END
