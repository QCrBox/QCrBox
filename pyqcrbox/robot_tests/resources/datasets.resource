*** Settings ***
Documentation
...    Keywords for dealing with cif management.

Library    DateTime
Library    OperatingSystem
Library    String
Library    ../libraries/my_keywords.py
Resource    api.resource
Resource    responses.resource
Resource    calculations.resource

*** Variables ***
${SESSION_ALIAS}    ${EMPTY}

*** Keywords ***
Upload Cif
    [Documentation]    Upload a cif file
    [Arguments]    ${path_to_file}    ${file_name}

    ${file_contents}=    Get Binary File    ${path_to_file}
    VAR    &{files}=    ${file_name}=${file_contents}

    ${response}=    Send API Request    POST    ${SESSION_ALIAS}    /datasets    201    files=${files}
    ${payload}=    Check Response Structure And Get Payload    ${response}
    Check Response Content Has Attributes    ${payload}    datasets

    ${n_datasets}=    Get Length    ${payload["datasets"]}
    Should Be Equal As Integers    ${n_datasets}    1    "Upload Cif has returned multiple datasets"

    RETURN    ${payload["datasets"]}

Delete Cif Dataset
    [Documentation]    Remove a dataset containing a test cif file
    [Arguments]    ${dataset_id}

    Send API Request    DELETE    ${SESSION_ALIAS}    /datasets/${dataset_id}    204

Get Output Dataset ID
    [Documentation]    Get the output dataset for a finished calculation
    [Arguments]    ${calculation_id}

    ${calculation_response}=    Wait Until Calculation Successful    ${calculation_id}

    RETURN    ${calculation_response["output_dataset_id"]}

Get Dataset File Contents
    [Documentation]    Get a cif file from a dataset, containing only that one cif file
    [Arguments]    ${dataset_id}

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /datasets/${dataset_id}/download    200
    ${content_disposition}=    Get From Dictionary    ${response.headers}    Content-Disposition

    ${parts}=    Split String    ${content_disposition}    filename=${EMPTY}
    VAR    ${filename}=    ${parts}[1]
    ${filename}=    Remove String    ${filename}
    ${filename}=    Remove String    ${filename}    "
    Should End With    ${filename}    .cif
    Should Not Contain
    ...    ${filename}
    ...    .zip
    ...    msg=The downloaded file is a .zip, but a .cif was expected. Filename: ${filename}

    Should Not Be Empty    ${response.content}
    ${output}=    Convert To String    ${response.content}

    RETURN    ${output}

Check Data File Content Media Type
    [Documentation]    Fetch a data file via the inline content endpoint and check its media type
    [Arguments]    ${data_file_id}    ${expected_media_type}

    ${response}=    Send API Request    GET    ${SESSION_ALIAS}    /data-files/${data_file_id}/content    200
    Should Be Equal    ${response.headers["Content-Type"]}    ${expected_media_type}
    Should Contain    ${response.headers["Content-Disposition"]}    inline
    Should Be Equal    ${response.headers["X-Content-Type-Options"]}    nosniff
