FROM python:3.9-slim

# Set the working directory
WORKDIR /usr/src/app

# Copy the requirements file
COPY src/app/requirements.txt ./

# Install python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source code
COPY src/app/ .

# Expose port 80
EXPOSE 80

# Command to run the python script
CMD ["python", "app.py"]