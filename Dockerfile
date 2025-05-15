# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install evalloop from TestPyPI, allowing fallback to PyPI for dependencies
RUN pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple \
    evalloop==0.0.1a0

# The playbook suggests a fixed entrypoint for testing the published package.
# Our actual action uses entrypoint.sh to parse inputs.
# For now, to match the playbook's intent for this *specific test of TestPyPI install*,
# we use its suggested entrypoint. We will revert/adapt this later.
# The action.yml still defines inputs, but this fixed entrypoint won't use them.
ENTRYPOINT ["evalloop", "run", "tests/basic_example.yaml"]

# To make this Dockerfile work with the existing action.yml which passes inputs,
# and to make the action still use its flexible entrypoint.sh, we should actually
# just modify the installation part and keep our existing entrypoint.sh logic.

# Corrected approach: Modify existing Dockerfile to pip install from TestPyPI,
# but keep the rest of our Dockerfile structure (Poetry, entrypoint.sh) for the full action functionality.

# Let's re-evaluate. The playbook's Dockerfile is *very* minimal and changes the entrypoint.
# This is okay for a *temporary test* to see if the action can *pull the wheel*.

# For this step, let's use the playbook's Dockerfile VERBATIM to test the TestPyPI package install and basic run.
# We will need to adjust it back afterwards for full action functionality.

# Install poetry
RUN pip install poetry==1.8.3 # Pinning poetry version for reproducibility in Docker

# Copy files required by Poetry to build/install the project and its dependencies
COPY pyproject.toml poetry.lock /app/
COPY src/ /app/src/
COPY tests/ /app/tests/
COPY entrypoint.sh /app/entrypoint.sh
COPY README.md /app/README.md
COPY LICENSE /app/LICENSE

# Configure Poetry to not create virtualenvs, then install
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-dev

# Make the entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Set the entrypoint
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