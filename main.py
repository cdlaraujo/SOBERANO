# main.py

import uuid
from flask import Flask, jsonify, request, render_template, make_response
from src.database import load_data
from src.director import initialize_llm, IntelligentDirector
from src.engine import GameEngine

app = Flask(__name__)

# --- INITIALIZATION ---
print(">>> SOVEREIGN: Initializing system...")
DB = load_data()

# Load AI once (heavy)
LLM = initialize_llm()

# REPAIR 3: Instantiate Director Globally
DIRECTOR = IntelligentDirector(DB['events'])

print(">>> SOVEREIGN: Ready.")

# Sessions
GAMES = {}

def get_game():
    user_id = request.cookies.get('sovereign_session')
    if not user_id or user_id not in GAMES:
        new_id = str(uuid.uuid4())
        GAMES[new_id] = GameEngine(DB)
        return GAMES[new_id], new_id
    return GAMES[user_id], user_id

# --- ROUTES ---

@app.route('/')
def index():
    _, user_id = get_game()
    resp = make_response(render_template('index.html'))
    resp.set_cookie('sovereign_session', user_id)
    return resp

@app.route('/get_state')
def get_state():
    game, _ = get_game()
    return jsonify(game.get_view_data())

@app.route('/pass_turn', methods=['POST'])
def pass_turn():
    game, _ = get_game()
    # Pass Director OBJECT, not loose function
    result = game.process_turn(LLM, DIRECTOR)
    return jsonify(result)

@app.route('/resolve_event', methods=['POST'])
def resolve_event():
    game, _ = get_game()
    d = request.json
    result = game.resolve_event(d.get('event_id'), d.get('option_id'))
    return jsonify(result)

@app.route('/toggle_policy', methods=['POST'])
def toggle_policy():
    game, _ = get_game()
    d = request.json
    msg, status = game.toggle_policy(d.get('id'))
    return jsonify(msg), status

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)