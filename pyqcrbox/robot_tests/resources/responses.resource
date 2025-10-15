*** Settings ***
Documentation
...    Keywords for dealing with API responses.

Library     DateTime
Library     ../libraries/my_keywords.py

*** Keywords ***
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

Check Calculations Structure
    [Documentation]    Check that a calculations response has the correct attributes/structure
    [Arguments]    ${calculations}

    FOR    ${calculation}    IN    @{calculations}
        Check Response Content Has Attributes
        ...    ${calculation}
        ...    calculation_id
        ...    application_slug
        ...    application_version
        ...    command_name
        ...    status
        ...    command_arguments
        ...    output_dataset_id
    END

Check Interactive Sessions Structure
    [Documentation]    Check that an interactive session response has the correct attributes/structure
    [Arguments]    @{interactive_sessions}

    FOR    ${interactive_session}    IN    @{interactive_sessions}
        Check Response Content Has Attributes
        ...    ${interactive_session}
        ...    session_id
        ...    client_private_inbox
        ...    application_slug
        ...    application_version
        ...    command_name
        ...    arguments
    END

Check Command Response Structure
    [Documentation]    Check that a commands response has the correct attributes/structure
    [Arguments]    ${command}

    Log    ${command}

    Check Response Content Has Attributes
    ...    ${command}
    ...    name
    ...    description
    ...    implemented_as
    ...    parameters
    ...    id
    ...    application_id
    ...    application
    ...    version
    ...    cmd_name
    ...    merge_cif_su
    ...    doi

Check Application Response Structure
    [Documentation]    Check that an applications responses has the correct attributes/structure
    [Arguments]    ${application}

    Log    ${application}

    Check Response Content Has Attributes
    ...    ${application}
    ...    name
    ...    slug
    ...    version
    ...    description
    ...    email
    ...    doi
    ...    gui_port
    ...    url
    ...    registered_at
    ...    commands
    FOR    ${command}    IN    @{application['commands']}
        Check Command Response Structure    ${command}
    END

Check Datasets Structure
    [Documentation]    Check that a datasets response has the correct attributes/structure
    [Arguments]    @{datasets}

    FOR    ${dataset}    IN    @{datasets}
        Check Response Content Has Attributes    ${dataset}    qcrbox_dataset_id    data_files
    END
