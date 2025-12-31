# [file name]: src/engine/game_state.py
# src/engine/game_state.py

class GameState:
    """Manages the core game state and state transitions."""
    
    def __init__(self, db):
        self.db = db
        self.config = db.get('config', {})
        self.reset()
    
    def reset(self):
        """Reset to initial state."""
        self.state = {
            "turn": 1,
            "stats": {
                "treasury": 50, "military": 50, "popularity": 50, 
                "stability": 50
            },
            "active_policies": ["serfdom", "absolutism"],
            "blocked_policies": {},
            "event_tags": [],
            "state_tags": [],
            "decision_memory": [],
            "log": ["The Director: 'The history begins...'"],
            "last_event": None,
            "game_over": False,
            "stats_history": [],
            "theme_history": []
        }
    
    def get_state(self):
        """Return the current state."""
        return self.state
    
    def set_state(self, state):
        """Set the entire state (careful!)."""
        self.state = state
    
    def update_stat(self, stat_name, delta):
        """Update a specific stat with limits."""
        if stat_name in self.state['stats']:
            new_value = self.state['stats'][stat_name] + delta
            self.state['stats'][stat_name] = max(0, min(100, new_value))
            return True
        return False
    
    def apply_stat_limits(self):
        """Ensure all stats stay within 0-100 bounds."""
        for stat in self.state['stats']:
            self.state['stats'][stat] = max(0, min(100, self.state['stats'][stat]))
    
    def add_log_entry(self, entry):
        """Add an entry to the game log."""
        self.state['log'].append(entry)
    
    def get_stats_snapshot(self):
        """Return a copy of current stats."""
        return self.state['stats'].copy()
    
    def increment_turn(self):
        """Advance to the next turn."""
        self.state['turn'] += 1
    
    def set_game_over(self, cause=None):
        """Mark the game as over."""
        self.state['game_over'] = True
        if cause:
            self.add_log_entry(f"--- END OF THE LINE: {cause} ---")
    
    def is_game_over(self):
        """Check if game is over."""
        return self.state['game_over']
    
    def add_event_tag(self, tag):
        """Add a permanent event tag."""
        if tag not in self.state['event_tags']:
            self.state['event_tags'].append(tag)
    
    def add_state_tag(self, tag):
        """Add a state tag (temporary)."""
        if tag not in self.state['state_tags']:
            self.state['state_tags'].append(tag)
    
    def clear_state_tags(self):
        """Clear all state tags."""
        self.state['state_tags'] = []
    
    def add_to_theme_history(self, theme):
        """Add theme to history for anti-repetition."""
        self.state['theme_history'].append(theme)
        if len(self.state['theme_history']) > 8:
            self.state['theme_history'].pop(0)
    
    def add_to_decision_memory(self, decision_text):
        """Add a decision to memory."""
        self.state['decision_memory'].append(decision_text)
        if len(self.state['decision_memory']) > 12:
            self.state['decision_memory'].pop(0)