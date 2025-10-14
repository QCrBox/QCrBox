# Writing a QCrBox application container test plan

When developing a new container to provide to others, it is recommended to create a test plan for the container that covers how to ensure that container commands are functioning as expected. By their nature, application containers are often complex and encapsulate software and dependencies at a number of levels, so having a measure of quality control for container can ensure that it continues to behave as expected. This has a number of benefits, including:

- For the application developers, it provides a means to test the container to ensure that its functionality behaves as expected throughout development and prior to making a release, by adding test cases to test each command as they are developed
- For QCrBox users of the container, they may use the test plan to ensure a functional installation of the application container and its commands. In addition to documentation, it also provides a concise set of instructions for how to use each command

## Format of test cases

A test plan could be compiled within a table within a text document, or within a spreadsheet. The following columns for each test case should be included at a minimum:

- Test ID - a unique identifier for the test case
- Brief description - a concise note on what the test case actually tests, e.g. in terms of commands
- Preconditions - any particular configuration or set up within the test plan or QCrBox or elsewhere that may be required, any dependent QCrBox services that need to be running, online services that are needed, etc.
- Input CIF file - provide at least one example CIF file that is used as input for this test
- Parameters - the parameters (if any) that are specified to the command for this test case
- Manual test steps - the steps required to invoke the command with the specified parameters using the QCrBox front-end
- Expected output CIF file - for each test input CIF, provide a corresponding output CIF file that is expected
- Expected results - a concise description for what the expected result should be, e.g. a set of fields that should appear within the output CIF file

## Good practice for writing manual test cases

See this [general guide](https://testsigma.com/guides/test-cases-for-manual-testing/) on writing manual tests.

- Write test cases from the user’s perspective — focus on behavior and outcomes, not just technical steps
- Keep them simple and unambiguous — anyone should be able to execute them without extra explanation
- Make each test independent — the outcome from one test should not affect another
- Ensure that all key functionality is tested with sufficient coverage - tests should exist for all provided container commands, such that the code paths for each command are sufficiently tested
- Prioritise writing test cases based on risk and impact
- Review test cases regularly to keep them relevant as the system evolves
