# Use an official lightweight Python image.
FROM python:3.12-slim

# Set the working directory in the container.
WORKDIR /app

RUN apt-get update && apt-get install -y supervisor

# Copy and install dependencies.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt


# Copy the rest of your application code.
COPY . .

# Expose the port uvicorn will run on.
EXPOSE 8000 8765

# Run the application with uvicorn.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
