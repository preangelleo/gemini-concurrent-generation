import os
import asyncio
import threading
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from main_functions import (
    gemini_chat_simple,
    gemini_structured_output_with_schema,
    gemini_cinematic_story_design,
    GEMINI_FLASH_MODEL,
    GEMINI_LATEST_MODEL
)

# Load environment variables from .env file (if it exists)
load_dotenv()

# --- Service Configuration ---
# Admin API Key for trusted, internal requests
ADMIN_API_KEY = os.getenv('ADMIN_API_KEY')

# Server's own Gemini API key (optional)
SERVER_GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# --- Global Concurrency Control ---
# This is the KEY: ONE global semaphore shared across ALL requests
DEFAULT_GLOBAL_CONCURRENCY = int(os.getenv("GEMINI_CONCURRENCY_LIMIT", "15"))
global_semaphore = None  # Will be created in startup event

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Gemini Concurrent Generation Service v2.0",
    description="A high-performance application for concurrent Gemini API calls with External Semaphore Pattern, 3-tier authentication, and standardized input/output structure.",
    version="2.0.0-volcengine-enhanced",
)

# --- Global Semaphore Registry for External Semaphore Pattern ---
_global_semaphores: Dict[str, asyncio.Semaphore] = {}
_global_semaphores_lock = threading.Lock()

@app.on_event("startup")
async def startup_event():
    """Initialize global semaphore in the correct event loop"""
    global global_semaphore
    global_semaphore = asyncio.Semaphore(DEFAULT_GLOBAL_CONCURRENCY)
    print("✅ Gemini Concurrent Service v2.0 started.")
    print(f"🚦 Global concurrency limit set to: {DEFAULT_GLOBAL_CONCURRENCY}")
    if ADMIN_API_KEY:
        print("🔑 Admin API Key is configured.")
    if SERVER_GEMINI_API_KEY:
        print("🔑 Server's own Gemini API Key is configured.")
    print("🌐 External Semaphore Pattern enabled for cross-service concurrency control")

@app.on_event("shutdown") 
async def shutdown_event():
    """Cleanup on shutdown"""
    global global_semaphore, _global_semaphores
    global_semaphore = None
    _global_semaphores.clear()
    print("🛑 Global concurrency semaphore cleaned up")

# --- External Semaphore Management Functions ---
def register_global_semaphore(semaphore_id: str, limit: int) -> asyncio.Semaphore:
    """Register a global semaphore for cross-service concurrency control"""
    with _global_semaphores_lock:
        if semaphore_id in _global_semaphores:
            print(f"⚠️ Global semaphore '{semaphore_id}' already exists, returning existing one")
            return _global_semaphores[semaphore_id]
        
        semaphore = asyncio.Semaphore(limit)
        _global_semaphores[semaphore_id] = semaphore
        print(f"🌐 Global semaphore '{semaphore_id}' registered with limit {limit}")
        return semaphore

def get_global_semaphore(semaphore_id: str) -> Optional[asyncio.Semaphore]:
    """Get a registered global semaphore by ID"""
    with _global_semaphores_lock:
        return _global_semaphores.get(semaphore_id)

def list_global_semaphores() -> List[str]:
    """List all registered global semaphores"""
    with _global_semaphores_lock:
        return list(_global_semaphores.keys())

# --- Pydantic Models for API Data Structure ---
class GeminiCredentials(BaseModel):
    gemini_api_key: Optional[str] = Field(None, description="Google Gemini API key")

class TaskItem(BaseModel):
    task_id: str = Field(..., description="Unique identifier for the task")
    prompt: str = Field(..., description="The prompt for Gemini API")
    system_prompt: Optional[str] = Field("", description="System prompt for the AI's behavior")
    model: Optional[str] = Field(GEMINI_FLASH_MODEL, description="Gemini model to use")
    output_filename: Optional[str] = Field(None, description="Optional: Desired output filename for tracking")

class StructuredTaskItem(BaseModel):
    task_id: str = Field(..., description="Unique identifier for the task")
    user_content: str = Field(..., description="Content to process")
    system_prompt: str = Field(..., description="System prompt (required for structured output)")
    json_schema: Dict[str, Any] = Field(..., description="JSON schema for output structure")
    model: Optional[str] = Field(GEMINI_LATEST_MODEL, description="Gemini model to use")
    output_filename: Optional[str] = Field(None, description="Optional: Desired output filename for tracking")

class CinematicTaskItem(BaseModel):
    task_id: str = Field(..., description="Unique identifier for the task")
    user_content: str = Field(..., description="Story concept to develop")
    system_prompt: str = Field(..., description="System prompt for story creation")
    model: Optional[str] = Field(GEMINI_LATEST_MODEL, description="Gemini model to use")
    output_filename: Optional[str] = Field(None, description="Optional: Desired output filename for tracking")

class BatchChatRequest(BaseModel):
    tasks: List[TaskItem] = Field(..., description="List of chat tasks to process")
    external_semaphore_id: Optional[str] = Field(None, description="External semaphore ID for cross-service concurrency control")
    credentials: Optional[GeminiCredentials] = Field(None, description="Optional Gemini credentials")

class BatchStructuredRequest(BaseModel):
    tasks: List[StructuredTaskItem] = Field(..., description="List of structured output tasks")
    external_semaphore_id: Optional[str] = Field(None, description="External semaphore ID for cross-service concurrency control")
    credentials: Optional[GeminiCredentials] = Field(None, description="Optional Gemini credentials")

class BatchCinematicRequest(BaseModel):
    tasks: List[CinematicTaskItem] = Field(..., description="List of cinematic story tasks")
    external_semaphore_id: Optional[str] = Field(None, description="External semaphore ID for cross-service concurrency control")
    credentials: Optional[GeminiCredentials] = Field(None, description="Optional Gemini credentials")

class TaskResult(BaseModel):
    task_id: str = Field(..., description="Task identifier")
    success: bool = Field(..., description="Whether the task succeeded")
    data: Optional[Any] = Field(None, description="Generated content")
    output_filename: Optional[str] = Field(None, description="Output filename if provided")
    error: Optional[str] = Field(None, description="Error message if failed")
    response_time: Optional[float] = Field(None, description="Response time in seconds")

class BatchResponse(BaseModel):
    total_tasks: int = Field(..., description="Total number of tasks processed")
    successful_count: int = Field(..., description="Number of successful tasks")
    failed_count: int = Field(..., description="Number of failed tasks")
    successful_results: List[TaskResult] = Field(..., description="Results for successful tasks")
    failed_results: List[TaskResult] = Field(..., description="Results for failed tasks")
    external_semaphore_used: bool = Field(False, description="Whether external semaphore was used")
    semaphore_id: Optional[str] = Field(None, description="External semaphore ID if used")

class SemaphoreRequest(BaseModel):
    semaphore_id: str = Field(..., description="Unique identifier for the semaphore")
    limit: int = Field(..., description="Maximum concurrent operations allowed")

# --- Authentication Helper ---
def get_api_key_from_request(req: Request, request_credentials: Optional[GeminiCredentials]) -> tuple[Optional[str], Optional[str], Optional[int]]:
    """
    SECURE 2-Tier Authentication System (Environment fallback REMOVED for security).
    
    Tier 1: Admin Key in Header -> Uses Server's Key (for internal services)
    Tier 2: API Key in Payload -> Uses User's Key (REQUIRED for non-admin requests)
    
    Returns:
        A tuple of (api_key, error_message, status_code).
    """
    # Tier 1: Check for Admin API Key in headers
    admin_key_from_header = req.headers.get('Admin-API-Key')
    if ADMIN_API_KEY and admin_key_from_header == ADMIN_API_KEY:
        if SERVER_GEMINI_API_KEY:
            return SERVER_GEMINI_API_KEY, None, None
        else:
            error_msg = "Admin authenticated, but the service is not configured with a GEMINI_API_KEY."
            return None, error_msg, 500

    # Tier 2: Check for user-provided API Key in the request payload
    if request_credentials and request_credentials.gemini_api_key:
        return request_credentials.gemini_api_key, None, None

    # SECURITY: No environment fallback - credentials are required
    # Tier 3: Authentication failed
    error_msg = "Authentication failed. Provide 'Admin-API-Key' in headers or 'credentials.gemini_api_key' in payload."
    return None, error_msg, 401

async def process_with_semaphore(handler, semaphore, *args, **kwargs):
    """Process request with semaphore control (for both internal and external semaphores)"""
    semaphore_info = f"external semaphore" if semaphore != global_semaphore else f"internal semaphore"
    print(f"⏳ Request waiting for {semaphore_info}...")
    
    async with semaphore:
        print(f"🟢 Acquired {semaphore_info}. Processing request...")
        try:
            result = await handler(*args, **kwargs)
            print("✅ Request processed successfully.")
            return result
        except Exception as e:
            print(f"❌ Error during request processing: {e}")
            raise e

# --- API Endpoints ---

@app.get("/")
def root():
    """Root endpoint with service information"""
    available_slots = global_semaphore._value if global_semaphore else "Not initialized"
    return {
        "status": "healthy",
        "service": "gemini-concurrent-generation",
        "version": "2.0.0-external-semaphore-enhanced",
        "message": "Enhanced Gemini Concurrent Generation with External Semaphore Pattern",
        "architecture": {
            "external_semaphore_pattern": "✅ Enabled",
            "perfect_input_output_correspondence": "✅ Enabled",
            "advanced_batch_processing": "✅ Enabled",
            "cross_service_coordination": "✅ Enabled"
        },
        "concurrency_status": {
            "global_concurrency_limit": DEFAULT_GLOBAL_CONCURRENCY,
            "current_available_slots": available_slots,
            "external_semaphores_count": len(_global_semaphores)
        },
        "semaphore_status": "initialized",
        "admin_key_configured": bool(ADMIN_API_KEY),
        "server_credentials_configured": bool(SERVER_GEMINI_API_KEY),
        "authentication": {
            "admin_api_key": "✅ Admin-API-Key header authentication",
            "user_credentials": "✅ User-provided credentials in payload", 
            "environment_variables": "✅ Environment variable fallback"
        }
    }

@app.get("/health")
def health_check():
    """Health check endpoint to confirm the service is running"""
    available_slots = global_semaphore._value if global_semaphore else "Not initialized"
    return {
        "status": "healthy",
        "service": "gemini-concurrent-generation",
        "version": "2.0.1-secure (Environment fallback vulnerability FIXED)",
        "concurrency_status": {
            "global_concurrency_limit": DEFAULT_GLOBAL_CONCURRENCY,
            "current_available_slots": available_slots
        },
        "features": ["External Semaphore Pattern", "3-Tier Authentication", "Batch Processing", "Structured Output"],
        "admin_key_configured": bool(ADMIN_API_KEY),
        "server_key_configured": bool(SERVER_GEMINI_API_KEY),
        "global_semaphores_count": len(_global_semaphores)
    }

@app.get("/global-semaphores")
def list_semaphores():
    """List all registered global semaphores"""
    semaphores = list_global_semaphores()
    return {
        "count": len(semaphores),
        "global_semaphores": semaphores
    }

@app.post("/global-semaphores")
async def create_global_semaphore(request: SemaphoreRequest, http_request: Request):
    """Register a new global semaphore (Admin only)"""
    admin_key_from_header = http_request.headers.get('Admin-API-Key')
    if not (ADMIN_API_KEY and admin_key_from_header == ADMIN_API_KEY):
        raise HTTPException(status_code=403, detail="Admin API Key required for semaphore management")
    
    semaphore = register_global_semaphore(request.semaphore_id, request.limit)
    return {
        "success": True,
        "semaphore_id": request.semaphore_id,
        "limit": request.limit,
        "message": f"Global semaphore '{request.semaphore_id}' registered successfully"
    }

@app.post("/chat-batch", response_model=BatchResponse)
async def chat_batch(request: BatchChatRequest, http_request: Request):
    """Process batch chat requests with external semaphore support"""
    api_key, error_msg, status_code = get_api_key_from_request(http_request, request.credentials)
    if error_msg:
        raise HTTPException(status_code=status_code, detail=error_msg)

    if not request.tasks:
        return BatchResponse(
            total_tasks=0, successful_count=0, failed_count=0,
            successful_results=[], failed_results=[],
            external_semaphore_used=False
        )

    # Determine which semaphore to use
    semaphore_to_use = global_semaphore
    external_semaphore_used = False
    semaphore_id = None
    
    if request.external_semaphore_id:
        external_semaphore = get_global_semaphore(request.external_semaphore_id)
        if external_semaphore:
            semaphore_to_use = external_semaphore
            external_semaphore_used = True
            semaphore_id = request.external_semaphore_id
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"External semaphore '{request.external_semaphore_id}' not found"
            )

    successful_results = []
    failed_results = []

    # Process tasks concurrently but with semaphore control
    async def process_task(task: TaskItem) -> TaskResult:
        try:
            result = await process_with_semaphore(
                gemini_chat_simple,
                semaphore_to_use,
                prompt=task.prompt,
                system_prompt=task.system_prompt,
                model=task.model,
                api_key=api_key
            )
            return TaskResult(
                task_id=task.task_id,
                success=True,
                data=result,
                output_filename=task.output_filename
            )
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                data=None,
                output_filename=task.output_filename,
                error=str(e)
            )

    # Execute all tasks concurrently
    task_results = await asyncio.gather(*[process_task(task) for task in request.tasks])
    
    # Separate successful and failed results
    for result in task_results:
        if result.success:
            successful_results.append(result)
        else:
            failed_results.append(result)

    return BatchResponse(
        total_tasks=len(request.tasks),
        successful_count=len(successful_results),
        failed_count=len(failed_results),
        successful_results=successful_results,
        failed_results=failed_results,
        external_semaphore_used=external_semaphore_used,
        semaphore_id=semaphore_id
    )

@app.post("/structured-output-batch", response_model=BatchResponse)
async def structured_output_batch(request: BatchStructuredRequest, http_request: Request):
    """Process batch structured output requests with external semaphore support"""
    api_key, error_msg, status_code = get_api_key_from_request(http_request, request.credentials)
    if error_msg:
        raise HTTPException(status_code=status_code, detail=error_msg)

    if not request.tasks:
        return BatchResponse(
            total_tasks=0, successful_count=0, failed_count=0,
            successful_results=[], failed_results=[],
            external_semaphore_used=False
        )

    # Determine which semaphore to use
    semaphore_to_use = global_semaphore
    external_semaphore_used = False
    semaphore_id = None
    
    if request.external_semaphore_id:
        external_semaphore = get_global_semaphore(request.external_semaphore_id)
        if external_semaphore:
            semaphore_to_use = external_semaphore
            external_semaphore_used = True
            semaphore_id = request.external_semaphore_id
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"External semaphore '{request.external_semaphore_id}' not found"
            )

    successful_results = []
    failed_results = []

    # Process tasks concurrently but with semaphore control
    async def process_task(task: StructuredTaskItem) -> TaskResult:
        try:
            result = await process_with_semaphore(
                gemini_structured_output_with_schema,
                semaphore_to_use,
                user_content=task.user_content,
                system_prompt=task.system_prompt,
                json_schema=task.json_schema,
                model=task.model,
                api_key=api_key
            )
            return TaskResult(
                task_id=task.task_id,
                success=result.get('success', False),
                data=result.get('data'),
                output_filename=task.output_filename,
                error=result.get('message') if not result.get('success') else None,
                response_time=result.get('response_time')
            )
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                data=None,
                output_filename=task.output_filename,
                error=str(e)
            )

    # Execute all tasks concurrently
    task_results = await asyncio.gather(*[process_task(task) for task in request.tasks])
    
    # Separate successful and failed results
    for result in task_results:
        if result.success:
            successful_results.append(result)
        else:
            failed_results.append(result)

    return BatchResponse(
        total_tasks=len(request.tasks),
        successful_count=len(successful_results),
        failed_count=len(failed_results),
        successful_results=successful_results,
        failed_results=failed_results,
        external_semaphore_used=external_semaphore_used,
        semaphore_id=semaphore_id
    )

@app.post("/cinematic-story-batch", response_model=BatchResponse)
async def cinematic_story_batch(request: BatchCinematicRequest, http_request: Request):
    """Process batch cinematic story requests with external semaphore support"""
    api_key, error_msg, status_code = get_api_key_from_request(http_request, request.credentials)
    if error_msg:
        raise HTTPException(status_code=status_code, detail=error_msg)

    if not request.tasks:
        return BatchResponse(
            total_tasks=0, successful_count=0, failed_count=0,
            successful_results=[], failed_results=[],
            external_semaphore_used=False
        )

    # Determine which semaphore to use
    semaphore_to_use = global_semaphore
    external_semaphore_used = False
    semaphore_id = None
    
    if request.external_semaphore_id:
        external_semaphore = get_global_semaphore(request.external_semaphore_id)
        if external_semaphore:
            semaphore_to_use = external_semaphore
            external_semaphore_used = True
            semaphore_id = request.external_semaphore_id
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"External semaphore '{request.external_semaphore_id}' not found"
            )

    successful_results = []
    failed_results = []

    # Process tasks concurrently but with semaphore control
    async def process_task(task: CinematicTaskItem) -> TaskResult:
        try:
            result = await process_with_semaphore(
                gemini_cinematic_story_design,
                semaphore_to_use,
                user_content=task.user_content,
                system_prompt=task.system_prompt,
                model=task.model,
                api_key=api_key
            )
            return TaskResult(
                task_id=task.task_id,
                success=result.get('success', False),
                data=result.get('data'),
                output_filename=task.output_filename,
                error=result.get('message') if not result.get('success') else None,
                response_time=result.get('response_time')
            )
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                data=None,
                output_filename=task.output_filename,
                error=str(e)
            )

    # Execute all tasks concurrently
    task_results = await asyncio.gather(*[process_task(task) for task in request.tasks])
    
    # Separate successful and failed results
    for result in task_results:
        if result.success:
            successful_results.append(result)
        else:
            failed_results.append(result)

    return BatchResponse(
        total_tasks=len(request.tasks),
        successful_count=len(successful_results),
        failed_count=len(failed_results),
        successful_results=successful_results,
        failed_results=failed_results,
        external_semaphore_used=external_semaphore_used,
        semaphore_id=semaphore_id
    )

# --- Legacy Endpoints for Backward Compatibility ---

@app.post("/chat")
async def legacy_chat(http_request: Request):
    """Legacy single chat endpoint for backward compatibility"""
    data = await http_request.json()
    
    # Convert legacy format to new format
    task = TaskItem(
        task_id="legacy_single_chat",
        prompt=data.get('prompt', ''),
        system_prompt=data.get('system_prompt', ''),
        model=data.get('model', GEMINI_FLASH_MODEL)
    )
    
    credentials = None
    if 'credentials' in data:
        credentials = GeminiCredentials(**data['credentials'])
    
    batch_request = BatchChatRequest(tasks=[task], credentials=credentials)
    
    # Process as batch
    result = await chat_batch(batch_request, http_request)
    
    # Return in legacy format
    if result.successful_count > 0:
        return {"success": True, "data": result.successful_results[0].data}
    else:
        return {"success": False, "error": result.failed_results[0].error if result.failed_results else "Unknown error"}

@app.post("/structured-output")
async def legacy_structured_output(http_request: Request):
    """Legacy single structured output endpoint for backward compatibility"""
    data = await http_request.json()
    
    # Convert legacy format to new format
    task = StructuredTaskItem(
        task_id="legacy_single_structured",
        user_content=data.get('user_content', ''),
        system_prompt=data.get('system_prompt', ''),
        json_schema=data.get('json_schema', {}),
        model=data.get('model', GEMINI_LATEST_MODEL)
    )
    
    credentials = None
    if 'credentials' in data:
        credentials = GeminiCredentials(**data['credentials'])
    
    batch_request = BatchStructuredRequest(tasks=[task], credentials=credentials)
    
    # Process as batch
    result = await structured_output_batch(batch_request, http_request)
    
    # Return in legacy format
    if result.successful_count > 0:
        return result.successful_results[0].data
    else:
        return {"success": False, "error": result.failed_results[0].error if result.failed_results else "Unknown error"}

@app.post("/cinematic-story-design")
async def legacy_cinematic_story(http_request: Request):
    """Legacy single cinematic story endpoint for backward compatibility"""
    data = await http_request.json()
    
    # Convert legacy format to new format
    task = CinematicTaskItem(
        task_id="legacy_single_cinematic",
        user_content=data.get('user_content', ''),
        system_prompt=data.get('system_prompt', ''),
        model=data.get('model', GEMINI_LATEST_MODEL)
    )
    
    credentials = None
    if 'credentials' in data:
        credentials = GeminiCredentials(**data['credentials'])
    
    batch_request = BatchCinematicRequest(tasks=[task], credentials=credentials)
    
    # Process as batch
    result = await cinematic_story_batch(batch_request, http_request)
    
    # Return in legacy format
    if result.successful_count > 0:
        return result.successful_results[0].data
    else:
        return {"success": False, "error": result.failed_results[0].error if result.failed_results else "Unknown error"}

# --- Main Execution ---
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=5004, debug=True)