import random

class GameEngine:
    def __init__(self, db):
        self.db = db
        self.config = db.get('config', {})
        self.state = {
            "turno": 1,
            "stats": {
                "tesouro": 50, "militar": 50, "popularidade": 50, 
                "estabilidade": 50, "agricultura": 50, "comercio": 50
            },
            "politicas_ativas": ["servidao", "absolutismo"],
            "politicas_bloqueadas": {},
            "tags_reputacao": [],  # NOVO: Armazena tags acumuladas
            "log": ["O Diretor: 'A história começa...'"],
            "ultimo_evento": None,
            "game_over": False
        }

    def _aplicar_limites(self, valor):
        return max(0, min(100, valor))

    def _checar_game_over(self):
        s = self.state['stats']
        causa = None
        
        if s['estabilidade'] <= 0: causa = "Anarquia total. O palácio foi invadido."
        elif s['popularidade'] <= 0: causa = "Revolução popular. Sua cabeça está numa lança."
        elif s['militar'] <= 0: causa = "Invasão bárbara. O reino caiu."
        elif s['tesouro'] <= 0 and s['militar'] < 20: causa = "Golpe mercenário por falta de pagamento."

        if causa and not self.state['game_over']:
            self.state['game_over'] = True
            self.state['log'].append(f"--- FIM DE JOGO: {causa} ---")
            
            # Cria evento final forçado
            evt_morte = {
                "id": 99999,
                "titulo": "FIM DA DINASTIA",
                "texto": causa,
                "tema": "game_over",
                "opcoes": [{"id": "RESET", "texto": "Reiniciar a História", "efeito": {}, "resposta": "O tempo recomeça..."}]
            }
            self.state['ultimo_evento'] = evt_morte
            return True
        return False

    def _inferir_tags_semanticas(self):
        """Gera tags baseadas no estado atual do reino (visão da IA)."""
        s = self.state['stats']
        tags = []
        
        # Tags baseadas em stats extremos
        if s['tesouro'] > 80: tags.append("midas")
        elif s['tesouro'] < 20: tags.extend(["falido", "pobre"])
        
        if s['militar'] > 80: tags.append("espartano")
        elif s['militar'] < 30: tags.append("vulneravel")
        
        if s['popularidade'] < 30: tags.extend(["impopular", "opressor"])
        elif s['popularidade'] > 80: tags.append("amado")
        
        if s['estabilidade'] < 30: tags.append("instavel")
        elif s['estabilidade'] > 80: tags.append("estavel")
        
        # Tags baseadas em políticas
        if "teocracia" in self.state['politicas_ativas']: tags.extend(["fanatico", "devoto"])
        if "secularismo" in self.state['politicas_ativas']: tags.append("herege")
        if "absolutismo" in self.state['politicas_ativas']: tags.append("tirano")
        if "parlamentarismo" in self.state['politicas_ativas']: tags.append("fraco")
        if "livre_comercio" in self.state['politicas_ativas']: tags.extend(["mercador", "globalista"])
        if "lei_marcial" in self.state['politicas_ativas']: tags.append("opressor")
        if "mecenato" in self.state['politicas_ativas']: tags.append("culto")
        if "policia_secreta" in self.state['politicas_ativas']: tags.append("paranoico")
        if "isolacionismo" in self.state['politicas_ativas']: tags.append("xenofobo")
        
        # Tags de reputação histórica (acumuladas de eventos)
        tags.extend(self.state['tags_reputacao'])
        
        return list(set(tags))  # Remove duplicatas

    def get_view_data(self):
        """Prepara dados para o Frontend."""
        # Processa políticas para visualização
        politicas_view = {}
        for pol in self.db['politicas']:
            cat = pol.get('categoria', 'outros').capitalize()
            if cat not in politicas_view: politicas_view[cat] = []
            
            p_data = pol.copy()
            p_data['ativa'] = pol['id'] in self.state['politicas_ativas']
            
            turnos = self.state['politicas_bloqueadas'].get(pol['id'], 0)
            p_data['bloqueada'] = turnos > 0
            p_data['turnos_bloqueio'] = turnos
            
            # Validação de clique
            p_data['clicavel'] = True
            motivos = []
            
            if 'req_ativacao' in pol:
                faltam = [r for r in pol['req_ativacao'] if r not in self.state['politicas_ativas']]
                if faltam:
                    motivos.append("Requisito ausente")
                    p_data['clicavel'] = False
            
            if 'incompativel_com' in pol:
                conflito = [i for i in pol['incompativel_com'] if i in self.state['politicas_ativas']]
                if conflito:
                    motivos.append("Incompatível")
                    p_data['clicavel'] = False
            
            p_data['motivo_bloqueio'] = ", ".join(motivos)
            politicas_view[cat].append(p_data)

        return {
            "stats": self.state['stats'],
            "turno": self.state['turno'],
            "log": self.state['log'],
            "politicas": politicas_view,
            "evento_atual": self.state['ultimo_evento'],
            "game_over": self.state['game_over'],
            "tags": self._inferir_tags_semanticas()  # CORRIGIDO: Agora popula as tags
        }

    def processar_turno(self, llm_instance, diretor_func):
        if self.state['game_over']: return {"status": "game_over"}

        self.state['turno'] += 1
        
        # 1. Efeitos Passivos
        for pid in self.state['politicas_ativas']:
            pol = next((p for p in self.db['politicas'] if p['id'] == pid), None)
            if pol:
                for k, v in pol.get('efeito_passivo', {}).items():
                    if k in self.state['stats']:
                        self.state['stats'][k] = self._aplicar_limites(self.state['stats'][k] + v)

        # 2. Cooldowns
        novos_bloq = {}
        for k, v in self.state['politicas_bloqueadas'].items():
            if v > 1: novos_bloq[k] = v - 1
        self.state['politicas_bloqueadas'] = novos_bloq

        # 3. Escolha do Evento ANTES de checar morte (CORRIGIDO)
        evento = diretor_func(llm_instance, self.state, self.db['eventos'])
        self.state['ultimo_evento'] = evento
        self.state['log'].append(f"--- Ano {self.state['turno']} ---")
        
        # 4. Checa morte DEPOIS de atribuir evento (CORRIGIDO)
        if self._checar_game_over(): 
            return {"status": "game_over"}

        return {"status": "ok"}

    def resolver_evento(self, evento_id, opcao_id):
        # Reset Game
        if evento_id == "99999" or opcao_id == "RESET":
            self.__init__(self.db) # Reseta estado
            return {"status": "reset"}

        ev = next((e for e in self.db['eventos'] if str(e['id']) == str(evento_id)), None)
        if ev:
            op = next((o for o in ev['opcoes'] if o['id'] == opcao_id), None)
            if op:
                # Aplica efeitos
                desc_efeitos = []
                for k, v in op.get('efeito', {}).items():
                    if k in self.state['stats']:
                        self.state['stats'][k] = self._aplicar_limites(self.state['stats'][k] + v)
                        sinal = "+" if v > 0 else ""
                        desc_efeitos.append(f"{k.capitalize()} {sinal}{v}")
                
                # NOVO: Adiciona tags de reputação
                if 'tags_efeito' in op:
                    for tag in op['tags_efeito']:
                        if tag not in self.state['tags_reputacao']:
                            self.state['tags_reputacao'].append(tag)
                
                self.state['log'].append(f"Decisão: {op['texto']} -> {op.get('resposta', 'Feito.')}")
                
                # Checa morte pós-evento
                self._checar_game_over()
        
        self.state['ultimo_evento'] = None
        return {"status": "ok"}

    def toggle_politica(self, pid):
        if self.state['game_over']: return {"erro": "Jogo acabou"}, 400

        pol = next((p for p in self.db['politicas'] if p['id'] == pid), None)
        if not pol: return {"erro": "Lei desconhecida"}, 400

        if pid in self.state['politicas_ativas']:
            # Revogar
            if self.state['politicas_bloqueadas'].get(pid, 0) > 0:
                return {"erro": "Bloqueada recentemente"}, 400
            self.state['politicas_ativas'].remove(pid)
            self.state['log'].append(f"Revogada: {pol['nome']}")
        else:
            # Aprovar
            custo = pol.get('custo_ativacao', {})
            # Checa custo
            for k, v in custo.items():
                if self.state['stats'].get(k, 0) + v < 0:
                    return {"erro": f"Recurso insuficiente: {k}"}, 400
            
            # Checa incompatibilidade
            if 'incompativel_com' in pol:
                for i in pol['incompativel_com']:
                    if i in self.state['politicas_ativas']:
                        return {"erro": "Incompatível com lei vigente"}, 400

            # Aplica custo
            for k, v in custo.items():
                self.state['stats'][k] = self._aplicar_limites(self.state['stats'][k] + v)
            
            self.state['politicas_ativas'].append(pid)
            self.state['politicas_bloqueadas'][pid] = self.config.get('turnos_bloqueio_padrao', 8)
            self.state['log'].append(f"Promulgada: {pol['nome']}")
            
        return {"status": "ok"}, 200