import shutil
import yaml
from pathlib import Path
from typing import Any, Dict, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

def generate_test_suite(config_path: Path, cif_path: Path, output_path: Path | None = None) -> None:
    """
    Generate a basic test suite from an application configuration file.
    
    Args:
        config_path: Path to the application configuration YAML file.
        cif_path: Path to a valid CIF file to use for testing.
        output_path: Path to write the generated test suite to. If None, defaults to test_{slug}.yaml.
    """
    console = Console()
    config_path = config_path.resolve()
    cif_path = cif_path.resolve()
    
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    app_slug = config.get("slug")
    app_version = config.get("version")
    
    if not app_slug:
        raise ValueError("Configuration file must contain a 'slug' field.")

    # Determine output paths
    if output_path:
        output_path = output_path.resolve()
        target_dir = output_path.parent
    else:
        target_dir = config_path.parent
        
        # Derive filename from config filename
        config_stem = config_path.stem
        if config_stem.startswith("config_"):
            test_filename = f"test_{config_stem[7:]}.yaml"
        else:
            test_filename = f"test_{config_stem}.yaml"
            
        output_path = target_dir / test_filename

    if output_path.exists():
        raise FileExistsError(f"Output file '{output_path}' already exists. Please delete it or specify a different output path.")

    # Setup CIF directory and copy file
    cif_dir = target_dir / "test_cif_files"
    cif_dir.mkdir(parents=True, exist_ok=True)
    
    target_cif_path = cif_dir / cif_path.name
    
    if target_cif_path.exists():
        raise FileExistsError(f"Target CIF file '{target_cif_path}' already exists. Please delete it to proceed.")

    shutil.copy2(cif_path, target_cif_path)
    
    # Relative path to be used in the YAML file
    relative_cif_path = f"./test_cif_files/{cif_path.name}"
    
    test_suite = {
        "application_slug": app_slug,
        "application_version": app_version,
        "description": f"Auto-generated test suite for {config.get('name', app_slug)}",
        "test_cases": []
    }
    
    commands = config.get("commands", [])
    todos = []
    
    for command in commands:
        command_name = command.get("name")
        parameters = command.get("parameters", [])
        
        # Find the parameter that accepts a CIF file
        cif_param_name = None
        required_params = []
        
        for param in parameters:
            param_name = param.get("name")
            dtype = param.get("dtype")
            default_value = param.get("default_value")
            
            if dtype == "QCrBox.cif_data_file":
                cif_param_name = param_name
            elif dtype == "QCrBox.output_cif":
                 required_params.append({
                    "name": param_name,
                    "type": "str",
                    "value": f"output_{command_name}.cif"
                })
            elif default_value is not None:
                # Use default value
                param_type = "str"
                if isinstance(default_value, int):
                    param_type = "int"
                elif isinstance(default_value, float):
                    param_type = "float"
                elif isinstance(default_value, bool):
                    param_type = "bool"
                
                required_params.append({
                    "name": param_name,
                    "type": param_type,
                    "value": default_value
                })
            else:
                # Required parameter without default value
                required_params.append({
                    "name": param_name,
                    "type": "str", # Default to str, user can change
                    "value": "TODO: Fill this value"
                })
                todos.append({
                    "command": command_name,
                    "parameter": param_name,
                    "type": dtype or "unknown"
                })

        if cif_param_name:
            test_case = {
                "name": f"test_{command_name}",
                "description": f"Basic test for {command_name}",
                "command_name": command_name,
                "timeout_seconds": 60,
                "input_parameters": [
                    {
                        "name": cif_param_name,
                        "type": "external_file",
                        "value": relative_cif_path
                    }
                ] + required_params,
                "expected_results": [
                    {
                        "result_type": "status",
                        "expected": "successful"
                    }
                ]
            }
            test_suite["test_cases"].append(test_case)
            
    if not test_suite["test_cases"]:
        console.print(f"[bold red]Warning:[/bold red] No commands found in {config_path} that accept a CIF file.")
        
    with open(output_path, "w") as f:
        yaml.dump(test_suite, f, sort_keys=False, default_flow_style=False)
    
    console.print(Panel(f"Generated test suite at [bold]{output_path}[/bold]", title="Success", style="green"))
    console.print(f"Copied CIF file to [bold]{target_cif_path}[/bold]")
    
    if todos:
        console.print("\n[bold yellow]Action Required:[/bold yellow]")
        console.print("The following parameters require values. Please edit the generated YAML file:")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Command")
        table.add_column("Parameter")
        table.add_column("Type")
        
        for todo in todos:
            table.add_row(todo["command"], todo["parameter"], todo["type"])
            
        console.print(table)
