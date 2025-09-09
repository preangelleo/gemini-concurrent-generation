# Gemini Concurrent Generation Service

## 1. Project Purpose & Overview

**核心目标 (Core Objective):** 最大限度地利用Google Gemini API的高并发处理能力，让个人的Gemini API账号支持尽可能大的并行处理，最大努力提高Large Language Model交互效率。

**English:** This service is designed to maximize Google Gemini API's high concurrency processing capabilities, enabling individual Gemini API accounts to support the highest possible parallel processing while maximizing efficiency in Large Language Model interactions.

### Key Design Principles:

1. **Maximum Async Parallelism**: Utilizes extensive async/await parallel processing to handle multiple requests simultaneously
2. **Rate Limit Compliance**: Never exceeds Google Gemini's maximum concurrency settings to avoid API throttling
3. **Intelligent Queue Management**: Implements a global semaphore system that respects API tier limits
4. **Efficiency Optimization**: Balances high throughput with API quota preservation

### Google Gemini API Rate Limits (2024-2025):

| Tier | RPM (Requests/Min) | TPM (Tokens/Min) | RPD (Requests/Day) |
|------|-------------------|------------------|-------------------|
| **Free Tier** | 5 | 25K | 25 |
| **Tier 1 (Paid)** | 300 | 1M | 1,000 |
| **Tier 2** | 1,000 | 2M | 10,000 |
| **Tier 3 (Enterprise)** | Custom | Custom | Custom |

This service automatically manages concurrency to maximize throughput while staying within your tier's limits.

## 2. Key Features

- **🚦 Global Concurrency Control**: All incoming requests share a single queue, protecting your Gemini API key from being rate-limited, regardless of how many clients are calling the service.
- **🔐 Flexible Authentication**: A robust, three-tiered authentication system to support both internal (trusted) and external (untrusted) requests.
- **🎭 Dual-Mode Operation**:
    - **Passthrough Chat**: A flexible endpoint that accepts standard Gemini chat inputs for general-purpose tasks.
    - **Structured Output**: A powerful endpoint that forces the Gemini API to return a JSON object conforming to a user-provided JSON Schema.
- **🐳 Dockerized for Portability**: Fully containerized for easy deployment, scaling, and integration into any environment.

## 3. Authentication

This service uses a two-path authentication system. Access is granted if **either** of the following methods is used:

### Method 1: Admin Authentication (for Trusted Internal Services)

This method is for services that you trust. It uses a pre-shared secret key.

- **How it works**: The service is launched with an `ADMIN_API_KEY` environment variable. The calling service must include this key in the `Admin-API-Key` header of its request.
- **Gemini Key Usage**: If the admin keys match, this service will use its own `GEMINI_API_KEY` (also set as an environment variable) to process the request.
- **Use Case**: Your other backend services calling this one.

### Method 2: User-Provided Key (for External or Untrusted Clients)

This method allows any client to use the service by providing their own Gemini API key.

- **How it works**: The client includes their Gemini API key inside the JSON payload of their request.
- **Path**: `credentials.gemini_api_key`
- **Use Case**: Public-facing applications or services where end-users provide their own API keys.

If neither authentication method is successful, the service will return a `401 Unauthorized` error.

## 4. Deployment

The service is designed to be run as a Docker container.

### Build the Docker Image

Navigate to the `animagent-process/gemini-concurrent-generation` directory and run:

```bash
docker build -t gemini-concurrent-generation .
```

### Run the Docker Container

Run the container, mapping a port and setting the necessary environment variables for authentication.

```bash
# Example: Running with both an Admin Key and a Server-side Gemini Key
docker run -d \
  -p 5004:5004 \
  --name gemini-concurrent-generation \
  -e ADMIN_API_KEY="your-super-secret-admin-key" \
  -e GEMINI_API_KEY="your-server-side-gemini-key" \
  -e GEMINI_CONCURRENCY_LIMIT=20 \
  gemini-concurrent-generation
```

- `-p 5004:5004`: Map port 5004 on your host to port 5004 in the container.
- `-e ADMIN_API_KEY`: **(Required for Admin Auth)** The secret key for trusted services.
- `-e GEMINI_API_KEY`: **(Optional)** The server's own Gemini key. Only needed if you plan to use Admin Authentication.
- `-e GEMINI_CONCURRENCY_LIMIT`: (Optional) Override the default concurrency limit of 15.

## 5. API Endpoints Overview

The service provides three main endpoints, each optimized for different use cases:

| Endpoint | Purpose | Schema | System Prompt | Best For |
|----------|---------|--------|---------------|-----------| 
| `/chat` | Simple LLM conversation | ❌ No | ✅ Supported | General chatbot interactions |
| `/structured-output` | Custom JSON structure | ✅ **User-defined** | ✅ **Required** | Any structured data extraction |
| `/cinematic-story-design` | Movie/animation stories | ✅ **Built-in** | ✅ **Required** | Cinematic story creation |

### 🎯 **System Prompt Best Practices**

**为了获得最佳的Structured Output效果，强烈建议针对你的schema提供专门的system prompt！**

- **Generic prompts** ❌: "Extract information"  
- **Schema-specific prompts** ✅: "You are a story designer. Create a complete cinematic story with characters, scenes, and narrative structure following the provided schema."

---

### Health Check

- **Endpoint**: `GET /`
- **Description**: Checks if the service is running and returns its configuration.
- **cURL Example**:
  ```bash
  curl http://localhost:5004/
  ```

### 1. Chat Endpoint

- **Endpoint**: `POST /chat`
- **Purpose**: Simple LLM conversations without structured output
- **Use Case**: General chatbot interactions, Q&A, casual conversation

#### Parameters:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | ✅ **Yes** | - | The user's message/question |
| `system_prompt` | string | ❌ Optional | `""` | Instructions for the AI's behavior |
| `model` | string | ❌ Optional | `gemini-1.5-flash-latest` | Gemini model to use |
| `credentials.gemini_api_key` | string | ✅ **Required*** | - | Your Gemini API key |

*\*Required unless using Admin-API-Key header*

#### Examples:

**User-Provided Key:**
```bash
curl -X POST http://localhost:5004/chat \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {
      "gemini_api_key": "YOUR_API_KEY"
    },
    "prompt": "What is the speed of light?",
    "system_prompt": "You are a helpful physics teacher."
  }'
```

**Admin Key:**
```bash
curl -X POST http://localhost:5004/chat \
  -H "Content-Type: application/json" \
  -H "Admin-API-Key: your-admin-key" \
  -d '{
    "prompt": "What is the speed of light?",
    "system_prompt": "You are a helpful physics teacher."
  }'
```

### 2. Structured Output

- **Endpoint**: `POST /structured-output`
- **Purpose**: Custom JSON structure generation with user-defined schema
- **Use Case**: Any structured data extraction, form processing, data analysis

#### Parameters:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `user_content` | string | ✅ **Yes** | - | The content to process/extract from |
| `system_prompt` | string | ✅ **Yes** | - | **Critical**: Schema-specific instructions for best results |
| `json_schema` | object | ✅ **Yes** | - | JSON Schema definition for the expected output structure |
| `model` | string | ❌ Optional | `gemini-1.5-pro-latest` | Gemini model to use |
| `credentials.gemini_api_key` | string | ✅ **Required*** | - | Your Gemini API key |

*\*Required unless using Admin-API-Key header*

#### Examples:

**User-Provided Key:**
```bash
curl -X POST http://localhost:5004/structured-output \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {
      "gemini_api_key": "YOUR_API_KEY"
    },
    "system_prompt": "You are a data extraction expert. Extract the person'\''s name and location from the text with high accuracy.",
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

**Admin Key:**
```bash
curl -X POST http://localhost:5004/structured-output \
  -H "Content-Type: application/json" \
  -H "Admin-API-Key: your-admin-key" \
  -d '{
    "system_prompt": "You are a data extraction expert. Extract the person'\''s name and location from the text with high accuracy.",
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

### 3. Cinematic Story Design

- **Endpoint**: `POST /cinematic-story-design`
- **Purpose**: Movie/animation story creation with built-in comprehensive schema
- **Use Case**: Professional cinematic story generation, animation scripts, video content planning

#### Parameters:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `user_content` | string | ✅ **Yes** | - | Story concept, theme, or outline to develop |
| `system_prompt` | string | ✅ **Yes** | - | **Critical**: Story-specific instructions for best cinematic results |
| `model` | string | ❌ Optional | `gemini-1.5-pro-latest` | Gemini model to use |
| `credentials.gemini_api_key` | string | ✅ **Required*** | - | Your Gemini API key |

*\*Required unless using Admin-API-Key header*

#### Built-in Schema Structure:
This endpoint automatically uses a comprehensive schema including:
- **Story Metadata**: title, YouTube video details, hashtags
- **Visual Elements**: illustration style, cover image descriptions
- **Narrator Configuration**: name, gender, voice ID
- **Character Definitions**: detailed character descriptions for image generation
- **Chapter Structure**: organized chapter breakdown with scene references
- **Scene Details**: complete scene descriptions, character interactions, audio scripts
- **Content Optimization**: tweet summaries, intentional repetition flags

#### Examples:

**User-Provided Key:**
```bash
curl -X POST http://localhost:5004/cinematic-story-design \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {
      "gemini_api_key": "YOUR_API_KEY"
    },
    "system_prompt": "You are a master storyteller and cinematic director. Create a complete story structure with vivid character descriptions suitable for animation and compelling scene narratives that flow naturally.",
    "user_content": "Create a historical drama about Liu Bang, the founder of Han Dynasty, focusing on his rise from a peasant to emperor with themes of leadership and perseverance."
  }'
```

**Admin Key:**
```bash
curl -X POST http://localhost:5004/cinematic-story-design \
  -H "Content-Type: application/json" \
  -H "Admin-API-Key: your-admin-key" \
  -d '{
    "system_prompt": "You are a master storyteller and cinematic director. Create a complete story structure with vivid character descriptions suitable for animation and compelling scene narratives that flow naturally.",
    "user_content": "Create a historical drama about Liu Bang, the founder of Han Dynasty, focusing on his rise from a peasant to emperor with themes of leadership and perseverance."
  }'
```

---

## 6. Scalable Endpoint Structure

The service supports unlimited expansion of new endpoints under the same path structure:
```
http://your-server:5004/{endpoint-name}
```

This allows adding future features like:
- `/image-analysis` - AI image processing
- `/code-generation` - Code generation assistance  
- `/translation` - Multi-language translation
- `/document-processing` - Document analysis and extraction