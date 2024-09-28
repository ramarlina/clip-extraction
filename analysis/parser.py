import json
import re
from typing import Union, Dict, List

def clean_json_string(json_string: str) -> str:
    """
    Clean and normalize a JSON string.
    
    Args:
        json_string (str): The input JSON string.
    
    Returns:
        str: The cleaned JSON string.
    """
    # Remove newlines and extra spaces
    json_string = re.sub(r'\s+', ' ', json_string.strip())
    # Normalize commas in key-value pairs
    json_string = re.sub(r'"\s*,\s*"', '","', json_string)
    return json_string

def parse_json(json_input: Union[str, Dict, List]) -> Union[Dict, List]:
    """
    Parse a JSON input, handling various formats and potential errors.
    
    Args:
        json_input (Union[str, Dict, List]): The input to parse, which can be a JSON string, dictionary, or list.
    
    Returns:
        Union[Dict, List]: The parsed JSON data.
    
    Raises:
        ValueError: If the input cannot be parsed as valid JSON.
    """
    if isinstance(json_input, (dict, list)):
        return json_input
    
    if not json_input or not isinstance(json_input, str):
        return {}

    try:
        return json.loads(json_input)
    except json.JSONDecodeError:
        # Try to extract JSON content from a larger string
        json_content = extract_json_content(json_input)
        
        try:
            return json.loads(json_content)
        except json.JSONDecodeError:
            # If still invalid, try cleaning the JSON string
            cleaned_json = clean_json_string(json_content)
            try:
                return json.loads(cleaned_json)
            except json.JSONDecodeError as e:
                raise ValueError(f"Unable to parse JSON: {e}")

def extract_json_content(text: str) -> str:
    """
    Extract JSON content from a larger string.
    
    Args:
        text (str): The input text containing JSON.
    
    Returns:
        str: The extracted JSON content.
    """
    # Find the outermost brackets or braces
    start_index = min(text.find('{'), text.find('['))
    if start_index == -1:
        return text  # No JSON-like structure found
    
    end_index = max(text.rfind('}'), text.rfind(']'))
    if end_index == -1:
        return text  # No closing bracket/brace found
    
    return text[start_index:end_index + 1]