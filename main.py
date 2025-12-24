import uuid
from flask import Flask, jsonify, request, render_template, make_response
from src.database import carregar_dados
from src.director import inicializar_llm, escolher_evento
from src.engine import GameEngine

app = Flask(__name__)

# --- CONFIGURAÇÃO ---
print(">>> SOBERANO: Inicializando módulos...")
DB = carregar_dados()
LLM = inicializar_llm()
print(">>> SOBERANO: Servidor pronto.")

# Armazena os jogos ativos em memória: { "session_id": GameEngineInstance }
# Nota: Em produção real, usaria Redis ou Banco de Dados.
GAMES = {}

def get_game():
    """Recupera ou cria a instância do jogo baseada no cookie do usuário."""
    user_id = request.cookies.get('soberano_session')
    
    if not user_id or user_id not in GAMES:
        # Se não existe sessão, cria uma nova
        new_id = str(uuid.uuid4())
        GAMES[new_id] = GameEngine(DB)
        return GAMES[new_id], new_id
    
    return GAMES[user_id], user_id

# --- ROTAS ---

@app.route('/')
def index():
    game, user_id = get_game()
    resp = make_response(render_template('index.html'))
    # Define cookie para identificar o jogador (dura até fechar o navegador)
    resp.set_cookie('soberano_session', user_id)
    return resp

@app.route('/get_estado')
def get_estado():
    game, _ = get_game()
    return jsonify(game.get_view_data())

@app.route('/passar_turno', methods=['POST'])
def passar_turno():
    game, _ = get_game()
    # Agora passamos a instância do jogo para o diretor usar os dados corretos
    resultado = game.processar_turno(LLM, escolher_evento)
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
    # Threaded=True ajuda a evitar bloqueios se múltiplos usuários jogarem
    app.run(debug=True, port=5000, threaded=True)