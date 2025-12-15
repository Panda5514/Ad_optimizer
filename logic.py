import requests
import json
import random
import base64

BASE_URL = "https://engine.prod.bria-api.com/v2"

# --- HELPER: IMAGE TO BASE64 ---
def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

# --- STYLE THIEF (Reference Image) ---
def extract_structure_from_image(api_key, image_file, product_prompt):
    headers = {"api_token": api_key, "Content-Type": "application/json"}
    payload = {
        "image_file": encode_image(image_file),
        "prompt": product_prompt,
        "sync": True
    }
    try:
        resp = requests.post(f"{BASE_URL}/structured_prompt/generate", headers=headers, json=payload)
        resp.raise_for_status()
        return json.loads(resp.json()["result"]["structured_prompt"])
    except Exception as e:
        print(f"Extraction Error: {e}")
        return None

# --- HELPER: BASIC STRUCTURE ---
def get_base_structure(api_key, product, context):
    # We explicitly add "side profile facing right" to stop the dog from flipping.
    full_prompt = f"{product}. {context}, side profile facing right, dynamic motion, detailed"
    
    headers = {"api_token": api_key, "Content-Type": "application/json"}
    resp_sp = requests.post(
        f"{BASE_URL}/structured_prompt/generate", 
        headers=headers, 
        json={"prompt": full_prompt, "sync": True}
    )
    return json.loads(resp_sp.json()["result"]["structured_prompt"])

# --- HELPER: GENERATION ---
def run_bria_generation(api_key, structure, seed=None):
    headers = {"api_token": api_key, "Content-Type": "application/json"}
    payload = {"structured_prompt": json.dumps(structure), "aspect_ratio": "16:9", "sync": True}
    if seed: payload["seed"] = seed
    try:
        resp = requests.post(f"{BASE_URL}/image/generate", headers=headers, json=payload)
        return resp.json()["result"]["image_url"]
    except:
        return "https://via.placeholder.com/512?text=Error"

# --- STEP 1: GENERATOR ---
def generate_step1(api_key, product, context, lighting_opts, angle_opts, ref_image=None):
    master_seed = random.randint(1, 1000000)
    results = []
    
    # Path A: Reference Image
    if ref_image:
        base_structure = extract_structure_from_image(api_key, ref_image, f"{product}. {context}")
        if not base_structure:
            base_structure = get_base_structure(api_key, product, context)
            
        url = run_bria_generation(api_key, base_structure, master_seed)
        results.append([{
            "url": url, "structure": base_structure, "seed": master_seed, "label": "✨ Style Cloned"
        }])
        return results, master_seed

    # Path B: Matrix
    base_structure = get_base_structure(api_key, product, context)
    
    for row_setting in lighting_opts:
        row_results = []
        for col_setting in angle_opts:
            current = json.loads(json.dumps(base_structure))
            
            # Inject Settings
            if "lighting" not in current: current["lighting"] = {}
            current["lighting"]["conditions"] = row_setting
            
            if "photographic_characteristics" not in current: current["photographic_characteristics"] = {}
            current["photographic_characteristics"]["camera_angle"] = col_setting
            
            # OPTIONAL: If using Studio lighting, force a clean background so it looks professional
            if "studio" in row_setting.lower():
                current["background"] = {"description": "clean solid studio background"}

            url = run_bria_generation(api_key, current, master_seed)
            row_results.append({
                "url": url, "structure": current, "seed": master_seed, "label": f"{row_setting}\n{col_setting}"
            })
        results.append(row_results)
        
    return results, master_seed

# --- STEP 2: LOCALIZATION (THE STUDIO KILLER) ---
def generate_locations(api_key, winning_structure, seed, location_config):
    results = []
    
    city_prompts = {
        "Tokyo, Japan": "neon lit Shinjuku street at night, wet pavement, crowd",
        "Paris, France": "sunny Parisian boulevard with Eiffel tower view",
        "New York, USA": "busy Manhattan street with yellow cabs",
        "Mars Colony": "red dusty martian landscape"
    }

    for loc_name, instruction in location_config.items():
        # Clone the winning structure
        loc_structure = json.loads(json.dumps(winning_structure))
        

        json_str = json.dumps(loc_structure)
        if "studio" in json_str.lower():
            # Replace 'studio' with 'outdoor' to force the AI to accept the new environment
            json_str = json_str.replace("Studio", "Outdoor").replace("studio", "outdoor")
            loc_structure = json.loads(json_str)

        # 1. Force the New Background
        if "background" not in loc_structure: loc_structure["background"] = {}
        bg_desc = city_prompts.get(loc_name, f"outdoor scenery in {loc_name}")
        loc_structure["background"]["description"] = bg_desc
        loc_structure["background"]["source_image"] = None 

        # 2. Inject Special Instructions
        if instruction and instruction.strip() != "":
            if "aesthetics" not in loc_structure: loc_structure["aesthetics"] = {}
            
            if "anime" in instruction.lower():
                loc_structure["aesthetics"]["medium"] = "anime illustration, 2D cell shaded"
                loc_structure["aesthetics"]["art_style"] = "anime"
            else:
                current_mood = loc_structure["aesthetics"].get("mood_atmosphere", "")
                loc_structure["aesthetics"]["mood_atmosphere"] = f"{current_mood}, {instruction}"

        url = run_bria_generation(api_key, loc_structure, seed)
        results.append({"loc": loc_name, "instruction": instruction, "url": url})
        
    return results