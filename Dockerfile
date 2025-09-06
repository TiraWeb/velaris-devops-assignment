FROM python:3.9-slim

WORKDIR /usr/src/app

COPY src/app/requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

# Copy the src code
COPY src/app/ .

EXPOSE 80

# Cmd to run the python script
CMD ["python", "app.py"]