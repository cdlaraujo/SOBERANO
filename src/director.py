# src/director.py

import random
import glob
from src.rules import RuleEngine
from src.inference import LLMDecisionEngine

# Try to load the AI library
try:
    from llama_cpp import Llama
    def initialize_llm():
        """Searches for .gguf model and starts AI."""
        model_files = glob.glob("*.gguf")
        if model_files:
            print(f">>> LOADING MODEL: {model_files[0]} ...")
            return Llama(model_path=model_files[0], n_ctx=4096, n_gpu_layers=-1, verbose=False)
        print(">>> NO MODEL FOUND.")
        return None
except ImportError:
    print(">>> LLAMA_CPP NOT INSTALLED.")
    def initialize_llm(): 
        return None


class IntelligentDirector:
    def __init__(self, event_list):
        self.all_events = event_list
        print(f">>> Director Init: {len(self.all_events)} events in memory.")
    
    def choose_event(self, llm_instance, gamestate):
        """
        Receives the LLM instance and game state.
        Returns an event dictionary.
        """
        
        # 1. RULES LAYER
        # Gamestate already comes prepared from engine with correct tags
        candidates = RuleEngine.filter_viable(self.all_events, gamestate)
        print(f">>> [RULES] {len(candidates)} viable events.")

        if not candidates:
            # Extreme fallback if rules kill everything (e.g. all events are 'hubris' and king is 'poor')
            print(">>> [ALERT] No viable events in rules. Picking random.")
            return random.choice(self.all_events)

        chosen = None

        # 2. AI LAYER
        if llm_instance and len(candidates) > 1:
            pool_ai = random.sample(candidates, min(5, len(candidates)))
            engine = LLMDecisionEngine(llm_instance)
            chosen = engine.select_event(pool_ai, gamestate)

        # 3. FALLBACK / DRAMA
        if not chosen:
            # Prioritize events with higher drama weight
            candidates.sort(key=lambda x: x.get('drama_weight', 50), reverse=True)
            # Small randomness among top 3 to avoid monotony
            top_3 = candidates[:3]
            chosen = random.choice(top_3)

        print(f">>> Event Selected: {chosen['title']}")
        return chosen