*** Settings ***
Documentation
...    Test suite for the calculations API endpoints

Resource    resources/keywords.resource

Suite Setup         Setup Suite
Suite Teardown      Teardown Suite
Test Timeout        2 minutes

*** Variables ***
${REGISTRY_ADDRESS}         %{QCRBOX_BIND_ADDRESS=127.0.0.1}
${REGISTRY_PORT}            %{QCRBOX_REGISTRY_PORT=11000}
${ENDPOINTS_API}            http://${REGISTRY_ADDRESS}:${REGISTRY_PORT}/api
${SESSION_ALIAS}    QCRBOX_REGISTRY_API_ENDPOINTS
${TEST_CALCULATION_ID}      ${EMPTY}


*** Test Cases ***
Get a list of calculations
    [Documentation]    A calculations responses, containing multiple calculations, should be returned

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /calculations    200
    ${payload}=    Check Response Structure And Get Payload    ${response}

    Check Response Content Has Attributes    ${payload}    calculations
    ${calculations}=    Set Variable    ${payload["calculations"]}
    ${n_calculations}=    Get Length    ${calculations}
    Should Be True    ${n_calculations} > 0    "No calculations retrieved, when we are expecting at least 1"

    Check Calculations Structure    ${calculations}
    ${test_calculation_id}=    Set Variable    ${calculations[0]["calculation_id"]}
    VAR    ${TEST_CALCULATION_ID}=    ${test_calculation_id}    scope=suite

Check you can request details for a specific calculation
    [Documentation]    A calculations response, containing a single calculation, should be returned for a correct id

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /calculations/${TEST_CALCULATION_ID}    200
    ${payload}=    Check Response Structure And Get Payload    ${response}

    Check Response Content Has Attributes    ${payload}    calculations
    VAR    ${calculations}=    ${payload["calculations"]}
    ${n_calculations}=    Get Length    ${calculations}
    Should Be Equal As Integers    ${n_calculations}    1    "Multiple calculations retrieved, when only one requested"
    Check Calculations Structure    ${calculations}

Check a 404 is returned for an incorrect calculation id
    [Documentation]    A 404 should be returned by the API if an incorrect id is supplied

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /calculations/-1    404
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
    Log Datetime Information
    Log    Starting test suite

Teardown Suite
    [Documentation]    Teardown the test environment for this suite

    Log Datetime Information
    Log    Test suite completed
