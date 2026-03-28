import os
import requests
import json
import time
from dotenv import load_dotenv
load_dotenv()

INDEX_FILE="database.json"
SKETCHFAB_TOKEN = os.getenv("SKETCHFAB_TOKEN")

if not SKETCHFAB_TOKEN:
    raise ValueError(" NO SKETCHFAB_TOKEN found in .env please get an api key to download models")

def save_index(data):
    temp_file = INDEX_FILE + ".tmp"
    with open(temp_file, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(temp_file, INDEX_FILE)  # atomic replace

def load_index():
    if not os.path.exists(INDEX_FILE):
        return {}

    try:
        with open(INDEX_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("Corrupted or empty database. Resetting...")
        return {}

def scan_local(root_folder):
    glb_files = []

    for root, dirs, files in os.walk(root_folder):
        for file in files:
            if file.lower().endswith(".glb"):
                full_path = os.path.join(root, file)
                glb_files.append({
                    "name": file,
                    "path": full_path,
                    "source": "local"
                })

    return glb_files

def search_web(query="car"):
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

def search_index(query):
    database = load_index()

    if not database:
        return []

    results = []
    for item in database.get("results", []):
        if query.lower() in item["name"].lower():
            results.append(item)

    return results

def unified_search(folder, query="car", use_cache=True):
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

def download_glb(model, save_folder):
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

        # Step 1: get download info
        url = f"https://api.sketchfab.com/v3/models/{uid}/download"
        res = requests.get(url, headers=headers)
        data = res.json()

        # Step 2: get actual GLB file URL
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
        r.raise_for_status()  # catch HTTP errors early, prevents silent crash
        with open(save_path, "wb") as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)

        print(f"Saved to {save_path}")

        # Update database.json: mark this model as local 
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