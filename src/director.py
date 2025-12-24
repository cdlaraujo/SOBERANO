import random
import re
import glob

# Tenta carregar a biblioteca da IA
try:
    from llama_cpp import Llama
    
    def inicializar_llm():
        """Busca modelo .gguf e inicia a IA."""
        model_files = glob.glob("*.gguf")
        if model_files:
            print(f">>> CARREGANDO MODELO: {model_files[0]} ...")
            return Llama(model_path=model_files[0], n_ctx=2048, n_gpu_layers=-1, verbose=False)
        print(">>> NENHUM MODELO ENCONTRADO. MODO LOBOTOMIA ATIVADO.")
        return None

except ImportError:
    print(">>> LLAMA_CPP NÃO INSTALADO. MODO LOBOTOMIA ATIVADO.")
    def inicializar_llm(): 
        return None


class DirectorInteligente:
    """Sistema de seleção de eventos em 3 camadas."""
    
    def __init__(self, lista_eventos):
        self.todos_eventos = lista_eventos
        self.eventos_por_tema = self._agrupar_por_tema()
        print(f">>> Director: {len(self.todos_eventos)} eventos carregados")
        print(f">>> Temas disponíveis: {list(self.eventos_por_tema.keys())}")
    
    def _agrupar_por_tema(self):
        """Organiza eventos por tema para busca rápida."""
        por_tema = {}
        for ev in self.todos_eventos:
            tema = ev.get('tema', 'geral')
            if tema not in por_tema:
                por_tema[tema] = []
            por_tema[tema].append(ev)
        return por_tema
    
    def escolher_evento(self, llm, gamestate):
        """Pipeline completo de seleção."""
        
        # [CAMADA 1] Filtro Determinístico (1ms)
        viaveis = self._filtrar_eventos_viaveis(gamestate)
        print(f">>> [1] Filtro: {len(viaveis)}/{len(self.todos_eventos)} viáveis")
        
        if not viaveis:
            print(">>> ATENÇÃO: Nenhum evento viável! Usando fallback.")
            viaveis = random.sample(self.todos_eventos, min(5, len(self.todos_eventos)))
        
        # [CAMADA 2] Retrieval por Relevância (5ms)
        candidatos = self._retrieve_top_candidatos(viaveis, gamestate, n=5)
        print(f">>> [2] Retrieval: {[c['titulo'][:30] for c in candidatos]}")
        
        # [CAMADA 3] Ranking LLM (500ms)
        if llm and len(candidatos) > 1:
            escolhido = self._ranking_llm(llm, candidatos, gamestate)
        else:
            escolhido = candidatos[0]
        
        print(f">>> [3] Escolhido: {escolhido['titulo']}")
        
        # Atualiza histórico
        self._atualizar_historico(gamestate, escolhido)
        
        return escolhido
    
    def _filtrar_eventos_viaveis(self, gamestate):
        """[CAMADA 1] Remove eventos impossíveis por regras hard."""
        s = gamestate['stats']
        tags_player = set(gamestate.get('tags_reputacao', []))
        ultimos_temas = gamestate.get('ultimos_temas', [])
        
        viaveis = []
        
        for ev in self.todos_eventos:
            # REGRA 1: Eventos de hubris só para ricos
            if ev['tema'] == 'hubris' and s['tesouro'] < 60:
                continue
            
            # REGRA 2: Eventos de desespero só para pobres/fracos
            if ev['tema'] == 'desespero' and s['tesouro'] > 60:
                continue
            
            # REGRA 3: Eventos de guerra precisam de militar extremo
            if ev['tema'] == 'guerra':
                if 40 <= s['militar'] <= 70:  # Zona neutra
                    continue
            
            # REGRA 4: Anti-repetição de tema (cooldown 3 turnos)
            if ultimos_temas and ev['tema'] in ultimos_temas[-3:]:
                continue
            
            # REGRA 5: Verifica gatilhos semânticos básicos
            gatilhos = ev.get('gatilho_semantico', [])
            if gatilhos:
                # Precisa ter pelo menos 1 match OU stats extremos
                tem_match = any(g in self._gerar_tags_estado(s) for g in gatilhos)
                stats_extremos = any(v < 25 or v > 75 for v in s.values())
                
                if not (tem_match or stats_extremos):
                    continue
            
            viaveis.append(ev)
        
        return viaveis
    
    def _gerar_tags_estado(self, stats):
        """Gera tags dinâmicas baseadas em stats (para filtro)."""
        tags = []
        
        if stats['tesouro'] > 75: tags.extend(['midas', 'rico'])
        elif stats['tesouro'] < 25: tags.extend(['falido', 'pobre'])
        
        if stats['militar'] > 75: tags.append('espartano')
        elif stats['militar'] < 25: tags.append('vulneravel')
        
        if stats['popularidade'] < 25: tags.extend(['impopular', 'opressor'])
        elif stats['popularidade'] > 75: tags.append('amado')
        
        if stats['estabilidade'] < 25: tags.append('instavel')
        
        return tags
    
    def _retrieve_top_candidatos(self, eventos, gamestate, n=5):
        """[CAMADA 2] Calcula score de relevância e retorna top N."""
        scored = []
        
        for ev in eventos:
            score = self._calcular_relevancia(ev, gamestate)
            scored.append((ev, score))
        
        # Ordena por score decrescente
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Retorna top N eventos
        return [ev for ev, score in scored[:n]]
    
    def _calcular_relevancia(self, evento, gamestate):
        """Calcula score 0-100 multi-dimensional."""
        score = 0
        s = gamestate['stats']
        tags_player = set(gamestate.get('tags_reputacao', []))
        tags_estado = set(self._gerar_tags_estado(s))
        
        # === DIMENSÃO 1: Match de Tags (0-40 pts) ===
        tags_ev = set(evento.get('gatilho_semantico', []))
        
        # Match com tags de reputação (histórico)
        match_reputacao = len(tags_player & tags_ev)
        score += match_reputacao * 15
        
        # Match com tags de estado atual
        match_estado = len(tags_estado & tags_ev)
        score += match_estado * 10
        
        # === DIMENSÃO 2: Peso Dramático Base (0-25 pts) ===
        peso_drama = evento.get('peso_drama', 50)
        score += (peso_drama / 100) * 25
        
        # === DIMENSÃO 3: Tensão por Stats Extremos (0-20 pts) ===
        extremidade = sum(1 for v in s.values() if v < 20 or v > 80)
        if peso_drama > 70:  # Eventos dramáticos brilham em crises
            score += extremidade * 4
        
        # === DIMENSÃO 4: Momentum Narrativo (0-15 pts) ===
        momentum = gamestate.get('momentum', {})
        tema = evento['tema']
        
        # Hubris quando ficando rico + impopular
        if tema == 'hubris':
            if momentum.get('tesouro') == 'subindo' and momentum.get('popularidade') == 'descendo':
                score += 15
        
        # Desespero quando caindo em múltiplas frentes
        if tema == 'desespero':
            quedas = sum(1 for v in momentum.values() if v == 'descendo')
            score += quedas * 5
        
        # Guerra quando militar oscilando
        if tema == 'guerra':
            if momentum.get('militar') in ['subindo', 'descendo']:
                score += 10
        
        return score
    
    def _ranking_llm(self, llm, candidatos, gamestate):
        """[CAMADA 3] LLM ranqueia os 5 finalistas."""
        
        # Prepara contexto ultra-compacto
        tags = gamestate.get('tags_reputacao', [])[:5]
        tags_str = ", ".join(tags) if tags else "neutro"
        
        # Lista compacta de eventos
        lista = "\n".join([
            f"{i+1}. {ev['titulo']}" 
            for i, ev in enumerate(candidatos)
        ])
        
        # Prompt minimalista
        prompt = f"""### RANK EVENTS
Player tags: {tags_str}

Events:
{lista}

Most dramatic (number only):"""

        try:
            output = llm(
                prompt, 
                max_tokens=3, 
                temperature=0.1, 
                stop=["\n", ".", " ", "because"],
                echo=False
            )
            
            resposta = output['choices'][0]['text'].strip()
            print(f">>> LLM respondeu: '{resposta}'")
            
            # Extrai número
            match = re.search(r'(\d+)', resposta)
            if match:
                idx = int(match.group(1)) - 1
                if 0 <= idx < len(candidatos):
                    return candidatos[idx]
            
        except Exception as e:
            print(f">>> Erro LLM: {e}")
        
        # Fallback: retorna o de maior score (primeiro da lista)
        print(">>> Usando fallback (score mais alto)")
        return candidatos[0]
    
    def _atualizar_historico(self, gamestate, evento):
        """Atualiza tracking de temas para anti-repetição."""
        if 'ultimos_temas' not in gamestate:
            gamestate['ultimos_temas'] = []
        
        gamestate['ultimos_temas'].append(evento['tema'])
        
        # Mantém apenas últimos 8 temas
        if len(gamestate['ultimos_temas']) > 8:
            gamestate['ultimos_temas'] = gamestate['ultimos_temas'][-8:]


def calcular_momentum(gamestate):
    """Detecta tendências nos stats dos últimos turnos."""
    historico = gamestate.get('historico_stats', [])
    
    if len(historico) < 3:
        return {}
    
    momentum = {}
    stats_atual = gamestate['stats']
    stats_antigo = historico[-3]  # 3 turnos atrás
    
    for stat in ['tesouro', 'militar', 'popularidade', 'estabilidade']:
        delta = stats_atual[stat] - stats_antigo[stat]
        
        if delta > 15:
            momentum[stat] = 'subindo'
        elif delta < -15:
            momentum[stat] = 'descendo'
        else:
            momentum[stat] = 'estavel'
    
    return momentum


# Função de compatibilidade com código antigo
def escolher_evento(llm, gamestate, lista_eventos):
    """Wrapper para manter compatibilidade com engine.py."""
    
    # Cria ou recupera instância do Director
    if not hasattr(escolher_evento, 'director'):
        escolher_evento.director = DirectorInteligente(lista_eventos)
    
    return escolher_evento.director.escolher_evento(llm, gamestate)