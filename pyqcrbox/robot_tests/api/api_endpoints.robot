*** Settings ***
Documentation
...    Test suite for the registry API endpoints
Suite Setup    Setup suite
Suite Teardown    Teardown suite
Library    DateTime
Library    RequestsLibrary
Library    JSONLibrary
Test Timeout    2 minutes

*** Variables ***

${ENDPOINTS_API}    http://127.0.0.1:11000/api

*** Test Cases ***

Check applications API returns list of registered applications
    ${response}=    Call GET API    /applications
    FOR    ${app}    IN    @{response.json()}
        Verify Application Data    ${app}
    END

Check calculations API returns calculations
    Call GET API    /calculations

Check commands API returns commands
    Call GET API    /commands

Check data_files API returns data_files
    Call GET API    /data_files

Check datasets API returns datasets
    Call GET API    /datasets

Check healthz API returns healthz
    Call GET API    /healthz

*** Keywords ***

Setup suite
    Create Session    api_endpoints    ${ENDPOINTS_API}
    Log datetime information
    Log    Starting test suite

Teardown suite
    Log datetime information
    Log    Test suite completed

Log datetime information
    ${date}=    Get Current Date
    Log    ${date}

Call GET API
    [Arguments]    ${api}
	${response}=    GET On Session    api_endpoints    ${api}
    Status Should Be    200    ${response}
    Log    ${response}
    Log    ${response.content}
    RETURN    ${response}

Call POST API
    [Arguments]    ${api}
    ${response}=    POST On Session    api_endpoints    ${api}
    Status Should Be    200    ${response}
    Log    ${response}
    Log    ${response.content}
    RETURN    ${response

Verify Application Data
    [Arguments]    ${app}
    Should Contain    ${app}    name
    Should Contain    ${app}    slug
    Should Contain    ${app}    version
    Should Contain    ${app}    description
    Should Contain    ${app}    url
    Should Contain    ${app}    registered_at
    Should Contain    ${app}    commands
    FOR    ${command}    IN    @{app['commands']}
        Should Contain    ${command}    name
        Should Contain    ${command}    description
        Should Contain    ${command}    implemented_as
        Should Contain    ${command}    parameters
    END
