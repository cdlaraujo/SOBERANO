# [file name]: src/engine/policy_manager.py
# src/engine/policy_manager.py

class PolicyManager:
    """Manages policies, their effects, and validation."""
    
    def __init__(self, game_state, db, tag_manager):
        self.game_state = game_state
        self.db = db
        self.tag_manager = tag_manager
        self._cached_policies_by_category = None
    
    def _cache_policies_by_category(self):
        """Cache policies organized by category for faster access."""
        if self._cached_policies_by_category is None:
            self._cached_policies_by_category = {}
            for pol in self.db['policies']:
                cat = pol.get('category', 'others').capitalize()
                if cat not in self._cached_policies_by_category:
                    self._cached_policies_by_category[cat] = []
                self._cached_policies_by_category[cat].append(pol.copy())
    
    def get_policies_view(self):
        """Return policies organized for UI display with validation."""
        self._cache_policies_by_category()
        
        policies_view = {}
        state = self.game_state.get_state()
        tags_at = self.tag_manager.get_reputation_tags()
        
        for cat, policies in self._cached_policies_by_category.items():
            policies_view[cat] = []
            
            for pol in policies:
                p_data = pol.copy()
                p_data['active'] = pol['id'] in state['active_policies']
                p_data['lock_turns'] = state['blocked_policies'].get(pol['id'], 0)
                p_data['blocked'] = p_data['lock_turns'] > 0
                p_data['clickable'] = True
                
                reasons = []
                cost_estab = 10
                
                # Extra cost for narrative incoherence
                if 'aversion' in pol:
                    if any(t in pol['aversion'] for t in tags_at):
                        cost_estab *= 2
                        reasons.append("Against your nature")
                
                if state['stats']['stability'] < cost_estab:
                    reasons.append(f"Too Unstable (-{cost_estab} Stab.)")
                    p_data['clickable'] = False
                else:
                    p_data['stability_cost'] = cost_estab
                
                if not p_data['active']:
                    # Check activation costs
                    cost_activ = pol.get('activation_cost', {})
                    for k, v in cost_activ.items():
                        if state['stats'].get(k, 0) + v < 0:
                            reasons.append(f"Lacks {abs(v)} {k}")
                            p_data['clickable'] = False
                
                # Check incompatibilities
                if 'incompatible_with' in pol:
                    if any(i in state['active_policies'] for i in pol['incompatible_with']):
                        reasons.append("Incompatible")
                        p_data['clickable'] = False
                
                p_data['block_reason'] = ", ".join(reasons)
                policies_view[cat].append(p_data)
        
        return policies_view
    
    def apply_passive_effects(self):
        """Apply passive effects from active policies."""
        state = self.game_state.get_state()
        
        for pid in state['active_policies']:
            pol = next((p for p in self.db['policies'] if p['id'] == pid), None)
            if pol and 'passive_effect' in pol:
                for stat, delta in pol['passive_effect'].items():
                    self.game_state.update_stat(stat, delta)
    
    def update_cooldowns(self):
        """Reduce policy cooldown timers."""
        state = self.game_state.get_state()
        new_blocked = {}
        
        for pid, turns in state['blocked_policies'].items():
            if turns > 1:
                new_blocked[pid] = turns - 1
        
        state['blocked_policies'] = new_blocked
    
    def toggle_policy(self, policy_id):
        """Enact or revoke a policy."""
        state = self.game_state.get_state()
        
        if state['game_over']:
            return {"error": "Game Over"}, 400
        
        pol = next((p for p in self.db['policies'] if p['id'] == policy_id), None)
        if not pol:
            return {"error": "Invalid Law"}, 400
        
        tags_at = self.tag_manager.get_reputation_tags()
        cost_base = 10
        
        if 'aversion' in pol and any(t in pol['aversion'] for t in tags_at):
            cost_base *= 2
        
        if state['stats']['stability'] < cost_base:
            return {"error": "Insufficient Stability"}, 400
        
        msg = ""
        is_active = policy_id in state['active_policies']
        
        if is_active:
            # REVOKE
            state['active_policies'].remove(policy_id)
            msg = f"Revoked: {pol['name']}"
        else:
            # ENACT
            # Validate cost
            cost = pol.get('activation_cost', {})
            for stat, amount in cost.items():
                if state['stats'].get(stat, 0) + amount < 0:
                    return {"error": f"Lacks {stat}"}, 400
            
            # Apply cost
            for stat, amount in cost.items():
                self.game_state.update_stat(stat, amount)
            
            state['active_policies'].append(policy_id)
            state['blocked_policies'][policy_id] = self.db['config'].get('default_lock_turns', 8)
            msg = f"Enacted: {pol['name']}"
        
        # Apply stability cost
        self.game_state.update_stat('stability', -cost_base)
        self.game_state.add_log_entry(msg)
        
        return {"status": "ok", "msg": msg}, 200