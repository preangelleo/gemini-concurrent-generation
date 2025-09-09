import os
import asyncio
from flask import Flask, request, jsonify
from main_functions import (
    gemini_chat_simple,
    gemini_structured_output_with_schema,
    gemini_cinematic_story_design,
    GEMINI_FLASH_MODEL,
    GEMINI_LATEST_MODEL
)

# --- App Initialization ---
app = Flask(__name__)

# --- Service Configuration ---
# The Admin API Key for trusted, internal requests.
# This key grants permission to use the server's own Gemini API key.
ADMIN_API_KEY = os.getenv('ADMIN_API_KEY')

# The server's own Gemini API key (optional).
# Can be used by requests authenticated with the Admin API Key.
SERVER_GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Global concurrency limit for all Gemini API calls made by this service.
GEMINI_CONCURRENCY_LIMIT = int(os.getenv('GEMINI_CONCURRENCY_LIMIT', 15))

# Create an event loop for handling semaphore if one doesn't exist
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

semaphore = asyncio.Semaphore(GEMINI_CONCURRENCY_LIMIT)

print("✅ Gemini Concurrent Service started.")
print(f"🚦 Global concurrency limit set to: {GEMINI_CONCURRENCY_LIMIT}")
if ADMIN_API_KEY:
    print("🔑 Admin API Key is configured.")
if SERVER_GEMINI_API_KEY:
    print("🔑 Server's own Gemini API Key is configured.")

# --- Authentication Helper ---

def get_api_key_from_request(req):
    """
    Determines the appropriate Gemini API key based on a 3-tier authentication logic.

    Tier 1: Admin Key in Header -> Uses Server's Key
    Tier 2: API Key in Payload -> Uses User's Key
    Tier 3: Failure

    Returns:
        A tuple of (api_key, error_message, status_code).
        On success, api_key is a string and the other two are None.
        On failure, api_key is None and the other two have values.
    """
    # Tier 1: Check for Admin API Key in headers
    admin_key_from_header = req.headers.get('Admin-API-Key')
    if ADMIN_API_KEY and admin_key_from_header == ADMIN_API_KEY:
        if SERVER_GEMINI_API_KEY:
            # Admin is authenticated and server has a key
            return SERVER_GEMINI_API_KEY, None, None
        else:
            # Admin is authenticated, but server is not configured with a key
            error_msg = "Admin authenticated, but the service is not configured with a GEMINI_API_KEY."
            return None, error_msg, 500 # Internal Server Error

    # Tier 2: Check for user-provided API Key in the JSON payload
    if req.is_json:
        data = req.get_json()
        payload_api_key = data.get('credentials', {}).get('gemini_api_key')
        if payload_api_key:
            return payload_api_key, None, None

    # Tier 3: Authentication failed
    error_msg = "Authentication failed. Provide 'Admin-API-Key' in headers or 'credentials.gemini_api_key' in payload."
    return None, error_msg, 401 # Unauthorized

# --- API Endpoints ---

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint to confirm the service is running."""
    return jsonify({
        "status": "ok",
        "service": "gemini-concurrent-generation",
        "concurrency_limit": GEMINI_CONCURRENCY_LIMIT,
        "admin_key_configured": bool(ADMIN_API_KEY),
        "server_key_configured": bool(SERVER_GEMINI_API_KEY)
    }), 200

async def process_request(handler, **kwargs):
    """Async wrapper to handle semaphore and execution logic."""
    queue_size = len(semaphore._waiters) if semaphore._waiters is not None else 0
    print(f"⏳ Request received. Waiting for semaphore... (Queue: {queue_size})")
    async with semaphore:
        print(f"🟢 Acquired semaphore. Processing request...")
        try:
            result = await handler(**kwargs)
            print("✅ Request processed successfully.")
            return result
        except Exception as e:
            print(f"❌ Error during request processing: {e}")
            raise e

@app.route('/chat', methods=['POST'])
async def handle_chat():
    """Handles general-purpose chat requests with the new authentication logic."""
    api_key, error, status_code = get_api_key_from_request(request)
    if error:
        return jsonify({"error": error}), status_code

    data = request.get_json()
    prompt = data.get('prompt')
    system_prompt = data.get('system_prompt', '')
    model = data.get('model', GEMINI_FLASH_MODEL)

    if not prompt:
        return jsonify({"error": "Missing required field: prompt"}), 400

    try:
        result = await process_request(
            gemini_chat_simple,
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            api_key=api_key
        )
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/structured-output', methods=['POST'])
async def handle_structured_output():
    """Handles requests for structured JSON output with the new auth logic."""
    api_key, error, status_code = get_api_key_from_request(request)
    if error:
        return jsonify({"error": error}), status_code

    data = request.get_json()
    user_content = data.get('user_content')
    system_prompt = data.get('system_prompt', '')
    json_schema = data.get('json_schema')
    model = data.get('model', GEMINI_LATEST_MODEL)

    if not all([user_content, system_prompt, json_schema]):
        return jsonify({"error": "Missing one or more required fields: user_content, system_prompt, json_schema"}), 400

    try:
        result = await process_request(
            gemini_structured_output_with_schema,
            user_content=user_content,
            system_prompt=system_prompt,
            json_schema=json_schema,
            model=model,
            api_key=api_key
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/cinematic-story-design', methods=['POST'])
async def handle_cinematic_story_design():
    """A specialized endpoint for cinematic story design with the new auth logic."""
    api_key, error, status_code = get_api_key_from_request(request)
    if error:
        return jsonify({"error": error}), status_code

    data = request.get_json()
    user_content = data.get('user_content')
    system_prompt = data.get('system_prompt', '')
    model = data.get('model', GEMINI_LATEST_MODEL)

    if not all([user_content, system_prompt]):
        return jsonify({"error": "Missing one or more required fields: user_content, system_prompt"}), 400

    try:
        result = await process_request(
            gemini_cinematic_story_design,
            user_content=user_content,
            system_prompt=system_prompt,
            model=model,
            api_key=api_key
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# --- Main Execution ---
if __name__ == '__main__':
    # For production, use a proper WSGI server like Gunicorn.
    # Example: gunicorn --workers 4 --bind 0.0.0.0:5004 app:app
    # For local testing:
    app.run(host='0.0.0.0', port=5004, debug=True)