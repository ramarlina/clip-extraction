from contextlib import contextmanager
import requests
import os

@contextmanager
def download_video(supabase_client, bucket_name: str, file_path: str):
    temp_file_path = None
    try:
        # Get the signed URL for the file
        signed_url = supabase_client.storage.from_(bucket_name).create_signed_url(file_path, 60)  # URL valid for 60 seconds

        # Download the entire file at once
        response = requests.get(signed_url['signedURL'])
        response.raise_for_status()

        # Create a temporary file and write the content
        temp_file_path = f"temp_{os.path.basename(file_path)}"
        with open(temp_file_path, 'wb') as f:
            f.write(response.content)
        
        yield temp_file_path

    except Exception as e:
        print(f"Error downloading video: {str(e)}")
        raise
    finally:
        # Delete the temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)