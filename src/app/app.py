import os
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from flask import Flask, render_template
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

app = Flask(__name__)

# Get config from environment variables
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "velaris-time-validation")
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")

# It's better to create the client once
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)

# Define our desired readable format
DATE_FORMAT = "%B %d, %Y, %I:%M:%S %p IST"

def get_container_id():
    """Fetches the unique container ID from the ECS metadata endpoint."""
    try:
        metadata_uri = os.environ.get('ECS_CONTAINER_METADATA_URI_V4')
        if not metadata_uri:
            return "local-dev-container"

        r = requests.get(metadata_uri, timeout=2)
        r.raise_for_status()
        metadata = r.json()
        return metadata['Labels']['com.amazonaws.ecs.task-arn'].split('/')[-1]
    except requests.exceptions.RequestException as e:
        print(f"Could not get container metadata: {e}")
        return "unknown-container"

@app.route('/')
def home():
    container_id = get_container_id()
    error_message = None
    fetched_time = "N/A"
    status = "N/A"

    try:
        response = table.get_item(Key={'container_id': 'global_time_check'})
        
        if 'Item' in response:
            item = response['Item']
            status = item.get('status', 'N/A')
            
            # Get the raw time string from the database
            fetched_time_raw = item.get('fetched_time', 'N/A')
            
            # Format the time string if it's not an error
            if fetched_time_raw not in ["N/A", "ERROR"]:
                # Parse the ISO string into a datetime object
                dt_object = datetime.fromisoformat(fetched_time_raw)
                # Format it into our readable string
                fetched_time = dt_object.strftime(DATE_FORMAT)
            else:
                fetched_time = fetched_time_raw
        else:
            error_message = "No check data found. Please wait for the next validation run."
            
    except Exception as e:
        error_message = f"An unexpected error occurred: {str(e)}"

    # Generate and format the container's current local time
    now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
    local_time_formatted = now_ist.strftime(DATE_FORMAT)

    return render_template(
        'index.html',
        container_id=container_id,
        fetched_time=fetched_time,
        local_time=local_time_formatted,
        status=status,
        error=error_message
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)