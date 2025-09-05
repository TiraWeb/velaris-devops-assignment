import os
import boto3
import json

ecs_client = boto3.client('ecs')

CLUSTER_NAME = os.environ['ECS_CLUSTER_NAME']
SERVICE_NAME = os.environ['ECS_SERVICE_NAME']

def handler(event, context):
    # This lambda scales the ECS service up or down.
    # The desired_count comes from the EventBridge rule.
    try:
        desired_count = int(event['desired_count'])
        print(f"Received event to update service {SERVICE_NAME} in cluster {CLUSTER_NAME} to {desired_count} tasks.")

        response = ecs_client.update_service(
            cluster=CLUSTER_NAME,
            service=SERVICE_NAME,
            desiredCount=desired_count
        )

        print("Successfully updated the service.")
        return {
            'statusCode': 200,
            'body': json.dumps(f'Successfully set desired count to {desired_count}')
        }

    except Exception as e:
        print(f"Error updating service: {e}")
        # Just log the error, monitoring will catch if the service is actually down.
        raise e