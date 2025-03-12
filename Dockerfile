# Use an official lightweight Python image.
FROM python:3.12-slim

# Set the working directory in the container.
WORKDIR /app
ENV APP_HOME=/app

RUN apt-get update && apt-get install -y supervisor

# Copy and install dependencies.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy supervisor configuration file
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy the rest of your application code.
COPY . .

# Expose the ports
EXPOSE 8000 8765

# Run supervisord
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]