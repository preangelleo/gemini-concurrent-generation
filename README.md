# Gemini Concurrent Generation Service

A high-performance, self-hosted FastAPI application for concurrent Google Gemini API operations, featuring intelligent batch processing, global concurrency management, and External Semaphore Pattern support.

## Purpose & Overview

This service maximizes Google Gemini API's concurrency capabilities, enabling individual API accounts to achieve optimal parallel processing while maintaining strict rate limit compliance and preventing API throttling.

### Key Features

1. **🔄 External Semaphore Pattern**: Enables cross-service concurrency control for multi-service deployments
2. **🚦 Global Concurrency Management**: All requests share a single semaphore pool to respect API limits
3. **📊 Batch Processing**: List of Dict structure for optimal throughput and perfect input/output correspondence
4. **🛡️ Account Protection**: Never exceeds Google Gemini API limits regardless of concurrent client load
5. **⚡ FastAPI Performance**: Pure async architecture for maximum efficiency

### Google Gemini API Rate Limits

| Tier | RPM (Requests/Min) | TPM (Tokens/Min) | RPD (Requests/Day) | **Recommended Concurrency** |
|------|-------------------|------------------|-------------------|----------------------------|
| **Free Tier** | 5 | 25K | 25 | **2-3** |
| **Tier 1 (Paid)** | 300 | 1M | 1,000 | **15-20** |
| **Tier 2** | 1,000 | 2M | 10,000 | **50-60** |
| **Tier 3 (Enterprise)** | Custom | Custom | Custom | **Custom** |

This service automatically manages concurrency to maximize throughput while staying within your tier's limits.

## Core Features

### 🚦 Global Concurrency Control
- **Single Shared Semaphore**: All requests across ALL clients share one global semaphore pool
- **API Protection**: Never exceeds your Gemini API account limits regardless of concurrent client load
- **Rate Limit Compliance**: Automatic queue management prevents API throttling and 429 errors

### 🌐 External Semaphore Pattern Support
- **Cross-Service Coordination**: Supports external semaphore registry for multi-service concurrency control
- **Global Semaphore Registry**: `/_admin/semaphores` endpoint for cross-service coordination
- **Template Architecture**: Follows proven concurrency management patterns

### 📋 Batch Processing Architecture
- **List of Dict Structure**: Standardized input/output format for optimal throughput
- **Perfect Correspondence**: Each input request maps exactly to one output result
- **Backward Compatibility**: Legacy single-request endpoints still supported

### 🔐 3-Tier Authentication System
1. **Admin API Key** (Highest Priority) → Uses server's configured credentials
2. **User Credentials** (Medium Priority) → Uses credentials from request payload  
3. **Environment Variables** (Lowest Priority) → Fallback to .env configuration

### 🎭 Dual-Mode Operation
- **Individual Endpoints**: Traditional single-request processing (`/chat`, `/structured-output`, etc.)
- **Batch Endpoints**: High-throughput batch processing (`/batch/chat`, `/batch/structured-output`, etc.)
- **Flexible Input**: Both modes support the same authentication and parameter structure

## Authentication System

The service implements a **3-tier authentication priority system** that provides flexibility for different deployment scenarios while maintaining security.

### Tier 1: Admin API Key (Highest Priority)

**For trusted internal services and production deployments**

- **Setup**: Configure `ADMIN_API_KEY` environment variable on server startup
- **Usage**: Include `Admin-API-Key: your_admin_key` in request headers
- **Credentials**: Server uses its own pre-configured `GEMINI_API_KEY` from environment
- **Security**: No API keys exposed in request payloads
- **Use Cases**: 
  - Internal microservices communication
  - Production backend-to-backend calls
  - Centralized API key management

```bash
# Example request with Admin authentication
curl -X POST http://localhost:5004/chat \
  -H "Content-Type: application/json" \
  -H "Admin-API-Key: your_secret_admin_key" \
  -d '{"prompt": "Hello world"}'
```

### Tier 2: User-Provided Credentials (Medium Priority)

**For external clients and user-specific API usage**

- **Setup**: No server configuration required
- **Usage**: Include credentials in request payload under `credentials` object
- **Credentials**: User provides their own `gemini_api_key` in request
- **Security**: API keys visible in request payload (use HTTPS)
- **Use Cases**:
  - Public-facing applications
  - User-specific API key billing
  - Development and testing

```bash
# Example request with user credentials
curl -X POST http://localhost:5004/chat \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {"gemini_api_key": "user_api_key"},
    "prompt": "Hello world"
  }'
```

### Tier 3: Environment Variables (Lowest Priority)

**For simple deployments and backward compatibility**

- **Setup**: Configure `GEMINI_API_KEY` environment variable
- **Usage**: No headers or credentials required in requests
- **Credentials**: Server uses environment variable automatically
- **Security**: Server-side API key management
- **Use Cases**:
  - Simple single-user deployments
  - Development environments
  - Backward compatibility

```bash
# Example request with environment fallback
curl -X POST http://localhost:5004/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello world"}'
```

### Authentication Failure

If none of the three tiers provide valid credentials, the service returns:
- **Status Code**: `401 Unauthorized`
- **Message**: `"Authentication failed. Provide 'Admin-API-Key' in headers or complete credentials in payload."`

## Deployment & Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ADMIN_API_KEY` | ❌ Optional | - | Secret key for admin authentication (Tier 1) |
| `GEMINI_API_KEY` | ❌ Optional | - | Server's Gemini API key (for admin auth and env fallback) |
| `GEMINI_CONCURRENCY_LIMIT` | ❌ Optional | `15` | Maximum concurrent requests (adjust per your Gemini tier) |
| `PORT` | ❌ Optional | `5004` | Port number for the FastAPI server |

### Docker Deployment

**Build the Docker Image:**
```bash
cd gemini-concurrent-generation
docker build -t gemini-concurrent-generation:latest .
```

**Production Deployment (Admin + Server Keys):**
```bash
docker run -d \
  --name gemini-concurrent-generation \
  -p 5004:5004 \
  -e ADMIN_API_KEY="your_secure_admin_key_here" \
  -e GEMINI_API_KEY="your_gemini_api_key_here" \
  -e GEMINI_CONCURRENCY_LIMIT=20 \
  gemini-concurrent-generation:latest
```

**Development Deployment (Environment Fallback Only):**
```bash
docker run -d \
  --name gemini-concurrent-generation \
  -p 5004:5004 \
  -e GEMINI_API_KEY="your_gemini_api_key_here" \
  -e GEMINI_CONCURRENCY_LIMIT=5 \
  gemini-concurrent-generation:latest
```

**Public Service (User Credentials Only):**
```bash
docker run -d \
  --name gemini-concurrent-generation \
  -p 5004:5004 \
  -e GEMINI_CONCURRENCY_LIMIT=30 \
  gemini-concurrent-generation:latest
```

### Local Development

**Using conda environment:**
```bash
cd gemini-concurrent-generation
conda activate animagent
pip install -r requirements.txt

# Set environment variables (optional)
export GEMINI_API_KEY="your_gemini_api_key"
export GEMINI_CONCURRENCY_LIMIT=10

# Run the server
python app.py
```

**Access the service:**
- **Health Check**: http://localhost:5004/
- **API Documentation**: http://localhost:5004/docs
- **OpenAPI Schema**: http://localhost:5004/openapi.json

## API Endpoints Overview

The service provides **dual-mode operation** with both individual and batch processing endpoints:

### Endpoint Categories

| Category | Individual Endpoints | Batch Endpoints | Best For |
|----------|---------------------|-----------------|----------|
| **💬 Chat** | `/chat` | `/batch/chat` | General LLM conversations |
| **📋 Structured** | `/structured-output` | `/batch/structured-output` | Custom JSON extraction |
| **🎬 Cinematic** | `/cinematic-story-design` | `/batch/cinematic-story-design` | Story generation |
| **🔧 Admin** | `/_admin/*` | - | Service management |

### Performance Comparison

| Mode | Input Format | Output Format | Throughput | Best Use Case |
|------|-------------|---------------|------------|---------------|
| **Individual** | Single request object | Single response | ⭐⭐⭐ Standard | Simple integrations, single requests |
| **Batch** | `List[Dict]` | `List[Dict]` | ⭐⭐⭐⭐⭐ **Optimal** | High-throughput, bulk processing |

### Batch Processing Benefits

- **📈 Higher Throughput**: Process multiple requests concurrently within shared semaphore
- **📊 Perfect Correspondence**: Each input maps exactly to one output in the same order
- **⚡ Optimal Resource Usage**: Single API call handles multiple Gemini requests
- **🔄 Backward Compatible**: Same authentication and parameter structure as individual endpoints

## Health & Admin Endpoints

### Health Check
- **Endpoint**: `GET /`
- **Description**: Service status, configuration, and semaphore monitoring
- **Authentication**: None required

```bash
curl http://localhost:5004/
```

### Admin Semaphore Registry
- **Endpoint**: `GET /_admin/semaphores`
- **Description**: External semaphore management for cross-service coordination
- **Authentication**: Admin API Key required

```bash
curl -H "Admin-API-Key: your_admin_key" http://localhost:5004/_admin/semaphores
```

## Chat Endpoints

### Individual Chat: `POST /chat`

**Purpose**: Single LLM conversation request
**Best For**: Simple integrations, single questions, chatbot interactions

#### Request Parameters:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | ✅ **Yes** | - | The user's message/question |
| `system_prompt` | string | ❌ Optional | `""` | Instructions for the AI's behavior |
| `model` | string | ❌ Optional | `gemini-2.5-flash` | Gemini model to use |
| `credentials` | object | ❌ Optional* | - | Authentication credentials |

*Required unless using Admin-API-Key header or environment variables*

#### Examples:

**Tier 1 (Admin Key):**
```bash
curl -X POST http://localhost:5004/chat \
  -H "Content-Type: application/json" \
  -H "Admin-API-Key: your_admin_key" \
  -d '{
    "prompt": "What is the speed of light?",
    "system_prompt": "You are a helpful physics teacher."
  }'
```

**Tier 2 (User Credentials):**
```bash
curl -X POST http://localhost:5004/chat \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {"gemini_api_key": "your_gemini_key"},
    "prompt": "What is the speed of light?",
    "system_prompt": "You are a helpful physics teacher."
  }'
```

**Tier 3 (Environment Variables):**
```bash
curl -X POST http://localhost:5004/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is the speed of light?",
    "system_prompt": "You are a helpful physics teacher."
  }'
```

### Batch Chat: `POST /batch/chat`

**Purpose**: Multiple LLM conversation requests in a single API call
**Best For**: High-throughput applications, bulk processing, optimal concurrency usage

#### Request Structure:

```json
{
  "requests": [
    {
      "prompt": "What is the speed of light?",
      "system_prompt": "You are a helpful physics teacher.",
      "model": "gemini-2.5-flash"
    },
    {
      "prompt": "Explain quantum mechanics",
      "system_prompt": "You are a quantum physics expert.",
      "model": "gemini-2.5-pro"
    }
  ],
  "credentials": {"gemini_api_key": "your_key"},
  "external_semaphore_id": "optional_cross_service_id"
}
```

#### Response Structure:

```json
{
  "results": [
    {
      "success": true,
      "response": "The speed of light is approximately 299,792,458 meters per second...",
      "model": "gemini-2.5-flash",
      "index": 0
    },
    {
      "success": true, 
      "response": "Quantum mechanics is the fundamental theory in physics...",
      "model": "gemini-2.5-pro",
      "index": 1
    }
  ],
  "total_requests": 2,
  "successful_requests": 2,
  "failed_requests": 0
}
```

## Structured Output Endpoints

### Individual Structured Output: `POST /structured-output`

**Purpose**: Custom JSON structure generation with user-defined schema
**Best For**: Single data extraction tasks, custom schemas, specific structured outputs

#### Request Parameters:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `user_content` | string | ✅ **Yes** | - | Content to process/extract from |
| `system_prompt` | string | ✅ **Yes** | - | **Critical**: Schema-specific instructions |
| `json_schema` | object | ✅ **Yes** | - | JSON Schema definition for output structure |
| `model` | string | ❌ Optional | `gemini-2.5-pro` | Gemini model to use |
| `credentials` | object | ❌ Optional* | - | Authentication credentials |

*Required unless using Admin-API-Key header or environment variables*

#### Example:

```bash
curl -X POST http://localhost:5004/structured-output \
  -H "Content-Type: application/json" \
  -H "Admin-API-Key: your_admin_key" \
  -d '{
    "system_prompt": "Extract person info with high accuracy.",
    "user_content": "My name is Jane and I live in New York.",
    "json_schema": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "city": {"type": "string"}
      },
      "required": ["name", "city"]
    }
  }'
```

### Batch Structured Output: `POST /batch/structured-output`

**Purpose**: Multiple structured extractions with different schemas in one API call
**Best For**: Bulk data processing, multiple extractions, optimal concurrency usage

#### Request Structure:

```json
{
  "requests": [
    {
      "user_content": "My name is Jane and I live in New York.",
      "system_prompt": "Extract person info accurately.",
      "json_schema": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "city": {"type": "string"}
        },
        "required": ["name", "city"]
      }
    },
    {
      "user_content": "Product: iPhone 15, Price: $999, Color: Blue",
      "system_prompt": "Extract product information.",
      "json_schema": {
        "type": "object", 
        "properties": {
          "product": {"type": "string"},
          "price": {"type": "number"},
          "color": {"type": "string"}
        },
        "required": ["product", "price", "color"]
      }
    }
  ],
  "credentials": {"gemini_api_key": "your_key"}
}
```

#### Response Structure:

```json
{
  "results": [
    {
      "success": true,
      "data": {"name": "Jane", "city": "New York"},
      "message": "Successfully generated structured output",
      "index": 0
    },
    {
      "success": true,
      "data": {"product": "iPhone 15", "price": 999, "color": "Blue"},
      "message": "Successfully generated structured output", 
      "index": 1
    }
  ],
  "total_requests": 2,
  "successful_requests": 2,
  "failed_requests": 0
}
```

## Cinematic Story Design Endpoints

### Individual Cinematic Story: `POST /cinematic-story-design`

**Purpose**: Professional movie/animation story creation with comprehensive built-in schema
**Best For**: Single story generation, animation scripts, cinematic planning

#### Built-in Schema Structure:
- **📝 Story Metadata**: title, YouTube details, hashtags
- **🎨 Visual Elements**: illustration style, cover image descriptions  
- **🎙️ Narrator Configuration**: name, gender, voice ID
- **👥 Character Definitions**: detailed descriptions for image generation
- **📖 Chapter Structure**: organized breakdown with scene references
- **🎬 Scene Details**: descriptions, character interactions, audio scripts
- **📱 Content Optimization**: tweet summaries, repetition flags

#### Request Parameters:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `user_content` | string | ✅ **Yes** | - | Story concept, theme, or outline |
| `system_prompt` | string | ✅ **Yes** | - | **Critical**: Story-specific instructions |
| `model` | string | ❌ Optional | `gemini-2.5-pro` | Gemini model to use |
| `credentials` | object | ❌ Optional* | - | Authentication credentials |

*Required unless using Admin-API-Key header or environment variables*

#### Example:

```bash
curl -X POST http://localhost:5004/cinematic-story-design \
  -H "Content-Type: application/json" \
  -H "Admin-API-Key: your_admin_key" \
  -d '{
    "system_prompt": "Master storyteller creating complete cinematic structure with vivid characters and compelling narratives.",
    "user_content": "Historical drama about Liu Bang, founder of Han Dynasty, focusing on his rise from peasant to emperor."
  }'
```

### Batch Cinematic Stories: `POST /batch/cinematic-story-design`

**Purpose**: Multiple story generation with the same comprehensive schema
**Best For**: Bulk story creation, series planning, content production pipelines

#### Request Structure:

```json
{
  "requests": [
    {
      "user_content": "Historical drama about Liu Bang's rise to power",
      "system_prompt": "Create epic historical narrative with strong character development.",
      "model": "gemini-2.5-pro"
    },
    {
      "user_content": "Sci-fi adventure on Mars colony in 2150",
      "system_prompt": "Develop futuristic story with technology and human themes.",
      "model": "gemini-2.5-pro" 
    }
  ],
  "credentials": {"gemini_api_key": "your_key"}
}
```

## External Semaphore Pattern

### Cross-Service Concurrency Control

The service supports **External Semaphore Pattern** for coordinating concurrency across multiple services:

#### Register Global Semaphore:
```bash
curl -X POST http://localhost:5004/_admin/semaphores \
  -H "Admin-API-Key: your_admin_key" \
  -H "Content-Type: application/json" \
  -d '{"semaphore_id": "global_ai_services", "limit": 50}'
```

#### Use in Batch Requests:
```json
{
  "requests": [...],
  "external_semaphore_id": "global_ai_services",
  "credentials": {"gemini_api_key": "your_key"}
}
```

This enables multiple AI services to share a **single global concurrency pool**, preventing total API usage from exceeding account limits.

## License

This project is licensed under the MIT License - see the LICENSE file for details.