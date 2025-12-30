import uuid
from flask import Flask, jsonify, request, render_template, make_response
from src.database import carregar_dados
from src.director import inicializar_llm, DirectorInteligente
from src.engine import GameEngine

app = Flask(__name__)

# --- INICIALIZAÇÃO ---
print(">>> SOBERANO: Inicializando sistema...")
DB = carregar_dados()

# Carrega a IA uma única vez (pesado)
LLM = inicializar_llm()

# CORREÇÃO 3: Instancia o Diretor Globalmente (ou por jogo, se preferir)
# Como o Diretor não guarda estado de sessão (só configuração), pode ser global.
DIRECTOR = DirectorInteligente(DB['eventos'])

print(">>> SOBERANO: Pronto.")

# Sessões
GAMES = {}

def get_game():
    user_id = request.cookies.get('soberano_session')
    if not user_id or user_id not in GAMES:
        new_id = str(uuid.uuid4())
        GAMES[new_id] = GameEngine(DB)
        return GAMES[new_id], new_id
    return GAMES[user_id], user_id

# --- ROTAS ---

@app.route('/')
def index():
    _, user_id = get_game()
    resp = make_response(render_template('index.html'))
    resp.set_cookie('soberano_session', user_id)
    return resp

@app.route('/get_estado')
def get_estado():
    game, _ = get_game()
    return jsonify(game.get_view_data())

@app.route('/passar_turno', methods=['POST'])
def passar_turno():
    game, _ = get_game()
    # Passamos o OBJETO Director, não mais uma função solta
    resultado = game.processar_turno(LLM, DIRECTOR)
    return jsonify(resultado)

@app.route('/resolver_evento', methods=['POST'])
def resolver_evento():
    game, _ = get_game()
    d = request.json
    resultado = game.resolver_evento(d.get('evento_id'), d.get('opcao_id'))
    return jsonify(resultado)

@app.route('/toggle_politica', methods=['POST'])
def toggle_politica():
    game, _ = get_game()
    d = request.json
    msg, status = game.toggle_politica(d.get('id'))
    return jsonify(msg), status

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)