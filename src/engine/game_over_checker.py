# [file name]: src/engine/game_over_checker.py
# src/engine/game_over_checker.py

class GameOverChecker:
    """Manages game end conditions and final event."""
    
    def __init__(self, game_state):
        self.game_state = game_state
    
    def check_game_over(self):
        """Check if game should end and set up final event if so."""
        state = self.game_state.get_state()
        
        if state['game_over']:
            return True
        
        s = state['stats']
        cause = None
        
        if s['stability'] <= 0:
            cause = "Total Anarchy. The realm collapsed."
        elif s['popularity'] <= 0:
            cause = "Popular Revolution. The guillotine awaits."
        elif s['military'] <= 0:
            cause = "External Conquest."
        elif s['treasury'] <= 0 and s['military'] < 20:
            cause = "State bankrupt and defenseless."
        
        if cause:
            self.game_state.set_game_over(cause)
            
            # Create final event
            evt_death = {
                "id": 99999,
                "title": "THE END OF THE DYNASTY",
                "text": cause,
                "theme": "game_over",
                "options": [{"id": "RESET", "text": "Start New History", "effect": {}, "response": "..."}]
            }
            state['last_event'] = evt_death
            return True
        
        return False
    
    def create_game_over_event(self, cause):
        """Create the game over event."""
        return {
            "id": 99999,
            "title": "THE END OF THE DYNASTY",
            "text": cause,
            "theme": "game_over",
            "options": [{"id": "RESET", "text": "Start New History", "effect": {}, "response": "..."}]
        }