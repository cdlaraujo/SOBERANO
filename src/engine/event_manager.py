# [file name]: src/engine/event_manager.py
# src/engine/event_manager.py

class EventManager:
    """Manages event resolution and option validation."""
    
    def __init__(self, game_state, db, tag_manager):
        self.game_state = game_state
        self.db = db
        self.tag_manager = tag_manager
    
    def validate_option_resources(self, option):
        """Check if player has resources for an option."""
        state = self.game_state.get_state()
        effects = option.get('effect', {})
        
        for stat, delta in effects.items():
            if delta < 0:  # It's a cost
                current = state['stats'].get(stat, 0)
                if current + delta < 0:
                    return False, f"Requires {abs(delta)} {stat.capitalize()}"
        
        return True, ""
    
    def prepare_event_options(self, event):
        """Prepare event options with blocking validation."""
        if not event or event['id'] == 99999:
            return
        
        state = self.game_state.get_state()
        options_blocked = 0
        total_options = len(event['options'])
        
        for option in event['options']:
            option['blocked'] = False
            option['block_reason'] = ""
            
            valid, reason = self.validate_option_resources(option)
            if not valid:
                option['blocked'] = True
                option['block_reason'] = reason
                options_blocked += 1
        
        # Anti-softlock: Add emergency option if all are blocked
        if options_blocked == total_options:
            event['options'].append({
                "id": "COLLAPSE",
                "text": "[NO RESOURCES] The government paralyzes...",
                "blocked": False,
                "effect": {"stability": -15, "popularity": -10},
                "block_reason": "Only available exit"
            })
    
    def resolve_event(self, event_id, option_id):
        """Resolve a player's event choice."""
        state = self.game_state.get_state()
        
        # Reset game
        if str(event_id) == "99999" or option_id == "RESET":
            self.game_state.reset()
            self.tag_manager.calculate_state_tags()
            return {"status": "reset"}
        
        # Collapse option
        if option_id == "COLLAPSE":
            self.game_state.update_stat('stability', -15)
            self.game_state.update_stat('popularity', -10)
            self.game_state.add_log_entry("Decision: The government failed to act. Chaos rises.")
            state['last_event'] = None
            return {"status": "ok"}
        
        # Find event
        ev = None
        if state['last_event'] and str(state['last_event']['id']) == str(event_id):
            ev = state['last_event']
        else:
            # Fallback search
            ev = next((e for e in self.db['events'] if str(e['id']) == str(event_id)), None)
        
        if not ev:
            return {"status": "error", "msg": "Event not found"}
        
        # Find option
        op = next((o for o in ev['options'] if o['id'] == option_id), None)
        if not op:
            return {"status": "error", "msg": "Option not found"}
        
        # Double-check resources
        valid, reason = self.validate_option_resources(op)
        if not valid:
            return {"status": "error", "msg": reason}
        
        # Apply effects
        effects = op.get('effect', {})
        for stat, delta in effects.items():
            self.game_state.update_stat(stat, delta)
        
        # Add event tags
        tags_new = []
        if 'effect_tags' in op:
            for tag in op['effect_tags']:
                self.game_state.add_event_tag(tag)
                tags_new.append(tag)
        
        # Record decision
        tags_str = f" [{', '.join(tags_new)}]" if tags_new else ""
        decision_text = f"Year {state['turn']}: Chose '{op['text']}' in '{ev['title']}'{tags_str}."
        self.game_state.add_to_decision_memory(decision_text)
        
        # Update theme history
        self.game_state.add_to_theme_history(ev.get('theme', 'general'))
        
        # Log decision
        self.game_state.add_log_entry(f"Decision: {op['text']}")
        
        # Clear current event
        state['last_event'] = None
        
        return {"status": "ok"}