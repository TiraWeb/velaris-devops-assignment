import os
import json
import boto3
import requests
from datetime import datetime, timezone, timedelta

SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']
ALB_DNS_NAME = os.environ['ALB_DNS_NAME']
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")

sns_client = boto3.client('sns', region_name=AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)

TIME_API_URL = "https://timeapi.io/api/time/current/zone?timeZone=Asia/Kolkata"

def send_alert(subject, message):
    try:
        sns_client.publish(TopicArn=SNS_TOPIC_ARN, Subject=subject, Message=message)
    except Exception as e:
        print(f"Failed to send SNS alert: {e}")

def lambda_handler(event, context):
    print("Starting health and time validation check.")
    
    # 1. Get time from the API
    try:
        response = requests.get(TIME_API_URL, timeout=10)
        response.raise_for_status()
        api_time_str_raw = response.json()['dateTime']
        print(f"Successfully fetched time: {api_time_str_raw}")

        if '.' in api_time_str_raw:
            main_part, fractional_part = api_time_str_raw.split('.')
            fractional_part = fractional_part[:6]
            api_time_str = f"{main_part}.{fractional_part}"
        else:
            api_time_str = api_time_str_raw

        api_time_obj = datetime.fromisoformat(api_time_str)
        
    except Exception as e:
        msg = f"Failed to fetch or parse time from API: {e}"
        send_alert("Validation Alert: Time API Failure", msg)
        return {'statusCode': 500, 'body': json.dumps(msg)}

    # 2. Get our local time and check if it's correct
    status = "UNKNOWN"
    try:
        local_time_utc = datetime.now(timezone.utc)
        
        # this was the fix for the timezone issue
        # create the IST timezone correctly using timedelta
        ist_timezone = timezone(timedelta(hours=5, minutes=30))
        local_time_in_ist = local_time_utc.astimezone(ist_timezone)
        
        if api_time_obj.hour == local_time_in_ist.hour:
            print(f"Validation Successful: API hour ({api_time_obj.hour}) matches Local IST hour ({local_time_in_ist.hour}).")
            status = "OK"
        else:
            print(f"Validation FAILED: API hour ({api_time_obj.hour}) does NOT match Local IST hour ({local_time_in_ist.hour}).")
            status = "FAILED"
            msg = f"Time validation failed. API time (IST): {api_time_str}, Our time (IST): {local_time_in_ist.isoformat()}"
            send_alert("Validation Alert: Time Mismatch", msg)
        
        url = f"http://{ALB_DNS_NAME}"
        server_response = requests.get(url, timeout=5)
        if server_response.status_code != 200:
             status = "FAILED"
             msg = f"Own application health check failed with status code {server_response.status_code}"
             print(msg) # log the failure
             # only send an alert if the time validation hadn't already failed
             if status != "FAILED":
                send_alert("Validation Alert: Application Unhealthy", msg)

    except Exception as e:
        status = "FAILED"
        msg = f"Failed to check server or validate time: {e}"
        send_alert("Validation Alert: Server Unreachable or Invalid", msg)
        
    # 4. Save the results to DynamoDB
    try:
        table.put_item(
            Item={
                'container_id': 'global_time_check',
                'fetched_time': api_time_str,
                'last_checked': datetime.now(timezone.utc).isoformat(),
                'status': status
            }
        )
        print("Successfully persisted results to DynamoDB.")
    except Exception as e:
        msg = f"Failed to write to DynamoDB: {e}"
        send_alert("Validation Alert: Database Failure", msg)

    return {'statusCode': 200, 'body': json.dumps('Check complete.')}