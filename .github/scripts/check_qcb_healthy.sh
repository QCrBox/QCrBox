# Change to the working directory
cd $GITHUB_WORKSPACE/QCrBox

# Source test environment variables
set -a
source .env.test
set +a

# Check if jq installed, used to parse the response from QCrBox
if ! command -v jq &> /dev/null; then
    echo "Error: jq is not installed. Please install jq to run this script." >&2
    exit 1
fi

# Wait for a response from the healthz API endpoint (max 30 attempts over 60 seconds)
for i in {1..30}; do
    # Check if the healthz endpoint is responsive
    if curl -s ${QCRBOX_BIND_ADDRESS}:${QCRBOX_REGISTRY_PORT}/api/healthz; then
        # Check that applications have been registered
        apps_response=$(curl -s ${QCRBOX_BIND_ADDRESS}:${QCRBOX_REGISTRY_PORT}/api/applications)
        if [ -n  "$apps_response" ]; then
            app_count=$(echo "$apps_response" | jq '.payload.applications | length' 2> /dev/null)
            if [[ "$app_count" -gt 0 ]]; then
                echo "QCrBox registry is healthy and applications registered."
                exit 0
            fi
        fi
        echo "QCrBox Registry is healthy, but waiting for applications to be registered."
        sleep 2
    fi
done

# If the loop completes, the registry did not start up in time
echo "QCrBox is not healthy after 60 seconds." >&2
exit 1
