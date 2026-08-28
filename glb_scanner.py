"""
GLB Scanner Module for Hand-AR Project.
Handles searching for local 3D models/point clouds and fetching/downloading downloadable models from Sketchfab API.
"""

import os
import requests
import json
import time
from dotenv import load_dotenv

load_dotenv()

INDEX_FILE = "database.json"
SKETCHFAB_TOKEN = os.getenv("SKETCHFAB_TOKEN")

if not SKETCHFAB_TOKEN:
    raise ValueError("NO SKETCHFAB_TOKEN found in .env. Please provide an API key to download models.")


def save_index(data: dict) -> None:
    """
    Atomically saves search index data to database.json.

    Args:
        data (dict): Dictionary containing query results and metadata to persist.
    """
    temp_file = INDEX_FILE + ".tmp"
    with open(temp_file, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(temp_file, INDEX_FILE)


def load_index() -> dict:
    """
    Loads the search database index from database.json.

    Returns:
        dict: The cached database content, or empty dict if non-existent/corrupted.
    """
    if not os.path.exists(INDEX_FILE):
        return {}

    try:
        with open(INDEX_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("Corrupted or empty database. Resetting...")
        return {}


def scan_local(root_folder: str) -> list:
    """
    Scans local directory for 3D model files (.glb, .obj, .csv) and assigns view modes.

    Args:
        root_folder (str): Directory path containing local 3D assets.

    Returns:
        list: List of dictionaries describing each local model file and its mode.
    """
    glb_files = []
    existing_modes = {}
    
    project_dir = os.path.dirname(root_folder)
    db_path = os.path.join(project_dir, "database.json")
    
    if not os.path.exists(db_path):
        db_path = os.path.join(root_folder, "database.json")

    if os.path.exists(db_path):
        try:
            with open(db_path, "r") as f:
                data = json.load(f)
                for item in data.get("results", []):
                    if "name" in item and "mode" in item:
                        existing_modes[item["name"]] = item["mode"]
        except Exception as e:
            print(f"Could not read existing modes: {e}")

    for root, dirs, files in os.walk(root_folder):
        for file in files:
            if file.lower().endswith((".glb", ".csv", ".obj")):
                full_path = os.path.join(root, file)
                default_mode = "explore" if file.lower().endswith(".csv") else "inspect"
                saved_mode = existing_modes.get(file, default_mode)
                
                glb_files.append({
                    "name": file,
                    "path": full_path,
                    "source": "local",
                    "mode": saved_mode
                })

    return glb_files


def search_web(query: str = "car") -> list:
    """
    Searches the Sketchfab API v3 for downloadable 3D models matching a query.

    Args:
        query (str): Search term for Sketchfab models. Defaults to "car".

    Returns:
        list: List of downloadable web model records containing name, UID, and viewer URL.
    """
    results = []
    url = "https://api.sketchfab.com/v3/search"
    params = {
        "q": query,
        "type": "models"
    }

    try:
        res = requests.get(url, params=params)
        data = res.json()

        for model in data.get("results", []):            
            if not model.get("isDownloadable", False):
                continue
            uid = model.get("uid")
            name = model.get("name")
            viewer_link = f"https://sketchfab.com/3d-models/{uid}"
            results.append({
                "name": name,
                "uid": uid,
                "viewer": viewer_link,
                "source": "web"
            })
    except Exception as e:
        print("Web search failed:", e)
    return results


def unified_search(folder: str, query: str = "car", use_cache: bool = True) -> list:
    """
    Combines local model files and online Sketchfab models into a unified search result.

    Args:
        folder (str): Local models directory path.
        query (str): Search query keyword. Defaults to "car".
        use_cache (bool): If True, returns cached results when queries match database.json.

    Returns:
        list: Deduplicated list of local and web search result records.
    """
    database = load_index()

    if use_cache and database:
        if database.get("query") == query:
            return database["results"]

    local_results = scan_local(folder)
    web_results = search_web(query)

    combined = local_results + web_results

    unique = {}
    for item in combined:
        key = item.get("path") or item.get("uid")
        unique[key] = item

    combined = list(unique.values())

    data = {
        "query": query,
        "timestamp": time.time(),
        "results": combined
    }

    save_index(data)
    return combined


def download_glb(model: dict, save_folder: str) -> str:
    """
    Downloads a GLB model asset from Sketchfab using the API token.

    Args:
        model (dict): Model dictionary containing source, uid, and name metadata.
        save_folder (str): Directory path to save the downloaded model.

    Returns:
        str: Absolute file path to the saved local GLB file, or None if download fails.
    """
    if model["source"] != "web":
        return model.get("path")

    try:
        uid = model.get("uid")
        if not uid:
            print("No UID found")
            return None

        headers = {
            "Authorization": f"Token {SKETCHFAB_TOKEN}"
        }

        url = f"https://api.sketchfab.com/v3/models/{uid}/download"
        res = requests.get(url, headers=headers)
        data = res.json()

        if "glb" in data:
            download_url = data["glb"]["url"]
        elif "zip" in data:
            download_url = data["zip"]["url"]
        else:
            print("No downloadable format..")
            return None

        name = model["name"].replace(" ", "_")
        save_path = os.path.abspath(os.path.join(save_folder, name + ".glb"))

        print(f"Downloading {name}...")

        r = requests.get(download_url, stream=True)
        r.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)

        print(f"Saved to {save_path}")

        database = load_index()
        updated = False
        for item in database.get("results", []):
            if item.get("uid") == uid:
                item["source"] = "local"
                item["path"]   = save_path
                updated = True
                break
        if updated:
            save_index(database)
            print(f"Database updated: {name} is now local")

        return save_path

    except Exception as e:
        print("Download failed:", e)
        return None