#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Apply database migrations
echo "Applying database migrations..."
python manage.py makemigrations tracker
python manage.py migrate --noinput # --noinput avoids prompts

# The CMD from Dockerfile or docker-compose.yml will be executed now.
# For example, if CMD is ["runserver"], it will execute `python manage.py runserver 0.0.0.0:8000`
# If CMD is ["gunicorn", "..."], it will start Gunicorn.

if [ "$1" = "runserver" ]; then
    echo "Starting development server..."
    exec python manage.py runserver 0.0.0.0:8000
elif [ "$1" = "gunicorn" ]; then
    # Example for Gunicorn, ensure Gunicorn is in requirements.txt
    # You might pass more Gunicorn args via docker-compose command
    echo "Starting Gunicorn server..."
    exec gunicorn expense_tracker_project.wsgi:application --bind 0.0.0.0:8000 ${@:2}
else
    # Execute any other command passed
    exec "$@"
fi
