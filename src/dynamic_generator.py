"""
Dynamic Generator for Sovereign: The Living Chronicle
Generates narrative events from mechanical archetypes using AI.
"""

import json
import random
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class DynamicGenerator:
    """
    Core engine for generating dynamic narrative events.
    Uses mechanical archetypes + narrative frameworks + AI to create events.
    """
    
    def __init__(self, llm_instance, lexicon: Dict, frameworks: Dict, 
                 characters: Dict, locations: Dict, policies: List = None):
        """
        Initialize the generator with all necessary data.
        
        Args:
            llm_instance: Initialized LLM (Llama, OpenAI, etc.)
            lexicon: Loaded mechanical_lexicon.json
            frameworks: Loaded narrative_frameworks.json
            characters: Loaded character_library.json
            locations: Loaded location_library.json
            policies: List of active policies (for context injection)
        """
        self.llm = llm_instance
        self.lexicon = lexicon
        
        # --- FIX: Index frameworks by archetype_id ---
        self.frameworks = {}
        # Handle if frameworks is passed as the raw json dict containing a list
        raw_list = frameworks.get("frameworks", []) if isinstance(frameworks, dict) else []
        
        if not raw_list and isinstance(frameworks, list):
             # Handle if it was passed as a direct list
             raw_list = frameworks

        for fw in raw_list:
            a_id = fw.get("archetype_id")
            if a_id:
                if a_id not in self.frameworks:
                    self.frameworks[a_id] = []
                self.frameworks[a_id].append(fw)
        
        logger.info(f"DynamicGenerator indexed {len(raw_list)} frameworks into {len(self.frameworks)} archetype categories")
        # ---------------------------------------------

        self.characters = characters
        self.locations = locations
        self.policies = policies or []
        
        # Cache for performance
        self.archetype_cache = {}
        self.framework_cache = {}
        
        # Statistics
        self.generation_stats = {
            "total_generated": 0,
            "successful_generations": 0,
            "fallback_used": 0,
            "last_generation_time": None
        }
        
        logger.info(f"DynamicGenerator initialized with {len(lexicon.get('archetypes', []))} archetypes")
    
    def generate_event(self, game_state: Dict) -> Optional[Dict]:
        """
        Generate a complete event from current game state.
        
        Returns:
            Dict: Event in the same format as events.json, or None if generation fails
        """
        start_time = datetime.now()
        
        try:
            # Step 1: Select viable mechanical archetype
            archetype = self._select_archetype(game_state)
            if not archetype:
                logger.warning("No viable archetype found for current state")
                self.generation_stats["fallback_used"] += 1
                return None
            
            # Step 2: Select narrative framework
            framework = self._select_framework(archetype["archetype_id"], game_state)
            if not framework:
                logger.warning(f"No framework found for archetype {archetype['archetype_id']}")
                self.generation_stats["fallback_used"] += 1
                return None
            
            # Step 3: Instantiate characters and locations
            instantiated_chars = self._instantiate_characters(framework, game_state)
            instantiated_loc = self._instantiate_location(framework, game_state)
            
            # Step 4: Build context for generation
            context = self._build_generation_context(
                archetype, framework, instantiated_chars, 
                instantiated_loc, game_state
            )
            
            # Step 5: Generate with LLM
            generated_event = self._generate_with_llm(context)
            
            # Step 6: Validate and assemble final event
            if generated_event:
                final_event = self._assemble_event(
                    generated_event, archetype, context, game_state
                )
                
                # Step 7: Add metadata for tracking
                final_event["_generated"] = True
                final_event["_archetype_id"] = archetype["archetype_id"]
                final_event["_framework_id"] = framework.get("id", "unknown")
                final_event["_generation_id"] = f"GEN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                self.generation_stats["successful_generations"] += 1
                logger.info(f"Successfully generated event: {final_event.get('title', 'Untitled')}")
                
                return final_event
            else:
                # Step 8: Fallback generation
                fallback_event = self._generate_fallback(archetype, framework, game_state)
                self.generation_stats["fallback_used"] += 1
                return fallback_event
                
        except Exception as e:
            logger.error(f"Generation failed: {str(e)}", exc_info=True)
            self.generation_stats["fallback_used"] += 1
            return None
            
        finally:
            self.generation_stats["total_generated"] += 1
            self.generation_stats["last_generation_time"] = datetime.now()
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.debug(f"Generation completed in {elapsed:.2f}s")
    
    def _select_archetype(self, game_state: Dict) -> Optional[Dict]:
        """
        Select a mechanical archetype based on game state.
        Uses RuleEngine-like filtering from state_requirements.
        """
        # Get all archetypes
        all_archetypes = self.lexicon.get("archetypes", [])
        
        # Filter by state requirements
        viable_archetypes = []
        
        for archetype in all_archetypes:
            if self._archetype_is_viable(archetype, game_state):
                viable_archetypes.append(archetype)
        
        if not viable_archetypes:
            logger.warning("No viable archetypes found after filtering")
            return None
        
        # Weight by drama range and relevance
        weighted_archetypes = []
        for archetype in viable_archetypes:
            weight = self._calculate_archetype_weight(archetype, game_state)
            weighted_archetypes.append((archetype, weight))
        
        # Select based on weights
        total_weight = sum(w for _, w in weighted_archetypes)
        if total_weight == 0:
            selected = random.choice(viable_archetypes)
        else:
            r = random.uniform(0, total_weight)
            cumulative = 0
            for archetype, weight in weighted_archetypes:
                cumulative += weight
                if r <= cumulative:
                    selected = archetype
                    break
            else:
                selected = viable_archetypes[-1][0] if weighted_archetypes else random.choice(viable_archetypes)
        
        logger.debug(f"Selected archetype: {selected['archetype_id']}")
        return selected
    
    def _archetype_is_viable(self, archetype: Dict, game_state: Dict) -> bool:
        """
        Check if archetype is viable for current game state.
        """
        reqs = archetype.get("state_requirements", {})
        
        # Check required tags
        required_tags = reqs.get("required_tags", [])
        if required_tags:
            player_tags = game_state.get("reputation_tags", []) + game_state.get("state_tags", [])
            if not any(tag in player_tags for tag in required_tags):
                return False
        
        # Check prohibited tags
        prohibited_tags = reqs.get("prohibited_tags", [])
        if prohibited_tags:
            player_tags = game_state.get("reputation_tags", []) + game_state.get("state_tags", [])
            if any(tag in player_tags for tag in prohibited_tags):
                return False
        
        # Check min stats
        min_stats = reqs.get("min_stats", {})
        for stat, min_val in min_stats.items():
            if game_state.get("stats", {}).get(stat, 0) < min_val:
                return False
        
        # Check max stats
        max_stats = reqs.get("max_stats", {})
        for stat, max_val in max_stats.items():
            if game_state.get("stats", {}).get(stat, 0) > max_val:
                return False
        
        # Check theme repetition (similar to RuleEngine)
        last_themes = game_state.get("last_themes", [])
        narrative_themes = archetype.get("narrative_themes", [])
        
        # Avoid repeating the same theme too soon
        for theme in narrative_themes:
            if theme in last_themes[-2:]:  # Last 2 turns
                return False
        
        return True
    
    def _calculate_archetype_weight(self, archetype: Dict, game_state: Dict) -> float:
        """
        Calculate selection weight for an archetype.
        Higher weight = more likely to be selected.
        """
        base_weight = 50.0
        
        # Adjust by drama weight (events with appropriate drama for current state)
        drama_range = archetype.get("drama_range", [50, 50])
        drama_mid = sum(drama_range) / 2
        
        # If stability is low, prefer higher drama
        stability = game_state.get("stats", {}).get("stability", 50)
        if stability < 30:
            drama_factor = drama_mid / 100
        elif stability > 70:
            drama_factor = (100 - drama_mid) / 100
        else:
            drama_factor = 1.0
        
        # Adjust by tag relevance
        tag_factor = 1.0
        player_tags = game_state.get("reputation_tags", []) + game_state.get("state_tags", [])
        archetype_tags = archetype.get("narrative_themes", [])
        
        matching_tags = len(set(player_tags) & set(archetype_tags))
        tag_factor += matching_tags * 0.2
        
        # Random variation
        random_factor = random.uniform(0.8, 1.2)
        
        final_weight = base_weight * drama_factor * tag_factor * random_factor
        return max(1.0, final_weight)
    
    def _select_framework(self, archetype_id: str, game_state: Dict) -> Optional[Dict]:
        """
        Select a narrative framework for the given archetype.
        """
        # Lookup in the indexed dictionary
        frameworks_for_archetype = self.frameworks.get(archetype_id, [])
        
        if not frameworks_for_archetype:
            logger.warning(f"No frameworks found for archetype {archetype_id}")
            return None
        
        # Filter by game state if needed
        viable_frameworks = []
        for framework in frameworks_for_archetype:
            # Check if framework is appropriate for current state
            if self._framework_is_appropriate(framework, game_state):
                viable_frameworks.append(framework)
        
        if not viable_frameworks:
            viable_frameworks = frameworks_for_archetype
        
        # Select randomly for now (can be weighted later)
        selected = random.choice(viable_frameworks)
        logger.debug(f"Selected framework: {selected.get('plot_premise', 'Unknown')[:50]}...")
        return selected
    
    def _framework_is_appropriate(self, framework: Dict, game_state: Dict) -> bool:
        """
        Check if framework is appropriate for current game state.
        Can be extended with more sophisticated logic.
        """
        # Example: Check if framework's required stats match
        required_stats = framework.get("required_stats", {})
        for stat, min_val in required_stats.items():
            if game_state.get("stats", {}).get(stat, 0) < min_val:
                return False
        
        return True
    
    def _instantiate_characters(self, framework: Dict, game_state: Dict) -> List[Dict]:
        """
        Instantiate characters for the framework.
        """
        character_archetypes = framework.get("characters", [])
        instantiated = []
        
        for archetype_name in character_archetypes:
            # Find character template
            char_template = self._find_character_template(archetype_name)
            if char_template:
                instantiated_char = self._instantiate_character(char_template, game_state)
                instantiated.append(instantiated_char)
        
        return instantiated
    
    def _find_character_template(self, archetype_name: str) -> Optional[Dict]:
        """
        Find character template by name or archetype.
        """
        for char in self.characters.get("characters", []):
            if char.get("archetype", "").lower() == archetype_name.lower():
                return char
            if char.get("name", "").lower() == archetype_name.lower():
                return char
        
        # Fallback: return a generic character
        return {
            "name": "Unknown",
            "archetype": archetype_name,
            "description": "A mysterious figure",
            "motivation": "Unknown motives"
        }
    
    def _instantiate_character(self, template: Dict, game_state: Dict) -> Dict:
        """
        Instantiate a specific character with details.
        """
        # Add contextual details based on game state
        character = template.copy()
        
        # Personalize based on player tags
        player_tags = game_state.get("reputation_tags", [])
        
        if "tyrant" in player_tags:
            character["attitude"] = "Fearful of the king"
        elif "merciful" in player_tags:
            character["attitude"] = "Hopeful for mercy"
        else:
            character["attitude"] = "Neutral"
        
        # Add unique identifier
        character["instance_id"] = f"CHAR_{random.randint(1000, 9999)}"
        
        return character
    
    def _instantiate_location(self, framework: Dict, game_state: Dict) -> Dict:
        """
        Instantiate location for the framework.
        """
        location_names = framework.get("settings", [])
        if not location_names:
            location_names = ["Throne Room"]  # Default
        
        location_name = random.choice(location_names)
        
        # Find location template
        location_template = self._find_location_template(location_name)
        if not location_template:
            location_template = {
                "name": location_name,
                "type": "Unknown",
                "description": "An unknown location"
            }
        
        # Enhance with contextual details
        location = location_template.copy()
        
        # Add time/weather/season
        location["time_of_day"] = random.choice(["dawn", "noon", "dusk", "midnight"])
        location["weather"] = random.choice(["clear", "rain", "fog", "storm"])
        
        # Add sensory details
        sensory_details = {
            "dawn": "The first light creeps through the windows",
            "noon": "Sunlight streams through the high windows",
            "dusk": "Shadows lengthen across the floor",
            "midnight": "Only moonlight illuminates the room"
        }
        location["sensory_detail"] = sensory_details.get(location["time_of_day"], "")
        
        return location
    
    def _find_location_template(self, location_name: str) -> Optional[Dict]:
        """
        Find location template by name.
        """
        for loc in self.locations.get("locations", []):
            if loc.get("name", "").lower() == location_name.lower():
                return loc
        
        return None
    
    def _build_generation_context(self, archetype: Dict, framework: Dict, 
                                 characters: List[Dict], location: Dict, 
                                 game_state: Dict) -> Dict:
        """
        Build comprehensive context for LLM generation.
        """
        # Extract player state
        player_tags = game_state.get("reputation_tags", []) + game_state.get("state_tags", [])
        stats = game_state.get("stats", {})
        turn = game_state.get("turn", 1)
        
        # Build character descriptions
        char_descriptions = []
        for char in characters:
            desc = f"{char.get('name', 'Unknown')} - {char.get('archetype', 'unknown')}. {char.get('description', '')}"
            if "attitude" in char:
                desc += f" {char['attitude']}."
            char_descriptions.append(desc)
        
        # Get archetype mechanics for options
        mechanics = archetype.get("core_mechanics", {})
        tag_outcomes = archetype.get("tag_outcomes", [])
        
        # Build context object
        context = {
            "player_state": {
                "tags": player_tags,
                "stats": stats,
                "turn": turn,
                "active_policies": self.policies
            },
            "archetype": {
                "id": archetype["archetype_id"],
                "name": archetype["name"],
                "description": archetype["description"],
                "mechanics": mechanics,
                "tag_outcomes": tag_outcomes,
                "themes": archetype.get("narrative_themes", [])
            },
            "framework": {
                "plot_premise": framework.get("plot_premise", ""),
                "characters": char_descriptions,
                "conflict_type": framework.get("conflict_type", ""),
                "emotional_tone": framework.get("emotional_tone", ""),
                "narrative_hooks": framework.get("narrative_hooks", [])
            },
            "location": location,
            "generation_instructions": {
                "required_mechanics": f"Option effects must match: {json.dumps(mechanics)}",
                "required_tags": f"Options should lead to tags: {tag_outcomes}",
                "tone": framework.get("emotional_tone", "medieval dramatic"),
                "length": "Title: 3-7 words. Description: 3-5 sentences. Options: 1 sentence each."
            }
        }
        
        return context
    
    def _generate_with_llm(self, context: Dict) -> Optional[Dict]:
        """
        Generate event using LLM with the provided context.
        """
        if not self.llm:
            logger.warning("No LLM instance available, using fallback")
            return None
        
        try:
            # Build the prompt
            prompt = self._build_llm_prompt(context)
            
            # Call the LLM
            logger.debug("Calling LLM for generation...")
            response = self.llm(
                prompt,
                max_tokens=800,
                temperature=0.7,
                stop=["###", "Human:", "User:", "END"],
                echo=False
            )
            
            generated_text = response['choices'][0]['text']
            logger.debug(f"LLM response received: {len(generated_text)} chars")
            
            # Parse the response
            parsed_event = self._parse_llm_response(generated_text, context)
            
            if parsed_event and self._validate_generated_event(parsed_event, context):
                return parsed_event
            else:
                logger.warning("Generated event failed validation")
                return None
                
        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            return None
    
    def _build_llm_prompt(self, context: Dict) -> str:
        """
        Build the prompt for the LLM.
        """
        player_tags = ", ".join(context["player_state"]["tags"]) if context["player_state"]["tags"] else "None"
        stats_str = ", ".join([f"{k}: {v}" for k, v in context["player_state"]["stats"].items()])
        
        prompt = f"""You are the Chronicler of the Kingdom, writing events for the medieval strategy game "Sovereign."

PLAYER'S STATE:
- Reputation Tags: {player_tags}
- Kingdom Stats: {stats_str}
- Current Turn: {context["player_state"]["turn"]}

EVENT ARCHETYPE:
- Type: {context["archetype"]["name"]}
- Description: {context["archetype"]["description"]}
- Themes: {", ".join(context["archetype"]["themes"])}

STORY FRAMEWORK:
- Plot Premise: {context["framework"]["plot_premise"]}
- Conflict: {context["framework"]["conflict_type"]}
- Tone: {context["framework"]["emotional_tone"]}
- Characters Present: {", ".join(context["framework"]["characters"])}

SETTING:
- Location: {context["location"].get("name", "Unknown")}
- Time: {context["location"].get("time_of_day", "unknown")}
- Details: {context["location"].get("description", "")} {context["location"].get("sensory_detail", "")}

MECHANICAL REQUIREMENTS:
- The event must have TWO options.
- Option A must result in these mechanical effects: {json.dumps(context["archetype"]["mechanics"])}
- Option B must have different but balanced effects (use similar magnitude but different stats).
- Options should lead to these narrative tags: {context["archetype"]["tag_outcomes"]}

WRITE THE EVENT:
1. TITLE: A compelling 3-7 word title.
2. DESCRIPTION: 3-5 sentences setting the scene, incorporating the characters and location.
3. OPTION A: One sentence describing the first choice. Must align with the mechanical effects above.
4. OPTION B: One sentence describing the second choice. Should present a meaningful alternative.
5. RESPONSE A: 1-2 sentences describing the immediate outcome of choosing Option A.
6. RESPONSE B: 1-2 sentences describing the immediate outcome of choosing Option B.

FORMAT YOUR RESPONSE EXACTLY AS:
TITLE: [Your title here]

DESCRIPTION: [Your description here]

OPTION A: [Option A text]
RESPONSE A: [Response A text]

OPTION B: [Option B text]
RESPONSE B: [Response B text]

IMPORTANT: The mechanical effects for Option A are fixed. Option B should have different but similarly impactful effects. Make both choices defensible but flawed.
"""
        
        return prompt
    
    def _parse_llm_response(self, text: str, context: Dict) -> Optional[Dict]:
        """
        Parse the LLM response into a structured event.
        """
        try:
            lines = text.strip().split('\n')
            event = {
                "title": "",
                "text": "",
                "options": []
            }
            
            current_section = None
            option_buffer = []
            
            for line in lines:
                line = line.strip()
                
                if line.startswith("TITLE:"):
                    event["title"] = line[6:].strip()
                elif line.startswith("DESCRIPTION:"):
                    event["text"] = line[12:].strip()
                elif line.startswith("OPTION A:"):
                    if option_buffer:
                        parsed_opt = self._parse_option_buffer(option_buffer, "A")
                        if parsed_opt:
                            event["options"].append(parsed_opt)
                    option_buffer = [line]
                elif line.startswith("OPTION B:"):
                    if option_buffer:
                        parsed_opt = self._parse_option_buffer(option_buffer, "B")
                        if parsed_opt:
                            event["options"].append(parsed_opt)
                    option_buffer = [line]
                elif line.startswith("RESPONSE"):
                    option_buffer.append(line)
                elif option_buffer and line:
                    # Continuation of current option/response
                    option_buffer.append(line)
            
            # Parse the last option
            if option_buffer:
                # Determine if it's A or B
                if "OPTION A" in option_buffer[0]:
                    opt_id = "A"
                elif "OPTION B" in option_buffer[0]:
                    opt_id = "B"
                else:
                    opt_id = "A" if len(event["options"]) == 0 else "B"
                
                parsed_opt = self._parse_option_buffer(option_buffer, opt_id)
                if parsed_opt:
                    event["options"].append(parsed_opt)
            
            # Ensure we have exactly 2 options
            while len(event["options"]) < 2:
                opt_id = "A" if len(event["options"]) == 0 else "B"
                event["options"].append({
                    "id": opt_id,
                    "text": f"Default {opt_id} option",
                    "response": f"Default response for option {opt_id}"
                })
            
            return event
            
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
            return None
    
    def _parse_option_buffer(self, buffer: List[str], option_id: str) -> Optional[Dict]:
        """
        Parse a buffer of lines into an option object.
        """
        option_text = ""
        response_text = ""
        
        for line in buffer:
            if line.startswith(f"OPTION {option_id}:"):
                option_text = line.split(":", 1)[1].strip()
            elif line.startswith(f"RESPONSE {option_id}:"):
                response_text = line.split(":", 1)[1].strip()
            elif line.startswith("RESPONSE") and ":" in line:
                # Generic response line
                response_text = line.split(":", 1)[1].strip()
            elif option_text and not response_text:
                # Continuation of option text
                option_text += " " + line
            elif response_text:
                # Continuation of response text
                response_text += " " + line
        
        if option_text:
            return {
                "id": option_id,
                "text": option_text,
                "response": response_text or f"Response to option {option_id}"
            }
        
        return None
    
    def _validate_generated_event(self, event: Dict, context: Dict) -> bool:
        """
        Validate that the generated event meets requirements.
        """
        # Basic validation
        required_fields = ["title", "text", "options"]
        for field in required_fields:
            if field not in event:
                logger.warning(f"Missing field in generated event: {field}")
                return False
        
        if len(event["options"]) != 2:
            logger.warning(f"Expected 2 options, got {len(event['options'])}")
            return False
        
        # Check option IDs
        option_ids = [opt["id"] for opt in event["options"]]
        if "A" not in option_ids or "B" not in option_ids:
            logger.warning("Options must have IDs 'A' and 'B'")
            return False
        
        # Check text lengths
        if len(event["title"]) < 3 or len(event["title"]) > 100:
            logger.warning(f"Title length invalid: {len(event['title'])} chars")
            return False
        
        if len(event["text"]) < 50 or len(event["text"]) > 500:
            logger.warning(f"Description length invalid: {len(event['text'])} chars")
            return False
        
        for option in event["options"]:
            if len(option["text"]) < 10 or len(option["text"]) > 200:
                logger.warning(f"Option text length invalid: {len(option['text'])} chars")
                return False
        
        return True
    
    def _assemble_event(self, generated_event: Dict, archetype: Dict, 
                       context: Dict, game_state: Dict) -> Dict:
        """
        Assemble final event with mechanics and metadata.
        """
        # Generate a unique ID
        import hashlib
        event_hash = hashlib.md5(
            f"{archetype['archetype_id']}_{datetime.now().timestamp()}".encode()
        ).hexdigest()[:8]
        event_id = int(f"9{event_hash}", 16) % 1000000  # 6-digit ID starting with 9
        
        # Determine theme from archetype
        themes = archetype.get("narrative_themes", [])
        theme = themes[0] if themes else "management"
        
        # Get semantic triggers from player tags
        semantic_triggers = []
        player_tags = game_state.get("reputation_tags", []) + game_state.get("state_tags", [])
        for tag in player_tags[:3]:  # Use first 3 tags as triggers
            semantic_triggers.append(tag)
        
        # Get drama weight from archetype
        drama_range = archetype.get("drama_range", [50, 50])
        drama_weight = random.randint(drama_range[0], drama_range[1])
        
        # Build the final event
        final_event = {
            "id": event_id,
            "title": generated_event["title"],
            "text": generated_event["text"],
            "theme": theme,
            "semantic_trigger": semantic_triggers,
            "drama_weight": drama_weight,
            "options": []
        }
        
        # Add options with mechanics
        mechanics = archetype.get("core_mechanics", {})
        tag_outcomes = archetype.get("tag_outcomes", [])
        
        for i, option in enumerate(generated_event["options"]):
            option_id = option["id"]
            
            # Distribute mechanics between options
            if option_id == "A":
                # Option A gets the archetype's core mechanics
                option_effects = mechanics.copy()
                option_tags = tag_outcomes[:len(tag_outcomes)//2] if len(tag_outcomes) > 1 else tag_outcomes
            else:
                # Option B gets inverse/alternative mechanics
                option_effects = self._generate_alternative_mechanics(mechanics)
                option_tags = tag_outcomes[len(tag_outcomes)//2:] if len(tag_outcomes) > 1 else []
            
            final_option = {
                "id": option_id,
                "text": option["text"],
                "effect": option_effects,
                "effect_tags": option_tags,
                "response": option.get("response", f"Response to option {option_id}")
            }
            final_event["options"].append(final_option)
        
        return final_event
    
    def _generate_alternative_mechanics(self, base_mechanics: Dict) -> Dict:
        """
        Generate alternative mechanics for Option B.
        Inverse or complementary to Option A.
        """
        alternative = {}
        
        for stat, value in base_mechanics.items():
            # Invert or modify the effect
            if value > 0:
                alternative[stat] = -value * random.uniform(0.8, 1.2)
            elif value < 0:
                alternative[stat] = -value * random.uniform(0.8, 1.2)
            else:
                # If zero, create a small effect
                alternative[stat] = random.choice([-5, 5])
        
        # Ensure at least one effect is positive
        if all(v <= 0 for v in alternative.values()):
            # Pick a random stat to make positive
            stat = random.choice(list(alternative.keys()))
            alternative[stat] = abs(alternative[stat])
        
        return alternative
    
    def _generate_fallback(self, archetype: Dict, framework: Dict, game_state: Dict) -> Dict:
        """
        Generate a fallback event without LLM.
        """
        logger.info("Using fallback template generation")
        
        # Generate a unique ID
        import hashlib
        event_hash = hashlib.md5(
            f"FALLBACK_{archetype['archetype_id']}_{datetime.now().timestamp()}".encode()
        ).hexdigest()[:8]
        event_id = int(f"8{event_hash}", 16) % 1000000
        
        # Use framework hooks
        hooks = framework.get("narrative_hooks", ["A situation arises that demands your attention."])
        hook = random.choice(hooks)
        
        # Get characters for flavor
        characters = framework.get("characters", ["advisor", "commoner"])
        char_desc = random.choice(characters)
        
        # Build fallback event
        event = {
            "id": event_id,
            "title": f"The {archetype['name']}",
            "text": f"{hook} {char_desc.capitalize()} approaches you with urgent news.",
            "theme": archetype.get("narrative_themes", ["management"])[0],
            "semantic_trigger": [],
            "drama_weight": sum(archetype.get("drama_range", [50, 50])) // 2,
            "_generated": True,
            "_fallback": True,
            "_archetype_id": archetype["archetype_id"],
            "options": []
        }
        
        # Add options with archetype mechanics
        mechanics = archetype.get("core_mechanics", {})
        tag_outcomes = archetype.get("tag_outcomes", [])
        
        option_a = {
            "id": "A",
            "text": f"Take decisive action regarding {archetype['name'].lower()}",
            "effect": mechanics.copy(),
            "effect_tags": tag_outcomes[:len(tag_outcomes)//2] if tag_outcomes else [],
            "response": "Your decision sets events in motion with significant consequences."
        }
        
        option_b = {
            "id": "B",
            "text": f"Adopt a cautious approach to {archetype['name'].lower()}",
            "effect": self._generate_alternative_mechanics(mechanics),
            "effect_tags": tag_outcomes[len(tag_outcomes)//2:] if tag_outcomes else [],
            "response": "Your careful consideration yields different, but no less impactful, results."
        }
        
        event["options"].append(option_a)
        event["options"].append(option_b)
        
        return event
    
    def get_stats(self) -> Dict:
        """Get generation statistics."""
        return self.generation_stats.copy()


class GenerationError(Exception):
    """Custom exception for generation errors."""
    pass