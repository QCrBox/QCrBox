#!/bin/bash

applications=$(find -name "config_*.yaml" | grep -Ev "dummy|_template|eval1x|crysalis-pro")
failed_apps=()

for app in $applications; do
    echo "Validating: $app"
    output=$(qcb validate "$app" 2>&1)
    status=$?
    if [ $status -ne 0 ]; then
        failed_apps+=("$app"$'\n'"$output"$'\n')
    fi
done

if [ ${#failed_apps[@]} -gt 0 ]; then
    echo -e "\n=== Failed Applications ==="
    for entry in "${failed_apps[@]}"; do
        echo -e "$entry"
        echo "----------------------------"
    done
else
    echo -e "\nAll applications validated successfully."
fi
