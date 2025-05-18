import yaml
from pathlib import Path
from typing import List, Optional
from pydantic import ValidationError

from promptcheck.core.schemas import TestFile, TestCase, PromptCheckConfig

class TestFileLoadError(Exception):
    # ... (no change internal to this class)
    pass

def load_test_cases_from_yaml(file_path: Path) -> TestFile:
    # ... (no change to internal logic, uses imported TestFile)
    pass

CONFIG_FILENAME = "promptcheck.config.yaml"

class ConfigFileLoadError(Exception):
    # ... (no change internal to this class)
    pass

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