# src/rules.py

class RuleEngine:
    """
    Layer 1: Deterministic Filters (Hard Constraints).
    Prevents the AI from suggesting impossible events for the current state.
    """
    
    @staticmethod
    def filter_viable(event_list, gamestate):
        s = gamestate['stats']
        last_themes = gamestate.get('last_themes', [])
        viable = []

        # Critical State Detection (Edge Case)
        is_bankrupt = s['treasury'] < 15
        is_anarchy = s['stability'] < 15

        for ev in event_list:
            theme = ev.get('theme', 'general')

            # 1. SURVIVAL RULE
            # If the kingdom is collapsing, block luxury events (hubris)
            if (is_bankrupt or is_anarchy) and theme == 'hubris':
                continue 

            # 2. RESOURCE RULE (Rigid Logic)
            if theme == 'hubris' and s['treasury'] < 60:
                continue
            if theme == 'despair' and s['treasury'] > 50:
                continue
            
            # 3. ANTI-REPETITION (2 turn cooldown)
            # 'game_over' and 'management' (generic events) bypass block
            if last_themes and theme not in ['game_over', 'management']:
                if theme in last_themes[-2:]:
                    continue

            # 4. SEMANTIC TRIGGERS
            # If the event requires specific tags (e.g., needs to be 'tyrant')
            reqs = ev.get('semantic_trigger', [])
            if reqs:
                # REPAIR ITEM 1:
                # Now uses tags directly calculated by engine.py
                # This ensures Rules and UI see the same reality.
                current_tags = gamestate.get('state_tags', []) + gamestate.get('reputation_tags', [])
                
                # If it has NONE of the required tags
                if not any(r in current_tags for r in reqs):
                    # If it's a very dramatic event, block. 
                    # If it's a minor event (<80 drama), let it pass randomly (10% chance)
                    if ev.get('drama_weight', 0) >= 80:
                        continue

            viable.append(ev)
        
        return viable