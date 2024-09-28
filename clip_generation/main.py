import boto3
import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv
from video_processing import extract_and_enhance_clip
from moviepy.editor import VideoFileClip
from downloader import download_video
from botocore.exceptions import ClientError
import threading

load_dotenv()

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

def generate_clips(video_id: str):
    try:
        # Fetch clips_info and video URL from Supabase
        response = supabase.table("video_urls").select("clips_info,url").eq("id", video_id).execute()
        clips_info = json.loads(response.data[0]['clips_info'])
        video_url = response.data[0]['url']
        supabase.table("video_urls").update({"status": "generating_clips"}).eq("id", video_id).execute()


        with download_video(
                supabase_client=supabase, 
                bucket_name="videos", 
                file_path=f"source_videos/{video_id}.mp4"
            ) as video_path:

            clip_paths = []
            clips_data = []
            with VideoFileClip(video_path) as video:
                for i, clip in enumerate(clips_info):
                    clip_fname = f"tmp/clip_{clip['start']}_{clip['end']}.mp4"
                    try:
                        extract_and_enhance_clip(video, clip['start'], clip['end'], clip_fname)

                        clip_object = f"clips/{video_id}/clip_{clip['start']}_{clip['end']}.mp4"
                        
                        # Upload to Supabase storage
                        with open(clip_fname, 'rb') as f:
                            try:
                                supabase.storage.from_("videos").upload(file=f, path=clip_object)
                            except Exception as e:
                                print(e)
                        
                        clips_data = {
                            "video_id": video_id,
                            "url": clip_object,
                            "summary": clip.get('summary', ''),
                            "relevance_score": clip.get('relevance_score', 0),
                            "duration": clip['end'] - clip['start'],
                            "start_time": clip['start'],
                            "end_time": clip['end']
                        }
                        
                        supabase.table("video_clips").insert(clips_data).execute()

                        # Delete local file
                        os.remove(clip_fname)

                    except Exception as e:
                        print(f"Error extracting clip {i}: {str(e)}")
                        continue    

            # Update status
            supabase.table("video_urls").update({"status": "completed", "error_message" : ""}).eq("id", video_id).execute()

            # Clean up the original video file
            os.remove(video_path)
    except Exception as e:
        supabase.table("video_urls").update({"status": "error", "error_message": str(e)}).eq("id", video_id).execute()
        raise(e)
    
def process_sqs_messages():
    print("Clip generation service started")
    print("Listening for messages on queue:", os.getenv("SQS_CLIPGEN_QUEUE_URL"))
    while True:
        response = sqs.receive_message(
            QueueUrl=os.getenv("SQS_CLIPGEN_QUEUE_URL"),
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
            AttributeNames=['All']
        )
        
        if 'Messages' in response:
            for message in response['Messages']:
                video_id = message['Body']
                receipt_handle = message['ReceiptHandle']
                
                print(f"Generating clips for video: {video_id}")

                # Start a thread to extend the visibility timeout
                stop_event = threading.Event()
                extend_visibility_thread = threading.Thread(
                    target=extend_visibility_timeout,
                    args=(receipt_handle, stop_event)
                )
                extend_visibility_thread.start()

                try:
                    generate_clips(video_id)
                    
                    # Delete the message from the queue
                    sqs.delete_message(
                        QueueUrl=os.getenv("SQS_CLIPGEN_QUEUE_URL"),
                        ReceiptHandle=receipt_handle
                    )
                except Exception as e:
                    print(f"Error generating clips for video {video_id}: {str(e)}")
                    # You might want to implement some error handling here,
                    # such as moving the message to a dead-letter queue
                finally:
                    # Stop the visibility extension thread
                    stop_event.set()
                    extend_visibility_thread.join()

def extend_visibility_timeout(receipt_handle, stop_event):
    while not stop_event.is_set():
        try:
            sqs.change_message_visibility(
                QueueUrl=os.getenv("SQS_CLIPGEN_QUEUE_URL"),
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=300  # Extend by 5 minutes
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'MessageNotInflight':
                # Message no longer exists or was already processed
                break
        stop_event.wait(120) 

if __name__ == "__main__":
    process_sqs_messages()