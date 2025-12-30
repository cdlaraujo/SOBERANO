# src/inference.py

import re
from src.prompts import DIRECTOR_THOUGHT_PROCESS

class LLMDecisionEngine:
    """
    Layer 3: Neural Decision Engine.
    Manages the call to the LLM and safely extracts the response.
    """
    def __init__(self, llm_instance):
        self.llm = llm_instance

    def select_event(self, candidates, gamestate):
        """
        Uses the LLM to rank events. Returns None if it fails.
        """
        if not self.llm or not candidates:
            return None

        # Prepare context
        tags = gamestate.get('reputation_tags', [])
        stats_str = ", ".join([f"{k}:{v}" for k,v in gamestate['stats'].items()])
        
        # Format option list
        list_fmt = "\n".join([
            f"#{i+1} [Theme: {ev.get('theme','general').upper()}] {ev['title']}" 
            for i, ev in enumerate(candidates)
        ])

        # Fill template
        prompt = DIRECTOR_THOUGHT_PROCESS.format(
            player_tags=", ".join(tags) if tags else "Neutral",
            stats_summary=stats_str,
            momentum="Normal", # Can be improved later with real data
            event_list=list_fmt
        )

        try:
            # Conservative configuration to ensure obedience
            output = self.llm(
                prompt,
                max_tokens=150, # Space for "Reasoning"
                temperature=0.3,
                stop=["###", "Human:", "User:"],
                echo=False
            )
            text = output['choices'][0]['text']
            print(f">>> AI THOUGHT:\n{text.strip()}")

            return self._extract_decision(text, candidates)

        except Exception as e:
            print(f">>> INFERENCE ERROR: {e}")
            return None

    def _extract_decision(self, text, candidates):
        """Searches for the choice number in the generated text."""
        # 1. Tries to find explicit pattern "Choice: #1"
        match = re.search(r'Choice:.*?#?(\d+)', text, re.IGNORECASE)
        
        # 2. If fails, searches for the last number mentioned in the text
        if not match:
            numbers = re.findall(r'\b(\d+)\b', text)
            if numbers:
                match = type('obj', (object,), {'group': lambda x: numbers[-1]})

        if match:
            try:
                idx = int(match.group(1)) - 1
                if 0 <= idx < len(candidates):
                    return candidates[idx]
            except:
                pass
        
        return None