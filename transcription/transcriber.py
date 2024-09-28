import replicate

def transcribe_video(supabase_client, video_id: str):
    
    print("Calling whisper on replicate") 
    signed_url = supabase_client.storage.from_("videos").create_signed_url(f"source_videos/{video_id}.mp4", 1800).get("signedURL")
    output = replicate.run(
        "openai/whisper:cdd97b257f93cb89dede1c7584e3f3dfc969571b357dbcee08e793740bedd854",
        input={
            "audio": signed_url,
            "model": "large-v3",
            "language": "auto",
            "translate": False,
            "temperature": 0,
            "transcription": "plain text",
            "suppress_tokens": "-1",
            "logprob_threshold": -1,
            "no_speech_threshold": 0.6,
            "condition_on_previous_text": True,
            "compression_ratio_threshold": 2.4,
            "temperature_increment_on_fallback": 0.2
        }
    )

    line_template = """{start}|{end}|{text}\n"""
    transcript = "segment_start_seconds|segment_end_seconds|transcript\n"

    for segment in output["segments"]:
        start = segment["start"]
        end = segment["end"]
        text = segment["text"]
        line = line_template.format(start=start, end=end, text=text)
        transcript += line

    print(transcript[:1000])

    supabase_client.table("video_urls").update({"status": "transcribed", "transcript": transcript}).eq("id", video_id).execute()
    return transcript