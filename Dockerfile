# Use an official Python runtime as a parent image
FROM python:3.13

# Set the working directory
WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy only the dependency files first for better caching
COPY pyproject.toml README.md /app/

# Install dependencies using Poetry
# RUN poetry config virtualenvs.create false \
    # && poetry install --no-interaction --no-ansi --no-root
RUN poetry install --no-interaction

# Copy the rest of the application code
COPY . /app

# Expose the port
EXPOSE 5000

# Command to run the application
CMD ["poetry", "run", "gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "main:app"]

