import boto3
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from transcriber import transcribe_video
from botocore.exceptions import ClientError
import threading

print(load_dotenv("../.env"))

supabase: Client = create_client(
    supabase_url=os.getenv("SUPABASE_AUTH_URL"), 
    supabase_key=os.getenv("SUPABASE_SERVICE_KEY")
)

sqs = boto3.client(
    'sqs', 
    region_name='us-west-2',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

def process_sqs_messages():
    print("Transcription service started")
    print("Listening for messages on queue:", os.getenv("SQS_TRANSCRIPTION_QUEUE_URL"))
    while True:
        response = sqs.receive_message(
            QueueUrl=os.getenv("SQS_TRANSCRIPTION_QUEUE_URL"),
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
            AttributeNames=['All']
        )
        
        if 'Messages' in response:
            for message in response['Messages']:
                video_id = message['Body']
                receipt_handle = message['ReceiptHandle']
                
                print("transcribing:", video_id)
                supabase.table("video_urls").update({"status": "transcribing"}).eq("id", video_id).execute()

                # Start a thread to extend the visibility timeout
                stop_event = threading.Event()
                extend_visibility_thread = threading.Thread(
                    target=extend_visibility_timeout,
                    args=(receipt_handle, stop_event)
                )
                extend_visibility_thread.start()

                try:
                    transcript = transcribe_video(
                        supabase_client=supabase, 
                        video_id=video_id,
                    )
                
                    supabase.table("video_urls").update({"status": "transcribed"}).eq("id", video_id).execute()

                    # Send to LLM analysis queue
                    sqs.send_message(
                        QueueUrl=os.getenv("SQS_LLM_QUEUE_URL"),
                        MessageBody=video_id
                    )
                
                    # Delete the message from the queue
                    sqs.delete_message(
                        QueueUrl=os.getenv("SQS_TRANSCRIPTION_QUEUE_URL"),
                        ReceiptHandle=receipt_handle
                    )
                finally:
                    # Stop the visibility extension thread
                    stop_event.set()
                    extend_visibility_thread.join()

def extend_visibility_timeout(receipt_handle, stop_event):
    while not stop_event.is_set():
        try:
            sqs.change_message_visibility(
                QueueUrl=os.getenv("SQS_TRANSCRIPTION_QUEUE_URL"),
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=300  # Extend by 5 minutes
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'MessageNotInflight':
                # Message no longer exists or was already processed
                break
        stop_event.wait(120)  # Wait for 2 minutes before extending again

if __name__ == "__main__":
    print("Starting transcription service")
    process_sqs_messages()