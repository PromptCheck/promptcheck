# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install poetry
RUN pip install poetry==1.8.3 # Pinning poetry version for reproducibility in Docker

# Copy files for dependency installation
COPY pyproject.toml poetry.lock ./

# Install project dependencies using poetry
# This layer is cached as long as pyproject.toml and poetry.lock don't change
RUN poetry install --no-interaction --no-ansi --no-dev

# Copy the rest of the application code and necessary files
COPY evalloop ./evalloop/
COPY tests ./tests/
COPY entrypoint.sh ./
COPY README.md ./
COPY LICENSE ./
# If src layout is adopted later, COPY evalloop ./evalloop/ would be COPY src ./src/

# Make the entrypoint executable
RUN chmod +x ./entrypoint.sh

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