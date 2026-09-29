# ✈️ GlobeTrotter - AI Travel & Destination Concierge

GlobeTrotter is an intelligent, multi-capable travel assistant built with the **Google Agent Development Kit (ADK)** and powered by **Gemini 2.5 Flash**. Designed to deliver personalized trip planning, GlobeTrotter crafts tailored itineraries, checks destination insights, safeguards traveler preferences and allergies across sessions, and dynamically generates custom travel imagery.

![GlobeTrotter Demo](./demo.gif)

---

## 🌟 Key Features

- **Personalized Travel Concierge**: Recommends multi-day itineraries, cultural highlights, local food spots, weather forecasts, and currency details for worldwide destinations.
- **Persistent Long-Term Memory (Vertex AI Memory Bank)**: Automatically records and recalls user preferences, travel styles, and strict food/drug/environmental allergy constraints across chat sessions.
- **Sandbox Code Execution (`AgentEngineSandboxCodeExecutor`)**: Safely executes Python code within a Vertex AI Agent Engine Sandbox to perform complex calculations and data processing.
- **Domain Image Generation Tool (`generate_domain_image`)**: Utilizes `gemini-3.1-flash-lite-image` in the `global` region to generate high-quality destination visuals, saves local artifacts, and uploads them to a public Google Cloud Storage bucket (`gs://globetrotter-media-qwiklabs-gcp-02-a6a16ea59f35`).
- **A2UI Rich Component Rendering**: Incorporates A2UI Schema Manager (v0.8) and Basic Catalog to produce interactive cards, columns, rows, images, and material icons.
- **Cloud Run Frontend & A2A Proxy**: Features a responsive FastAPI proxy communicating via the Agent-to-Agent (A2A) protocol with a branded, mobile-friendly web UI.

---

## 🏗️ Architecture & Stack

```
                                  +---------------------------------------+
                                  |         Cloud Run Web Frontend        |
                                  |   (Branded HTML/CSS + A2UI Renderer)  |
                                  +-------------------+-------------------+
                                                      |
                                                      | A2A Protocol (ADC)
                                                      v
                                  +-------------------+-------------------+
                                  |     FastAPI Proxy Container           |
                                  +-------------------+-------------------+
                                                      |
                                                      v
+-----------------------------------------------------+-----------------------------------------------------+
|                              Vertex AI Agent Runtime / Agent Engine                                |
|                                                                                                   |
|  +--------------------------+    +----------------------------+    +-----------------------------------+  |
|  |   Gemini 2.5 Flash       |    | Vertex AI Memory Bank      |    | Agent Engine Sandbox Executor     |  |
|  |   (Root Agent)           |    | (Allergy & Preference Store) |    | (Sandboxed Python Code Runtime)   |  |
|  +------------+-------------+    +----------------------------+    +-----------------------------------+  |
|               |                                                                                           |
|               +-------------------------------+                                                           |
|                                               v                                                           |
|                            +------------------+-------------------+                                       |
|                            |  Domain Image Tool                   |                                       |
|                            |  (gemini-3.1-flash-lite-image)       |                                       |
|                            +------------------+-------------------+                                       |
|                                               |                                                           |
|                                               v                                                           |
|                            +------------------+-------------------+                                       |
|                            | Public Cloud Storage Media Bucket |                                       |
|                            +--------------------------------------+                                       |
+-----------------------------------------------------------------------------------------------------------+
```

---

## 📁 Project Structure

```
globetrotter/
├── app/
│   ├── agent.py               # Root ADK agent, tools, callbacks & system prompts
│   ├── a2ui_utils.py          # A2UI response formatter callback
│   └── fast_api_app.py        # Local FastAPI app entrypoint
├── frontend/
│   ├── main.py                # FastAPI proxy connecting to Agent Runtime via A2A
│   ├── Procfile               # Cloud Run web service entrypoint definition
│   ├── requirements.txt       # Frontend dependencies (a2a-sdk, fastapi, uvicorn)
│   └── static/
│       └── index.html         # Branded chat UI with prompt chips & A2UI renderer
├── demo.gif                   # Recorded demonstration animation
├── record_demo.py             # Playwright browser automation demo recorder
├── deployment_metadata.json   # Deployed Agent Engine resource configuration
└── pyproject.toml             # Project dependencies & package specs
```

---

## 🚀 Live Deployments

- **Cloud Run Frontend Service**: [https://globetrotter-frontend-982946819912.us-east1.run.app](https://globetrotter-frontend-982946819912.us-east1.run.app)
- **Agent Engine Resource**: `projects/982946819912/locations/us-east1/reasoningEngines/8445320225645133824`
- **Memory Bank Instance**: `1242931374747287552` (region `us-central1`)
- **GCS Media Bucket**: `gs://globetrotter-media-qwiklabs-gcp-02-a6a16ea59f35`

---

## 🛠️ Local Development & Testing

### 1. Install Dependencies
```bash
agents-cli install
```

### 2. Launch Local Playground
```bash
agents-cli playground
```
Or launch with Memory Bank support:
```bash
adk web app --memory_service_uri=https://us-central1-aiplatform.googleapis.com/v1/projects/982946819912/locations/us-central1/reasoningEngines/1242931374747287552
```

### 3. Record Automated Demo
```bash
uv run python record_demo.py
```

### 4. Deploy Agent & Frontend
```bash
# Redeploy Agent logic to Agent Runtime
agents-cli deploy

# Deploy Frontend to Cloud Run
gcloud run deploy globetrotter-frontend --source ./frontend --region us-east1 --allow-unauthenticated
```
