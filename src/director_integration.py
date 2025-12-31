"""
Director Integration Layer for Sovereign: The Living Chronicle
Integrates DynamicGenerator with existing IntelligentDirector system.
"""

import random
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class EnhancedIntelligentDirector:
    """
    Enhanced version of IntelligentDirector that supports both static and dynamic events.
    Works alongside your existing director.py without breaking it.
    """
    
    def __init__(self, event_list: List[Dict], skeletons_db: Optional[Dict] = None, 
                 dynamic_generator: Optional[Any] = None):
        """
        Initialize the enhanced director.
        
        Args:
            event_list: Original static events from events.json
            skeletons_db: Loaded mechanical lexicon (optional)
            dynamic_generator: Initialized DynamicGenerator (optional)
        """
        self.all_events = event_list
        self.skeletons_db = skeletons_db or {}
        self.dynamic_generator = dynamic_generator
        
        # --- CONFIGURATION: TEST MODE (100% PROBABILITY) ---
        self.dynamic_probability = 1.0  # Changed from 0.3 to 1.0 for testing
        self.min_dynamic_events = 5     # Need 5 successful generations before increasing
        self.max_dynamic_probability = 1.0  # Can go up to 100%
        
        # Statistics tracking
        self.static_events_selected = 0
        self.dynamic_events_selected = 0
        self.dynamic_generation_failures = 0
        self.last_10_choices = []  # Track last 10 event selections for analysis
        
        # Cache for rule filtering results
        self.rule_filter_cache = {}
        
        logger.info(f"EnhancedIntelligentDirector initialized: {len(self.all_events)} static events, "
                   f"{len(self.skeletons_db.get('archetypes', [])) if self.skeletons_db else 0} archetypes")
    
    def set_dynamic_generator(self, dynamic_gen: Any) -> None:
        """Set or update the dynamic generator."""
        self.dynamic_generator = dynamic_gen
        logger.info("Dynamic generator attached to EnhancedIntelligentDirector")
    
    def choose_event(self, llm_instance: Any, gamestate: Dict) -> Dict:
        """
        Main event selection method - replaces the original choose_event.
        
        This method:
        1. Decides whether to use dynamic or static events
        2. Handles dynamic generation if chosen
        3. Falls back to static if dynamic fails
        4. Tracks statistics for adaptive learning
        """
        # Log the incoming gamestate for debugging
        logger.debug(f"Choosing event for turn {gamestate.get('turn', 'unknown')}")
        
        # Step 1: Decide whether to attempt dynamic generation
        should_use_dynamic = self._should_attempt_dynamic(gamestate)
        
        if should_use_dynamic and self.dynamic_generator:
            logger.info("Attempting dynamic event generation...")
            
            try:
                # Step 2: Generate dynamic event
                dynamic_event = self._generate_dynamic_event(gamestate)
                
                if dynamic_event and self._validate_dynamic_event(dynamic_event, gamestate):
                    # Success! Use dynamic event
                    self.dynamic_events_selected += 1
                    self.last_10_choices.append(('dynamic', dynamic_event.get('_archetype_id', 'unknown')))
                    self._adjust_probability(success=True)
                    
                    logger.info(f"✅ DYNAMIC EVENT: {dynamic_event.get('title', 'Untitled')} "
                              f"(Archetype: {dynamic_event.get('_archetype_id', 'unknown')})")
                    
                    # Ensure the event has all required fields
                    final_event = self._ensure_event_compatibility(dynamic_event, gamestate)
                    return final_event
                else:
                    # Dynamic generation failed
                    logger.warning("Dynamic generation failed or validation rejected event")
                    self.dynamic_generation_failures += 1
                    self._adjust_probability(success=False)
                    
            except Exception as e:
                logger.error(f"Dynamic generation error: {str(e)}", exc_info=True)
                self.dynamic_generation_failures += 1
                self._adjust_probability(success=False)
        
        # Step 3: Fall back to static event selection (original logic)
        logger.info("Using static event selection")
        static_event = self._choose_static_event(llm_instance, gamestate)
        
        if static_event:
            self.static_events_selected += 1
            self.last_10_choices.append(('static', static_event.get('id', 'unknown')))
            
            # Mark as static for tracking
            static_event["_generated"] = False
            static_event["_selection_method"] = "static"
            
            logger.info(f"✅ STATIC EVENT: {static_event.get('title', 'Untitled')}")
        
        return static_event
    
    def _should_attempt_dynamic(self, gamestate: Dict) -> bool:
        """
        Determine if we should attempt dynamic generation.
        """
        # Don't generate during game over
        if gamestate.get("game_over", False):
            return False
        
        # Check probability (Will always pass if probability is 1.0)
        if random.random() > self.dynamic_probability:
            logger.debug(f"Skipping dynamic (probability: {self.dynamic_probability:.2f})")
            return False
        
        # Check if we have enough successful dynamic events to be confident
        if self.dynamic_events_selected < self.min_dynamic_events:
            logger.debug(f"Need more dynamic events ({self.dynamic_events_selected}/{self.min_dynamic_events})")
            return True  # Still try to build up experience
        
        # Check game state stability
        # COMMENTED OUT FOR TESTING: Even if crisis, force dynamic event
        # stability = gamestate.get("stats", {}).get("stability", 50)
        # if stability < 20:
        #     # During crises, be more conservative
        #     crisis_probability = self.dynamic_probability * 0.3
        #     if random.random() > crisis_probability:
        #         logger.debug(f"Skipping dynamic during crisis (stability: {stability})")
        #         return False
        
        # Check recent failure rate
        total_attempts = self.dynamic_events_selected + self.dynamic_generation_failures
        if total_attempts > 0:
            failure_rate = self.dynamic_generation_failures / total_attempts
            if failure_rate > 0.5:  # More than 50% failure rate
                logger.warning(f"High failure rate ({failure_rate:.2f}), being conservative")
                # For testing, we keep this higher than normal (50% instead of 10%)
                return random.random() < 0.5 
        
        return True
    
    def _generate_dynamic_event(self, gamestate: Dict) -> Optional[Dict]:
        """Generate a dynamic event using the DynamicGenerator."""
        if not self.dynamic_generator:
            logger.warning("No dynamic generator available")
            return None
        
        # Prepare gamestate for generator
        enhanced_gamestate = self._enhance_gamestate(gamestate)
        
        # Add director context
        enhanced_gamestate["director_context"] = {
            "static_events_available": len(self.all_events),
            "recent_choices": self.last_10_choices[-5:] if self.last_10_choices else [],
            "current_dynamic_probability": self.dynamic_probability
        }
        
        # Generate the event
        event = self.dynamic_generator.generate_event(enhanced_gamestate)
        
        if event:
            # Add director metadata
            event["_director"] = "EnhancedIntelligentDirector"
            event["_selection_method"] = "dynamic_generation"
            event["_generation_timestamp"] = datetime.now().isoformat()
        
        return event
    
    def _enhance_gamestate(self, gamestate: Dict) -> Dict:
        """
        Ensure gamestate has all fields needed for generation.
        This mirrors what your GameEngine provides.
        """
        enhanced = gamestate.copy()
        
        # Ensure all required fields exist with defaults
        defaults = {
            "reputation_tags": [],
            "state_tags": [],
            "last_themes": [],
            "decision_memory": [],
            "theme_history": [],
            "stats": {
                "treasury": 50, "military": 50, "popularity": 50,
                "stability": 50, "agriculture": 50, "commerce": 50
            },
            "turn": 1,
            "active_policies": [],
            "game_over": False
        }
        
        for key, default in defaults.items():
            if key not in enhanced:
                enhanced[key] = default
            elif isinstance(default, dict) and isinstance(enhanced[key], dict):
                # Merge dictionaries
                for subkey, subdefault in default.items():
                    if subkey not in enhanced[key]:
                        enhanced[key][subkey] = subdefault
        
        # Ensure stats are all present
        stat_defaults = defaults["stats"]
        for stat, default in stat_defaults.items():
            if stat not in enhanced["stats"]:
                enhanced["stats"][stat] = default
        
        # Calculate combined tags for easier access
        enhanced["all_tags"] = (
            enhanced.get("reputation_tags", []) + 
            enhanced.get("state_tags", [])
        )
        
        return enhanced
    
    def _validate_dynamic_event(self, event: Dict, gamestate: Dict) -> bool:
        """
        Validate that a dynamically generated event is suitable for the current state.
        
        This adds an extra layer of safety beyond the generator's own validation.
        """
        if not event:
            return False
        
        # Basic structure validation
        required_fields = ["id", "title", "text", "options"]
        for field in required_fields:
            if field not in event:
                logger.warning(f"Dynamic event missing required field: {field}")
                return False
        
        # Check options
        if len(event.get("options", [])) != 2:
            logger.warning(f"Dynamic event doesn't have exactly 2 options")
            return False
        
        # Check option IDs
        option_ids = [opt.get("id") for opt in event.get("options", [])]
        if "A" not in option_ids or "B" not in option_ids:
            logger.warning("Dynamic event options missing A/B IDs")
            return False
        
        # Validate option effects are within reasonable bounds
        for option in event.get("options", []):
            effects = option.get("effect", {})
            for stat, change in effects.items():
                # Check if change is numeric
                if not isinstance(change, (int, float)):
                    logger.warning(f"Option {option.get('id')} has non-numeric effect for {stat}: {change}")
                    return False
                
                # Check for extreme values (can be adjusted based on your game balance)
                if abs(change) > 100:
                    logger.warning(f"Option {option.get('id')} has extreme effect for {stat}: {change}")
                    return False
        
        # Check if event theme is appropriate for current state
        # (Optional - can be expanded based on your RuleEngine logic)
        theme = event.get("theme")
        if theme:
            last_themes = gamestate.get("last_themes", [])
            if theme in last_themes[-2:]:  # Avoid repeating same theme too soon
                logger.debug(f"Theme {theme} repeated too soon")
                # Not necessarily invalid, just worth noting
                # return False  # Uncomment to enforce strict theme rotation
        
        return True
    
    def _ensure_event_compatibility(self, event: Dict, gamestate: Dict) -> Dict:
        """
        Ensure the dynamic event is compatible with the existing game engine.
        
        This adds any missing fields that the engine expects.
        """
        # Start with the event
        compatible_event = event.copy()
        
        # Ensure it has all fields that static events have
        static_example = self.all_events[0] if self.all_events else {}
        
        for field in ["semantic_trigger", "drama_weight"]:
            if field not in compatible_event:
                if field in static_example:
                    compatible_event[field] = static_example[field]
                else:
                    # Provide sensible defaults
                    if field == "semantic_trigger":
                        compatible_event[field] = []
                    elif field == "drama_weight":
                        compatible_event[field] = 50
        
        # Ensure options have all required fields
        for option in compatible_event.get("options", []):
            if "effect_tags" not in option:
                option["effect_tags"] = []
            
            # Ensure effect is a dict
            if "effect" not in option:
                option["effect"] = {}
            
            # Ensure response field exists
            if "response" not in option:
                option["response"] = f"Response to option {option.get('id', 'unknown')}"
        
        return compatible_event
    
    def _choose_static_event(self, llm_instance: Any, gamestate: Dict) -> Dict:
        """
        Select a static event using the original logic.
        
        This mimics the behavior of your existing IntelligentDirector.choose_event()
        but can be called from within the enhanced director.
        """
        try:
            # Import the original RuleEngine
            from src.rules import RuleEngine
            
            # Step 1: Apply rule filtering (same as original)
            candidates = RuleEngine.filter_viable(self.all_events, gamestate)
            logger.debug(f"[Static Selection] {len(candidates)} viable events after rules")
            
            if not candidates:
                logger.warning("[Static Selection] No viable events after rules, picking random")
                return random.choice(self.all_events)
            
            chosen = None
            
            # Step 2: AI selection layer (if LLM is available)
            if llm_instance and len(candidates) > 1:
                try:
                    from src.inference import LLMDecisionEngine
                    
                    # Create a smaller pool for AI consideration (same as original)
                    pool_ai = random.sample(candidates, min(5, len(candidates)))
                    
                    # Use the LLM to select
                    engine = LLMDecisionEngine(llm_instance)
                    chosen = engine.select_event(pool_ai, gamestate)
                    
                    if chosen:
                        logger.debug("[Static Selection] AI selected an event")
                except Exception as e:
                    logger.warning(f"[Static Selection] AI selection failed: {e}")
            
            # Step 3: Fallback to drama-weighted random selection
            if not chosen:
                # Sort by drama weight (descending)
                candidates.sort(key=lambda x: x.get('drama_weight', 50), reverse=True)
                
                # Pick from top 3
                top_3 = candidates[:3]
                chosen = random.choice(top_3)
                logger.debug("[Static Selection] Selected from top 3 by drama weight")
            
            logger.info(f"[Static Selection] Selected: {chosen.get('title', 'Unknown')}")
            return chosen
            
        except Exception as e:
            logger.error(f"[Static Selection] Error: {e}", exc_info=True)
            # Ultimate fallback
            return random.choice(self.all_events)
    
    def _adjust_probability(self, success: bool) -> None:
        """
        Adjust the dynamic event probability based on success/failure.
        
        This creates a self-adjusting system that becomes more confident
        as it succeeds and more cautious as it fails.
        """
        old_probability = self.dynamic_probability
        
        if success:
            # Increase probability gradually
            # More aggressive increase when we have few events, more conservative later
            if self.dynamic_events_selected < 10:
                increase_factor = 1.15  # 15% increase
            elif self.dynamic_events_selected < 30:
                increase_factor = 1.08  # 8% increase
            else:
                increase_factor = 1.03  # 3% increase
            
            self.dynamic_probability = min(
                self.max_dynamic_probability,
                self.dynamic_probability * increase_factor
            )
        else:
            # Decrease probability on failure
            # More severe decrease for repeated failures
            recent_failures = min(10, self.dynamic_generation_failures)
            decrease_factor = 0.85 - (recent_failures * 0.02)  # 15-35% decrease
            
            self.dynamic_probability = max(
                0.05,  # Never go below 5%
                self.dynamic_probability * decrease_factor
            )
        
        # Log if probability changed significantly
        if abs(old_probability - self.dynamic_probability) > 0.05:
            logger.info(f"Dynamic probability adjusted: {old_probability:.2f} → {self.dynamic_probability:.2f}")
    
    def get_stats(self) -> Dict:  # <-- RENAMED from get_statistics
        """Get comprehensive director statistics."""
        total_events = self.static_events_selected + self.dynamic_events_selected
        total_attempts = self.dynamic_events_selected + self.dynamic_generation_failures
        
        return {
            "static_events_selected": self.static_events_selected,
            "dynamic_events_selected": self.dynamic_events_selected,
            "dynamic_generation_failures": self.dynamic_generation_failures,
            "total_events_selected": total_events,
            "dynamic_success_rate": (
                self.dynamic_events_selected / total_attempts 
                if total_attempts > 0 else 0
            ),
            "dynamic_ratio": (
                self.dynamic_events_selected / total_events 
                if total_events > 0 else 0
            ),
            "current_dynamic_probability": self.dynamic_probability,
            "recent_choices": self.last_10_choices[-10:] if self.last_10_choices else []
        }
    
    def get_debug_info(self) -> Dict:
        """Get debug information about the director's state."""
        return {
            "config": {
                "dynamic_probability": self.dynamic_probability,
                "min_dynamic_events": self.min_dynamic_events,
                "max_dynamic_probability": self.max_dynamic_probability
            },
            "cache_info": {
                "rule_filter_cache_size": len(self.rule_filter_cache)
            },
            "generator_status": "attached" if self.dynamic_generator else "detached",
            "skeletons_available": len(self.skeletons_db.get('archetypes', [])) if self.skeletons_db else 0
        }


# Backward compatibility functions
def create_enhanced_from_original(original_director, dynamic_generator=None, skeletons_db=None):
    """
    Create an EnhancedIntelligentDirector from an existing IntelligentDirector.
    
    This provides backward compatibility - you can wrap your existing director
    instead of replacing it entirely.
    """
    enhanced = EnhancedIntelligentDirector(
        event_list=original_director.all_events,
        skeletons_db=skeletons_db,
        dynamic_generator=dynamic_generator
    )
    
    # Copy any relevant state from the original director
    if hasattr(original_director, 'recent_selections'):
        enhanced.last_10_choices = original_director.recent_selections[-10:] if original_director.recent_selections else []
    
    logger.info("Created enhanced director from original director")
    return enhanced


def hybrid_director_factory(static_events, llm_instance=None, 
                            dynamic_generator=None, initial_dynamic_prob=0.3):
    """
    Factory function to create a hybrid director.
    
    Useful for testing or gradual integration.
    """
    director = EnhancedIntelligentDirector(
        event_list=static_events,
        dynamic_generator=dynamic_generator
    )
    
    # Override initial probability if specified
    director.dynamic_probability = initial_dynamic_prob
    
    logger.info(f"Created hybrid director with {initial_dynamic_prob*100:.0f}% initial dynamic probability")
    return director