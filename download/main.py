import boto3
import yt_dlp
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import json

load_dotenv("../.env")

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

def download_and_upload_video(video_id: str, url: str):
    try:
        # Download video
        ydl_opts = {
            'format': 'bestvideo[height<=480]+bestaudio[ext=m4a]/best',
            'outtmpl': f'{video_id}.%(ext)s',
            'noplaylist': True,
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'no_warnings': True,

            'cookiefile': 'cookies.txt',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'referer': 'https://www.youtube.com/',
            'quiet': True,
            'limit_rate': '100K',
            'sleep_interval': 5,
            'max_sleep_interval': 30,
        }
        
        supabase.table("video_urls").update({"status": "downloading"}).eq("id", video_id).execute()
     
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        
        supabase.table("video_urls").update({"status": "downloaded"}).eq("id", video_id).execute()

        # Upload to Supabase storage
        with open(filename, 'rb') as f:
            try:
                supabase.storage.from_("videos").upload(file=f, path=f"source_videos/{filename}")
            except Exception as e:
                print(e)

        # Delete local file
        os.remove(filename)
        
        # Update status and send to transcription queue
        supabase.table("video_urls").update({"status": "uploaded"}).eq("id", video_id).execute()
        
        sqs.send_message(
            QueueUrl=os.getenv("SQS_TRANSCRIPTION_QUEUE_URL"),
            MessageBody=video_id
        )
    except Exception as e:
        supabase.table("video_urls").update({"status": "error", "error_message": str(e)}).eq("id", video_id).execute()
        raise(e)

def process_sqs_messages():
    while True:
        response = sqs.receive_message(
            QueueUrl=os.getenv("SQS_DOWNLOAD_QUEUE_URL"),
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20
        )
        
        if 'Messages' in response:
            for message in response['Messages']:
                video_id, url = message['Body'].split(',')

                print(f"Processing video: {video_id}")
                download_and_upload_video(video_id, url)
                
                # Delete the message from the queue
                sqs.delete_message(
                    QueueUrl=os.getenv("SQS_DOWNLOAD_QUEUE_URL"),
                    ReceiptHandle=message['ReceiptHandle']
                )


def lambda_handler(event, context):
    for record in event['Records']:
        video_id, url = record['body'].split(',')
        print(f"Processing video: {video_id}")
        download_and_upload_video(video_id, url)
    
    return {
        'statusCode': 200,
        'body': json.dumps('Processing completed')
    }

if __name__ == "__main__":
    process_sqs_messages()