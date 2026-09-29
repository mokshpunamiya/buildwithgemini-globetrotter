# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
from pathlib import Path
import urllib.parse
import urllib.request
import uuid
from zoneinfo import ZoneInfo
from google.cloud import firestore, storage
from google import genai

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from .a2ui_utils import a2ui_callback

# Hardcode project ID explicitly to prevent project number resolution issues on Agent Platform
PROJECT_ID = "qwiklabs-gcp-02-a6a16ea59f35"
BUCKET_NAME = "globetrotter-media-qwiklabs-gcp-02-a6a16ea59f35"

# Load Agent Engine resource ID from deployment_metadata.json
deployment_meta_file = Path(__file__).parent.parent / "deployment_metadata.json"
agent_engine_resource_name = "projects/982946819912/locations/us-east1/reasoningEngines/6378167996682076160"
if deployment_meta_file.exists():
    try:
        with open(deployment_meta_file) as f:
            meta = json.load(f)
            if meta.get("remote_agent_runtime_id"):
                agent_engine_resource_name = meta["remote_agent_runtime_id"]
    except Exception:
        pass

# Extract Memory Bank ID from Agent Engine resource name
MEMORY_BANK_ID = agent_engine_resource_name.split("/")[-1]
LOCATION = "us-east1"

# Initialize Agent Engine Sandbox Code Executor
code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=agent_engine_resource_name
)


# Memory Bank Service builder for deployed container / app memory service
def memory_bank_service_builder():
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location=LOCATION,
        agent_engine_id=MEMORY_BANK_ID,
    )


# Memory-generation callback to extract and persist cross-session facts, preferences, and allergies
async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None


def _get_firestore_db():
    return firestore.Client(project=PROJECT_ID)


def generate_destination_image(prompt: str, tool_context: ToolContext) -> str:
    """Generates an image of a travel destination or landmark using gemini-3.1-flash-lite-image in the global region.
    
    Saves the image as an ADK artifact with tool_context.save_artifact and uploads it to the public Cloud Storage bucket.

    Args:
        prompt: Description of the travel destination or scenery to generate (e.g. 'Kyoto ancient temple in autumn').
        tool_context: Injected ADK ToolContext instance.

    Returns:
        The public Cloud Storage URL of the generated image.
    """
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    res = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
    )

    img_bytes = None
    if res.candidates and res.candidates[0].content and res.candidates[0].content.parts:
        for part in res.candidates[0].content.parts:
            if getattr(part, "inline_data", None):
                img_bytes = part.inline_data.data
                break

    if not img_bytes:
        return f"Could not generate image for prompt: '{prompt}'."

    safe_slug = "".join(c if c.isalnum() else "_" for c in prompt[:20].lower()).strip("_") or "destination"
    filename = f"{safe_slug}_{uuid.uuid4().hex[:6]}.jpg"

    # 1. Save image artifact with tool_context.save_artifact
    artifact_part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload image to public Cloud Storage bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(img_bytes, content_type="image/jpeg")

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
    return f"Successfully generated destination image. Public URL: {public_url}"


def fetch_location_info(location: str) -> str:
    """Fetches real live summary information, historical details, and thumbnail image URLs for a travel destination or landmark from Wikipedia.

    Args:
        location: The city, landmark, or destination name (e.g., 'Kyoto', 'Eiffel Tower', 'Banff National Park').

    Returns:
        JSON string containing title, description, summary extract, thumbnail image URL, and Wikipedia page URL.
    """
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(location)}"
    req = urllib.request.Request(url, headers={"User-Agent": "GlobeTrotter/1.0 (TravelPlannerAgent)"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return json.dumps({
                "title": data.get("title"),
                "description": data.get("description"),
                "extract": data.get("extract"),
                "thumbnail": data.get("thumbnail", {}).get("source"),
                "content_url": data.get("content_urls", {}).get("desktop", {}).get("page"),
            })
    except Exception as e:
        return f"Could not fetch location details for '{location}': {str(e)}"


def get_live_destination_weather(city: str) -> str:
    """Fetches real live weather forecast, temperature, wind speed, and timezone for any city using the Open-Meteo public API.

    Args:
        city: The name of the city to get live weather for (e.g., 'Kyoto', 'Paris', 'San Francisco', 'Tokyo').

    Returns:
        JSON string containing city, country, temperature (°C and °F), wind speed, and day/night status.
    """
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1"
    req = urllib.request.Request(geo_url, headers={"User-Agent": "GlobeTrotter/1.0"})
    try:
        with urllib.request.urlopen(req) as resp:
            geo_data = json.loads(resp.read().decode("utf-8"))
            results = geo_data.get("results", [])
            if not results:
                return f"City '{city}' not found."
            loc = results[0]
            lat, lon = loc["latitude"], loc["longitude"]
            country = loc.get("country", "")
            tz = loc.get("timezone", "UTC")

        wx_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        wx_req = urllib.request.Request(wx_url, headers={"User-Agent": "GlobeTrotter/1.0"})
        with urllib.request.urlopen(wx_req) as resp:
            wx_data = json.loads(resp.read().decode("utf-8"))
            cur = wx_data.get("current_weather", {})
            temp_c = cur.get("temperature", 0)
            return json.dumps({
                "city": loc.get("name"),
                "country": country,
                "timezone": tz,
                "temperature_celsius": temp_c,
                "temperature_fahrenheit": round(temp_c * 1.8 + 32, 1),
                "windspeed_kmh": cur.get("windspeed"),
                "is_daytime": bool(cur.get("is_day", 1)),
            }, indent=2)
    except Exception as e:
        return f"Error fetching live weather for {city}: {str(e)}"


def get_exchange_rates(base_currency: str = "USD") -> str:
    """Fetches real-time foreign currency exchange rates for travel budgeting from Open Exchange Rates API.

    Args:
        base_currency: The base currency code (e.g., 'USD', 'EUR', 'GBP', 'JPY'). Default is 'USD'.

    Returns:
        JSON string containing live conversion rates for major travel currencies (EUR, JPY, GBP, CAD, AUD, CHF, CNY, SGD).
    """
    url = f"https://open.er-api.com/v6/latest/{base_currency.upper()}"
    req = urllib.request.Request(url, headers={"User-Agent": "GlobeTrotter/1.0"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            rates = data.get("rates", {})
            travel_currencies = ["EUR", "JPY", "GBP", "CAD", "AUD", "CHF", "CNY", "SGD"]
            filtered = {c: rates.get(c) for c in travel_currencies if c in rates}
            return json.dumps({
                "base_currency": base_currency.upper(),
                "rates": filtered,
                "last_updated": data.get("time_last_update_utc"),
            }, indent=2)
    except Exception as e:
        return f"Could not fetch exchange rates for {base_currency}: {str(e)}"


def get_destinations(category: str = "") -> str:
    """Reads destinations from the Firestore database, optionally filtering by category.

    Args:
        category: Optional category filter (e.g. 'Culture & History', 'Food & Dining', 'Nature & Adventure', 'Beach & Relaxation').

    Returns:
        JSON string of destinations from Firestore.
    """
    db = _get_firestore_db()
    docs = db.collection("destinations").stream()
    
    results = []
    for doc in docs:
        data = doc.to_dict()
        if category and category.lower() not in data.get("category", "").lower():
            continue
        results.append(data)
        
    return json.dumps(results, indent=2)


def search_destination(query: str) -> str:
    """Searches for a specific travel destination by name, city, or country in Firestore.

    Args:
        query: The city, destination name, or country to search for.

    Returns:
        JSON string of matching destination documents.
    """
    db = _get_firestore_db()
    docs = db.collection("destinations").stream()
    
    q_lower = query.lower()
    matches = []
    for doc in docs:
        data = doc.to_dict()
        name = data.get("name", "").lower()
        city = data.get("city", "").lower()
        country = data.get("country", "").lower()
        
        if q_lower in name or q_lower in city or q_lower in country:
            matches.append(data)
            
    return json.dumps(matches, indent=2)


def add_destination(
    name: str,
    city: str,
    country: str,
    category: str,
    description: str,
    budget_tier: str = "$$$",
    highlights: str = "",
) -> str:
    """Writes a new travel destination doc into the Firestore database collection.

    Args:
        name: Name of the destination (e.g., 'Kyoto Temples').
        city: City where the destination is located.
        country: Country where the destination is located.
        category: Travel category (e.g., 'Culture & History', 'Nature & Adventure').
        description: Description of the destination experience.
        budget_tier: Budget indicator (e.g., '$', '$$', '$$$', '$$$$').
        highlights: Comma-separated list of key attractions/highlights.

    Returns:
        Status message with created document ID.
    """
    db = _get_firestore_db()
    doc_id = f"dest_{city.lower().replace(' ', '_')}_{name.lower().replace(' ', '_')[:10]}"
    
    highlight_list = [h.strip() for h in highlights.split(",")] if highlights else []
    
    dest_data = {
        "id": doc_id,
        "name": name,
        "city": city,
        "country": country,
        "category": category,
        "description": description,
        "budget_tier": budget_tier,
        "highlights": highlight_list,
        "rating": 5.0,
    }
    
    db.collection("destinations").document(doc_id).set(dest_data)
    return f"Successfully added destination '{name}' in {city}, {country} to Firestore with ID '{doc_id}'."


def get_current_time(query: str) -> str:
    """Simulates getting current time for a city.

    Args:
        query: The name of the city to get current time for.

    Returns:
        A string with current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


# Initialize A2UI Schema Manager version 0.8 with Basic Catalog
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are GlobeTrotter, a helpful AI Travel Concierge. You assist users in discovering travel "
        "destinations, planning custom itineraries, generating travel destination visual images, "
        "checking real-time weather using Open-Meteo, fetching live currency rates, looking up location info, "
        "executing code in your sandbox for trip budget math and data processing, "
        "remembering user travel preferences and budget across conversations, "
        "and managing saved destinations in Firestore."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "CRITICAL MEMORY & ALLERGY INSTRUCTIONS: "
        "Pay strict attention to any food allergies, drug/medication allergies, or environmental allergies mentioned by the user (e.g. peanuts, shellfish, gluten, dairy, penicillin). "
        "Always remember user allergies across conversations and sessions using your Memory Bank. "
        "When recommending restaurants, dining spots, meal options, or travel activities, proactively account for and warn against any allergens that conflict with the user's saved allergies. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction,
    code_executor=code_executor,
    tools=[
        PreloadMemoryTool(),
        generate_destination_image,
        get_destinations,
        search_destination,
        add_destination,
        fetch_location_info,
        get_live_destination_weather,
        get_exchange_rates,
        get_current_time,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
