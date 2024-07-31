#!/usr/bin/env bash

set -euo pipefail

input_cif_path=$1
output_cif_path=$2

# Convert unified input cif to specific qcrbox_work.cif according to yml instructions
# delete if there is no input cif
python -m qcrboxtools.cif specific_by_yml $1 ./qcrbox_work.cif ./configure_{{ cookiecutter.application_slug }}.yml sample_cmd input_cif_path

# Replace with running your application
echo "Hello from '{{ cookiecutter.application_name }}' (version {{ cookiecutter.application_version }})"

# Convert specific output cif to unified output cif and merge with input according to yml
# delete if there is no output cif
python -m qcrboxtools.cif unified_by_yml ./qcrbox_work.cif $2 $1 ./configure_{{ cookiecutter.application_slug }}.yml sample_cmd output_cif_path

