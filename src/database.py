# src/database.py
import json
import os

def load_data():
    """
    Reads JSON files from the 'data' folder and combines them into a single dictionary.
    """
    base_path = 'data'
    
    def read(filename):
        path = os.path.join(base_path, filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"WARNING: File not found: {path}")
            return [] if 'config' not in filename else {}
        except Exception as e:
            print(f"CRITICAL ERROR loading {path}: {e}")
            return []

    # Assembles the unified structure
    db = {
        "config": read('config.json').get('rules', {}),
        "themes": read('config.json').get('narrative_themes', {}),
        "policies": read('policies.json'), # Changed from politicas.json
        "events": read('events.json')      # Changed from eventos.json
    }

    # Simple validation
    if not db['policies']: print(">>> WARNING: No policies loaded.")
    if not db['events']: print(">>> WARNING: No events loaded.")
    
    return db