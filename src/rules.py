# src/rules.py
class RuleEngine:
    """
    Camada 1: Filtros Determinísticos (Hard Constraints).
    Impede que a IA sugira eventos impossíveis para o estado atual.
    """
    
    @staticmethod
    def filtrar_viaveis(lista_eventos, gamestate):
        s = gamestate['stats']
        ultimos = gamestate.get('ultimos_temas', [])
        viaveis = []

        # Detecção de Estado Crítico (Edge Case)
        is_falido = s['tesouro'] < 15
        is_anarquia = s['estabilidade'] < 15

        for ev in lista_eventos:
            tema = ev.get('tema', 'geral')

            # 1. REGRA DE SOBREVIVÊNCIA
            # Se o reino está em colapso, bloqueia eventos de luxo (hubris)
            if (is_falido or is_anarquia) and tema == 'hubris':
                continue 

            # 2. REGRA DE RECURSOS (Lógica Rígida)
            if tema == 'hubris' and s['tesouro'] < 60:
                continue
            if tema == 'desespero' and s['tesouro'] > 50:
                continue
            
            # 3. ANTI-REPETIÇÃO (Cooldown de 2 turnos)
            # 'game_over' e 'gestao' (eventos genéricos) furam o bloqueio
            if ultimos and tema not in ['game_over', 'gestao']:
                if tema in ultimos[-2:]:
                    continue

            # 4. GATILHOS SEMÂNTICOS
            # Se o evento exige tags específicas (ex: precisa ser 'tirano')
            reqs = ev.get('gatilho_semantico', [])
            if reqs:
                # CORREÇÃO ITEM 1:
                # Agora usa diretamente as tags já calculadas pela engine.py
                # Isso garante que Regras e UI vejam a mesma realidade.
                tags_atuais = gamestate.get('tags_estado', []) + gamestate.get('tags_reputacao', [])
                
                # Se não tem NENHUMA das tags exigidas
                if not any(r in tags_atuais for r in reqs):
                    # Se for um evento muito dramático, bloqueia. 
                    # Se for evento menor (<80 drama), deixa passar aleatoriamente (10% de chance)
                    if ev.get('peso_drama', 0) >= 80:
                        continue

            viaveis.append(ev)
        
        return viaveis
