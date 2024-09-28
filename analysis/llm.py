import anthropic
from parser import parse_json
from dotenv import load_dotenv
import os

load_dotenv("../.env")

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

VIDEO_ANALYSIS_TEMPLATE = """
**Objective**: Analyze the provided news transcript and identify at least {num_clips} most valuable or interesting sections that could potentially engage viewers. This task aims to extract standalone clips suitable for social media or promotional use.

**Selection Process**:
1. Identify all sections meeting the criteria below.
2. Prioritize based on relevance score and content diversity.

**Clip Selection Criteria**:
1. **Natural Start and End**:
    - Begin at the start of a new thought or topic.
    - Conclude with a statement or natural pause.
2. **Standalone Content**:
    - Choose sections that are engaging and comprehensible without additional context.
3. **Content Value**:
    - Prioritize sections containing:
        {criteria_formatted}
4. **Clip Duration**:
    - Each clip should be between **{clip_duration_range_min}** and **{clip_duration_range_max}** seconds.
    - Vary lengths within this range for diversity.

**Relevance Score Calculation**:
- Assign a score from 0 to 100 based on:
    - Alignment with selection criteria (40%)
    - Potential viewer engagement (30%)
    - Clarity and conciseness (20%)
    - Uniqueness of information (10%)

**Output Format**:
Return a JSON array of clip objects, each containing:
[
 {{
    - `"start"`: Start time in seconds
    - `"end"`: End time in seconds
    - `"summary"`: Concise summary of the clip's content (max 50 words)
    - `"relevance_score"`: Calculated score (0-100)
    - `"justification"`: Brief explanation for selecting this clip (max 30 words)
 }}
]

Remember, select at least {num_clips} clips that meet the criteria and provide a diverse range of content.

Transcript:
<transcript>
{transcript}
</transcript>

Based on the above instructions, generate the JSON array of clip objects. Ensure that the output is valid JSON.
"""

def analyze_video(transcript: str, selection_criteria: list[str], num_clips: int, clip_duration_range: tuple):

    clip_duration_range_min, clip_duration_range_max = clip_duration_range
    criteria_formatted = '\n'.join([f"- **{criterion}**" for criterion in selection_criteria])

    prompt = VIDEO_ANALYSIS_TEMPLATE.format(
        transcript=transcript,
        criteria_formatted=criteria_formatted,
        num_clips=num_clips,
        clip_duration_range_min=clip_duration_range_min,
        clip_duration_range_max=clip_duration_range_max
    ).strip()

    print("Prompting Claude with:", prompt)

    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=8192,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    print("Response from Claude:", response.content[0].text)

    clips_data = parse_json(response.content[0].text)
    
    sorted_clips = sorted(clips_data, key=lambda x: x['relevance_score'], reverse=True)

    non_overlapping_clips = []
    for clip in sorted_clips:
        # Check for overlap with existing non-overlapping clips
        overlaps = False
        for existing_clip in non_overlapping_clips:
            if (clip['start'] < existing_clip['end'] and clip['end'] > existing_clip['start']):
                overlaps = True
                break
        
        # If no overlap, add to non_overlapping_clips
        if not overlaps:
            non_overlapping_clips.append(clip)
    
    # Sort final clips by start time
    non_overlapping_clips.sort(key=lambda x: -x['relevance_score'])
    
    return non_overlapping_clips