# Video Clip Generation Pipeline

This project is a microservices-based pipeline for automatically generating video clips from longer videos. It uses AWS ECS, SQS, and various AI services to process videos, transcribe them, select interesting segments, and create short clips.

## Overview

The pipeline consists of four microservices:

1. Downloader
2. Transcriber
3. Clip Selector
4. Clip Generator

These services communicate via SQS queues and process jobs asynchronously.

## Key Features

- AWS ECS-based microservices architecture
- SQS for job queueing
- API for job submission, status checking, and clip retrieval
- GPT-3.5 for intelligent clip selection
- Whisper (via Replicate) for accurate transcription
- Face detection and motion smoothing for improved clip quality

## Usage

The service can be accessed via an API. Here are the main endpoints:

- POST /submit-job: Submit a video URL for processing
- GET /job-status/{job_id}: Check the status of a job
- GET /download-clip/{job_id}: Download the generated clip

A Swagger UI is available for testing the API (include link).

## Technical Details

- Transcription: Uses Whisper model on Replicate, running on NVIDIA T4 GPUs
- Language Model: GPT-3.5 for clip selection
- Face Detection: Custom implementation for tracking speaker's face
- Motion Smoothing: Reduces jitter in clip output

## Performance Improvements

Recent improvements include:

- Switched to GPT-3.5 for better performance and latency
- Included timestamps in transcription data
- Added face detection and motion smoothing to clip generation