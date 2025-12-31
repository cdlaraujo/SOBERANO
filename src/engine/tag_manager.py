# [file name]: src/engine/tag_manager.py
# src/engine/tag_manager.py

class TagManager:
    """Manages all tag calculations and combinations."""
    
    def __init__(self, game_state, db):
        self.game_state = game_state
        self.db = db
    
    def calculate_state_tags(self):
        """Calculate tags based on current stats."""
        s = self.game_state.get_stats_snapshot()
        tags = []
        
        # Treasury tags
        if s['treasury'] > 75: tags.extend(["midas", "rich"])
        elif s['treasury'] < 10: tags.extend(["bankrupt", "poor"])
        elif s['treasury'] < 25: tags.append("poor")
        
        # Military tags
        if s['military'] > 75: tags.append("spartan")
        elif s['military'] < 25: tags.append("vulnerable")
        
        # Popularity tags
        if s['popularity'] < 25: tags.extend(["unpopular", "hated", "oppressor"])
        elif s['popularity'] > 75: tags.append("beloved")
        
        # Stability tags
        if s['stability'] < 25: tags.append("chaos")
        
        # Update state
        self.game_state.clear_state_tags()
        for tag in tags:
            self.game_state.add_state_tag(tag)
    
    def get_law_tags(self):
        """Get tags from active policies."""
        law_tags = []
        state = self.game_state.get_state()
        
        for pid in state['active_policies']:
            pol = next((p for p in self.db['policies'] if p['id'] == pid), None)
            if pol and 'permanent_tags' in pol:
                law_tags.extend(pol['permanent_tags'])
        
        return law_tags
    
    def get_reputation_tags(self):
        """Combine event tags and law tags."""
        state = self.game_state.get_state()
        law_tags = self.get_law_tags()
        
        # Return unique list
        return list(set(state['event_tags'] + law_tags))
    
    def get_all_tags(self):
        """Get all active tags (reputation + state)."""
        reputation_tags = self.get_reputation_tags()
        state = self.game_state.get_state()
        
        return list(set(reputation_tags + state['state_tags']))
    
    def has_any_tag(self, tags_to_check):
        """Check if player has any of the specified tags."""
        all_tags = self.get_all_tags()
        return any(tag in all_tags for tag in tags_to_check)