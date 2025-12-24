# src/inference.py
import re
from src.prompts import DIRECTOR_THOUGHT_PROCESS

class LLMDecisionEngine:
    """
    Camada 3: Motor de Decisão Neural.
    Gerencia a chamada à LLM e extrai a resposta com segurança.
    """
    def __init__(self, llm_instance):
        self.llm = llm_instance

    def selecionar_evento(self, candidatos, gamestate):
        """
        Usa a LLM para ranquear os eventos. Retorna None se falhar.
        """
        if not self.llm or not candidatos:
            return None

        # Prepara contexto
        tags = gamestate.get('tags_reputacao', [])
        stats_str = ", ".join([f"{k}:{v}" for k,v in gamestate['stats'].items()])
        
        # Formata lista de opções
        lista_fmt = "\n".join([
            f"#{i+1} [Tema: {ev.get('tema','geral').upper()}] {ev['titulo']}" 
            for i, ev in enumerate(candidatos)
        ])

        # Preenche o template
        prompt = DIRECTOR_THOUGHT_PROCESS.format(
            player_tags=", ".join(tags) if tags else "Neutro",
            stats_summary=stats_str,
            momentum="Normal", # Pode ser melhorado depois com dados reais
            event_list=lista_fmt
        )

        try:
            # Configuração conservadora para garantir obediência
            output = self.llm(
                prompt,
                max_tokens=150, # Espaço para o "Raciocínio"
                temperature=0.3,
                stop=["###", "Human:", "User:"],
                echo=False
            )
            text = output['choices'][0]['text']
            print(f">>> PENSAMENTO DA IA:\n{text.strip()}")

            return self._extrair_decisao(text, candidatos)

        except Exception as e:
            print(f">>> ERRO NA INFERÊNCIA: {e}")
            return None

    def _extrair_decisao(self, text, candidatos):
        """Busca o número da escolha no texto gerado."""
        # 1. Tenta achar padrão explícito "Escolha: #1"
        match = re.search(r'Escolha:.*?#?(\d+)', text, re.IGNORECASE)
        
        # 2. Se falhar, procura o último número mencionado no texto
        if not match:
            numeros = re.findall(r'\b(\d+)\b', text)
            if numeros:
                match = type('obj', (object,), {'group': lambda x: numeros[-1]})

        if match:
            try:
                idx = int(match.group(1)) - 1
                if 0 <= idx < len(candidatos):
                    return candidatos[idx]
            except:
                pass
        
        return None