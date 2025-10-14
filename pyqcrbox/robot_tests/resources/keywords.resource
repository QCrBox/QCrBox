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
