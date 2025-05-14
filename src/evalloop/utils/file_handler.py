import yaml
from pathlib import Path
from typing import List, Optional
from pydantic import ValidationError

from evalloop.core.schemas import TestFile, TestCase, EvalLoopConfig # Assuming schemas.py is in evalloop.core

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
        return TestFile(__root__=[]) # Return an empty list of test cases
        
    if not isinstance(raw_data, list):
        raise TestFileLoadError(
            "YAML content should be a list of test cases.", 
            file_path=file_path
        )

    try:
        test_file = TestFile(__root__=raw_data)
        return test_file
    except ValidationError as e:
        raise TestFileLoadError(
            "Test file content does not match the required schema.",
            file_path=file_path,
            errors=e.errors()
        )

# Example Usage (for testing this file directly):
if __name__ == '__main__':
    # Create a dummy valid test file
    dummy_tests_dir = Path("temp_tests_for_loader")
    dummy_tests_dir.mkdir(exist_ok=True)
    valid_test_file = dummy_tests_dir / "valid_sample.yaml"
    valid_test_content = """
- id: test001
  name: My First Test
  input:
    prompt: "Hello AI"
  expected:
    exact_match_string: "Hello User"
  metrics:
    - metric: exact_match
  model:
    provider: openai
    model_name: gpt-3.5-turbo

- name: My Second Test # ID is optional
  input_data:
    prompt: "Another prompt"
  expected_output:
    reference_texts: ["Some reference"]
  metric_configs:
    - metric: rouge_l
      threshold:
        f_score: 0.7
    """
    with open(valid_test_file, 'w') as f:
        f.write(valid_test_content)

    # Create a dummy invalid test file (missing required field 'name')
    invalid_test_file_structure = dummy_tests_dir / "invalid_structure.yaml"
    invalid_content_structure = """
- id: test002
  # name is missing
  input:
    prompt: "Test prompt"
  expected:
    exact_match_string: "Test expected"
  metrics:
    - metric: "exact_match"
    """
    with open(invalid_test_file_structure, 'w') as f:
        f.write(invalid_content_structure)
    
    # Create a file that is not a list
    not_a_list_file = dummy_tests_dir / "not_a_list.yaml"
    not_a_list_content = """
    test_case: 
      name: "A single object, not a list"
      input:
        prompt: "..."
      expected:
        exact_match_string: "..."
      metrics: [{"metric": "exact_match"}]
    """
    with open(not_a_list_file, 'w') as f:
        f.write(not_a_list_content)

    # Test loading the valid file
    print(f"--- Loading valid file: {valid_test_file} ---")
    try:
        loaded_tests = load_test_cases_from_yaml(valid_test_file)
        print(f"Successfully loaded {len(loaded_tests)} test cases.")
        for i, test_case in enumerate(loaded_tests):
            print(f"Test Case {i+1} Name: {test_case.name}")
            print(f"  Input prompt: {test_case.input_data.prompt}")
            print(f"  Metrics: {[mc.metric for mc in test_case.metric_configs]}")
            print(f"  Model provider: {test_case.model_config.provider}")
    except TestFileLoadError as e:
        print(f"Error loading test file: {e}")

    # Test loading the invalid file (structure error)
    print(f"\n--- Loading invalid structure file: {invalid_test_file_structure} ---")
    try:
        load_test_cases_from_yaml(invalid_test_file_structure)
    except TestFileLoadError as e:
        print(f"Successfully caught error: {e}")

    # Test loading the file that is not a list
    print(f"\n--- Loading file that is not a list: {not_a_list_file} ---")
    try:
        load_test_cases_from_yaml(not_a_list_file)
    except TestFileLoadError as e:
        print(f"Successfully caught error: {e}")

    # Test loading a non-existent file
    print(f"\n--- Loading non-existent file ---")
    try:
        load_test_cases_from_yaml(Path("non_existent_file.yaml"))
    except TestFileLoadError as e:
        print(f"Successfully caught error: {e}")
        
    # Clean up dummy files
    import shutil
    shutil.rmtree(dummy_tests_dir)
    print(f"\nCleaned up {dummy_tests_dir}")

CONFIG_FILENAME = "evalloop.config.yaml" # Standard config file name

class ConfigFileLoadError(Exception):
    """Custom exception for errors during config file loading or parsing."""
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

def load_evalloop_config(config_dir: Path = Path(".")) -> EvalLoopConfig:
    """
    Loads the EvalLoop configuration from evalloop.config.yaml in the specified directory.
    If the file doesn't exist or is empty, returns a default EvalLoopConfig object.

    Args:
        config_dir: The directory where evalloop.config.yaml is expected.

    Returns:
        An EvalLoopConfig object.

    Raises:
        ConfigFileLoadError: If the file is invalid YAML or does not conform to schema.
    """
    config_file_path = config_dir / CONFIG_FILENAME

    if not config_file_path.exists():
        # If no config file, return a default config. This is fine as most things are optional.
        return EvalLoopConfig()
    
    try:
        with open(config_file_path, 'r') as f:
            raw_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigFileLoadError(f"Invalid YAML format in config: {e}", file_path=config_file_path)
    except IOError as e:
        raise ConfigFileLoadError(f"Could not read config file: {e}", file_path=config_file_path)

    if raw_data is None: # Handle empty YAML file
        return EvalLoopConfig()

    if not isinstance(raw_data, dict):
        raise ConfigFileLoadError(
            "Config file content should be a dictionary (mapping).", 
            file_path=config_file_path
        )

    try:
        config = EvalLoopConfig(**raw_data)
        return config
    except ValidationError as e:
        raise ConfigFileLoadError(
            "Config file content does not match the required schema.",
            file_path=config_file_path,
            errors=e.errors()
        )

# Need to import EvalLoopConfig for the function signature if it's not already imported globally
from evalloop.core.schemas import EvalLoopConfig
