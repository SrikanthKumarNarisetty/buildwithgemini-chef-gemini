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
from zoneinfo import ZoneInfo

from typing import Any, Dict, List, Optional
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.cloud import firestore
from google.genai import types

MODEL = "gemini-3.8-flash"
FIRESTORE_PROJECT = "qwiklabs-gcp-04-610bbf0144b0"

_db_client: Optional[firestore.Client] = None


def _get_db() -> firestore.Client:
    """Gets or initializes the Firestore client with the explicit project ID."""
    global _db_client
    if _db_client is None:
        _db_client = firestore.Client(project=FIRESTORE_PROJECT)
    return _db_client


def list_recipes() -> List[Dict[str, Any]]:
    """Lists all available recipes from the catalog.

    Returns:
        A list of dictionaries representing recipes in the database with their
        title, cuisine, difficulty, prep time, calories, and key ingredients.
    """
    db = _get_db()
    docs = db.collection("recipes").stream()
    recipes = []
    for doc in docs:
        data = doc.to_dict()
        recipes.append({
            "id": doc.id,
            "title": data.get("title", ""),
            "cuisine": data.get("cuisine", ""),
            "difficulty": data.get("difficulty", ""),
            "prep_time_minutes": data.get("prep_time_minutes", 0),
            "cook_time_minutes": data.get("cook_time_minutes", 0),
            "servings": data.get("servings", 0),
            "calories_per_serving": data.get("calories_per_serving", 0),
            "dietary_tags": data.get("dietary_tags", []),
            "ingredients": data.get("ingredients", []),
        })
    return recipes


def get_recipe_details(recipe_id: str) -> Dict[str, Any]:
    """Retrieves full details for a specific recipe, including step-by-step instructions and macros.

    Args:
        recipe_id: The ID of the recipe (e.g. 'lemon-herb-grilled-chicken').

    Returns:
        A dictionary with full details including instructions and macro breakdown,
        or an error message if not found.
    """
    db = _get_db()
    doc = db.collection("recipes").document(recipe_id).get()
    if not doc.exists:
        return {"error": f"Recipe '{recipe_id}' not found."}
    return doc.to_dict()


def search_recipes(
    ingredient: Optional[str] = None,
    dietary_tag: Optional[str] = None,
    max_calories: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Searches recipes by ingredient, dietary tag, or calorie limit.

    Args:
        ingredient: Optional ingredient keyword to filter by (e.g., 'chicken', 'salmon', 'beans').
        dietary_tag: Optional dietary tag (e.g., 'vegan', 'gluten-free', 'high-protein').
        max_calories: Optional maximum calories per serving.

    Returns:
        A list of matching recipe summaries.
    """
    all_recipes = list_recipes()
    results = []

    for r in all_recipes:
        if dietary_tag and dietary_tag.lower() not in [t.lower() for t in r.get("dietary_tags", [])]:
            continue
        if ingredient and not any(ingredient.lower() in ing.lower() for ing in r.get("ingredients", [])):
            continue
        if max_calories and r.get("calories_per_serving", 0) > max_calories:
            continue
        results.append(r)

    return results


def save_recipe(
    recipe_id: str,
    title: str,
    cuisine: str,
    difficulty: str,
    prep_time_minutes: int,
    cook_time_minutes: int,
    servings: int,
    calories_per_serving: int,
    ingredients: List[str],
    instructions: List[str],
    dietary_tags: List[str]
) -> Dict[str, Any]:
    """Saves or creates a new recipe in the Firestore recipe catalog.

    Args:
        recipe_id: Unique slug/identifier for the recipe (e.g., 'avocado-toast').
        title: Title of the dish.
        cuisine: Cuisine type (e.g., 'Mediterranean', 'American').
        difficulty: Difficulty level ('Easy', 'Medium', 'Hard').
        prep_time_minutes: Minutes needed for prep.
        cook_time_minutes: Minutes needed for cooking.
        servings: Number of servings.
        calories_per_serving: Calories per serving.
        ingredients: List of ingredients.
        instructions: Ordered list of step-by-step instructions.
        dietary_tags: Dietary tags like 'vegan', 'gluten-free', etc.

    Returns:
        A confirmation dictionary indicating success.
    """
    db = _get_db()
    data = {
        "id": recipe_id,
        "title": title,
        "cuisine": cuisine,
        "difficulty": difficulty,
        "prep_time_minutes": prep_time_minutes,
        "cook_time_minutes": cook_time_minutes,
        "servings": servings,
        "calories_per_serving": calories_per_serving,
        "ingredients": ingredients,
        "instructions": instructions,
        "dietary_tags": dietary_tags,
    }
    db.collection("recipes").document(recipe_id).set(data)
    return {"status": "success", "message": f"Recipe '{title}' saved successfully with ID '{recipe_id}'."}


def log_meal(
    meal_type: str,
    recipe_name: str,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """Logs a meal consumed or planned by the user to the Firestore 'meal_logs' collection.

    Args:
        meal_type: Type of meal, e.g. 'breakfast', 'lunch', 'dinner', or 'snack'.
        recipe_name: The name or title of the dish consumed/planned.
        notes: Any optional user feedback, rating, or tweaks made.

    Returns:
        A confirmation message indicating the meal was logged.
    """
    db = _get_db()
    entry = {
        "meal_type": meal_type,
        "recipe_name": recipe_name,
        "notes": notes or "",
        "timestamp": firestore.SERVER_TIMESTAMP,
    }
    _, doc_ref = db.collection("meal_logs").add(entry)
    return {"status": "success", "message": f"Logged {meal_type} '{recipe_name}' with entry ID {doc_ref.id}."}


def scale_recipe_and_calculate_macros(
    recipe_id: str,
    target_servings: int
) -> Dict[str, Any]:
    """Scales a recipe's serving size and calculates scaled nutritional macros.

    Args:
        recipe_id: The ID of the recipe to scale (e.g., 'lemon-herb-grilled-chicken').
        target_servings: The desired number of servings to scale to.

    Returns:
        A dictionary with the scaled recipe title, scale multiplier, per-serving macros,
        total batch macros (calories, protein, carbs, fat), and scaled serving count.
    """
    db = _get_db()
    doc = db.collection("recipes").document(recipe_id).get()
    if not doc.exists:
        return {"error": f"Recipe '{recipe_id}' not found."}

    data = doc.to_dict()
    base_servings = data.get("servings", 1) or 1
    multiplier = round(target_servings / base_servings, 2)

    base_calories = data.get("calories_per_serving", 0)
    base_macros = data.get("macros", {})
    protein_per_serving = base_macros.get("protein_g", 0)
    carbs_per_serving = base_macros.get("carbs_g", 0)
    fat_per_serving = base_macros.get("fat_g", 0)

    return {
        "recipe_id": recipe_id,
        "title": data.get("title", ""),
        "original_servings": base_servings,
        "target_servings": target_servings,
        "scale_factor": multiplier,
        "per_serving": {
            "calories": base_calories,
            "protein_g": protein_per_serving,
            "carbs_g": carbs_per_serving,
            "fat_g": fat_per_serving,
        },
        "total_batch": {
            "calories": round(base_calories * target_servings),
            "protein_g": round(protein_per_serving * target_servings),
            "carbs_g": round(carbs_per_serving * target_servings),
            "fat_g": round(fat_per_serving * target_servings),
        },
        "ingredients": data.get("ingredients", []),
    }


import json
import urllib.parse
import urllib.request


def search_public_recipes(query: str) -> List[Dict[str, Any]]:
    """Searches the free public TheMealDB recipe database for global meal recipes and ideas.

    Args:
        query: Name or ingredient of the dish (e.g. 'pasta', 'chicken', 'curry', 'salmon').

    Returns:
        A list of matching recipe results containing title, category, cuisine area,
        instructions snippet, and image URL.
    """
    safe_query = urllib.parse.quote(query.strip())
    url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={safe_query}"
    req = urllib.request.Request(url, headers={"User-Agent": "ChefGemini/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        return [{"error": f"Failed to fetch public recipes: {str(e)}"}]

    meals = data.get("meals") or []
    results = []
    for m in meals[:5]:  # return top 5 matches
        # extract non-empty ingredients
        ingredients = []
        for i in range(1, 21):
            ing = m.get(f"strIngredient{i}")
            meas = m.get(f"strMeasure{i}")
            if ing and ing.strip():
                measure_str = f"{meas.strip()} " if meas and meas.strip() else ""
                ingredients.append(f"{measure_str}{ing.strip()}")

        results.append({
            "title": m.get("strMeal"),
            "category": m.get("strCategory"),
            "area": m.get("strArea"),
            "image_url": m.get("strMealThumb"),
            "instructions": (m.get("strInstructions") or "")[:400] + ("..." if len(m.get("strInstructions") or "") > 400 else ""),
            "ingredients": ingredients,
        })

    return results


import os


def geocode_address(address: str) -> Dict[str, Any]:
    """Converts an address into geographic coordinates using Google Maps Geocoding API.

    Args:
        address: The street address, city, or location name to geocode.

    Returns:
        A dictionary containing formatted address, latitude, and longitude.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key or api_key == "PASTE_KEY_HERE":
        return {"error": "GOOGLE_MAPS_API_KEY is not configured in environment or .env."}

    safe_address = urllib.parse.quote(address.strip())
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={safe_address}&key={api_key}"
    req = urllib.request.Request(url, headers={"User-Agent": "ChefGemini/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        return {"error": f"Geocoding request failed: {str(e)}"}

    if data.get("status") != "OK" or not data.get("results"):
        return {"error": f"Geocoding failed with status: {data.get('status')}", "message": data.get("error_message")}

    first = data["results"][0]
    loc = first.get("geometry", {}).get("location", {})
    return {
        "formatted_address": first.get("formatted_address"),
        "latitude": loc.get("lat"),
        "longitude": loc.get("lng"),
        "place_id": first.get("place_id"),
    }


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "grocery_store",
    radius_meters: float = 2000.0
) -> List[Dict[str, Any]]:
    """Finds nearby places (e.g. grocery stores, supermarkets, restaurants) using Google Places API (New).

    Args:
        latitude: Latitude coordinate for search center.
        longitude: Longitude coordinate for search center.
        place_type: Included place type (e.g., 'grocery_store', 'supermarket', 'bakery', 'restaurant').
        radius_meters: Search radius in meters (default 2000.0, max 50000.0).

    Returns:
        A list of nearby places with display name, formatted address, and coordinates.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key or api_key == "PASTE_KEY_HERE":
        return [{"error": "GOOGLE_MAPS_API_KEY is not configured in environment or .env."}]

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.types",
    }
    payload = {
        "includedTypes": [place_type],
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
                "radius": radius_meters,
            }
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        return [{"error": f"Places API HTTP error {e.code}: {error_body}"}]
    except Exception as e:
        return [{"error": f"Places API request failed: {str(e)}"}]

    places = data.get("places", [])
    results = []
    for p in places[:10]:
        display_name = p.get("displayName", {}).get("text", "")
        formatted_address = p.get("formattedAddress", "")
        loc = p.get("location", {})
        results.append({
            "name": display_name,
            "address": formatted_address,
            "location": {
                "latitude": loc.get("latitude"),
                "longitude": loc.get("longitude"),
            },
            "types": p.get("types", []),
        })

    return results


import re
import uuid
from google.adk.tools import ToolContext
from google import genai
from google.cloud import storage

PUBLIC_STORAGE_BUCKET = "chefgemini-recipes-qwiklabs-gcp-04-610bbf0144b0"
_genai_client: Optional[genai.Client] = None
_storage_client: Optional[storage.Client] = None


def _get_genai_client() -> genai.Client:
    """Initializes Google GenAI client in global region on Vertex AI."""
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(
            vertexai=True,
            project=FIRESTORE_PROJECT,
            location="global"
        )
    return _genai_client


def _get_storage_client() -> storage.Client:
    """Initializes Cloud Storage client."""
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=FIRESTORE_PROJECT)
    return _storage_client


async def generate_dish_image(
    dish_name: str,
    tool_context: ToolContext,
    presentation_details: Optional[str] = None,
) -> Dict[str, Any]:
    """Generates an appetizing plating photograph for a dish/recipe using gemini-3.1-flash-lite-image.

    The generated image is saved as an artifact in the playground's Artifacts panel,
    and uploaded to public Cloud Storage, returning its public HTTPS URL.

    Args:
        dish_name: The name of the dish or recipe (e.g. 'Lemon Herb Grilled Chicken').
        tool_context: The ADK ToolContext used to save artifacts.
        presentation_details: Optional plating or styling notes (e.g. 'garnished with fresh parsley and lemon wedges on rustic ceramics').

    Returns:
        A dictionary with the public image URL, artifact filename, and status.
    """
    client = _get_genai_client()
    prompt = f"Professional food photography of {dish_name}"
    if presentation_details:
        prompt += f", {presentation_details}"
    prompt += ", beautifully plated, restaurant presentation, natural soft lighting, high resolution, 4k."

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )
    except Exception as e:
        return {"error": f"Failed to generate image: {str(e)}"}

    # Extract image bytes
    image_bytes = None
    mime_type = "image/jpeg"
    for candidate in response.candidates or []:
        for part in candidate.content.parts or []:
            if getattr(part, "inline_data", None) and part.inline_data.data:
                image_bytes = part.inline_data.data
                mime_type = part.inline_data.mime_type or "image/jpeg"
                break
        if image_bytes:
            break

    if not image_bytes:
        return {"error": "No image data returned from image generation model."}

    # Generate unique filenames
    slug = re.sub(r"[^a-z0-9]+", "-", dish_name.lower()).strip("-")
    unique_suffix = uuid.uuid4().hex[:8]
    ext = "jpg" if "jpeg" in mime_type else "png"
    filename = f"{slug}-{unique_suffix}.{ext}"

    # 1. Save with tool_context.save_artifact for Playground Artifacts panel
    try:
        artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)
    except Exception as e:
        print(f"Warning: save_artifact failed: {e}")

    # 2. Upload same bytes directly to the public Cloud Storage bucket
    try:
        gcs_client = _get_storage_client()
        bucket = gcs_client.bucket(PUBLIC_STORAGE_BUCKET)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)
        public_url = f"https://storage.googleapis.com/{PUBLIC_STORAGE_BUCKET}/{filename}"
    except Exception as e:
        return {"error": f"Failed to upload image to Cloud Storage: {str(e)}"}

    return {
        "status": "success",
        "dish_name": dish_name,
        "artifact_filename": filename,
        "image_url": public_url,
        "message": f"Successfully generated dish image and published to {public_url}",
    }


from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.memory import VertexAiMemoryBankService
from google.adk.code_executors.agent_engine_sandbox_code_executor import AgentEngineSandboxCodeExecutor

MEMORY_BANK_ID = "1254020499269222400"
MEMORY_BANK_LOCATION = "us-east1"
SANDBOX_RESOURCE_NAME = "projects/592580295044/locations/us-east1/reasoningEngines/1254020499269222400/sandboxEnvironments/8082697847490772992"
AGENT_ENGINE_RESOURCE_NAME = "projects/592580295044/locations/us-east1/reasoningEngines/1254020499269222400"


def memory_bank_service_builder():
    """Builds the VertexAiMemoryBankService for the app when deployed."""
    return VertexAiMemoryBankService(
        project=FIRESTORE_PROJECT,
        location=MEMORY_BANK_LOCATION,
        agent_engine_id=MEMORY_BANK_ID,
    )


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: after each turn, persists session and extracts durable user facts, allergies, and dietary constraints."""
    await callback_context.add_session_to_memory()
    return None


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are ChefGemini, an expert culinary assistant and personal meal planner. "
        "You remember the user's stated food allergies, dietary restrictions, and meal preferences "
        "across all conversations and strictly use them to personalize recipe recommendations, ingredient swaps, "
        "and meal plans. Never recommend or include ingredients that conflict with the user's remembered allergies.\n\n"
        "You help users discover recipes, tailor meal choices to their dietary preferences, "
        "scale recipe portions and calculate nutritional macros, search online public recipes, "
        "generate mouth-watering plating photos for dishes, find nearby grocery stores with Google Maps tools, "
        "safely execute Python code in your Agent Platform sandbox for custom mathematical or data computations, "
        "and track meals. "
        "Use your tools whenever the user asks for recipes, dish visuals/images, ingredient recommendations, "
        "grocery store locations, public recipe lookups, portion adjustments/macro calculations, data computations, or wants to log meals."
    ),
    after_agent_callback=generate_memories_callback,
    code_executor=AgentEngineSandboxCodeExecutor(
        sandbox_resource_name=SANDBOX_RESOURCE_NAME,
        agent_engine_resource_name=AGENT_ENGINE_RESOURCE_NAME,
    ),
    tools=[
        PreloadMemoryTool(),
        list_recipes,
        get_recipe_details,
        search_recipes,
        save_recipe,
        log_meal,
        scale_recipe_and_calculate_macros,
        search_public_recipes,
        geocode_address,
        find_nearby_places,
        generate_dish_image,
    ],
)


app = App(
    root_agent=root_agent,
    name="app",
)






