from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, Field, TypeAdapter, field_validator, model_validator

from .expected_values import ExpectedResultType

# ---------------- Input Parameter Models ---------------- #


class QCrBoxParameter(BaseModel):
    model_config = {"str_strip_whitespace": True, "extra": "forbid"}

    name: str = Field(..., min_length=1)
    value: str | int | float | bool

    @classmethod
    def from_yaml_dict(cls, data: dict, base_folder: Path) -> Self:
        """Create parameter from YAML dictionary."""
        param_type = data.get("type", "str")
        param_data = {"name": data["name"], "value": data["value"]}
        upload_filename = data.get("upload_filename")

        if param_type == "external_file":
            return QCrBoxFileParameter.from_external_file(
                file_path=data["value"],
                name=data["name"],
                base_folder=base_folder,
                upload_filename=upload_filename,
            )
        elif param_type == "internal_file":
            return QCrBoxFileParameter.from_internal_file(
                file_content=data["value"], name=data["name"], upload_filename=upload_filename
            )
        else:
            return cls(**param_data)


class QCrBoxFileParameter(BaseModel):
    name: str = Field(..., min_length=1)
    file_content: str
    upload_filename: str | None = Field(default=None, description="Filename to use when uploading to QCrBox")

    @classmethod
    def from_internal_file(cls, file_content: str, name: str, upload_filename: str | None = None) -> Self:
        return cls(name=name, file_content=file_content, upload_filename=upload_filename)

    @classmethod
    def from_external_file(
        cls, file_path: str | Path, name: str, base_folder: Path, upload_filename: str | None = None
    ) -> Self:
        file_path = Path(file_path)
        if not file_path.is_absolute():
            file_path = base_folder / file_path
        file_content = file_path.read_text()
        return cls(name=name, file_content=file_content, upload_filename=upload_filename)


# union of all parameter types
QCrBoxParameterType = QCrBoxParameter | QCrBoxFileParameter


class TestCase(BaseModel):
    model_config = {"extra": "forbid"}

    name: str = Field(..., min_length=1)
    description: str = Field(default="")

    qcrbox_application_slug: str = Field(..., min_length=1)
    qcrbox_application_version: str = Field(..., min_length=1)
    qcrbox_command_name: str = Field(..., min_length=1)
    qcrbox_command_parameters: list[QCrBoxParameterType] = Field(default_factory=list)
    timeout_seconds: float = Field(default=600.0)

    expected_results: list[ExpectedResultType] = Field(default_factory=list)

    @classmethod
    def from_yaml_dict(cls, data: dict, application_slug: str, application_version: str, base_folder: Path) -> Self:
        """Create TestCase from YAML dictionary."""
        # Parse parameters
        parameters: list[QCrBoxParameterType] = [
            QCrBoxParameter.from_yaml_dict(param, base_folder=base_folder) for param in data.get("input_parameters", [])
        ]

        # Parse expected results - Pydantic handles discrimination automatically
        expected_results_adapter = TypeAdapter(list[ExpectedResultType])
        expected_results = expected_results_adapter.validate_python(data.get("expected_results", []))

        return cls(
            name=data["name"],
            description=data.get("description", ""),
            qcrbox_application_slug=application_slug,
            qcrbox_application_version=application_version,
            qcrbox_command_name=data["command_name"],
            timeout_seconds=data.get("timeout_seconds", 600.0),
            qcrbox_command_parameters=parameters,
            expected_results=expected_results,
        )

    @field_validator("expected_results")
    @classmethod
    def must_have_at_least_one_result(cls, v):
        if not v:
            raise ValueError("Test case must have at least one expected result")
        return v

    @model_validator(mode="after")
    def validate_parameter_names_unique(self):
        names = [p.name for p in self.qcrbox_command_parameters]
        if len(names) != len(set(names)):
            duplicates = {n for n in names if names.count(n) > 1}
            raise ValueError(f"Duplicate parameter names found: {duplicates}")
        return self


class TestSuite(BaseModel):
    model_config = {"extra": "forbid"}

    application_slug: str = Field(..., min_length=1)
    application_version: str = Field(..., min_length=1)
    description: str = Field(default="")
    tests: list[TestCase] = Field(default_factory=list)

    @classmethod
    def from_yaml_dict(cls, data: dict, base_folder: Path) -> Self:
        """Create TestSuite from parsed YAML dictionary."""
        application_slug = data["application_slug"]
        application_version = data["application_version"]

        tests = [
            TestCase.from_yaml_dict(test_data, application_slug, application_version, base_folder)
            for test_data in data.get("test_cases", [])
        ]

        return cls(
            application_slug=application_slug,
            application_version=application_version,
            description=data.get("description", ""),
            tests=tests,
        )

    @classmethod
    def from_yaml_file(cls, file_path: str | Path) -> Self:
        """Load TestSuite directly from YAML file."""
        file_path = Path(file_path)
        with open(file_path) as file:
            data = yaml.safe_load(file)
        return cls.from_yaml_dict(data, base_folder=file_path.parent)

    @field_validator("tests")
    @classmethod
    def must_have_tests(cls, v):
        if not v:
            raise ValueError("Test suite must contain at least one test")
        return v

    @model_validator(mode="after")
    def validate_test_names_unique(self):
        names = [t.name for t in self.tests]
        if len(names) != len(set(names)):
            duplicates = {n for n in names if names.count(n) > 1}
            raise ValueError(f"Duplicate test names found: {duplicates}")
        return self

    def to_json_file(self, file_path: str):
        """Export test suite to JSON."""
        with open(file_path, "w") as f:
            f.write(self.model_dump_json(indent=2))

    def to_dict(self) -> dict:
        """Export to dictionary."""
        return self.model_dump(mode="json")
