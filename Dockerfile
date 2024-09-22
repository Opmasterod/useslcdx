FROM python:3.10-slim  # Use a slimmer base image

# Set work directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port that your application listens on
EXPOSE 8080  # Use the correct port (8080)

# Run your application
CMD ["python", "main.py"]

# Create a health check endpoint in your 'app.py' file
# (Refer to the previous responses for an example of this)
