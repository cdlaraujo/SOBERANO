# src/engine.py

import random

class GameEngine:
    def __init__(self, db):
        self.db = db
        self.config = db.get('config', {})
        self.state = {
            "turn": 1,
            "stats": {
                "treasury": 50, "military": 50, "popularity": 50, 
                "stability": 50, "agriculture": 50, "commerce": 50
            },
            "active_policies": ["serfdom", "absolutism"],
            "blocked_policies": {},
            
            # REPAIR 1: Tag Separation
            "event_tags": [],    # Tags gained from decisions (Permanent)
            "state_tags": [],    # Tags calculated from stats (Dynamic)
            # 'reputation_tags' will now be a calculated property, not stored pure
            
            "decision_memory": [], 
            "log": ["The Director: 'The history begins...'"],
            "last_event": None,
            "game_over": False,
            "stats_history": []
        }
        
        self.update_tags()

    def _apply_limits(self, value):
        """Ensures strict rule: Gold and stats always between 0 and 100."""
        return max(0, min(100, value))

    def update_tags(self):
        """Recalculates all tags based on current state."""
        s = self.state['stats']
        tags_st = []
        
        # 1. Numeric Tags (State)
        if s['treasury'] > 75: tags_st.extend(["midas", "rich"])
        elif s['treasury'] < 10: tags_st.extend(["bankrupt", "poor"])
        elif s['treasury'] < 25: tags_st.append("poor")
        
        if s['military'] > 75: tags_st.append("spartan")
        elif s['military'] < 25: tags_st.append("vulnerable")
        
        if s['popularity'] < 25: tags_st.extend(["unpopular", "hated", "oppressor"])
        elif s['popularity'] > 75: tags_st.append("beloved")
        
        if s['stability'] < 25: tags_st.append("chaos")
        
        self.state['state_tags'] = tags_st

    def get_reputation_tags(self):
        """
        Combines Event Tags (History) + Active Law Tags.
        This solves the 'Eternal Memory' bug when revoking laws.
        """
        law_tags = []
        for pid in self.state['active_policies']:
            pol = next((p for p in self.db['policies'] if p['id'] == pid), None)
            if pol and 'permanent_tags' in pol:
                law_tags.extend(pol['permanent_tags'])
        
        # Return unique list without duplicates
        return list(set(self.state['event_tags'] + law_tags))

    def get_view_data(self):
        evt = self.state['last_event']
        
        # Option Blocking Logic
        if evt and evt['id'] != 99999:
            options_blocked = 0
            total_options = len(evt['options'])

            for op in evt['options']:
                op['blocked'] = False
                op['block_reason'] = ""
                costs = {k: v for k, v in op.get('effect', {}).items() if v < 0}
                
                for stat, cost in costs.items():
                    # Check if player has balance (respecting 0 limit)
                    if self.state['stats'].get(stat, 0) + cost < 0:
                        op['blocked'] = True
                        op['block_reason'] = f"Requires {abs(cost)} {stat.capitalize()}"
                
                if op['blocked']: options_blocked += 1

            # REPAIR 2: Anti-Softlock
            # If ALL options are blocked (e.g. has 0 gold and everything costs gold),
            # Inject an escape option so game doesn't freeze.
            if options_blocked == total_options:
                evt['options'].append({
                    "id": "COLLAPSE",
                    "text": "[NO RESOURCES] The government paralyzes...",
                    "blocked": False,
                    "effect": {"stability": -15, "popularity": -10},
                    "block_reason": "Only available exit"
                })

        # Policies View (Same corrected logic as before)
        policies_view = {}
        tags_at = self.get_reputation_tags() # Use corrected getter

        for pol in self.db['policies']:
            cat = pol.get('category', 'others').capitalize()
            if cat not in policies_view: policies_view[cat] = []
            
            p_data = pol.copy()
            p_data['active'] = pol['id'] in self.state['active_policies']
            p_data['lock_turns'] = self.state['blocked_policies'].get(pol['id'], 0)
            p_data['blocked'] = p_data['lock_turns'] > 0
            p_data['clickable'] = True
            
            reasons = []
            cost_estab = 10
            
            # Extra cost for narrative incoherence
            if 'aversion' in pol:
                if any(t in pol['aversion'] for t in tags_at):
                    cost_estab *= 2
                    reasons.append("Against your nature")

            if self.state['stats']['stability'] < cost_estab:
                reasons.append(f"Too Unstable (-{cost_estab} Stab.)")
                p_data['clickable'] = False
            else:
                p_data['stability_cost'] = cost_estab

            if not p_data['active']:
                # Check activation costs
                cost_activ = pol.get('activation_cost', {})
                for k, v in cost_activ.items():
                    if self.state['stats'].get(k, 0) + v < 0:
                        reasons.append(f"Lacks {abs(v)} {k}")
                        p_data['clickable'] = False
            
            # Check incompatibilities
            if 'incompatible_with' in pol:
                if any(i in self.state['active_policies'] for i in pol['incompatible_with']):
                    reasons.append("Incompatible")
                    p_data['clickable'] = False

            p_data['block_reason'] = ", ".join(reasons)
            policies_view[cat].append(p_data)

        return {
            "stats": self.state['stats'],
            "turn": self.state['turn'],
            "log": self.state['log'],
            "policies": policies_view,
            "current_event": self.state['last_event'],
            "game_over": self.state['game_over'],
            "tags": list(set(tags_at + self.state['state_tags']))
        }

    def process_turn(self, llm_instance, director_obj):
        if self.state['game_over']: return {"status": "game_over"}

        # History
        self.state['stats_history'].append(self.state['stats'].copy())
        if len(self.state['stats_history']) > 5: self.state['stats_history'].pop(0)

        self.state['turn'] += 1
        
        # Passive Effects
        for pid in self.state['active_policies']:
            pol = next((p for p in self.db['policies'] if p['id'] == pid), None)
            if pol:
                for k, v in pol.get('passive_effect', {}).items():
                    if k in self.state['stats']:
                        self.state['stats'][k] = self._apply_limits(self.state['stats'][k] + v)

        # Cooldowns
        new_blocked = {}
        for k, v in self.state['blocked_policies'].items():
            if v > 1: new_blocked[k] = v - 1
        self.state['blocked_policies'] = new_blocked

        self.update_tags()

        # Call Director (passing object instance)
        # We prepare gamestate injecting correctly calculated tags
        gamestate_snapshot = self.state.copy()
        gamestate_snapshot['reputation_tags'] = self.get_reputation_tags()
        gamestate_snapshot['last_themes'] = [e['theme'] for e in self.state['decision_memory'] if isinstance(e, dict)] # Correction for theme tracking if needed, simplified below
        # Actually logic uses 'last_themes' in rules.py, but state saves 'decision_memory' as strings...
        # Let's fix this slightly: rules.py expects 'last_themes'. 
        # We need to extract themes from log or store them. 
        # Since original code had 'ultimos_temas' logic but didn't implement it fully in engine, 
        # I'll add a helper list for themes.
        if 'theme_history' not in self.state: self.state['theme_history'] = []
        gamestate_snapshot['last_themes'] = self.state['theme_history']

        event = director_obj.choose_event(llm_instance, gamestate_snapshot)
        
        self.state['last_event'] = event
        self.state['log'].append(f"--- Year {self.state['turn']} ---")
        
        if self._check_game_over(): 
            return {"status": "game_over"}

        return {"status": "ok"}

    def resolve_event(self, event_id, option_id):
        if str(event_id) == "99999" or option_id == "RESET":
            self.__init__(self.db)
            return {"status": "reset"}

        # Collapse Option Treatment (Safety Valve)
        if option_id == "COLLAPSE":
            self.state['stats']['stability'] = self._apply_limits(self.state['stats']['stability'] - 15)
            self.state['stats']['popularity'] = self._apply_limits(self.state['stats']['popularity'] - 10)
            self.state['log'].append("Decision: The government failed to act. Chaos rises.")
            self.state['last_event'] = None
            self._check_game_over()
            return {"status": "ok"}

        ev = None
        if self.state['last_event'] and str(self.state['last_event']['id']) == str(event_id):
            ev = self.state['last_event']
        else:
            # Fallback
            ev = next((e for e in self.db['events'] if str(e['id']) == str(event_id)), None)

        if ev:
            op = next((o for o in ev['options'] if o['id'] == option_id), None)
            if op:
                effects = op.get('effect', {})
                # Resource Validation (Double Check)
                for k, v in effects.items():
                    if v < 0:
                        current = self.state['stats'].get(k, 0)
                        if current + v < 0:
                            return {"status": "error", "msg": f"Insufficient resources: {k}"}

                # Apply
                for k, v in effects.items():
                    if k in self.state['stats']:
                        self.state['stats'][k] = self._apply_limits(self.state['stats'][k] + v)

                # REPAIR 1: Event Tags go to separate list
                tags_new = []
                if 'effect_tags' in op:
                    for tag in op['effect_tags']:
                        if tag not in self.state['event_tags']:
                            self.state['event_tags'].append(tag)
                            tags_new.append(tag)
                
                tags_str = f" [{', '.join(tags_new)}]" if tags_new else ""
                self.state['decision_memory'].append(f"Year {self.state['turn']}: Chose '{op['text']}' in '{ev['title']}'{tags_str}.")
                if len(self.state['decision_memory']) > 12: self.state['decision_memory'].pop(0)

                # Update theme history for Rules
                if 'theme_history' not in self.state: self.state['theme_history'] = []
                self.state['theme_history'].append(ev.get('theme', 'general'))
                if len(self.state['theme_history']) > 8: self.state['theme_history'].pop(0)

                self.state['log'].append(f"Decision: {op['text']}")
                self.update_tags()
                self._check_game_over()
        
        self.state['last_event'] = None
        return {"status": "ok"}
    
    def _check_game_over(self):
        s = self.state['stats']
        cause = None
        
        if s['stability'] <= 0: cause = "Total Anarchy. The realm collapsed."
        elif s['popularity'] <= 0: cause = "Popular Revolution. The guillotine awaits."
        elif s['military'] <= 0: cause = "External Conquest."
        elif s['treasury'] <= 0 and s['military'] < 20: cause = "State bankrupt and defenseless."

        if cause and not self.state['game_over']:
            self.state['game_over'] = True
            self.state['log'].append(f"--- END OF THE LINE: {cause} ---")
            
            evt_death = {
                "id": 99999,
                "title": "THE END OF THE DYNASTY",
                "text": cause,
                "theme": "game_over",
                "options": [{"id": "RESET", "text": "Start New History", "effect": {}, "response": "..."}]
            }
            self.state['last_event'] = evt_death
            return True
        return False

    def toggle_policy(self, pid):
        # Simplified logic as get_view_data does heavy validation
        if self.state['game_over']: return {"error": "Game Over"}, 400
        
        pol = next((p for p in self.db['policies'] if p['id'] == pid), None)
        if not pol: return {"error": "Invalid Law"}, 400
        
        tags_at = self.get_reputation_tags()
        cost_base = 10
        if 'aversion' in pol and any(t in pol['aversion'] for t in tags_at):
            cost_base *= 2
            
        if self.state['stats']['stability'] < cost_base:
            return {"error": "Insufficient Stability"}, 400

        msg = ""
        if pid in self.state['active_policies']:
            # REVOKE
            self.state['active_policies'].remove(pid)
            # Obs: Tags vanish automatically in next get_reputation_tags()
            msg = f"Revoked: {pol['name']}"
        else:
            # ENACT
            # Validate cost
            cost = pol.get('activation_cost', {})
            for k, v in cost.items():
                if self.state['stats'].get(k, 0) + v < 0:
                     return {"error": f"Lacks {k}"}, 400
            
            # Apply cost
            for k, v in cost.items():
                self.state['stats'][k] = self._apply_limits(self.state['stats'][k] + v)
                
            self.state['active_policies'].append(pid)
            self.state['blocked_policies'][pid] = self.config.get('default_lock_turns', 8)
            msg = f"Enacted: {pol['name']}"

        self.state['stats']['stability'] -= cost_base
        self.state['log'].append(msg)
        self.update_tags()
        
        return {"status": "ok", "msg": msg}, 200