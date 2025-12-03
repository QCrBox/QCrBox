import yaml
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from qcrbox_cmd_tester.init_cmd import generate_test_suite

@pytest.fixture
def mock_console():
    with patch("qcrbox_cmd_tester.init_cmd.Console") as mock:
        yield mock

def test_generate_test_suite_basic(tmp_path, mock_console):
    # Setup
    config_content = {
        "slug": "test-app",
        "version": "1.0",
        "commands": [
            {
                "name": "cmd1",
                "parameters": [
                    {"name": "input_cif", "dtype": "QCrBox.cif_data_file"}
                ]
            }
        ]
    }
    config_file = tmp_path / "config_app.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_content, f)
        
    cif_file = tmp_path / "structure.cif"
    cif_file.write_text("data_test")
    
    # Execute
    generate_test_suite(config_file, cif_file)
    
    # Verify
    expected_output = tmp_path / "test_app.yaml"
    assert expected_output.exists()
    
    with open(expected_output) as f:
        result = yaml.safe_load(f)
        
    assert result["application_slug"] == "test-app"
    assert len(result["test_cases"]) == 1
    assert result["test_cases"][0]["command_name"] == "cmd1"
    assert result["test_cases"][0]["input_parameters"][0]["value"] == "./test_cif_files/structure.cif"
    
    # Verify CIF copy
    copied_cif = tmp_path / "test_cif_files" / "structure.cif"
    assert copied_cif.exists()
    assert copied_cif.read_text() == "data_test"

def test_generate_test_suite_with_defaults_and_todos(tmp_path, mock_console):
    # Setup
    config_content = {
        "slug": "test-app",
        "version": "1.0",
        "commands": [
            {
                "name": "cmd1",
                "parameters": [
                    {"name": "input_cif", "dtype": "QCrBox.cif_data_file"},
                    {"name": "param_default", "default_value": 123},
                    {"name": "param_todo", "dtype": "str"}
                ]
            }
        ]
    }
    config_file = tmp_path / "config_app.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_content, f)
        
    cif_file = tmp_path / "structure.cif"
    cif_file.write_text("data_test")
    
    # Execute
    generate_test_suite(config_file, cif_file)
    
    # Verify
    expected_output = tmp_path / "test_app.yaml"
    with open(expected_output) as f:
        result = yaml.safe_load(f)
        
    params = result["test_cases"][0]["input_parameters"]
    param_map = {p["name"]: p["value"] for p in params}
    
    assert param_map["param_default"] == 123
    assert param_map["param_todo"] == "TODO: Fill this value"

def test_generate_test_suite_output_exists_error(tmp_path, mock_console):
    # Setup
    config_content = {"slug": "test-app"}
    config_file = tmp_path / "config_app.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_content, f)
        
    cif_file = tmp_path / "structure.cif"
    cif_file.write_text("data_test")
    
    # Create existing output file
    (tmp_path / "test_app.yaml").touch()
    
    # Execute & Verify
    with pytest.raises(FileExistsError, match="Output file .* already exists"):
        generate_test_suite(config_file, cif_file)

def test_generate_test_suite_cif_exists_error(tmp_path, mock_console):
    # Setup
    config_content = {"slug": "test-app"}
    config_file = tmp_path / "config_app.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_content, f)
        
    cif_file = tmp_path / "structure.cif"
    cif_file.write_text("data_test")
    
    # Create existing CIF in target
    cif_dir = tmp_path / "test_cif_files"
    cif_dir.mkdir()
    (cif_dir / "structure.cif").touch()
    
    # Execute & Verify
    with pytest.raises(FileExistsError, match="Target CIF file .* already exists"):
        generate_test_suite(config_file, cif_file)

def test_generate_test_suite_custom_output(tmp_path, mock_console):
    # Setup
    config_content = {
        "slug": "test-app",
        "commands": [{"name": "cmd1", "parameters": [{"name": "cif", "dtype": "QCrBox.cif_data_file"}]}]
    }
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_content, f)
        
    cif_file = tmp_path / "structure.cif"
    cif_file.write_text("data_test")
    
    output_path = tmp_path / "custom_test.yaml"
    
    # Execute
    generate_test_suite(config_file, cif_file, output_path=output_path)
    
    # Verify
    assert output_path.exists()
    # CIF should be relative to output path
    assert (tmp_path / "test_cif_files" / "structure.cif").exists()

def test_generate_test_suite_no_slug_error(tmp_path, mock_console):
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump({}, f)
    
    cif_file = tmp_path / "structure.cif"
    cif_file.write_text("data")
    
    with pytest.raises(ValueError, match="must contain a 'slug' field"):
        generate_test_suite(config_file, cif_file)

def test_generate_test_suite_skips_interactive(tmp_path, mock_console):
    # Setup
    config_content = {
        "slug": "test-app",
        "commands": [
            {
                "name": "interactive_cmd",
                "implemented_as": "interactive_session",
                "parameters": [{"name": "cif", "dtype": "QCrBox.cif_data_file"}]
            },
            {
                "name": "normal_cmd",
                "implemented_as": "python_callable",
                "parameters": [{"name": "cif", "dtype": "QCrBox.cif_data_file"}]
            }
        ]
    }
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_content, f)
        
    cif_file = tmp_path / "structure.cif"
    cif_file.write_text("data_test")
    
    # Execute
    generate_test_suite(config_file, cif_file)
    
    # Verify
    expected_output = tmp_path / "test_config.yaml"
    with open(expected_output) as f:
        result = yaml.safe_load(f)
        
    assert len(result["test_cases"]) == 1
    assert result["test_cases"][0]["command_name"] == "normal_cmd"
