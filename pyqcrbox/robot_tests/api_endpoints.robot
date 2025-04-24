*** Settings ***
Documentation
...    Test suite for the registry API endpoints
Suite Setup    Setup suite
Suite Teardown    Teardown suite
Resource    ../api_keywords.resource
Library    DateTime
Test Timeout    2 minutes

*** Variables ***

${ENDPOINTS_API}    http://127.0.0.1:11000/api

*** Test Cases ***

Check applications API returns list of registered applications
    ${response}=    Call GET API    api_endpoints    /applications
    FOR    ${app}    IN    @{response.json()}
        Verify Application Data    ${app}
    END

Check calculations API returns calculations
    Call GET API    api_endpoints    /calculations

Check commands API returns commands
    Call GET API    api_endpoints    /commands

Check data_files API returns data_files
    Call GET API    api_endpoints    /data_files


Check datasets API returns datasets
    Call GET API    api_endpoints    /datasets

Check healthz API returns healthz
    Call GET API    api_endpoints    /healthz

*** Keywords ***

Setup suite
    ${api_session}=    Create API Session    api_endpoints    ${ENDPOINTS_API}
    Log datetime information
    Log    Starting test suite

Teardown suite
    Log datetime information
    Log    Test suite completed

Log datetime information
    ${date}=    Get Current Date
    Log    ${date}

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
