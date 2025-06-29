# Dockerfile

# --- Base Image ---
# Use an official Python runtime as a parent image
FROM python:3.13.5-slim

# --- Environment Variables ---
# Set environment variables to prevent Python from buffering stdout and stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# --- Working Directory ---
# Set the working directory in the container
WORKDIR /app

# --- Install System Dependencies ---
# Install system dependencies if needed (e.g., for PostgreSQL client)
# For SQLite, no extra system dependencies are strictly needed here for the basic app
# If you switch to PostgreSQL, you might need:
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     postgresql-client \
#     && rm -rf /var/lib/apt/lists/*

# --- Copy Requirements and Install Python Dependencies ---
# Copy the requirements file into the container at /app
COPY requirements.txt /app/

# Install any needed packages specified in requirements.txt
# --no-cache-dir: Disables the cache, which can reduce image size.
# -r requirements.txt: Specifies the file to read requirements from.
RUN pip install --no-cache-dir -r requirements.txt

# --- Copy Application Code ---
# Copy the current directory contents into the container at /app
# This includes your Django project and the tracker app.
COPY . /app/

# --- Expose Port ---
# Make port 8000 available to the world outside this container
# This is the default port Django development server runs on.
EXPOSE 8000

# --- Default Command ---
# Define the command to run your application
# This will run migrations and then start the development server.
# For production, you would use a production-grade WSGI server like Gunicorn.
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# --- Entrypoint Script (Optional but Recommended for migrations) ---
# Create an entrypoint script to run migrations before starting the server.
# See entrypoint.sh example below.
COPY ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
# If using the entrypoint script, the CMD in docker-compose.yml or here
# will be passed as arguments to the entrypoint script.
# For development server:
CMD ["runserver"]
# For Gunicorn (production example, install gunicorn in requirements.txt):
# CMD ["gunicorn", "expense_tracker_project.wsgi:application", "--bind", "0.0.0.0:8000"]