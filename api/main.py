from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import boto3
import uvicorn
import logging
from typing import Optional, List

load_dotenv("../.env")

app = FastAPI()
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

class VideoURLs(BaseModel):
    urls: list[str]

class VideoStatus(BaseModel):
    id: str
    status: str
    error_message: Optional[str] = None

@app.get("/")
def health_check():
    return {"status": "healthy"}

@app.post("/video/process")
async def process_video(video: VideoURLs):
    pending_videos = []
    try:
        for url in video.urls:
            # Insert record into Supabase
            response = supabase.table("video_urls").insert({"url": str(url), "status": "pending"}).execute()
            video_id = response.data[0]['id']

            # Send message to SQS
            sqs.send_message(
                QueueUrl=os.getenv("SQS_DOWNLOAD_QUEUE_URL"),
                MessageBody=f"{video_id},{str(url)}"
            )

            pending_videos.append({"id": video_id, "status": "pending"})

        return pending_videos
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/video/status", response_model=List[VideoStatus])
async def get_video_status(video_id: Optional[str] = Query(None)):
    try:
        query = supabase.table("video_urls").select("id,status,error_message")
        if video_id:
            query = query.eq("id", video_id)
        response = query.execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Video not found")
        
        return [VideoStatus(**item) for item in response.data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/video/clips")
async def get_video_signed_url(video_id: str = Query(...)):
    try:
        # Check if the video processing is completed
        response = supabase.table("video_urls").select("status").eq("id", video_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Video not found")
        
        video_info = response.data[0]
        status = video_info['status']
        if not status in ("completed", "generating_clips"):
            raise HTTPException(status_code=400, detail=f"Video processing is not completed. Current status: {status}")

        clips = supabase.table("video_clips").select("*").eq("video_id", video_id).order("relevance_score", desc=True).execute().data
        if not clips:
            return {"clips": []}
        
        clip_urls = []
        for clip in clips:
            clip_url = clip['url']
            
            signed_url = supabase.storage.from_("videos").create_signed_url(clip_url, 1800)  # 30 minutes expiration
            clip["url"] = signed_url.get("signedURL")
            clip_urls.append(clip)

        return {"clips": clip_urls}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)s)",
    )

    uvicorn.run("main:app", log_config=None, host="0.0.0.0", port=28000, reload=True)