# src/director.py
import random
import glob
from src.rules import RuleEngine
from src.inference import LLMDecisionEngine

# Tenta carregar a biblioteca da IA
try:
    from llama_cpp import Llama
    def inicializar_llm():
        """Busca modelo .gguf e inicia a IA."""
        model_files = glob.glob("*.gguf")
        if model_files:
            print(f">>> CARREGANDO MODELO: {model_files[0]} ...")
            return Llama(model_path=model_files[0], n_ctx=4096, n_gpu_layers=-1, verbose=False)
        print(">>> NENHUM MODELO ENCONTRADO.")
        return None
except ImportError:
    print(">>> LLAMA_CPP NÃO INSTALADO.")
    def inicializar_llm(): 
        return None


class DirectorInteligente:
    def __init__(self, lista_eventos):
        self.todos_eventos = lista_eventos
        print(f">>> Director v2: {len(self.todos_eventos)} eventos carregados")
    
    def escolher_evento(self, llm_instance, gamestate):
        """Pipeline Híbrido: Regras -> IA -> Fallback"""
        
        # 1. CAMADA DE REGRAS (Filtra o impossível)
        candidatos = RuleEngine.filtrar_viaveis(self.todos_eventos, gamestate)
        print(f">>> [RULES] {len(candidatos)} eventos viáveis.")

        # Se as regras removerem tudo (raro), usa fallback total
        if not candidatos:
            print(">>> [ALERTA] Nenhum evento viável. Usando aleatório.")
            return random.choice(self.todos_eventos)

        escolhido = None

        # 2. CAMADA DE IA (Pensa e Escolhe)
        # Só ativa se houver IA e houver mais de 1 opção
        if llm_instance and len(candidatos) > 1:
            # Limita a 5 opções para não confundir a IA
            pool_ia = random.sample(candidatos, min(5, len(candidatos)))
            
            engine = LLMDecisionEngine(llm_instance)
            escolhido = engine.selecionar_evento(pool_ia, gamestate)

        # 3. FALLBACK (Se IA falhar, não existir, ou escolher inválido)
        if not escolhido:
            if llm_instance: print(">>> [FALLBACK] IA falhou ou retornou inválido.")
            # Escolha baseada em 'peso_drama' + pequena aleatoriedade
            # Ordena por drama decrescente e pega um do top 3
            candidatos.sort(key=lambda x: x.get('peso_drama', 50), reverse=True)
            top_3 = candidatos[:3]
            escolhido = random.choice(top_3)

        print(f">>> Evento Selecionado: {escolhido['titulo']}")
        self._atualizar_historico(gamestate, escolhido)
        return escolhido

    def _atualizar_historico(self, gamestate, evento):
        """Mantém registro para evitar repetições."""
        if 'ultimos_temas' not in gamestate:
            gamestate['ultimos_temas'] = []
        
        gamestate['ultimos_temas'].append(evento['tema'])
        
        # Mantém histórico curto (últimos 4 são suficientes para cooldown)
        if len(gamestate['ultimos_temas']) > 4:
            gamestate['ultimos_temas'] = gamestate['ultimos_temas'][-4:]


# Função de compatibilidade (Interface usada pelo engine.py)
def escolher_evento(llm, gamestate, lista_eventos):
    if not hasattr(escolher_evento, 'director'):
        escolher_evento.director = DirectorInteligente(lista_eventos)
    
    return escolher_evento.director.escolher_evento(llm, gamestate)