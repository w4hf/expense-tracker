# Build
podman build --name budgetz:v1 -f Dockerfile .

# Run
# podman run -d -p 8000:8000 --name budgetz -v /home/user/db/:/app/db/:Z localhost/budgetz:v1
podman run -d -p 8000:8000 --name budgetz -v /home/w4hf/projects/budgetz-gemini/dev/db/:/app/db/:Z localhost/budgetz:v1 