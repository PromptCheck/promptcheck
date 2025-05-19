import yaml
from pathlib import Path
from typing import List, Optional
from pydantic import ValidationError

from promptcheck.core.schemas import TestFile, TestCase, PromptCheckConfig

class TestFileLoadError(Exception):
    """Custom exception for errors during test file loading or parsing."""
    def __init__(self, message, file_path: Optional[Path] = None, errors: Optional[List[dict]] = None):
        super().__init__(message)
        self.file_path = file_path
        self.errors = errors # For Pydantic validation errors

    def __str__(self):
        error_str = super().__str__()
        if self.file_path:
            error_str += f"\nFile: {self.file_path}"
        if self.errors:
            for err in self.errors:
                loc = " -> ".join(map(str, err['loc']))
                error_str += f"\n  Error at '{loc}': {err['msg']} (type: {err['type']})"
        return error_str

def load_test_cases_from_yaml(file_path: Path) -> TestFile:
    """
    Loads test cases from a specified YAML file.

    Args:
        file_path: Path to the YAML file.

    Returns:
        A TestFile object containing a list of validated TestCase objects.

    Raises:
        TestFileLoadError: If the file cannot be opened, is not valid YAML,
                           or does not conform to the TestCase schema.
    """
    if not file_path.exists():
        raise TestFileLoadError(f"Test file not found.", file_path=file_path)
    if not file_path.is_file():
        raise TestFileLoadError(f"Path provided is not a file.", file_path=file_path)

    try:
        with open(file_path, 'r') as f:
            raw_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise TestFileLoadError(f"Invalid YAML format: {e}", file_path=file_path)
    except IOError as e:
        raise TestFileLoadError(f"Could not read file: {e}", file_path=file_path)

    if raw_data is None: # Handle empty YAML file
        return TestFile(root=[]) # Use root= for Pydantic V2 RootModel
        
    if not isinstance(raw_data, list):
        raise TestFileLoadError(
            "YAML content should be a list of test cases.", 
            file_path=file_path
        )

    try:
        # Pydantic V2: Pass the list directly to the RootModel constructor using the 'root' argument
        test_file = TestFile(root=raw_data)
        return test_file
    except ValidationError as e:
        raise TestFileLoadError(
            "Test file content does not match the required schema.",
            file_path=file_path,
            errors=e.errors()
        )

CONFIG_FILENAME = "promptcheck.config.yaml"

class ConfigFileLoadError(Exception):
    def __init__(self, message, file_path: Optional[Path] = None, errors: Optional[List[dict]] = None):
        super().__init__(message)
        self.file_path = file_path
        self.errors = errors

    def __str__(self):
        error_str = super().__str__()
        if self.file_path:
            error_str += f"\nFile: {self.file_path}"
        if self.errors:
            for err in self.errors:
                loc = " -> ".join(map(str, err['loc']))
                error_str += f"\n  Error at '{loc}': {err['msg']} (type: {err['type']})"
        return error_str

def load_promptcheck_config(config_dir: Path = Path(".")) -> PromptCheckConfig:
    """
    Loads the PromptCheck configuration from promptcheck.config.yaml in the specified directory.
    If the file doesn't exist or is empty, returns a default PromptCheckConfig object.
    """
    config_file_path = config_dir / CONFIG_FILENAME

    if not config_file_path.exists():
        return PromptCheckConfig()
    
    try:
        with open(config_file_path, 'r') as f:
            raw_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigFileLoadError(f"Invalid YAML format in config: {e}", file_path=config_file_path)
    except IOError as e:
        raise ConfigFileLoadError(f"Could not read config file: {e}", file_path=config_file_path)

    if raw_data is None: 
        return PromptCheckConfig()

    if not isinstance(raw_data, dict):
        raise ConfigFileLoadError(
            "Config file content should be a dictionary (mapping).", 
            file_path=config_file_path
        )
    try:
        config = PromptCheckConfig(**raw_data)
        return config
    except ValidationError as e:
        raise ConfigFileLoadError(
            "Config file content does not match the required schema.",
            file_path=config_file_path,
            errors=e.errors()
        )

# Remove old import if it was duplicated at the end of the file
# from promptcheck.core.schemas import PromptCheckConfig 