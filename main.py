from flask import Flask, jsonify, request, render_template
from src.database import carregar_dados
from src.director import inicializar_llm, escolher_evento
from src.engine import GameEngine

app = Flask(__name__)

# --- INICIALIZAÇÃO ---
print(">>> SOBERANO: Inicializando módulos...")
DB = carregar_dados()
LLM = inicializar_llm()
GAME = GameEngine(DB)
print(">>> SOBERANO: Pronto para reinar.")

# --- ROTAS ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_estado')
def get_estado():
    return jsonify(GAME.get_view_data())

@app.route('/passar_turno', methods=['POST'])
def passar_turno():
    # Passa a função do diretor e a instância LLM para a engine usar quando necessário
    resultado = GAME.processar_turno(LLM, escolher_evento)
    return jsonify(resultado)

@app.route('/resolver_evento', methods=['POST'])
def resolver_evento():
    d = request.json
    resultado = GAME.resolver_evento(d.get('evento_id'), d.get('opcao_id'))
    return jsonify(resultado)

@app.route('/toggle_politica', methods=['POST'])
def toggle_politica():
    d = request.json
    msg, status = GAME.toggle_politica(d.get('id'))
    return jsonify(msg), status

if __name__ == '__main__':
    app.run(debug=True, port=5000)