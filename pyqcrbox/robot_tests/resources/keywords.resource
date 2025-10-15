*** Settings ***
Documentation
...    Generic keywords which are used throughout the Robot Framework test suites.

Library     DateTime
Library     ../libraries/my_keywords.py
Resource    api.resource
Resource    datasets.resource
Resource    calculations.resource
Resource    responses.resource

*** Keywords ***
Log Datetime Information
    [Documentation]    Log the current date and time

    ${date}=    Get Current Date
    Log    ${date}

Check Test Applications Available
    [Documentation]    Check that Dummy CLI and Dummy GUI applications are available

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /applications    200
    ${payload}=    Check Response Structure And Get Payload    ${response}

    Check Response Content Has Attributes    ${payload}    applications
    ${n_applications}=    Get Length    ${payload["applications"]}
    Should Be True    ${n_applications} > 0    "No registered applications, which is unexpected"

    VAR    @{required_applications}=    dummy_cli    dummy_gui
    VAR    @{available_application_slugs}=    ${EMPTY}
    FOR    ${application}    IN    @{payload["applications"]}
        Check Application Response Structure    ${application}
        Append To List    ${available_application_slugs}    ${application["slug"]}
    END

    List Should Contain Sub List
    ...    ${available_application_slugs}
    ...    ${required_applications}
    ...    msg=One or more required applications not available: ${required_applications}

Check QCrBox Healthy
    [Documentation]    If QCrBox is alive, this should return healthy

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /healthz    200
    ${content}=    Decode Response Content    ${response}
    Check Response Content Has Attributes    ${content}    status    timestamp
    Should Be Equal    ${content["status"]}    ok    "The QCrBox registry is either not healthy or alive"

Check Suite Can Run
    [Documentation]    Check if QCrBox is ready for the test suite to run

    Wait Until Keyword Succeeds    10s    1s    Check QcrBox Healthy
    Wait Until Keyword Succeeds    10s    1s    Check Test Applications Available
