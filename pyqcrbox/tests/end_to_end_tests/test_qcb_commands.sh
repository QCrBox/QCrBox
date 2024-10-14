#!/usr/bin/env bash
source approvals.bash

D="[0-9]"
TIMESTAMP="$D$D$D$D-$D$D-$D$D $D$D:$D$D:$D$D"
QCRBOX_CALC_ID='qcrbox_calc_0x[0-9a-f]+'
allow_diff "($TIMESTAMP|$QCRBOX_CALC_ID)"

describe "qcb list applications"
  it "prints a list of registered applications"
    approve "qcb list applications"

describe "qcb list commands"
  it "prints a list of registered commands"
    approve "qcb list commands"

describe "qcb list calculations"
  context "when no commands have been invoked"
    the "list of calculations is empty"
    approve "qcb list calculations" "qcb_list_empty"

  context "after invoking a command"
    qcb invoke greet_and_sleep name="John Doe" duration=0
    it "displays a single calculation"
    approve "qcb list calculations" "qcb_list_single_calculation"
