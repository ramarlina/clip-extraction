from moviepy.editor import VideoFileClip
import cv2
import numpy as np
import logging
from moviepy.audio.fx.all import audio_normalize
import dlib
from tqdm import tqdm

# Initialize the face detector
face_detector = dlib.get_frontal_face_detector()

def detect_face(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_detector(gray, 1)
    if len(faces) > 0:
        face = faces[0]
        return (face.left(), face.top(), face.width(), face.height())
    return None

def smooth_positions(positions, window_size=10):
    smoothed = []
    for i in range(len(positions)):
        start = max(0, i - window_size // 2)
        end = min(len(positions), i + window_size // 2)
        window = positions[start:end]
        smoothed.append(int(np.mean(window)))
    return smoothed

def auto_reframe(clip, target_aspect_ratio):
    w, h = clip.size
    new_w = int(h * target_aspect_ratio)
    
    # Pre-compute face positions for all frames
    face_positions = []
    fps = 16
    for t in tqdm(np.arange(0, clip.duration, 1/fps)):
        frame = clip.get_frame(t)
        face = detect_face(frame)
        if face is not None:
            x, y, fw, fh = face
            center_x = x + fw // 2
            face_positions.append(center_x)
        else:
            face_positions.append(w // 2)
    
    # Smooth the face positions
    smoothed_positions = smooth_positions(face_positions)
    
    def reframe(get_frame, t):
        frame = get_frame(t)
        frame_index = int(t * fps)
        center_x = smoothed_positions[frame_index]
        
        x1 = max(0, min(w - new_w, center_x - new_w // 2))
        return frame[:, x1:x1+new_w]

    return clip.fl(reframe)

def extract_and_enhance_clip(video_clip: VideoFileClip, start_time: int, end_time: int, output_path: str):
    logging.info(f"Extracting clip from {start_time} to {end_time}")
    
    if start_time is None or end_time is None:
        raise ValueError(f"Invalid start or end time: start={start_time}, end={end_time}")
    
    # Extract the clip
    clip = video_clip.subclip(start_time, min(end_time, video_clip.duration))
    
    logging.info("Auto reframing clip")
    # Auto reframe clip
    try:
        clip = auto_reframe(clip, 1)  # For 1:1 aspect ratio
    except Exception as e:
        logging.error(f"Error during auto reframe: {str(e)}")
        raise
    
    logging.info("Adding fade in and fade out")
    # Add fade in and fade out
    clip = clip.fadein(0.5).fadeout(0.5)
    
    # Normalize the audio
    if clip.audio is not None:
        logging.info("Normalizing audio")
        try:
            clip.audio = clip.audio.fx(audio_normalize)
        except Exception as e:
            logging.error(f"Error during audio normalization: {str(e)}")
            logging.warning("Continuing without audio normalization")
    else:
        logging.warning("Clip has no audio track")

    logging.info(f"Writing video file to {output_path}")
    # Write the final clip
    clip.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        ffmpeg_params=["-pix_fmt", "yuv420p"]
    )
    
    logging.info(f"Clip extracted and enhanced successfully: {output_path}")