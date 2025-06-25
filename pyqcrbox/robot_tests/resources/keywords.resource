*** Settings ***
Library     DateTime
Library     ../libraries/my_keywords.py


*** Keywords ***
Log datetime information
    ${date}=    Get Current Date
    Log    ${date}

Check Response And Get Payload
    [Arguments]    ${response}

    ${content}=    Get Response Content    ${response}
    Check For Error Response    ${content}
    Check Response Structure    ${content}
    ${payload}=    Set Variable    ${content["payload"]}

    Log    ${response}
    Log    ${content}
    Log    ${payload}

    RETURN    ${payload}

Check Response Structure
    [Arguments]    ${response}
    Check Json Has Attributes    ${response}    status    message    timestamp    payload

Check Response Has Attributes
    [Arguments]    ${payload}    @{attribute}
    Check Json Has Attributes    ${payload}    @{attribute}

Check For Error Response
    [Arguments]    ${response}

    IF    "${response['status']}" == "error"
        Fail    "Error ${response['error']['code']} returned from API: ${response['error']['message']}"
    END

Get Response Content
    [Arguments]    ${response}

    ${decoded_content}=    Evaluate    $response.content.decode('utf-8')
    ${json_content}=    Evaluate    json.loads($decoded_content)    json

    RETURN    ${json_content}
