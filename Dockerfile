FROM python:3.10

# Set work directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port that your application listens on
EXPOSE 80

# Run your application
CMD ["python", "main.py"] 
