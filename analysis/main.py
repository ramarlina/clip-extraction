import boto3
import os
import json
from llm import analyze_video
from supabase import create_client, Client
from dotenv import load_dotenv

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

selection_criteria_list = [
    "Key insights or unique perspectives that challenge common assumptions or provide fresh angles on current events, trends, or societal issues.",
    "Surprising or little-known facts that have the potential to make viewers say 'I didn't know that!' or want to share with others.",
    "Practical, actionable advice or information that viewers can immediately apply to their daily lives or work.",
    "Emotionally resonant moments that evoke strong feelings (e.g., empathy, inspiration, awe) or personal connections with the subject matter.",
    "Controversial or thought-provoking points that could spark meaningful discussions or debates among viewers.",
    "Concise explanations of complex topics that make them more accessible to a general audience.",
    "Predictions or forecasts about future trends or developments in relevant fields.",
    "Compelling personal anecdotes or case studies that illustrate broader concepts or issues.",
    "Comparisons or contrasts that highlight important differences or similarities between ideas, events, or phenomena.",
    "Calls to action or statements that encourage viewers to engage further with the topic or make positive changes."
]

def analyze_and_postprocess(video_id: str):
    print("Analyzing video:", video_id)
    supabase.table("video_urls").update({"status": "transcribing"}).eq("id", video_id).execute()

    # Fetch transcript from Supabase
    response = supabase.table("video_urls").select("transcript").eq("id", video_id).execute()
    transcript_text = response.data[0]['transcript']

    # Update status to "analyzing"
    supabase.table("video_urls").update({"status": "analyzing"}).eq("id", video_id).execute()
    
    clips_info = analyze_video(
        transcript=transcript_text,
        selection_criteria=selection_criteria_list,
        num_clips=5,
        clip_duration_range=(15, 30)
    )

    # Store analysis and clips_info in Supabase and update status
    supabase.table("video_urls").update({
        "status": "analysis_complete",
        "clips_info": json.dumps(clips_info)
        }).eq("id", video_id).execute()

    # Send to clip generation queue
    sqs.send_message(
        QueueUrl=os.getenv("SQS_CLIPGEN_QUEUE_URL"),
        MessageBody=video_id
    )
    print("Analysis complete for video:", video_id)
    

def process_sqs_messages():
    while True:
        response = sqs.receive_message(
            QueueUrl=os.getenv("SQS_LLM_QUEUE_URL"),
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20
        )
        
        if 'Messages' in response:
            for message in response['Messages']:
                video_id = message['Body']
                analyze_and_postprocess(video_id)
                
                # Delete the message from the queue
                sqs.delete_message(
                    QueueUrl=os.getenv("SQS_LLM_QUEUE_URL"),
                    ReceiptHandle=message['ReceiptHandle']
                )

if __name__ == "__main__":
    process_sqs_messages()