import os
import json
import time
import asyncio
import google.generativeai as genai

# --- Constants ---
GEMINI_FLASH_MODEL = "gemini-2.5-flash"
GEMINI_LATEST_MODEL = "gemini-2.5-pro"

# --- Core Functions ---

async def gemini_chat_simple(prompt: str, system_prompt: str = '', model: str = GEMINI_FLASH_MODEL, api_key: str = None) -> str:
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
        # Use asyncio.to_thread to run the blocking API call in a thread pool
        response = await asyncio.to_thread(genai_model.generate_content, prompt)
        return response.text
    except Exception as e:
        print(f"❌ An error occurred in gemini_chat_simple: {e}")
        # In a service context, you might want to raise a specific HTTP exception
        raise

async def gemini_structured_output_with_schema(
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
            response = await asyncio.to_thread(
                genai_model.generate_content,
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
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                print(f"❌ Attempt {attempt + 1}: Empty response from Gemini API.")
                if attempt == max_retries - 1:
                    return {
                        'success': False, 'data': None,
                        'message': f'Empty response from Gemini API after {max_retries} attempts.',
                        'response_time': time.time() - start_time, 'retries_used': attempt + 1
                    }
                await asyncio.sleep(2 ** attempt)

        except Exception as e:
            print(f"❌ Attempt {attempt + 1}: Gemini API error: {e}")
            if attempt == max_retries - 1:
                return {
                    'success': False, 'data': None,
                    'message': f'Gemini API error after {max_retries} attempts: {e}',
                    'response_time': time.time() - start_time, 'retries_used': attempt + 1
                }
            await asyncio.sleep(2 ** attempt)

    return {
        'success': False, 'data': None,
        'message': f'All {max_retries} attempts failed.',
        'response_time': time.time() - start_time, 'retries_used': max_retries
    }

# --- Schema-Specific Helper Functions ---

async def gemini_cinematic_story_design(user_content: str, system_prompt: str, model: str = None, api_key: str = None, max_retries: int = 3) -> dict:
    """
    Generates a full cinematic story design using a predefined schema.
    This is a direct replacement for the previous OpenAI-based structured output function.
    """
    schema = {
        "type": "object",
        "properties": {
            "illustration_style": {
                "type": "string",
                "description": "Illustration style for the story, for example: Traditional Chinese Ink Illustration"
            },
            "story_title": {
                "type": "string",
                "description": "Title of the story, extracted from the content or created if not present, no special characters that can be used for file name or folder name."
            },
            "youtube_video_title": {
                "type": "string",
                "description": "Title of the YouTube video with eye-catching keywords, add author's name if known. Separate different keywords by | and keep total length under 100 characters"
            },
            "youtube_video_description": {
                "type": "string",
                "description": "Description of the YouTube video. Begin with keywords to help viewers find your video easily. Less than 4000 characters."
            },
            "youtube_video_hashtags": {
                "type": "string",
                "description": "Relevant hashtags for YouTube, TikTok, and Twitter. Max 10 hashtags under 100 characters, separated by space and all lowercase."
            },
            "cover_image_description": {
                "type": "string",
                "description": "Detailed visual description of the cover image prompt for AI generation, must include the main character and story title, styled for adult historical storytelling"
            },
            "narrator_name": {
                "type": "string",
                "description": "Name of the narrator, must be a character from the story"
            },
            "narrator_gender": {
                "type": "string",
                "enum": [
                    "male",
                    "female",
                    "neutral"
                ],
                "description": "Gender of the narrator, must be a character from the story"
            },
            "narrator_voice_id": {
                "type": "string",
                "description": "Voice ID that matches the narrator the best, especially the gender must match. Must choose from the given voice_id_list."
            },
            "cover_image_characters": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "List of characters to appear in the cover image, must exist in character_list. All lowercase."
            },
            "character_list": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "character_number": {
                            "type": "integer",
                            "description": "Unique identifier number for the character"
                        },
                        "character_name": {
                            "type": "string",
                            "description": "Name of the character in lowercase, the first character must be the major charactor (not the narrator) of the whole story."
                        },
                        "character_image_description": {
                            "type": "string",
                            "description": "Detailed visual description of the character (only one) that will be used as a prompt for image generation, focusing on appearance and personality traits that can be illustrated clearly."
                        }
                    },
                    "required": [
                        "character_number",
                        "character_name",
                        "character_image_description"
                    ]
                },
                "description": "List of essential characters who are major characters in at least 2 scenes, max 20 characters"
            },
            "chapter_list": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "chapter_number": {
                            "type": "integer",
                            "description": "Sequential number identifying the chapters"
                        },
                        "chapter_name": {
                            "type": "string",
                            "description": "Descriptive name for the chapter"
                        },
                        "chapter_scene_list": {
                            "type": "array",
                            "items": {
                                "type": "integer"
                            },
                            "description": "List of scenes that belong to this chapter"
                        }
                    },
                    "required": [
                        "chapter_number",
                        "chapter_name",
                        "chapter_scene_list"
                    ]
                },
                "description": "List of chapters index and chapter name and scenes that belong to this chapter"
            },
            "scene_list": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "scene_number": {
                            "type": "integer",
                            "description": "Sequential number identifying the scenes"
                        },
                        "scene_name": {
                            "type": "string",
                            "description": "Descriptive name for the scene"
                        },
                        "scene_image_description": {
                            "type": "string",
                            "description": "Detailed visual description of the scene that will be used as a prompt for image generation, designed to be visually engaging for storytelling."
                        },
                        "scene_major_character": {
                            "type": "string",
                            "description": "The ONE major character that is the visual focus of this scene, in lowercase, could not be NULL. Never put narrator name here."
                        },
                        "scene_other_characters": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "List of other characters that will be included in the scene, could be null if there's no need to highlight any other character in this scene."
                        },
                        "scene_audio_script": {
                            "type": "string",
                            "description": "Script text for this scene, designed for around 60 seconds of spoken narration, try not repeat what you've said in the previous scenes."
                        },
                        "is_intentional_repetition": {
                            "type": "string",
                            "enum": [
                                "yes",
                                "no"
                            ],
                            "description": "Set to 'yes' ONLY if the `scene_audio_script` is or has an intentional, artistic repetition of the previous scene's sentences for dramatic effect. In all other cases, it should be 'no'. Always use lowercase yes or no."
                        }
                    },
                    "required": [
                        "scene_number",
                        "scene_name",
                        "scene_image_description",
                        "scene_major_character",
                        "scene_other_characters",
                        "scene_audio_script",
                        "is_intentional_repetition"
                    ]
                },
                "description": "List of scenes with visually rich prompts and narration script."
            },
            "scene_audio_language": {
                "type": "string",
                "description": "In which language the `scene_audio_script` is written. Always use lowercase."
            },
            "tweet": {
                "type": "string",
                "description": "A concise, engaging tweet text for Twitter promotion. Must be under 240 characters to leave room for YouTube URL. Should capture the essence of the story and encourage viewers to watch the video. Include relevant hashtags from youtube_video_hashtags if space allows."
            }
        },
        "required": [
            "illustration_style",
            "story_title",
            "youtube_video_title",
            "youtube_video_description",
            "youtube_video_hashtags",
            "cover_image_description",
            "narrator_name",
            "narrator_gender",
            "narrator_voice_id",
            "cover_image_characters",
            "character_list",
            "chapter_list",
            "scene_list",
            "scene_audio_language",
            "tweet"
        ]
    }
    return await gemini_structured_output_with_schema(
        user_content=user_content,
        system_prompt=system_prompt,
        json_schema=schema,
        model=model,
        api_key=api_key,
        max_retries=max_retries
    )