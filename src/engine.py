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
            "tags_reputacao": [],  # Histórico (Memória Permanente)
            "tags_estado": [],     # Estado Atual (Dinâmico)
            "memoria_decisoes": [], 
            "log": ["O Diretor: 'A história começa...'"],
            "ultimo_evento": None,
            "game_over": False,
            "historico_stats": []
        }
        
        # INICIALIZAÇÃO CRÍTICA:
        # Aplica as tags das políticas iniciais como reputação base
        for pid in self.state['politicas_ativas']:
            pol = next((p for p in self.db['politicas'] if p['id'] == pid), None)
            if pol and 'tags_permanentes' in pol:
                self.state['tags_reputacao'].extend(pol['tags_permanentes'])
        
        self.atualizar_tags()

    def _aplicar_limites(self, valor):
        return max(0, min(100, valor))

    def atualizar_tags(self):
        """Gera a 'Ficha do Personagem' para a LLM."""
        s = self.state['stats']
        tags_est = []
        
        # Tags de Estado (Refletem os números atuais)
        if s['tesouro'] > 75: tags_est.append("midas")
        elif s['tesouro'] < 25: tags_est.extend(["falido", "pobre"])
        
        if s['militar'] > 75: tags_est.append("espartano")
        elif s['militar'] < 25: tags_est.append("vulneravel")
        
        if s['popularidade'] < 25: tags_est.extend(["impopular", "odiado"])
        elif s['popularidade'] > 75: tags_est.append("amado")
        
        if s['estabilidade'] < 25: tags_est.append("caos")
        
        self.state['tags_estado'] = tags_est
        
        # Retorna combinação para a UI
        return list(set(tags_est + self.state['tags_reputacao']))

    # --- FUNÇÃO RESTAURADA ---
    def _checar_game_over(self):
        s = self.state['stats']
        causa = None
        
        if s['estabilidade'] <= 0: causa = "Anarquia total. O reino colapsou em guerra civil."
        elif s['popularidade'] <= 0: causa = "Revolução popular. A guilhotina aguarda."
        elif s['militar'] <= 0: causa = "Conquista externa. O reino é agora uma colônia."
        elif s['tesouro'] <= 0 and s['militar'] < 20: causa = "Estado falido. Os mercenários saquearam o palácio."

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

    def get_view_data(self):
        evt = self.state['ultimo_evento']
        
        # Bloqueio de Eventos (por falta de recursos)
        if evt and evt['id'] != 99999:
            for op in evt['opcoes']:
                op['bloqueado'] = False
                op['motivo_bloqueio'] = ""
                custos = {k: v for k, v in op.get('efeito', {}).items() if v < 0}
                for stat, custo in custos.items():
                    if self.state['stats'].get(stat, 0) + custo < 0:
                        op['bloqueado'] = True
                        op['motivo_bloqueio'] = f"Requer {abs(custo)} {stat.capitalize()}"
        
        # Visualização de Políticas
        politicas_view = {}
        for pol in self.db['politicas']:
            cat = pol.get('categoria', 'outros').capitalize()
            if cat not in politicas_view: politicas_view[cat] = []
            
            p_data = pol.copy()
            p_data['ativa'] = pol['id'] in self.state['politicas_ativas']
            
            turnos = self.state['politicas_bloqueadas'].get(pol['id'], 0)
            p_data['bloqueada'] = turnos > 0
            p_data['turnos_bloqueio'] = turnos
            
            p_data['clicavel'] = True
            motivos = []
            
            # Custo de Estabilidade (INÉRCIA POLÍTICA)
            custo_estab = 10
            
            # Penalidade de Incoerência Narrativa (A IA Julga)
            if 'aversao' in pol:
                conflitos_alma = [t for t in self.state['tags_reputacao'] if t in pol['aversao']]
                if conflitos_alma:
                    custo_estab *= 2
                    motivos.append(f"Contra sua natureza ({', '.join(conflitos_alma)})")

            # Verifica se tem estabilidade para aguentar o tranco
            if self.state['stats']['estabilidade'] < custo_estab:
                motivos.append(f"Reino muito instável (-{custo_estab} Estab.)")
                p_data['clicavel'] = False
            else:
                p_data['custo_estabilidade'] = custo_estab

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
            
            if not p_data['ativa']:
                custo_ativ = pol.get('custo_ativacao', {})
                for k, v in custo_ativ.items():
                    if self.state['stats'].get(k, 0) + v < 0:
                        motivos.append(f"Custo: {abs(v)} {k}")
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
            "tags": list(set(self.state['tags_reputacao'] + self.state['tags_estado']))
        }

    def processar_turno(self, llm_instance, diretor_func):
        if self.state['game_over']: return {"status": "game_over"}

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

        # O Diretor agora recebe o estado com a MEMÓRIA NARRATIVA
        evento = diretor_func(llm_instance, self.state, self.db['eventos'])
        self.state['ultimo_evento'] = evento
        self.state['log'].append(f"--- Ano {self.state['turno']} ---")
        
        # AQUI ESTAVA O ERRO: Chamava a função, mas ela não existia
        if self._checar_game_over(): 
            return {"status": "game_over"}

        return {"status": "ok"}

    def resolver_evento(self, evento_id, opcao_id):
        if str(evento_id) == "99999" or opcao_id == "RESET":
            self.__init__(self.db)
            return {"status": "reset"}

        ev = None
        if self.state['ultimo_evento'] and str(self.state['ultimo_evento']['id']) == str(evento_id):
            ev = self.state['ultimo_evento']
        else:
            ev = next((e for e in self.db['eventos'] if str(e['id']) == str(evento_id)), None)

        if ev:
            op = next((o for o in ev['opcoes'] if o['id'] == opcao_id), None)
            if op:
                # Verifica custos
                efeitos = op.get('efeito', {})
                for k, v in efeitos.items():
                    if v < 0:
                        atual = self.state['stats'].get(k, 0)
                        if atual + v < 0:
                            return {"status": "erro", "msg": f"Recursos insuficientes: {k}"}

                # Aplica efeitos
                for k, v in efeitos.items():
                    if k in self.state['stats']:
                        self.state['stats'][k] = self._aplicar_limites(self.state['stats'][k] + v)

                # TAGS PERMANENTES (A Alma do Rei)
                tags_novas = []
                if 'tags_efeito' in op:
                    for tag in op['tags_efeito']:
                        if tag not in self.state['tags_reputacao']:
                            self.state['tags_reputacao'].append(tag)
                            tags_novas.append(tag)
                
                tags_str = f" [{', '.join(tags_novas)}]" if tags_novas else ""
                
                # MEMÓRIA NARRATIVA
                resumo_acao = f"Ano {self.state['turno']}: Diante de '{ev['titulo']}', escolheu '{op['texto']}'{tags_str}."
                self.state['memoria_decisoes'].append(resumo_acao)
                if len(self.state['memoria_decisoes']) > 12:
                    self.state['memoria_decisoes'].pop(0)

                self.state['log'].append(f"Decisão: {op['texto']} -> {op.get('resposta', 'Feito.')}")
                
                self.atualizar_tags()
                self._checar_game_over()
        
        self.state['ultimo_evento'] = None
        return {"status": "ok"}

    def toggle_politica(self, pid):
        if self.state['game_over']: return {"erro": "Jogo acabou"}, 400

        pol = next((p for p in self.db['politicas'] if p['id'] == pid), None)
        if not pol: return {"erro": "Lei desconhecida"}, 400

        # CÁLCULO DE CUSTO POLÍTICO
        custo_base = 10
        if 'aversao' in pol:
            conflitos = [t for t in self.state['tags_reputacao'] if t in pol['aversao']]
            if conflitos:
                custo_base *= 2
        
        if self.state['stats']['estabilidade'] < custo_base:
             return {"erro": f"Reino instável demais ({custo_base} necessário)"}, 400

        msg = ""
        if pid in self.state['politicas_ativas']:
            if self.state['politicas_bloqueadas'].get(pid, 0) > 0:
                return {"erro": "Bloqueada recentemente"}, 400
            self.state['politicas_ativas'].remove(pid)
            msg = f"Lei Revogada: {pol['nome']}"
        else:
            custo = pol.get('custo_ativacao', {})
            for k, v in custo.items():
                if self.state['stats'].get(k, 0) + v < 0:
                    return {"erro": f"Recurso insuficiente: {k}"}, 400
            
            if 'incompativel_com' in pol:
                for i in pol['incompativel_com']:
                    if i in self.state['politicas_ativas']:
                        return {"erro": "Incompatível com lei vigente"}, 400

            for k, v in custo.items():
                self.state['stats'][k] = self._aplicar_limites(self.state['stats'][k] + v)
            
            self.state['politicas_ativas'].append(pid)
            self.state['politicas_bloqueadas'][pid] = self.config.get('turnos_bloqueio_padrao', 8)
            
            # APLICA TAGS PERMANENTES DA POLÍTICA
            if 'tags_permanentes' in pol:
                for tag in pol['tags_permanentes']:
                    if tag not in self.state['tags_reputacao']:
                        self.state['tags_reputacao'].append(tag)
            
            msg = f"Promulgada: {pol['nome']}"
            
        # PAGA O PREÇO POLÍTICO
        self.state['stats']['estabilidade'] -= custo_base
        self.state['memoria_decisoes'].append(f"Ano {self.state['turno']}: {msg}")
        self.state['log'].append(msg)
        
        self.atualizar_tags()
        return {"status": "ok", "msg": f"{msg} (-{custo_base} Estabilidade)"}, 200