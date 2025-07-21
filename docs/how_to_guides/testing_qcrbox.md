# Testing changes made to QCrBox

It is important to test changes made to QCrBox to ensure reliability, maintain backwards compatibility, and prevent
regressions from being introduced. This page covers the current testing infrastructure for QCrBox.

## Robot Framework test suite

QCrBox uses Robot Framework to run acceptance tests that validate the system's behavior from an end-user perspective.
Test suites for Robot Framework are kept in `QCrBox/pyqcbox/robot_tests`. There are currently two test suites:

- `api_endpoints.robot` - tests the API endpoints
- `web_interface.robot` - tests the QCrBoxFrontend Django website

We have used Robot Framework because it's keyword-driven approach to makes writing, reading and maintaining tests simple
in comparison to other testing frameworks. This should make it easier for tests suites to be maintained and expanded by
new developers. Its extensive library and ecosystem also allows us to easily test Rest APIs, validate responses and
integrate with our CI/CD pipeline without the need of writing and maintaining large amount of boilerplate code. Finally,
the automated logging helps identify and debug failed tests.

To run the Robot Framework test suites, execute the following:

```shell
cd ./pyqcrbox/robot_tests
robot *.robot
```

## CI/CD pipeline

GitHub Actions are used to test the QCrBox builds and that the API behaves as expected. These tests are run on every
pull request to `main` and `dev` and typically takes ~10 minutes to run.

### Using the `--test-only` flag with `qcb` to build the minimum set of containers for testing

It is not recommended to do this for regular development work. This functionality exists to decrease build and test times
in GitHub actions or for power users who need faster testing.

If you need to use this flag, take down all QCrBox containers to avoid conflicts between different container
configurations and port mappings.

```shell
qcb down
```

Using the `--test-only` flag will build the minimum set of containers required for running the test suite, including:
qcrbox-registry, qcrbox-nats, olex2, qcrbox_quality and qcrbox-reverse-proxy. This setup excludes building multiple
application and logging containers which aren't necessary for core testing.

```shell
qcb up --test-only
```

When using `--test-only`, the same ports will be used as the normal deployment. Note that there will be no log
aggregation in the test deployment.

## Devbox test script

The devbox test script provides a convenient way to run the complete API test suite with a single command:

```shell
devbox run test-api
```

This command will automatically:

- Take down any running containers
- Start the necessary test containers if they're not already running
- Execute the full Robot Framework test suite against the API endpoints

## Best practices for testing

When making changes to QCrBox, follow these testing guidelines:

1. **Run tests locally** before submitting pull requests to catch issues early
2. **Write new tests** for any new API endpoints or significant functionality changes
3. **Update existing tests** when modifying API expected behavior
4. **Test edge cases** including error conditions, invalid inputs, and boundary conditions
5. **Verify backwards compatibility** by ensuring existing tests continue to pass after changes
