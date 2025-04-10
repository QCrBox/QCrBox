*** Settings ***
Documentation
...  Test suite for registry view handler
Suite Setup    Setup suite
Suite Teardown    Teardown suite
Library  DateTime
Library  RequestsLibrary
Library  JSONLibrary
Library    api_endpoints_robot.py
Test Timeout    2 minutes

*** Variables ***
${ENDPOINTS_API}  http://127.0.0.1:11000/views

*** Test Cases ***

Check applications API returns applications
    Call API  /applications

Check data_files API returns data_files
    Call API  /data_files

Check index API returns index
    Call API  /index

 Check restart API retuns a restart screen
    Call API  /restart

Check restart_docker_containers API restarts the containers
    Call POST API  /restart_docker_containers

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

Call POST API
   [Arguments]    ${api}
    Create Session  api_endpoints   ${ENDPOINTS_API}
    ${response}=	POST On Session  api_endpoints  ${api}
    Status Should Be  200  ${response}
    Log     ${response}
    Log     ${response.content}
