*** Settings ***
Documentation
...    Keywords for dealing with calculation/command management.

Library     DateTime
Library     ../libraries/my_keywords.py
Resource    api.resource
Resource    responses.resource
Resource    datasets.resource

*** Keywords ***
Invoke Command With Arguments
    [Documentation]    Invoke a command with the provided arguments
    [Arguments]    ${application_slug}
    ...    ${application_version}
    ...    ${command_name}
    ...    ${command_arguments}
    ...    ${endpoint}=/commands

    VAR    &{command_request}=
    ...    application_slug=${application_slug}
    ...    application_version=${application_version}
    ...    command_name=${command_name}
    ...    command_arguments=${command_arguments}
    Log    Command invocation request: ${command_request}

    ${response}=    Send API Request    POST    ${SESSION_ALIAS}    ${endpoint}    201    json_data=${command_request}
    # VAR    ${response_json}=    ${response.json()}
    Log    Command invocation response: ${response.json()}

    RETURN    ${response}

Invoke Command And Get Output Dataset ID
    [Documentation]    Invoke a command and get the output dataset
    [Arguments]    ${application_slug}    ${application_version}    ${command_name}    ${command_arguments}

    ${invoke_response}=    Invoke Command With Arguments
    ...    ${application_slug}
    ...    ${application_version}
    ...    ${command_name}
    ...    ${command_arguments}
    ${invoke_response}=    Decode Response Content    ${invoke_response}
    ${calculation_id}=    Get Calculation ID    ${invoke_response}
    ${output_dataset_id}=    Get Output Dataset ID    ${calculation_id}

    RETURN    ${output_dataset_id}

Get Calculation ID
    [Documentation]    Get the calculation ID from a command invocation response
    [Arguments]    ${invocation_response}

    RETURN    ${invocation_response["payload"]["calculation_id"]}

Get Calculation Status
    [Documentation]    Get the status of a calculation
    [Arguments]    ${calculation_id}

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /calculations/${calculation_id}    200
    ${payload}=    Check Response Structure And Get Payload    ${response}

    Check Response Content Has Attributes    ${payload}    calculations
    VAR    ${calculations}=    ${payload["calculations"]}
    ${n_calculations}=    Get Length    ${calculations}
    Should Be Equal As Integers    ${n_calculations}    1    "Multiple calculations retrieved, when only one requested"
    VAR    ${calculation_status}=    ${calculations[0]}

    RETURN    ${calculation_status}

Check Calculation Successful
    [Documentation]    Check if a calculation has executed successfully
    [Arguments]    ${calculation_id}

    ${calculation_response}=    Get Calculation Status    ${calculation_id}
    Should Be Equal    ${calculation_response["status"]}    successful

    RETURN    ${calculation_response}

Wait Until Calculation Successful
    [Documentation]    Wait until a calculation has been succesfully executed
    [Arguments]    ${calculation_id}

    ${calculation_response}=    Wait Until Keyword Succeeds
    ...    10s
    ...    2s
    ...    Check Calculation Successful
    ...    ${calculation_id}

    Log    Calculation response: ${calculation_response}

    RETURN    ${calculation_response}

Check Calculation Failed
    [Documentation]    Check if a calculation has failed
    [Arguments]    ${calculation_id}

    ${calculation_response}=    Get Calculation Status    ${calculation_id}
    Should Be Equal    ${calculation_response["status"]}    failed

    RETURN    ${calculation_response}
