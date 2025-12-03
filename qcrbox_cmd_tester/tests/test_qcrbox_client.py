"""Tests for the qcrbox_client module, focusing on timeout and interrupt handling."""

from unittest.mock import Mock, patch

import pytest

from qcrbox_cmd_tester.qcrbox_client import (
    run_qcrbox_command,
)


@pytest.fixture
def mock_client():
    """Create a mock QCrBox client."""
    return Mock()


@pytest.fixture
def mock_calculation_response_running():
    """Mock response for a running calculation."""
    mock_response = Mock()
    mock_calculation = Mock()
    mock_calculation.status = "running"
    mock_response.payload.calculations = [mock_calculation]
    return mock_response


@pytest.fixture
def mock_calculation_response_successful():
    """Mock response for a successful calculation."""
    mock_response = Mock()
    mock_calculation = Mock()
    mock_calculation.status = "successful"
    mock_calculation.output_dataset_id = "output-dataset-123"
    mock_calculation.status_events = []
    mock_response.payload.calculations = [mock_calculation]
    return mock_response


@pytest.fixture
def mock_calculation_response_failed():
    """Mock response for a failed calculation."""
    mock_response = Mock()
    mock_calculation = Mock()
    mock_calculation.status = "failed"
    mock_calculation.status_events = ["Error: computation failed"]
    mock_response.payload.calculations = [mock_calculation]
    return mock_response


@patch("qcrbox_cmd_tester.qcrbox_client.prepare_qcrbox_parameters")
@patch("qcrbox_cmd_tester.qcrbox_client.invoke_command")
@patch("qcrbox_cmd_tester.qcrbox_client.get_calculation_by_id")
@patch("qcrbox_cmd_tester.qcrbox_client.stop_running_calculation")
@patch("qcrbox_cmd_tester.qcrbox_client.download_dataset_by_id")
@patch("qcrbox_cmd_tester.qcrbox_client.delete_dataset_by_id")
@patch("time.sleep")  # Mock sleep to avoid delays in tests
def test_timeout_stops_calculation(
    mock_sleep,
    mock_delete_dataset,
    mock_download_dataset,
    mock_stop_calculation,
    mock_get_calculation,
    mock_invoke_command,
    mock_prepare_params,
    mock_client,
    mock_calculation_response_running,
):
    """Test that timeout properly stops the running calculation."""
    # Setup mocks
    mock_prepare_params.return_value = ({}, [])

    mock_invoke_response = Mock()
    mock_invoke_response.payload.calculation_id = "calc-123"
    mock_invoke_command.sync.return_value = mock_invoke_response

    # Always return running status (simulates a long-running calculation)
    mock_get_calculation.sync.return_value = mock_calculation_response_running

    # Run with very short timeout
    result = run_qcrbox_command(
        client=mock_client,
        command_name="test_command",
        application_slug="test_app",
        application_version="1.0.0",
        command_parameters=[],
        timeout_seconds=0.5,
    )

    # Verify timeout behavior
    assert result.status == "timeout"
    assert result.result_cif is None
    assert len(result.status_events) == 1
    assert "timeout of 0.5 seconds" in result.status_events[0]

    # Verify that stop_running_calculation was called
    mock_stop_calculation.sync.assert_called_once_with(id="calc-123", client=mock_client)

    # Verify that get_calculation was called at least once
    assert mock_get_calculation.sync.call_count >= 1


@patch("qcrbox_cmd_tester.qcrbox_client.prepare_qcrbox_parameters")
@patch("qcrbox_cmd_tester.qcrbox_client.invoke_command")
@patch("qcrbox_cmd_tester.qcrbox_client.get_calculation_by_id")
@patch("qcrbox_cmd_tester.qcrbox_client.stop_running_calculation")
@patch("qcrbox_cmd_tester.qcrbox_client.delete_dataset_by_id")
@patch("time.sleep")
def test_keyboard_interrupt_stops_calculation(
    mock_sleep,
    mock_delete_dataset,
    mock_stop_calculation,
    mock_get_calculation,
    mock_invoke_command,
    mock_prepare_params,
    mock_client,
    mock_calculation_response_running,
):
    """Test that KeyboardInterrupt properly stops the calculation and re-raises."""
    # Setup mocks
    mock_prepare_params.return_value = ({}, [])

    mock_invoke_response = Mock()
    mock_invoke_response.payload.calculation_id = "calc-456"
    mock_invoke_command.sync.return_value = mock_invoke_response

    # First call returns running, second raises KeyboardInterrupt
    mock_get_calculation.sync.side_effect = [
        mock_calculation_response_running,
        KeyboardInterrupt(),
    ]

    # Should re-raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        run_qcrbox_command(
            client=mock_client,
            command_name="test_command",
            application_slug="test_app",
            application_version="1.0.0",
            command_parameters=[],
            timeout_seconds=300.0,
        )

    # Verify that stop_running_calculation was called
    mock_stop_calculation.sync.assert_called_once_with(id="calc-456", client=mock_client)


@patch("qcrbox_cmd_tester.qcrbox_client.prepare_qcrbox_parameters")
@patch("qcrbox_cmd_tester.qcrbox_client.invoke_command")
@patch("qcrbox_cmd_tester.qcrbox_client.get_calculation_by_id")
@patch("qcrbox_cmd_tester.qcrbox_client.stop_running_calculation")
@patch("qcrbox_cmd_tester.qcrbox_client.download_dataset_by_id")
@patch("qcrbox_cmd_tester.qcrbox_client.delete_dataset_by_id")
@patch("time.sleep")
def test_keyboard_interrupt_during_sleep(
    mock_sleep,
    mock_delete_dataset,
    mock_download_dataset,
    mock_stop_calculation,
    mock_get_calculation,
    mock_invoke_command,
    mock_prepare_params,
    mock_client,
    mock_calculation_response_running,
):
    """Test that KeyboardInterrupt during sleep properly stops the calculation."""
    # Setup mocks
    mock_prepare_params.return_value = ({}, [])

    mock_invoke_response = Mock()
    mock_invoke_response.payload.calculation_id = "calc-789"
    mock_invoke_command.sync.return_value = mock_invoke_response

    mock_get_calculation.sync.return_value = mock_calculation_response_running

    # Simulate KeyboardInterrupt during sleep
    mock_sleep.side_effect = KeyboardInterrupt()

    # Should re-raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        run_qcrbox_command(
            client=mock_client,
            command_name="test_command",
            application_slug="test_app",
            application_version="1.0.0",
            command_parameters=[],
            timeout_seconds=300.0,
        )

    # Verify that stop_running_calculation was called
    mock_stop_calculation.sync.assert_called_once_with(id="calc-789", client=mock_client)


@patch("qcrbox_cmd_tester.qcrbox_client.prepare_qcrbox_parameters")
@patch("qcrbox_cmd_tester.qcrbox_client.invoke_command")
@patch("qcrbox_cmd_tester.qcrbox_client.get_calculation_by_id")
@patch("qcrbox_cmd_tester.qcrbox_client.stop_running_calculation")
@patch("qcrbox_cmd_tester.qcrbox_client.download_dataset_by_id")
@patch("qcrbox_cmd_tester.qcrbox_client.delete_dataset_by_id")
@patch("time.sleep")
def test_successful_completion_before_timeout(
    mock_sleep,
    mock_delete_dataset,
    mock_download_dataset,
    mock_stop_calculation,
    mock_get_calculation,
    mock_invoke_command,
    mock_prepare_params,
    mock_client,
    mock_calculation_response_running,
    mock_calculation_response_successful,
):
    """Test that successful completion works correctly before timeout."""
    # Setup mocks
    mock_prepare_params.return_value = ({}, ["dataset-1", "dataset-2"])

    mock_invoke_response = Mock()
    mock_invoke_response.payload.calculation_id = "calc-success"
    mock_invoke_command.sync.return_value = mock_invoke_response

    # Running for 2 iterations, then successful
    mock_get_calculation.sync.side_effect = [
        mock_calculation_response_running,
        mock_calculation_response_running,
        mock_calculation_response_successful,
    ]

    mock_download_dataset.sync.return_value = b"data_result\n_test 1\n"

    # Run with sufficient timeout
    result = run_qcrbox_command(
        client=mock_client,
        command_name="test_command",
        application_slug="test_app",
        application_version="1.0.0",
        command_parameters=[],
        timeout_seconds=300.0,
    )

    # Verify successful completion
    assert result.status == "successful"
    assert result.result_cif == "data_result\n_test 1\n"
    assert result.status_events == []

    # Verify stop_running_calculation was NOT called
    mock_stop_calculation.sync.assert_not_called()

    # Verify datasets were cleaned up
    assert mock_delete_dataset.sync.call_count == 3  # 2 input + 1 output


@patch("qcrbox_cmd_tester.qcrbox_client.prepare_qcrbox_parameters")
@patch("qcrbox_cmd_tester.qcrbox_client.invoke_command")
@patch("qcrbox_cmd_tester.qcrbox_client.get_calculation_by_id")
@patch("qcrbox_cmd_tester.qcrbox_client.stop_running_calculation")
@patch("qcrbox_cmd_tester.qcrbox_client.delete_dataset_by_id")
@patch("time.sleep")
def test_failed_calculation_cleanup(
    mock_sleep,
    mock_delete_dataset,
    mock_stop_calculation,
    mock_get_calculation,
    mock_invoke_command,
    mock_prepare_params,
    mock_client,
    mock_calculation_response_failed,
):
    """Test that failed calculations still clean up input datasets."""
    # Setup mocks
    mock_prepare_params.return_value = ({}, ["input-dataset-1"])

    mock_invoke_response = Mock()
    mock_invoke_response.payload.calculation_id = "calc-fail"
    mock_invoke_command.sync.return_value = mock_invoke_response

    mock_get_calculation.sync.return_value = mock_calculation_response_failed

    # Run command
    result = run_qcrbox_command(
        client=mock_client,
        command_name="test_command",
        application_slug="test_app",
        application_version="1.0.0",
        command_parameters=[],
        timeout_seconds=300.0,
    )

    # Verify failed status
    assert result.status == "failed"
    assert result.result_cif is None

    # Verify input dataset was cleaned up
    mock_delete_dataset.sync.assert_called_once_with(id="input-dataset-1", client=mock_client)

    # Verify stop_running_calculation was NOT called (calculation already finished)
    mock_stop_calculation.sync.assert_not_called()


@patch("qcrbox_cmd_tester.qcrbox_client.prepare_qcrbox_parameters")
@patch("qcrbox_cmd_tester.qcrbox_client.invoke_command")
@patch("qcrbox_cmd_tester.qcrbox_client.get_calculation_by_id")
@patch("qcrbox_cmd_tester.qcrbox_client.stop_running_calculation")
@patch("qcrbox_cmd_tester.qcrbox_client.delete_dataset_by_id")
@patch("time.sleep")
def test_timeout_cleans_up_input_datasets(
    mock_sleep,
    mock_delete_dataset,
    mock_stop_calculation,
    mock_get_calculation,
    mock_invoke_command,
    mock_prepare_params,
    mock_client,
    mock_calculation_response_running,
):
    """Test that timeout still cleans up input datasets in finally block."""
    # Setup mocks
    mock_prepare_params.return_value = ({}, ["input-dataset-1", "input-dataset-2"])

    mock_invoke_response = Mock()
    mock_invoke_response.payload.calculation_id = "calc-timeout"
    mock_invoke_command.sync.return_value = mock_invoke_response

    mock_get_calculation.sync.return_value = mock_calculation_response_running

    # Run with very short timeout
    result = run_qcrbox_command(
        client=mock_client,
        command_name="test_command",
        application_slug="test_app",
        application_version="1.0.0",
        command_parameters=[],
        timeout_seconds=0.1,
    )

    # Verify timeout occurred
    assert result.status == "timeout"

    # Verify input datasets were cleaned up
    assert mock_delete_dataset.sync.call_count == 2
    mock_delete_dataset.sync.assert_any_call(id="input-dataset-1", client=mock_client)
    mock_delete_dataset.sync.assert_any_call(id="input-dataset-2", client=mock_client)

    # Verify stop was called
    mock_stop_calculation.sync.assert_called_once()


@patch("qcrbox_cmd_tester.qcrbox_client.prepare_qcrbox_parameters")
@patch("qcrbox_cmd_tester.qcrbox_client.invoke_command")
@patch("qcrbox_cmd_tester.qcrbox_client.get_calculation_by_id")
@patch("qcrbox_cmd_tester.qcrbox_client.stop_running_calculation")
@patch("qcrbox_cmd_tester.qcrbox_client.delete_dataset_by_id")
@patch("time.sleep")
def test_keyboard_interrupt_cleans_up_input_datasets(
    mock_sleep,
    mock_delete_dataset,
    mock_stop_calculation,
    mock_get_calculation,
    mock_invoke_command,
    mock_prepare_params,
    mock_client,
    mock_calculation_response_running,
):
    """Test that KeyboardInterrupt still cleans up input datasets in finally block."""
    # Setup mocks
    mock_prepare_params.return_value = ({}, ["input-dataset-1"])

    mock_invoke_response = Mock()
    mock_invoke_response.payload.calculation_id = "calc-interrupt"
    mock_invoke_command.sync.return_value = mock_invoke_response

    # Raise KeyboardInterrupt on second poll
    mock_get_calculation.sync.side_effect = [
        mock_calculation_response_running,
        KeyboardInterrupt(),
    ]

    # Should re-raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        run_qcrbox_command(
            client=mock_client,
            command_name="test_command",
            application_slug="test_app",
            application_version="1.0.0",
            command_parameters=[],
            timeout_seconds=300.0,
        )

    # Verify input dataset was cleaned up despite exception
    mock_delete_dataset.sync.assert_called_once_with(id="input-dataset-1", client=mock_client)

    # Verify stop was called
    mock_stop_calculation.sync.assert_called_once()


@patch("qcrbox_cmd_tester.qcrbox_client.prepare_qcrbox_parameters")
@patch("qcrbox_cmd_tester.qcrbox_client.invoke_command")
@patch("qcrbox_cmd_tester.qcrbox_client.get_calculation_by_id")
@patch("qcrbox_cmd_tester.qcrbox_client.stop_running_calculation")
@patch("qcrbox_cmd_tester.qcrbox_client.delete_dataset_by_id")
@patch("time.sleep")
@patch("time.time")
def test_timeout_timing_accuracy(
    mock_time,
    mock_sleep,
    mock_delete_dataset,
    mock_stop_calculation,
    mock_get_calculation,
    mock_invoke_command,
    mock_prepare_params,
    mock_client,
    mock_calculation_response_running,
):
    """Test that timeout is checked at the right time."""
    # Setup mocks
    mock_prepare_params.return_value = ({}, [])

    mock_invoke_response = Mock()
    mock_invoke_response.payload.calculation_id = "calc-timing"
    mock_invoke_command.sync.return_value = mock_invoke_response

    mock_get_calculation.sync.return_value = mock_calculation_response_running

    # Simulate time progression: start at 1000, add 1 second per iteration
    current_time = [1000.0]

    def increment_time():
        result = current_time[0]
        current_time[0] += 1.0
        return result

    mock_time.side_effect = increment_time

    # Run with 3 second timeout - should timeout on 4th iteration
    result = run_qcrbox_command(
        client=mock_client,
        command_name="test_command",
        application_slug="test_app",
        application_version="1.0.0",
        command_parameters=[],
        timeout_seconds=3.0,
    )

    # Verify timeout occurred
    assert result.status == "timeout"

    # Should have polled approximately 4 times before timeout
    # (start_time check + 3 iterations before exceeding 3 seconds)
    assert mock_get_calculation.sync.call_count >= 3
    assert mock_get_calculation.sync.call_count <= 5
