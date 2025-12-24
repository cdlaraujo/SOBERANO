import random
import re
import glob

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
    def inicializar_llm(): return None


class DirectorInteligente:
    def __init__(self, lista_eventos):
        self.todos_eventos = lista_eventos
    
    def escolher_evento(self, llm, gamestate):
        # [CAMADA 1] Filtro
        viaveis = self._filtrar_eventos_viaveis(gamestate)
        
        # [CAMADA 1.5] Fallback para 'Gestão'
        # Se não houver eventos dramáticos viáveis, usamos eventos de gestão
        # para manter a narrativa a andar e acumular tags.
        if not viaveis:
            gestao = [e for e in self.todos_eventos if e.get('tema') == 'gestao']
            if gestao:
                return random.choice(gestao)
            else:
                return self.todos_eventos[0] # Último recurso
        
        # [CAMADA 2] Retrieval (Top 5)
        candidatos = self._retrieve_top_candidatos(viaveis, gamestate, n=5)
        
        # [CAMADA 3] LLM com MEMÓRIA
        if llm and len(candidatos) > 1:
            escolhido = self._ranking_llm(llm, candidatos, gamestate)
        else:
            escolhido = candidatos[0]
        
        self._atualizar_historico(gamestate, escolhido)
        return escolhido
    
    def _filtrar_eventos_viaveis(self, gamestate):
        s = gamestate['stats']
        ultimos_temas = gamestate.get('ultimos_temas', [])
        # Usa todas as tags (estado + reputação) para o filtro hard
        tags_totais = set(gamestate.get('tags_reputacao', []) + gamestate.get('tags_estado', []))
        
        viaveis = []
        for ev in self.todos_eventos:
            # Ignora gestão na busca principal
            if ev.get('tema') == 'gestao': continue

            gatilhos = ev.get('gatilho_semantico', [])
            if gatilhos:
                # Se o evento exige tags, o jogador tem de ter pelo menos uma
                tem_match = any(g in tags_totais for g in gatilhos)
                if not tem_match: continue 
            
            if ev['tema'] == 'hubris' and s['tesouro'] < 50: continue
            if ev['tema'] == 'desespero' and s['tesouro'] > 50: continue
            
            if ultimos_temas and ev['tema'] in ultimos_temas[-3:]: continue
            
            viaveis.append(ev)
        return viaveis
    
    def _retrieve_top_candidatos(self, eventos, gamestate, n=5):
        scored = []
        for ev in eventos:
            score = self._calcular_relevancia(ev, gamestate)
            scored.append((ev, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [ev for ev, score in scored[:n]]
    
    def _calcular_relevancia(self, evento, gamestate):
        score = 0
        tags_totais = set(gamestate.get('tags_reputacao', []) + gamestate.get('tags_estado', []))
        gatilhos = set(evento.get('gatilho_semantico', []))
        
        match = len(tags_totais & gatilhos)
        score += match * 20 
        score += (evento.get('peso_drama', 50) / 100) * 20
        return score
    
    def _ranking_llm(self, llm, candidatos, gamestate):
        memoria = gamestate.get('memoria_decisoes', [])[-8:] # Últimas 8 memórias
        historia_texto = "\n".join(memoria) if memoria else "O reinado começou recentemente."
        
        # Estrutura Tags
        reputacao = ", ".join(gamestate.get('tags_reputacao', ['Desconhecido']))
        estado_atual = ", ".join(gamestate.get('tags_estado', ['Estável']))
        
        lista = "\n".join([f"{i+1}. {ev['titulo']} (Tema: {ev['tema']})" for i, ev in enumerate(candidatos)])
        
        prompt = f"""### KINGDOM SIMULATOR
[PROFILE]
The King is known as: {reputacao}
Current Kingdom State: {estado_atual}

[RECENT HISTORY]
{historia_texto}

[PENDING EVENTS]
{lista}

[TASK]
Select the Event Number (1-5) that best challenges the King's current reputation or forces a difficult choice based on history.
Selection:"""

        try:
            output = llm(prompt, max_tokens=3, temperature=0.1, stop=["\n"], echo=False)
            resposta = output['choices'][0]['text'].strip()
            match = re.search(r'(\d+)', resposta)
            if match:
                idx = int(match.group(1)) - 1
                if 0 <= idx < len(candidatos):
                    return candidatos[idx]
        except Exception:
            pass
        return candidatos[0]
    
    def _atualizar_historico(self, gamestate, evento):
        if 'ultimos_temas' not in gamestate: gamestate['ultimos_temas'] = []
        gamestate['ultimos_temas'].append(evento['tema'])
        if len(gamestate['ultimos_temas']) > 8:
            gamestate['ultimos_temas'] = gamestate['ultimos_temas'][-8:]

def escolher_evento(llm, gamestate, lista_eventos):
    if not hasattr(escolher_evento, 'director'):
        escolher_evento.director = DirectorInteligente(lista_eventos)
    return escolher_evento.director.escolher_evento(llm, gamestate)