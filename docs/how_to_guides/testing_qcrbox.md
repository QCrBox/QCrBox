# Testing changes made to QCrBox

It is important to test changes made to QCrBox to ensure reliability, maintain backwards compatibility, and prevent
regressions from being introduced. This page covers the current testing infrastructure for QCrBox.

## Robot Framework test suite

QCrBox uses Robot Framework to run acceptance tests that validate the system's behavior from an end-user perspective.
Test suites for Robot Framework are kept in `QCrBox/pyqcbox/robot_tests`. There are currently two test suites:

- `1_endpoints.robot` - tests some API endpoints which are used in the other test suites
- `2_non_interactive_commands.robot` - tests non-interactive command invocation, status checking and stopping
- `3_interactive.robot` - tests interactive command invocation, status checking and closing
- `4_calculations.robot` - tests the calculation status endpoints more thoroughly

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

## Pytest

In addition to the Robot Framework acceptance tests, we also have a small suite of unit (and smaller integration) tests.
These tests are designed to poke at the core functionality of the `pyqcrbox` Python package, whereas the Robot Framework
tests are for validation the API.

```shell
cd ./pyqcrbox/tests
pytest
```

## CI/CD pipeline

GitHub Actions are used to test the QCrBox builds and that the API behaves as expected. These tests are run on every
pull request to `main` and `dev` and typically takes ~10 minutes to run.

### Using the `--test` flag with `qcb` to build the minimum set of containers for testing

It is not recommended to do this for regular development work. This functionality exists to decrease build and test
times in GitHub actions or for power users who need faster testing. Using the `--test` flag will build the minimum set
of containers required for running the test suite: qcrbox-registry, qcrbox-nats, qcrbox-reverse-proxy, dummy_cli and
dummy_gui. This setup excludes building multiple application and logging containers which aren't necessary for core
testing.

```shell
qcb up --test
```

When using `--test`, the same ports will be used as the normal deployment but note that there will be no log
aggregation in the test deployment.

## Devbox test script

We have multiple Devbox scripts which provide a convenient way to run the test suites:

```shell
devbox run build-test-mode
devbox run robot-framework
devbox run pytest
```

These commands will:

1. Remove any running containers and bring QCrBox into test mode (`qcb up --test`)
2. Execute the Robot Framework test suite
3. Execute the Pytest test suite

To do all these at once, you can use the Devbox script:

```shell
devbox run tests
```

## Best practices for testing

When making changes to QCrBox, follow these testing guidelines:

1. **Run tests locally** before submitting pull requests to catch issues early
2. **Write new tests** for any new API endpoints or significant functionality changes
3. **Update existing tests** when modifying API expected behavior
4. **Test edge cases** including error conditions, invalid inputs, and boundary conditions
5. **Verify backwards compatibility** by ensuring existing tests continue to pass after changes
