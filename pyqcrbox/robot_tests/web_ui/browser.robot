*** Settings ***
Documentation
...  Test suite for the Web UI
Suite Setup    Setup suite
Suite Teardown    Teardown suite
Library  DateTime
Test Timeout    2 minutes

*** Variables ***
${WEB_URL}  http://127.0.0.1:11000

*** Test Cases ***

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
