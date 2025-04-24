*** Settings ***

Library    RequestsLibrary
Library    JSONLibrary

*** Keywords ***

Log Response
    [Arguments]    ${response}
    Log    ${response.status_code}
    Log    ${response.content}

Create API Session
    [Arguments]    ${session_alias}    ${base_url}
    Create Session    ${session_alias}    ${base_url}    verify=True
    RETURN    ${session_alias}

Call GET API
    [Arguments]    ${session_alias}    ${base_url}
	${response}=    GET On Session    ${session_alias}    ${base_url}
    Status Should Be    200    ${response}
    Log Response    ${response}
    RETURN    ${response}

Call POST API
    [Arguments]    ${session_alias}    ${base_url}
	${response}=    POST On Session    ${session_alias}    ${base_url}
    Status Should Be    200    ${response}
    Log Response    ${response}
    RETURN    ${response}

Call DELETE API
    [Arguments]    ${session_alias}    ${base_url}
	${response}=    DELETE On Session    ${session_alias}    ${base_url}
    Status Should Be    204    ${response}
    Log Response    ${response}
    RETURN    ${response}
