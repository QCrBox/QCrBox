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
${REGISTRY_ADDRESS}         %{QCRBOX_BIND_ADDRESS=127.0.0.1}
${REGISTRY_PORT}            %{QCRBOX_REGISTRY_PORT=11000}
${ENDPOINTS_API}            http://${REGISTRY_ADDRESS}:${REGISTRY_PORT}/api
${SESSION_ALIAS}            QCRBOX_REGISTRY_API_ENDPOINTS

${TEST_CALCULATION_ID}      ${EMPTY}


*** Test Cases ***
Check /calculations returns a list of calculations
    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /calculations    200
    ${payload}=    Check Response Structure And Get Payload    ${response}

    Check Response Content Has Attributes    ${payload}    calculations
    ${calculations}=    Set Variable    ${payload["calculations"]}
    ${n_calculations}=    Get Length    ${calculations}
    Should Be True    ${n_calculations} > 0    "No calculations retrieved, when we are expecting at least 1"

    Check Calculations Structure    ${calculations}
    ${test_calculation_id}=    Set Variable    ${calculations[0]["calculation_id"]}
    Set Suite Variable    ${TEST_CALCULATION_ID}    ${test_calculation_id}

Check /calculation/id returns a calculation
    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /calculations/${TEST_CALCULATION_ID}    200
    ${payload}=    Check Response Structure And Get Payload    ${response}

    Check Response Content Has Attributes    ${payload}    calculations
    ${calculations}=    Set Variable    ${payload["calculations"]}
    ${n_calculations}=    Get Length    ${calculations}
    Should Be Equal As Integers    ${n_calculations}    1    "Multiple calculations retrieved, when only one requested"

    Check Calculations Structure    ${calculations}

Check /calculations/id returns 404 for incorrect id
    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /calculations/-1    404
    ${content}=    Decode Response Content    ${response}

    Check Response Content Has Attributes    ${content}    status    error
    Should Be Equal    ${content["status"]}    error

    ${error_payload}=    Set Variable    ${content["error"]}
    Check Response Content Has Attributes    ${error_payload}    code    message    details
    Should Be Equal As Integers    ${error_payload["code"]}    404


*** Keywords ***
Setup Suite
    Create API Session    ${SESSION_ALIAS}    ${ENDPOINTS_API}
    Log Datetime Information
    Log    Starting test suite

Teardown Suite
    Log Datetime Information
    Log    Test suite completed
