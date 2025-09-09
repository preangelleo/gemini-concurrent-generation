# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Make port 5004 available to the world outside this container
EXPOSE 5004

# --- Environment Variables ---
# These can be set at runtime (e.g., with `docker run -e ...`)

# (Optional) The server's own Gemini API key for admin-authenticated requests.
ENV GEMINI_API_KEY=""

# (Optional) A secret key to identify trusted, internal requests.
ENV ADMIN_API_KEY=""

# The global concurrency limit for all Gemini API calls.
ENV GEMINI_CONCURRENCY_LIMIT=15

# Run app.py when the container launches
# Use Gunicorn for a production-ready WSGI server
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5004", "app:app"]