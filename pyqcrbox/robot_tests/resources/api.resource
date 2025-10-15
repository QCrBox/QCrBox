*** Settings ***
Documentation
...    Keywords for sending HTTP requests to QCrBox's API.

Library    Collections
Library     RequestsLibrary
Library     JSONLibrary

*** Keywords ***
Create API Session
    [Documentation]    Create a new HTTP session with SSL verification
    [Arguments]    ${session_alias}    ${base_url}

    Create Session    ${session_alias}    ${base_url}    verify=True

Send API Request
    [Documentation]    Make a HTTP request using the specified method.
    [Arguments]
    ...    ${method}
    ...    ${session_alias}
    ...    ${endpoint}
    ...    ${expected_status}
    ...    ${json_data}=${None}
    ...    ${files}=${None}
    ...    ${headers}=${None}

    ${kwargs}=    Create Dictionary
    IF    $json_data is not None
        Set To Dictionary    ${kwargs}    json=${json_data}
    END
    IF    $files is not None    Set To Dictionary    ${kwargs}    files=${files}
    IF    $headers is not None
        Set To Dictionary    ${kwargs}    headers=${headers}
    END

    IF    '${method}' == 'GET'
        ${response}=    GET On Session
        ...    ${session_alias}
        ...    ${endpoint}
        ...    expected_status=${expected_status}
        ...    &{kwargs}
    ELSE IF    '${method}' == 'POST'
        ${response}=    POST On Session
        ...    ${session_alias}
        ...    ${endpoint}
        ...    expected_status=${expected_status}
        ...    &{kwargs}
    ELSE IF    '${method}' == 'DELETE'
        ${response}=    DELETE On Session
        ...    ${session_alias}
        ...    ${endpoint}
        ...    expected_status=${expected_status}
        ...    &{kwargs}
    ELSE
        Fail    Unsupported method: ${method}
    END

    Log    Response status code: ${response.status_code}
    Log    Response content: ${response.content}

    RETURN    ${response}
