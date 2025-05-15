# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install poetry
RUN pip install poetry==1.8.3 # Pinning poetry version for reproducibility in Docker

# Copy files required by Poetry to build/install the project and its dependencies
COPY pyproject.toml poetry.lock /app/ # Explicitly use WORKDIR path with trailing slash
COPY src/ ./src/  # Source and destination are directories

# Install project dependencies AND the project itself
# This layer is cached if pyproject.toml, poetry.lock, and src/ don't change significantly for Poetry
RUN poetry install --no-interaction --no-ansi --no-dev

# Copy other necessary files needed at runtime by the entrypoint or action
COPY tests/ ./tests/ # Source and destination are directories
COPY entrypoint.sh ./
COPY README.md ./
COPY LICENSE ./

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