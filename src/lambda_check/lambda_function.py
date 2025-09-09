import os
import json
import boto3
import requests
from datetime import datetime, timezone, timedelta

# These get passed from Terraform
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']
ALB_DNS_NAME = os.environ['ALB_DNS_NAME']
ABSTRACT_API_KEY = os.environ['ABSTRACT_API_KEY'] # The new API key
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")

sns_client = boto3.client('sns', region_name=AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)

# AbstractAPI endpoint and get the time 
API_ENDPOINT = "https://timezone.abstractapi.com/v1/current_time/"
LOCATION = "Kolkata, India"

def send_alert(subject, message):
    try:
        sns_client.publish(TopicArn=SNS_TOPIC_ARN, Subject=subject, Message=message)
    except Exception as e:
        print(f"Failed to send SNS alert: {e}")

def lambda_handler(event, context):
    print("Starting health and time validation check.")
    
    api_time_obj = None
    fetched_time_str = ""
    status = "UNKNOWN"

    # 1. Grabbing the time from AbstractAPI
    try:
        params = {'api_key': ABSTRACT_API_KEY, 'location': LOCATION}
        response = requests.get(API_ENDPOINT, params=params, timeout=10)
        response.raise_for_status()
        
        # AbstractAPI gives a 'datetime' field that looks like "2025-09-05 12:30:00"
        api_datetime_str = response.json()['datetime']
        fetched_time_str = api_datetime_str # Storing the raw string just in case something goes wrong
        api_time_obj = datetime.strptime(api_datetime_str, '%Y-%m-%d %H:%M:%S')
        
        print(f"Successfully fetched time: {fetched_time_str}")

    except Exception as e:
        msg = f"Failed to fetch or parse time from API: {e}"
        send_alert("Validation Alert: Time API Failure", msg)
        fetched_time_str = "API_ERROR"
        print(msg)

    # 2. Check the app's health and see if the times are in sync
    try:
        url = f"http://{ALB_DNS_NAME}"
        server_response = requests.get(url, timeout=5)
        
        if server_response.status_code != 200:
             status = "FAILED"
             msg = f"Application health check failed with status code {server_response.status_code}"
             send_alert("Validation Alert: Application Unhealthy", msg)
             print(msg)
        else:
            if api_time_obj is None:
                status = "DEGRADED"
                print("Server is OK, but time validation could not be performed due to API failure.")
            else:
                ist_timezone = timezone(timedelta(hours=5, minutes=30))
                local_time_in_ist = datetime.now(timezone.utc).astimezone(ist_timezone)
                
                if api_time_obj.hour == local_time_in_ist.hour:
                    status = "OK"
                    print("Validation Successful: Time is in sync and server is healthy.")
                else:
                    status = "FAILED"
                    msg = f"Time validation failed. API hour: {api_time_obj.hour}, Local IST hour: {local_time_in_ist.hour}"
                    send_alert("Validation Alert: Time Mismatch", msg)
                    print(msg)

    except Exception as e:
        status = "FAILED"
        msg = f"Failed to connect to the application server: {e}"
        send_alert("Validation Alert: Server Unreachable", msg)
        print(msg)
        
    # 3. And then save the findings to DynamoDB
    try:
        table.put_item(
            Item={
                'container_id': 'global_time_check',
                'fetched_time': fetched_time_str,
                'last_checked': datetime.now(timezone.utc).isoformat(),
                'status': status
            }
        )
        print(f"Successfully persisted final status '{status}' to DynamoDB.")
    except Exception as e:
        msg = f"Failed to write to DynamoDB: {e}"
        send_alert("Validation Alert: Database Failure", msg)
        print(msg)

    return {'statusCode': 200, 'body': json.dumps(f'Check complete. Final status: {status}')}