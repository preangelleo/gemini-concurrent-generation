import os
import json
import time
import google.generativeai as genai

# --- Constants ---
GEMINI_FLASH_MODEL = "gemini-2.5-flash"
GEMINI_LATEST_MODEL = "gemini-2.5-pro"

# --- Core Functions ---

def gemini_chat_simple(prompt: str, system_prompt: str = '', model: str = GEMINI_FLASH_MODEL, api_key: str = None) -> str:
    """
    A simple, direct chat with the Gemini API.

    Args:
        prompt: The user's prompt.
        system_prompt: The system instruction for the model.
        model: The model name to use.
        api_key: The Google Gemini API key.

    Returns:
        The text response from the model.
    """
    if not api_key:
        raise ValueError("API key is required for Gemini API calls.")

    genai.configure(api_key=api_key)

    try:
        genai_model = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_prompt if system_prompt else None
        )
        response = genai_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"❌ An error occurred in gemini_chat_simple: {e}")
        # In a service context, you might want to raise a specific HTTP exception
        raise

def gemini_structured_output_with_schema(
    user_content: str, 
    system_prompt: str, 
    json_schema: dict, 
    model: str = GEMINI_LATEST_MODEL, 
    api_key: str = None, 
    max_retries: int = 3
) -> dict:
    """
    Generates structured output conforming to a specified JSON Schema using the Gemini API.

    Args:
        user_content: The user's input content.
        system_prompt: The system prompt to guide the model.
        json_schema: The JSON Schema definition.
        model: The model name to use.
        api_key: The Google Gemini API key.
        max_retries: The maximum number of retries on failure.

    Returns:
        A dictionary containing the success status, data, and other metadata.
    """
    if not api_key:
        return {
            'success': False,
            'data': None,
            'message': 'API key is required.',
            'response_time': 0,
            'retries_used': 0
        }

    genai.configure(api_key=api_key)

    # For structured output, it's best to combine the instructions and schema into the system prompt.
    full_system_prompt = f"""{system_prompt}

You must respond with a valid JSON object that strictly conforms to the following JSON Schema. Do not include any other text or markdown formatting like ```json in your response. Your response must be ONLY the JSON object itself.

JSON Schema:
{json.dumps(json_schema, indent=2)}
"""

    start_time = time.time()

    for attempt in range(max_retries):
        try:
            genai_model = genai.GenerativeModel(
                model_name=model,
                system_instruction=full_system_prompt
            )
            
            # Enable JSON mode for models that support it
            response = genai_model.generate_content(
                user_content,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.1 # Lower temperature for more predictable structured output
                )
            )

            if response and hasattr(response, 'text') and response.text:
                try:
                    # The response should already be JSON, but we'll keep the robust parsing
                    # logic just in case of model misbehavior.
                    response_text = response.text.strip()
                    if response_text.startswith('```json'):
                        response_text = response_text[7:].strip()
                        if response_text.endswith('```'):
                            response_text = response_text[:-3].strip()
                    elif response_text.startswith('```'):
                        response_text = response_text[3:].strip()
                        if response_text.endswith('```'):
                            response_text = response_text[:-3].strip()

                    result_data = json.loads(response_text)
                    response_time = time.time() - start_time
                    return {
                        'success': True,
                        'data': result_data,
                        'message': f'Successfully generated structured output using {model}.',
                        'response_time': response_time,
                        'retries_used': attempt
                    }
                except json.JSONDecodeError as e:
                    print(f"❌ Attempt {attempt + 1}: JSON parsing failed. Error: {e}")
                    print(f"📄 Raw response: {response.text}")
                    if attempt == max_retries - 1:
                        return {
                            'success': False, 'data': None,
                            'message': f'JSON parsing failed after {max_retries} attempts: {e}',
                            'response_time': time.time() - start_time, 'retries_used': attempt + 1
                        }
                    time.sleep(2 ** attempt)  # Exponential backoff
            else:
                print(f"❌ Attempt {attempt + 1}: Empty response from Gemini API.")
                if attempt == max_retries - 1:
                    return {
                        'success': False, 'data': None,
                        'message': f'Empty response from Gemini API after {max_retries} attempts.',
                        'response_time': time.time() - start_time, 'retries_used': attempt + 1
                    }
                time.sleep(2 ** attempt)

        except Exception as e:
            print(f"❌ Attempt {attempt + 1}: Gemini API error: {e}")
            if attempt == max_retries - 1:
                return {
                    'success': False, 'data': None,
                    'message': f'Gemini API error after {max_retries} attempts: {e}',
                    'response_time': time.time() - start_time, 'retries_used': attempt + 1
                }
            time.sleep(2 ** attempt)

    return {
        'success': False, 'data': None,
        'message': f'All {max_retries} attempts failed.',
        'response_time': time.time() - start_time, 'retries_used': max_retries
    }

# --- Schema-Specific Helper Functions ---

def gemini_cinematic_story_design(user_content: str, system_prompt: str, model: str = None, api_key: str = None, max_retries: int = 3) -> dict:
    """
    Generates a full cinematic story design using a predefined schema.
    This is a direct replacement for the previous OpenAI-based structured output function.
    """
    schema = {
        "type": "object",
        "properties": {
            "illustration_style": {"type": "string"},
            "story_title": {"type": "string"},
            "youtube_video_title": {"type": "string"},
            "youtube_video_description": {"type": "string"},
            "youtube_video_hashtags": {"type": "string"},
            "cover_image_description": {"type": "string"},
            "narrator_name": {"type": "string"},
            "narrator_gender": {"type": "string", "enum": ["male", "female", "neutral"]},
            "narrator_voice_id": {"type": "string"},
            "cover_image_characters": {"type": "array", "items": {"type": "string"}},
            "character_list": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "character_number": {"type": "integer"},
                        "character_name": {"type": "string"},
                        "character_image_description": {"type": "string"}
                    },
                    "required": ["character_number", "character_name", "character_image_description"]
                }
            },
            "chapter_list": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "chapter_number": {"type": "integer"},
                        "chapter_name": {"type": "string"},
                        "chapter_scene_list": {"type": "array", "items": {"type": "integer"}}
                    },
                    "required": ["chapter_number", "chapter_name", "chapter_scene_list"]
                }
            },
            "scene_list": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "scene_number": {"type": "integer"},
                        "scene_name": {"type": "string"},
                        "scene_image_description": {"type": "string"},
                        "scene_major_character": {"type": "string"},
                        "scene_other_characters": {"type": "array", "items": {"type": "string"}},
                        "scene_audio_script": {"type": "string"},
                        "is_intentional_repetition": {"type": "string", "enum": ["yes", "no"]}
                    },
                    "required": ["scene_number", "scene_name", "scene_image_description", "scene_major_character", "scene_other_characters", "scene_audio_script", "is_intentional_repetition"]
                }
            },
            "scene_audio_language": {"type": "string"},
            "tweet": {"type": "string"}
        },
        "required": [
            "illustration_style", "story_title", "youtube_video_title", "youtube_video_description",
            "youtube_video_hashtags", "cover_image_description", "narrator_name", "narrator_gender",
            "narrator_voice_id", "cover_image_characters", "character_list", "chapter_list", 
            "scene_list", "scene_audio_language", "tweet"
        ]
    }
    return gemini_structured_output_with_schema(
        user_content=user_content,
        system_prompt=system_prompt,
        json_schema=schema,
        model=model,
        api_key=api_key,
        max_retries=max_retries
    )