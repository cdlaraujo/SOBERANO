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
            
            # CORREÇÃO 1: Separação de Tags
            "tags_eventos": [],    # Tags ganhas em decisões (Permanentes)
            "tags_estado": [],     # Tags calculadas dos stats (Dinâmicas)
            # 'tags_reputacao' agora será uma propriedade calculada, não armazenada pura
            
            "memoria_decisoes": [], 
            "log": ["O Diretor: 'A história começa...'"],
            "ultimo_evento": None,
            "game_over": False,
            "historico_stats": []
        }
        
        self.atualizar_tags()

    def _aplicar_limites(self, valor):
        """Garante a regra estrita: Ouro e stats sempre entre 0 e 100."""
        return max(0, min(100, valor))

    def atualizar_tags(self):
        """Recalcula todas as tags baseadas no estado atual."""
        s = self.state['stats']
        tags_est = []
        
        # 1. Tags Numéricas (Estado)
        if s['tesouro'] > 75: tags_est.extend(["midas", "rico"])
        elif s['tesouro'] < 10: tags_est.extend(["falido", "pobre"])
        elif s['tesouro'] < 25: tags_est.append("pobre")
        
        if s['militar'] > 75: tags_est.append("espartano")
        elif s['militar'] < 25: tags_est.append("vulneravel")
        
        if s['popularidade'] < 25: tags_est.extend(["impopular", "odiado", "opressor"])
        elif s['popularidade'] > 75: tags_est.append("amado")
        
        if s['estabilidade'] < 25: tags_est.append("caos")
        
        self.state['tags_estado'] = tags_est

    def get_tags_reputacao(self):
        """
        Combina tags de Eventos (Histórico) + Tags de Leis Ativas.
        Isso resolve o bug da 'Memória Eterna' ao revogar leis.
        """
        tags_leis = []
        for pid in self.state['politicas_ativas']:
            pol = next((p for p in self.db['politicas'] if p['id'] == pid), None)
            if pol and 'tags_permanentes' in pol:
                tags_leis.extend(pol['tags_permanentes'])
        
        # Retorna lista única sem duplicatas
        return list(set(self.state['tags_eventos'] + tags_leis))

    def get_view_data(self):
        evt = self.state['ultimo_evento']
        
        # Lógica de Bloqueio de Opções
        if evt and evt['id'] != 99999:
            opcoes_bloqueadas = 0
            total_opcoes = len(evt['opcoes'])

            for op in evt['opcoes']:
                op['bloqueado'] = False
                op['motivo_bloqueio'] = ""
                custos = {k: v for k, v in op.get('efeito', {}).items() if v < 0}
                
                for stat, custo in custos.items():
                    # Verifica se o jogador tem saldo (respeitando o limite 0)
                    if self.state['stats'].get(stat, 0) + custo < 0:
                        op['bloqueado'] = True
                        op['motivo_bloqueio'] = f"Requer {abs(custo)} {stat.capitalize()}"
                
                if op['bloqueado']: opcoes_bloqueadas += 1

            # CORREÇÃO 2: Anti-Softlock
            # Se TODAS as opções estiverem bloqueadas (ex: tem 0 ouro e tudo custa ouro),
            # Injeta uma opção de fuga para o jogo não travar.
            if opcoes_bloqueadas == total_opcoes:
                evt['opcoes'].append({
                    "id": "COLLAPSE",
                    "texto": "[SEM RECURSOS] O governo paralisa...",
                    "bloqueado": False,
                    "efeito": {"estabilidade": -15, "popularidade": -10},
                    "motivo_bloqueio": "Única saída disponível"
                })

        # Visualização de Políticas (Mesma lógica corrigida anterior)
        politicas_view = {}
        tags_at = self.get_tags_reputacao() # Usa o getter corrigido

        for pol in self.db['politicas']:
            cat = pol.get('categoria', 'outros').capitalize()
            if cat not in politicas_view: politicas_view[cat] = []
            
            p_data = pol.copy()
            p_data['ativa'] = pol['id'] in self.state['politicas_ativas']
            p_data['turnos_bloqueio'] = self.state['politicas_bloqueadas'].get(pol['id'], 0)
            p_data['bloqueada'] = p_data['turnos_bloqueio'] > 0
            p_data['clicavel'] = True
            
            motivos = []
            custo_estab = 10
            
            # Custo extra por incoerência narrativa
            if 'aversao' in pol:
                if any(t in pol['aversao'] for t in tags_at):
                    custo_estab *= 2
                    motivos.append("Contra sua natureza")

            if self.state['stats']['estabilidade'] < custo_estab:
                motivos.append(f"Instável demais (-{custo_estab} Estab.)")
                p_data['clicavel'] = False
            else:
                p_data['custo_estabilidade'] = custo_estab

            if not p_data['ativa']:
                # Verifica custos de ativação
                custo_ativ = pol.get('custo_ativacao', {})
                for k, v in custo_ativ.items():
                    if self.state['stats'].get(k, 0) + v < 0:
                        motivos.append(f"Falta {abs(v)} {k}")
                        p_data['clicavel'] = False
            
            # Verifica incompativeis
            if 'incompativel_com' in pol:
                if any(i in self.state['politicas_ativas'] for i in pol['incompativel_com']):
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
            "tags": list(set(tags_at + self.state['tags_estado']))
        }

    def processar_turno(self, llm_instance, director_obj):
        if self.state['game_over']: return {"status": "game_over"}

        # Histórico
        self.state['historico_stats'].append(self.state['stats'].copy())
        if len(self.state['historico_stats']) > 5: self.state['historico_stats'].pop(0)

        self.state['turno'] += 1
        
        # Efeitos Passivos
        for pid in self.state['politicas_ativas']:
            pol = next((p for p in self.db['politicas'] if p['id'] == pid), None)
            if pol:
                for k, v in pol.get('efeito_passivo', {}).items():
                    if k in self.state['stats']:
                        self.state['stats'][k] = self._aplicar_limites(self.state['stats'][k] + v)

        # Cooldowns
        novos_bloq = {}
        for k, v in self.state['politicas_bloqueadas'].items():
            if v > 1: novos_bloq[k] = v - 1
        self.state['politicas_bloqueadas'] = novos_bloq

        self.atualizar_tags()

        # Chama o Diretor (passando o objeto instanciado, não função estática)
        # Preparamos o gamestate injetando as tags calculadas corretamente
        gamestate_snapshot = self.state.copy()
        gamestate_snapshot['tags_reputacao'] = self.get_tags_reputacao()
        
        evento = director_obj.escolher_evento(llm_instance, gamestate_snapshot)
        
        self.state['ultimo_evento'] = evento
        self.state['log'].append(f"--- Ano {self.state['turno']} ---")
        
        if self._checar_game_over(): 
            return {"status": "game_over"}

        return {"status": "ok"}

    def resolver_evento(self, evento_id, opcao_id):
        if str(evento_id) == "99999" or opcao_id == "RESET":
            self.__init__(self.db)
            return {"status": "reset"}

        # Tratamento da Opção de Colapso (Safety Valve)
        if opcao_id == "COLLAPSE":
            self.state['stats']['estabilidade'] = self._aplicar_limites(self.state['stats']['estabilidade'] - 15)
            self.state['stats']['popularidade'] = self._aplicar_limites(self.state['stats']['popularidade'] - 10)
            self.state['log'].append("Decisão: O governo não conseguiu agir. O caos aumenta.")
            self.state['ultimo_evento'] = None
            self._checar_game_over()
            return {"status": "ok"}

        ev = None
        if self.state['ultimo_evento'] and str(self.state['ultimo_evento']['id']) == str(evento_id):
            ev = self.state['ultimo_evento']
        else:
            # Fallback (não deveria acontecer em fluxo normal)
            ev = next((e for e in self.db['eventos'] if str(e['id']) == str(evento_id)), None)

        if ev:
            op = next((o for o in ev['opcoes'] if o['id'] == opcao_id), None)
            if op:
                efeitos = op.get('efeito', {})
                # Validação de Recursos (Double Check)
                for k, v in efeitos.items():
                    if v < 0:
                        atual = self.state['stats'].get(k, 0)
                        if atual + v < 0:
                            return {"status": "erro", "msg": f"Recursos insuficientes: {k}"}

                # Aplica
                for k, v in efeitos.items():
                    if k in self.state['stats']:
                        self.state['stats'][k] = self._aplicar_limites(self.state['stats'][k] + v)

                # CORREÇÃO 1: Tags de Eventos vão para lista separada
                tags_novas = []
                if 'tags_efeito' in op:
                    for tag in op['tags_efeito']:
                        if tag not in self.state['tags_eventos']:
                            self.state['tags_eventos'].append(tag)
                            tags_novas.append(tag)
                
                tags_str = f" [{', '.join(tags_novas)}]" if tags_novas else ""
                self.state['memoria_decisoes'].append(f"Ano {self.state['turno']}: Escolheu '{op['texto']}' em '{ev['titulo']}'{tags_str}.")
                if len(self.state['memoria_decisoes']) > 12: self.state['memoria_decisoes'].pop(0)

                self.state['log'].append(f"Decisão: {op['texto']}")
                self.atualizar_tags()
                self._checar_game_over()
        
        self.state['ultimo_evento'] = None
        return {"status": "ok"}
    
    def _checar_game_over(self):
        s = self.state['stats']
        causa = None
        
        if s['estabilidade'] <= 0: causa = "Anarquia total. O reino colapsou."
        elif s['popularidade'] <= 0: causa = "Revolução popular. A guilhotina aguarda."
        elif s['militar'] <= 0: causa = "Conquista externa."
        # Mantemos a lógica original de falência + fraqueza militar
        elif s['tesouro'] <= 0 and s['militar'] < 20: causa = "Estado falido e indefeso."

        if causa and not self.state['game_over']:
            self.state['game_over'] = True
            self.state['log'].append(f"--- FIM DA LINHA: {causa} ---")
            
            evt_morte = {
                "id": 99999,
                "titulo": "O FIM DA DINASTIA",
                "texto": causa,
                "tema": "game_over",
                "opcoes": [{"id": "RESET", "texto": "Começar Nova História", "efeito": {}, "resposta": "..."}]
            }
            self.state['ultimo_evento'] = evt_morte
            return True
        return False

    def toggle_politica(self, pid):
        # Lógica simplificada pois get_view_data já faz validação pesada
        if self.state['game_over']: return {"erro": "Fim de jogo"}, 400
        
        pol = next((p for p in self.db['politicas'] if p['id'] == pid), None)
        if not pol: return {"erro": "Lei inválida"}, 400
        
        tags_at = self.get_tags_reputacao()
        custo_base = 10
        if 'aversao' in pol and any(t in pol['aversao'] for t in tags_at):
            custo_base *= 2
            
        if self.state['stats']['estabilidade'] < custo_base:
            return {"erro": "Estabilidade insuficiente"}, 400

        msg = ""
        if pid in self.state['politicas_ativas']:
            # REVOGAR
            self.state['politicas_ativas'].remove(pid)
            # Obs: As tags somem automaticamente no próximo get_tags_reputacao()
            # pois ele lê de politicas_ativas
            msg = f"Revogada: {pol['nome']}"
        else:
            # PROMULGAR
            # Valida custo
            custo = pol.get('custo_ativacao', {})
            for k, v in custo.items():
                if self.state['stats'].get(k, 0) + v < 0:
                     return {"erro": f"Falta {k}"}, 400
            
            # Aplica custo
            for k, v in custo.items():
                self.state['stats'][k] = self._aplicar_limites(self.state['stats'][k] + v)
                
            self.state['politicas_ativas'].append(pid)
            self.state['politicas_bloqueadas'][pid] = self.config.get('turnos_bloqueio_padrao', 8)
            msg = f"Promulgada: {pol['nome']}"

        self.state['stats']['estabilidade'] -= custo_base
        self.state['log'].append(msg)
        self.atualizar_tags()
        
        return {"status": "ok", "msg": msg}, 200