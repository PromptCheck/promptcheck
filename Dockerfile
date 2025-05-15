# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install evalloop from TestPyPI and its dependencies
RUN pip install --no-cache-dir --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple \
    evalloop==0.0.1a0

# Install Poetry, as entrypoint.sh uses `poetry run`
RUN pip install --no-cache-dir poetry==1.8.3
# Configure Poetry to use the system Python where evalloop is now installed
RUN poetry config virtualenvs.create false

# Copy the entrypoint script for the action
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# The action.yml defines inputs that entrypoint.sh uses.
# test_path and config_dir are relative to GITHUB_WORKSPACE which is /app here.
# The entrypoint.sh will need access to test files and potentially a config file from the repo.
# These are available in GITHUB_WORKSPACE on the runner, which is mounted into /app by default for Docker actions.
# However, our entrypoint.sh expects test_path and config_dir to be resolved correctly.
# The `evalloop` command installed by pip will be on the PATH.

ENTRYPOINT ["/app/entrypoint.sh"]

# The command `evalloop` should be available on the PATH after `poetry install` 
# if pyproject.toml defines it as a script. Let's ensure that is the case or add an entrypoint.

# Example: If pyproject.toml has:
# [tool.poetry.scripts]
# evalloop = "evalloop.main:app"
# Then `evalloop` command will be available.

# Default command can be overridden in action.yml
# ENTRYPOINT ["poetry", "run", "evalloop"]
# CMD ["--help"]

# For the action, the ENTRYPOINT will likely be a script that handles inputs
# or action.yml will directly call `poetry run evalloop ...` 