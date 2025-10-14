*** Settings ***
Documentation
...    Keywords which are used throughout the Robot Framework test suites.

Library     DateTime
Library     ../libraries/my_keywords.py

*** Keywords ***
Log Datetime Information
    [Documentation]    Log the current date and time

    ${date}=    Get Current Date
    Log    ${date}

Check For Error Response
    [Documentation]    Check if an API response includes an error message or status
    [Arguments]    ${response}

    IF    "${response['status']}" == "error"
        Fail    "Error ${response['error']['code']} returned from API: ${response['error']['message']}"
    END

Check Response Structure
    [Documentation]    Check that an API response has the correct structure and attributes
    [Arguments]    ${response}

    Check Json Has Attributes    ${response}    status    message    timestamp    payload

Decode Response Content
    [Documentation]    Decode the API's responses content into json representation
    [Arguments]    ${response}

    ${decoded_content}=    Evaluate    $response.content.decode('utf-8')
    ${json_content}=    Evaluate    json.loads($decoded_content)    json

    RETURN    ${json_content}

Check Response Structure And Get Payload
    [Documentation]    Check the structure and attributes in an API response and return its payload
    [Arguments]    ${response}

    ${content}=    Decode Response Content    ${response}
    Check For Error Response    ${content}
    Check Response Structure    ${content}
    VAR    ${payload}=    ${content["payload"]}

    Log    Raw response: ${response}
    Log    Response content: ${content}
    Log    Response payload: ${payload}

    RETURN    ${payload}

Check Response Content Has Attributes
    [Documentation]    Check that part of a response has the provided attributes/structure
    [Arguments]    ${payload}    @{attribute}

    Check Json Has Attributes    ${payload}    @{attribute}
