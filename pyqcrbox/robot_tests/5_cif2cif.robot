*** Settings ***
Documentation
...                 Test suite for the CIF2CIF translation and merging

Resource    resources/keywords.resource

Suite Setup         Setup Suite
Suite Teardown      Teardown Suite
Test Timeout        2 minutes

*** Variables ***
${REGISTRY_ADDRESS}         %{QCRBOX_BIND_ADDRESS=127.0.0.1}
${REGISTRY_PORT}            %{QCRBOX_REGISTRY_PORT=11000}
${ENDPOINTS_API}            http://${REGISTRY_ADDRESS}:${REGISTRY_PORT}/api
${SUITE_SESSION_ALIAS}      QCRBOX_REGISTRY_API_ENDPOINTS


*** Test Cases ***
Returned cif should unmodified when untouched and no entries for input and output parameters
    [Documentation]    If no cif entries are set in the parameter yaml, an unmodified cif is expected to be returned

    ${input_cif_dataset}=    Upload Cif    ${CURDIR}/test_data/to_specific_test_cif.cif    to_specific_test_cif.cif
    VAR    &{input_cif}=
    ...    data_file_id=${input_cif_dataset[0]["data_files"]["to_specific_test_cif.cif"]["qcrbox_file_id"]}
    VAR    &{command_arguments}=    input_cif=${input_cif}    print_times=3

    ${output_dataset_id}=    Invoke Command And Get Output Dataset ID
    ...    dummy_cli
    ...    0.1.0
    ...    print_cif
    ...    ${command_arguments}

    ${original_cif}=    Get Binary File    ${CURDIR}/test_data/to_specific_test_cif.cif
    ${original_cif}=    Convert To String    ${original_cif}
    ${processed_cif}=    Get Dataset File Contents    ${output_dataset_id}
    Should Be Equal    ${processed_cif}    ${original_cif}

    [Teardown]    Run Keywords
    ...    Delete Cif Dataset    ${output_dataset_id}    AND
    ...    Delete Cif Dataset    ${input_cif_dataset[0]["qcrbox_dataset_id"]}

Returned cif should be modified when no entries for input and output parameter specified
    [Documentation]    We should expect that updated cif to be returned when no required cif entries are specified.

    ${input_cif_dataset}=    Upload Cif    ${CURDIR}/test_data/to_specific_test_cif.cif    to_specific_test_cif.cif

    VAR    &{input_cif}=
    ...    data_file_id=${input_cif_dataset[0]["data_files"]["to_specific_test_cif.cif"]["qcrbox_file_id"]}
    VAR    &{command_arguments}=    input_cif=${input_cif}    output_cif=merged_cif.cif

    ${output_dataset_id}=    Invoke Command And Get Output Dataset ID
    ...    dummy_cli
    ...    0.1.0
    ...    test_merged_cifs
    ...    ${command_arguments}

    ${original_cif}=    Get Dataset File Contents    ${input_cif_dataset[0]["qcrbox_dataset_id"]}
    ${processed_cif}=    Get Dataset File Contents    ${output_dataset_id}
    Log    Processed cif:\n ${processed_cif}
    Should Not Be Equal    ${processed_cif}    ${original_cif}
    Should Contain    ${processed_cif}    test_value.with_su
    Should Not Contain    ${processed_cif}    _custom.test

    [Teardown]    Run Keywords
    ...    Delete Cif Dataset    ${input_cif_dataset[0]["qcrbox_dataset_id"]}    AND
    ...    Delete Cif Dataset    ${output_dataset_id}

Returned cif should be modified after being transformed to specific format
    [Documentation]    We should expect some additional entries to be in the cif after command execution

    ${input_cif_dataset}=    Upload Cif    ${CURDIR}/test_data/to_specific_test_cif.cif    to_specific_test_cif.cif

    VAR    &{input_cif}=
    ...    data_file_id=${input_cif_dataset[0]["data_files"]["to_specific_test_cif.cif"]["qcrbox_file_id"]}
    VAR    &{command_arguments}=    input_cif=${input_cif}    output_cif_dummy="foo"

    ${output_dataset_id}=    Invoke Command And Get Output Dataset ID
    ...    dummy_cli
    ...    0.1.0
    ...    test_cif_to_specific
    ...    ${command_arguments}

    ${original_cif}=    Get Dataset File Contents    ${input_cif_dataset[0]["qcrbox_dataset_id"]}
    ${processed_cif}=    Get Dataset File Contents    ${output_dataset_id}
    Should Not Be Equal    ${processed_cif}    ${original_cif}

    FOR    ${sub}    IN    _cell_length_a    _cell_length_b    _atom_site_label    _atom_site_fract_y
        Should Contain    ${processed_cif}    ${sub}
    END
    FOR    ${sub}    IN    _cell.length_a_su    _cell.length_b_su    _atom_site.fract_x_su    _atom_site.fract_z
        Should Not Contain    ${processed_cif}    ${sub}
    END

    [Teardown]    Run Keywords
    ...    Delete Cif Dataset    ${input_cif_dataset[0]["qcrbox_dataset_id"]}    AND
    ...    Delete Cif Dataset    ${output_dataset_id}

Returned cif should be in the unified cif format
    [Documentation]    We should expect a cif to be returned as a unified cif with invalidated entries

    ${input_cif_dataset}=    Upload Cif    ${CURDIR}/test_data/to_specific_test_cif.cif    to_specific_test_cif.cif
    ${merge_cif_dataset}=    Upload Cif    ${CURDIR}/test_data/to_unified_test_cif.cif    to_unified_test_cif.cif

    VAR    &{input_cif}=
    ...    data_file_id=${input_cif_dataset[0]["data_files"]["to_specific_test_cif.cif"]["qcrbox_file_id"]}
    VAR    &{merge_cif}=
    ...    data_file_id=${merge_cif_dataset[0]["data_files"]["to_unified_test_cif.cif"]["qcrbox_file_id"]}
    VAR    &{command_arguments}=    input_cif=${input_cif}    to_merge_cif=${merge_cif}    output_cif="merged_cif.cif"

    ${output_dataset_id}=    Invoke Command And Get Output Dataset ID
    ...    dummy_cli
    ...    0.1.0
    ...    test_to_unified_cif
    ...    ${command_arguments}

    ${original_cif}=    Get Dataset File Contents    ${input_cif_dataset[0]["qcrbox_dataset_id"]}
    ${processed_cif}=    Get Dataset File Contents    ${output_dataset_id}
    Should Not Be Equal    ${processed_cif}    ${original_cif}

    VAR    @{should_include}=
    ...    _test_value.with_su
    ...    _test_value.with_su_su
    ...    _test_value.without_su
    ...    _test_loop.id
    ...    _test_loop.value_to_merge
    FOR    ${sub}    IN    @{should_include}
        Should Contain    ${processed_cif}    ${sub}
    END

    [Teardown]    Run Keywords
    ...    Delete Cif Dataset    ${input_cif_dataset[0]["qcrbox_dataset_id"]}    AND
    ...    Delete Cif Dataset    ${merge_cif_dataset[0]["qcrbox_dataset_id"]}    AND
    ...    Delete Cif Dataset    ${output_dataset_id}


*** Keywords ***
Setup Suite
    [Documentation]    Setup the test environment for this suite

    VAR    ${SESSION_ALIAS}=    ${SUITE_SESSION_ALIAS}    scope=GLOBAL
    Create API Session    ${SUITE_SESSION_ALIAS}    ${ENDPOINTS_API}
    Log Datetime Information
    Log    Starting test suite

Teardown Suite
    [Documentation]    Teardown the test environment for this suite

    Log Datetime Information
    Log    Test suite completed
