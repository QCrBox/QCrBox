*** Settings ***
Documentation
...  Test suite for API endpoints
Suite Setup    Setup suite
Suite Teardown    Teardown suite
Library  DateTime
Library  RequestsLibrary
Library  JSONLibrary
Library    api_endpoints_robot.py
Test Timeout    2 minutes

*** Variables ***
${ENDPOINTS_API}  http://127.0.0.1:11000/api
#${CONVERTYODA}  https://api.funtranslations.com

*** Test Cases ***

Check applications API returns applications
    Call API  /applications

Check calculations API returns calculations
    Call API  /calculations

Check commands API returns commands
    Call API  /commands

Check data_files API returns data_files
    Call API  /data_files

Check datasets API returns datasets
    Call API  /datasets

Check healthz API returns healthz
    Call API  /healthz

*** Keywords ***
Setup suite
    Log datetime information
    Log  Starting the test

Teardown suite
    Log datetime information
    Log  Test execution completed

Log datetime information
    ${date}=  Get Current Date
    log  ${date}

Call API
    [Arguments]    ${api}
	Create Session  api_endpoints   ${ENDPOINTS_API}
	${response}=	GET On Session  api_endpoints  ${api}
    Status Should Be  200  ${response}
    Log     ${response}
    Log     ${response.content}
