# Writing a QCrBox application container test plan

When developing a new container to provide to others, it is recommended to create a test plan for the container that covers how to ensure that container commands are functioning as expected. By their nature, application containers are often complex and encapsulate software and dependencies at a number of levels, so having a measure of quality control for container can ensure that it continues to behave as expected. This has a number of benefits, including:

- For the application developers, it provides a means to test the container to ensure that its functionality behaves as expected throughout development and prior to making a release, by adding test cases to test each command as they are developed
- For QCrBox users of the container, they may use the test plan to ensure a functional installation of the application container and its commands. In addition to documentation, it also provides a concise set of instructions for how to use each command

## Format of test cases

### Automated Tests (Non-Interactive Commands)

For commands that take inputs and produce outputs without user intervention, the recommended format is a **QCrBox Command Tester YAML file**. This executable format serves as both the documentation of the test plan and the script to run it.

For a step-by-step guide on creating these tests, see [Creating Automated Tests](../how_to_guides/create_automated_tests.md). For the full specification of the file format, see the [Test Suite Format](../technical_reference/command_tester/test_suite_format.md) reference.

### Manual Test Plans (Interactive Commands)

For interactive commands (e.g., GUIs, visualizers) or scenarios that cannot be easily automated, you should create a manual test plan. This can be a table in a text document or a spreadsheet.

The following columns should be included at a minimum:

- **Test ID** - a unique identifier for the test case
- **Brief description** - a concise note on what the test case actually tests
- **Preconditions** - any particular configuration, dependent services, or online services required
- **Input CIF file** - example CIF file used as input
- **Parameters** - parameters specified to the command
- **Manual test steps** - step-by-step instructions to invoke the command and interact with the interface
- **Expected results** - description of the expected outcome (e.g., "Window opens with structure displayed", "Dialog box appears")

## Good practice for writing manual test cases

See this [general guide](https://testsigma.com/guides/test-cases-for-manual-testing/) on writing manual tests.

- Write test cases from the user’s perspective — focus on behavior and outcomes, not just technical steps
- Keep them simple and unambiguous — anyone should be able to execute them without extra explanation
- Make each test independent — the outcome from one test should not affect another
- Ensure that all key functionality is tested with sufficient coverage - tests should exist for all provided container commands, such that the code paths for each command are sufficiently tested
- Prioritise writing test cases based on risk and impact
- Review test cases regularly to keep them relevant as the system evolves
