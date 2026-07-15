*** Settings ***
Documentation
...    Test suite for non-interactive commands

Resource    resources/keywords.resource

Suite Setup         Setup Suite
Suite Teardown      Teardown Suite
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
Start a short running non-interactive command
    [Documentation]    Start a short running command in the Dummy CLI application

    VAR    &{input_file}=    data_file_id=${TEST_DATA_FILE_ID}
    VAR    &{arguments}=    input_cif=${input_file}    print_times=3
    ${invoke_response}=    Invoke Command With Arguments    dummy_cli    0.1.0    print_cif    ${arguments}

    ${invoke_payload}=    Check Response Structure And Get Payload    ${invoke_response}
    Check Response Content Has Attributes    ${invoke_payload}    calculation_id
    VAR    ${TEST_CALCULATION_ID}=    ${invoke_payload["calculation_id"]}    scope=SUITE

Check that short command status is successful and returns some output
    [Documentation]    The short command should be successful and return a dataset ID

    ${calculation}=    Wait Until Calculation Successful    ${TEST_CALCULATION_ID}
    VAR    ${TEST_OUTPUT_DATASET_ID}=    ${calculation["output_dataset_id"]}    scope=SUITE
    Should Not Be None    ${TEST_OUTPUT_DATASET_ID}

Download the output dataset from the short running command
    [Documentation]    Ensure we can download the dataset from the non-interactive command

    ${cif_file}=    Get Dataset File Contents    ${TEST_OUTPUT_DATASET_ID}
    Should Not Be Empty    ${cif_file}
    Delete Cif Dataset    ${TEST_OUTPUT_DATASET_ID}

Invoke a long running non-interactive command
    [Documentation]    Start a long running command which will never finish

    VAR    &{arguments}=    dummy="hello"
    ${response}=    Invoke Command With Arguments    dummy_cli    0.1.0    infinite_loop    ${arguments}

    ${payload}=    Check Response Structure And Get Payload    ${response}
    Check Response Content Has Attributes    ${payload}    calculation_id
    VAR    ${TEST_CALCULATION_ID}=    ${payload["calculation_id"]}    scope=SUITE

Check that the long running command is still running
    [Documentation]    The long running command should still be running

    Sleep    5s    "Letting the long running command run"
    ${calculation_status}=    Get Calculation Status    ${TEST_CALCULATION_ID}
    Should Be Equal    ${calculation_status["status"]}    running

Stop the long running command
   [Documentation]    We should be able to prematurely end a long running command

   ${response}=    Send API Request    POST    ${SESSION_ALIAS}    /calculations/${TEST_CALCULATION_ID}/stop    200
   ${payload}=    Check Response Structure And Get Payload    ${response}
   Check Response Content Has Attributes    ${payload}    calculations
   Should Be Equal    ${payload["calculations"][0]["calculation_id"]}    ${TEST_CALCULATION_ID}
   Should Be Equal    ${payload["calculations"][0]["status"]}    successful

Check that the long command has stopped and has returned no output
    [Documentation]    The calculation status should be successful and return no output

    ${calculation_status}=    Check Calculation Successful    ${TEST_CALCULATION_ID}
    Should Be None    ${calculation_status["output_dataset_id"]}

An error should be returned if a dataset ID is used instead of a data file ID
    [Documentation]    Check that we can catch a simple error of passing a dataset ID instead of a data file ID

    VAR    &{input_file}=    data_file_id=${TEST_DATASET_ID}
    VAR    &{arguments}=    input_cif=${input_file}    print_times=3

    ${response}=    Invoke Command With Arguments    dummy_cli    0.1.0    print_cif    ${arguments}
    ${invoke_payload}=    Check Response Structure And Get Payload    ${response}
    Check Response Content Has Attributes    ${invoke_payload}    calculation_id
    VAR    ${calculation_id}=    ${invoke_payload["calculation_id"]}
    Sleep    2s    "Waiting for command to fail before checking status"

    ${calculation_status}=    Get Calculation Status    ${calculation_id}
    Should Be Equal    ${calculation_status["status"]}    failed
    Should Contain     ${calculation_status["status_events"][-1]["extra_info"]["error_msg"]}    is a dataset


Typed artifacts are captured alongside the output cif
    [Documentation]    generate_report_artifacts returns an output cif plus one artifact of every
    ...    kind; all six files must land in one dataset with the correct kinds and be served
    ...    inline with the correct media types.

    VAR    &{input_file}=    data_file_id=${TEST_DATA_FILE_ID}
    VAR    &{arguments}=    input_cif=${input_file}
    ${output_dataset_id}=    Invoke Command And Get Output Dataset ID
    ...    dummy_cli
    ...    0.1.0
    ...    generate_report_artifacts
    ...    ${arguments}

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /datasets/${output_dataset_id}    200
    ${payload}=    Check Response Structure And Get Payload    ${response}
    VAR    ${data_files}=    ${payload["datasets"][0]["data_files"]}
    ${n_files}=    Get Length    ${data_files}
    Should Be Equal As Integers    ${n_files}    6    Expected cif + 5 artifacts in the output dataset

    Should Be Equal    ${data_files["result.cif"]["kind"]}    ${None}
    Should Be Equal    ${data_files["report.txt"]["kind"]}    text
    Should Be Equal    ${data_files["report.svg"]["kind"]}    image
    Should Be Equal    ${data_files["report.html"]["kind"]}    html
    Should Be Equal    ${data_files["structure.cif"]["kind"]}    interactive_structure
    Should Be Equal    ${data_files["graph.json"]["kind"]}    interactive_graph

    Check Data File Content Media Type    ${data_files["result.cif"]["qcrbox_file_id"]}    chemical/x-cif
    Check Data File Content Media Type    ${data_files["report.txt"]["qcrbox_file_id"]}    text/plain; charset=utf-8
    Check Data File Content Media Type    ${data_files["report.svg"]["qcrbox_file_id"]}    image/svg+xml
    Check Data File Content Media Type    ${data_files["report.html"]["qcrbox_file_id"]}    text/html; charset=utf-8
    Check Data File Content Media Type
    ...    ${data_files["structure.cif"]["qcrbox_file_id"]}
    ...    chemical/x-cif
    Check Data File Content Media Type    ${data_files["graph.json"]["qcrbox_file_id"]}    application/json

    [Teardown]    Delete Cif Dataset    ${output_dataset_id}

Artifact-only commands succeed without an output cif
    [Documentation]    generate_report_only returns typed artifacts but no cif; the optional,
    ...    never-written output must be skipped without failing the calculation.

    VAR    &{input_file}=    data_file_id=${TEST_DATA_FILE_ID}
    VAR    &{arguments}=    input_cif=${input_file}
    ${output_dataset_id}=    Invoke Command And Get Output Dataset ID
    ...    dummy_cli
    ...    0.1.0
    ...    generate_report_only
    ...    ${arguments}

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /datasets/${output_dataset_id}    200
    ${payload}=    Check Response Structure And Get Payload    ${response}
    VAR    ${data_files}=    ${payload["datasets"][0]["data_files"]}
    ${n_files}=    Get Length    ${data_files}
    Should Be Equal As Integers    ${n_files}    2    Expected exactly the two written artifacts
    Should Be Equal    ${data_files["report.txt"]["kind"]}    text
    Should Be Equal    ${data_files["graph.json"]["kind"]}    interactive_graph
    Dictionary Should Not Contain Key    ${data_files}    never_written.txt

    [Teardown]    Delete Cif Dataset    ${output_dataset_id}

CLI commands capture their declared outputs
    [Documentation]    report_via_cli writes a text report via a shell pipeline; the declared
    ...    output must be captured into a dataset (this was unsupported before typed outputs).

    VAR    &{input_file}=    data_file_id=${TEST_DATA_FILE_ID}
    VAR    &{arguments}=    input_cif=${input_file}
    ${output_dataset_id}=    Invoke Command And Get Output Dataset ID
    ...    dummy_cli
    ...    0.1.0
    ...    report_via_cli
    ...    ${arguments}

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /datasets/${output_dataset_id}    200
    ${payload}=    Check Response Structure And Get Payload    ${response}
    VAR    ${data_files}=    ${payload["datasets"][0]["data_files"]}
    Should Be Equal    ${data_files["cif_head.txt"]["kind"]}    text
    ${response}=    Send API Request
    ...    GET
    ...    ${SESSION_ALIAS}
    ...    /data-files/${data_files["cif_head.txt"]["qcrbox_file_id"]}/download
    ...    200
    Should Not Be Empty    ${response.text}

    [Teardown]    Delete Cif Dataset    ${output_dataset_id}

A missing required output fails the calculation
    [Documentation]    generate_report_broken declares a required text output which is never
    ...    written; the calculation must report failed instead of silently succeeding.

    VAR    &{input_file}=    data_file_id=${TEST_DATA_FILE_ID}
    VAR    &{arguments}=    input_cif=${input_file}
    ${invoke_response}=    Invoke Command With Arguments    dummy_cli    0.1.0    generate_report_broken    ${arguments}
    ${invoke_payload}=    Check Response Structure And Get Payload    ${invoke_response}
    VAR    ${calculation_id}=    ${invoke_payload["calculation_id"]}

    Wait Until Keyword Succeeds    10s    2s    Check Calculation Failed    ${calculation_id}


*** Keywords ***
Setup Suite
    [Documentation]    Setup the test environment for this suite

    Create API Session    ${SESSION_ALIAS}    ${ENDPOINTS_API}
    Check Suite Can Run
    Log Datetime Information
    Upload Test Dataset
    Log    Starting test suite

Teardown Suite
    [Documentation]    Teardown the test environment for this suite

    Log Datetime Information
    Delete Cif Dataset    ${TEST_DATASET_ID}
    Log    Test suite completed

Upload Test Dataset
    [Documentation]    Upload the shared test CIF to QCrBox

    ${datasets}=    Upload Cif    ${TEST_CIF_FILE}    ${TEST_CIF_FILE_NAME}
    VAR    ${test_dataset_id}=    ${datasets[0]["qcrbox_dataset_id"]}
    VAR    ${TEST_DATASET_ID}=    ${test_dataset_id}    scope=SUITE
    VAR    ${TEST_DATA_FILE_ID}=
    ...    ${datasets[0]["data_files"]["${TEST_CIF_FILE_NAME}"]["qcrbox_file_id"]}
    ...    scope=SUITE
