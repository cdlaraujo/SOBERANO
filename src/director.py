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
        print(f">>> Director Init: {len(self.todos_eventos)} eventos na memória.")
    
    def escolher_evento(self, llm_instance, gamestate):
        """
        Recebe a instância da LLM e o estado do jogo.
        Retorna um dicionário de evento.
        """
        
        # 1. CAMADA DE REGRAS
        # O gamestate já vem preparado pela engine com as tags corretas
        candidatos = RuleEngine.filtrar_viaveis(self.todos_eventos, gamestate)
        print(f">>> [RULES] {len(candidatos)} eventos viáveis.")

        if not candidatos:
            # Fallback extremo se as regras matarem tudo (ex: todos eventos são 'hubris' e rei está 'pobre')
            print(">>> [ALERTA] Nenhum evento viável nas regras. Sorteando qualquer um.")
            return random.choice(self.todos_eventos)

        escolhido = None

        # 2. CAMADA DE IA
        if llm_instance and len(candidatos) > 1:
            pool_ia = random.sample(candidatos, min(5, len(candidatos)))
            engine = LLMDecisionEngine(llm_instance)
            escolhido = engine.selecionar_evento(pool_ia, gamestate)

        # 3. FALLBACK / DRAMA
        if not escolhido:
            # Prioriza eventos com maior peso dramático
            candidatos.sort(key=lambda x: x.get('peso_drama', 50), reverse=True)
            # Pequena aleatoriedade entre os top 3 para não ficar monótono
            top_3 = candidatos[:3]
            escolhido = random.choice(top_3)

        print(f">>> Evento Selecionado: {escolhido['titulo']}")
        return escolhido