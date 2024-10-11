#!/usr/bin/env bash

set -euo pipefail

#readonly PROGNAME=$(basename $0)
#readonly CUR_WORK_DIR=$(pwd)
#readonly ARGS="$*"


verify_output_of_qcb_list_applications() {
    if qcb list applications |
       grep -q "dummy_cli.*Dummy CLI.*0.1.0";
    then
        echo "Success: 'qcb list applications' contained expected info about Dummy CLI"
    else
        exit 1
    fi
}


verify_output_of_qcb_list_commands() {
    if qcb list commands |
       grep -q "greet_and_sleep";
    then
        echo "Success: 'qcb list commands' contained expected output 'greet_and_sleep'"
    else
        exit 1
    fi
}



main() {
    verify_output_of_qcb_list_applications
    verify_output_of_qcb_list_commands
}
main
