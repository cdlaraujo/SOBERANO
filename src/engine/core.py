# [file name]: src/engine/core.py
# src/engine/core.py

from .game_state import GameState
from .tag_manager import TagManager
from .policy_manager import PolicyManager
from .event_manager import EventManager
from .game_over_checker import GameOverChecker

class GameEngine:
    """Main game engine coordinating all subsystems."""
    
    def __init__(self, db):
        self.db = db
        self.config = db.get('config', {})
        
        # Initialize subsystems
        self.game_state = GameState(db)
        self.tag_manager = TagManager(self.game_state, db)
        self.policy_manager = PolicyManager(self.game_state, db, self.tag_manager)
        self.event_manager = EventManager(self.game_state, db, self.tag_manager)
        self.game_over_checker = GameOverChecker(self.game_state)
        
        # Calculate initial tags
        self.tag_manager.calculate_state_tags()
    
    def get_view_data(self):
        """Return game state formatted for UI."""
        state = self.game_state.get_state()
        
        # Prepare event options if needed
        if state['last_event']:
            self.event_manager.prepare_event_options(state['last_event'])
        
        # Get policies view
        policies_view = self.policy_manager.get_policies_view()
        
        # Get all tags
        all_tags = self.tag_manager.get_all_tags()
        
        return {
            "stats": state['stats'].copy(),
            "turn": state['turn'],
            "log": state['log'].copy(),
            "policies": policies_view,
            "current_event": state['last_event'],
            "game_over": state['game_over'],
            "tags": all_tags
        }
    
    def process_turn(self, llm_instance, director_obj):
        """Process the next game turn."""
        state = self.game_state.get_state()
        
        if state['game_over']:
            return {"status": "game_over"}
        
        # Save stats history
        state['stats_history'].append(state['stats'].copy())
        if len(state['stats_history']) > 5:
            state['stats_history'].pop(0)
        
        # Increment turn
        self.game_state.increment_turn()
        
        # Apply passive policy effects
        self.policy_manager.apply_passive_effects()
        
        # Update policy cooldowns
        self.policy_manager.update_cooldowns()
        
        # Recalculate tags
        self.tag_manager.calculate_state_tags()
        
        # Prepare gamestate for director
        gamestate_snapshot = state.copy()
        gamestate_snapshot['reputation_tags'] = self.tag_manager.get_reputation_tags()
        gamestate_snapshot['last_themes'] = state['theme_history'].copy()
        
        # Get next event from director
        event = director_obj.choose_event(llm_instance, gamestate_snapshot)
        
        # Set as current event
        state['last_event'] = event
        
        # Log new turn
        self.game_state.add_log_entry(f"--- Year {state['turn']} ---")
        
        # Check for game over
        if self.game_over_checker.check_game_over():
            return {"status": "game_over"}
        
        return {"status": "ok"}
    
    def resolve_event(self, event_id, option_id):
        """Public method to resolve an event choice."""
        return self.event_manager.resolve_event(event_id, option_id)
    
    def toggle_policy(self, policy_id):
        """Public method to toggle a policy."""
        return self.policy_manager.toggle_policy(policy_id)
    
    # Convenience methods
    def get_gamestate_snapshot(self):
        """Get a snapshot for director/rules."""
        state = self.game_state.get_state()
        return {
            'stats': state['stats'].copy(),
            'reputation_tags': self.tag_manager.get_reputation_tags(),
            'state_tags': state['state_tags'].copy(),
            'last_themes': state['theme_history'].copy(),
            'turn': state['turn'],
            'game_over': state['game_over']
        }