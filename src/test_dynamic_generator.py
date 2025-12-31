# test_dynamic_generator.py
"""
Test script for DynamicGenerator and EnhancedIntelligentDirector.
Run with: python test_dynamic_generator.py
"""

import json
import sys
import os
from pathlib import Path

# Add the src directory to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def load_test_data():
    """Load test data files."""
    data_dir = Path('data')
    
    files_to_load = {
        'lexicon': 'mechanical_lexicon.json',
        'frameworks': 'narrative_frameworks.json',
        'characters': 'character_library.json',
        'locations': 'location_library.json'
    }
    
    loaded_data = {}
    
    for key, filename in files_to_load.items():
        filepath = data_dir / filename
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                loaded_data[key] = json.load(f)
            print(f"✓ Loaded {filename}: {len(loaded_data[key].get('archetypes' if key == 'lexicon' else key, []))} entries")
        except FileNotFoundError:
            print(f"✗ Missing file: {filename}")
            loaded_data[key] = {}
        except json.JSONDecodeError as e:
            print(f"✗ JSON error in {filename}: {e}")
            loaded_data[key] = {}
    
    return loaded_data

def create_mock_gamestate():
    """Create a realistic mock game state for testing."""
    return {
        "turn": 15,
        "stats": {
            "treasury": 65,
            "military": 40,
            "popularity": 55,
            "stability": 60,
            "agriculture": 50,
            "commerce": 45
        },
        "reputation_tags": ["tyrant", "autocrat", "rich"],
        "state_tags": ["midas", "spartan"],
        "last_themes": ["hubris", "intrigue", "war"],
        "active_policies": ["absolutism", "serfdom"],
        "game_over": False,
        "decision_memory": [
            "Year 12: Executed the prophet",
            "Year 13: Crushed peasant rebellion",
            "Year 14: Built golden statue"
        ]
    }

def test_data_integrity(loaded_data):
    """Test that data files have correct structure."""
    print("\n" + "="*60)
    print("DATA INTEGRITY TESTS")
    print("="*60)
    
    # Test lexicon
    lexicon = loaded_data.get('lexicon', {})
    archetypes = lexicon.get('archetypes', [])
    
    if not archetypes:
        print("✗ No archetypes found in lexicon")
        return False
    
    print(f"✓ Found {len(archetypes)} archetypes")
    
    # Check a few required fields
    required_fields = ['archetype_id', 'name', 'core_mechanics']
    for archetype in archetypes[:3]:  # Check first 3
        for field in required_fields:
            if field not in archetype:
                print(f"✗ Archetype missing required field: {field}")
                return False
    
    print("✓ All archetypes have required fields")
    
    # Test frameworks
    frameworks = loaded_data.get('frameworks', {})
    if not frameworks:
        print("✗ No frameworks found")
        return False
    
    # Check if we have frameworks for some archetypes
    archetype_ids = [a['archetype_id'] for a in archetypes[:5]]
    frameworks_count = sum(len(frameworks.get(aid, [])) for aid in archetype_ids)
    print(f"✓ Found frameworks for {frameworks_count} archetype instances")
    
    return True

def test_generator_without_llm(loaded_data):
    """Test DynamicGenerator without LLM (uses fallback)."""
    print("\n" + "="*60)
    print("DYNAMIC GENERATOR TEST (No LLM)")
    print("="*60)
    
    try:
        from src.dynamic_generator import DynamicGenerator
        
        # Create generator without LLM
        generator = DynamicGenerator(
            llm_instance=None,
            lexicon=loaded_data['lexicon'],
            frameworks=loaded_data['frameworks'],
            characters=loaded_data['characters'],
            locations=loaded_data['locations']
        )
        
        print("✓ DynamicGenerator initialized without LLM")
        
        # Test archetype selection
        gamestate = create_mock_gamestate()
        archetype = generator._select_archetype(gamestate)
        
        if archetype:
            print(f"✓ Selected archetype: {archetype['archetype_id']} - {archetype['name']}")
        else:
            print("✗ Failed to select archetype")
            return False
        
        # Test framework selection
        framework = generator._select_framework(archetype['archetype_id'], gamestate)
        
        if framework:
            print(f"✓ Selected framework: {framework.get('plot_premise', 'Unknown')[:50]}...")
        else:
            print("✗ Failed to select framework")
            return False
        
        # Test fallback generation
        fallback_event = generator._generate_fallback(archetype, framework, gamestate)
        
        if fallback_event:
            print(f"✓ Generated fallback event: {fallback_event['title']}")
            print(f"  Options: {[opt['id'] for opt in fallback_event['options']]}")
            print(f"  Theme: {fallback_event['theme']}")
            
            # Verify structure
            required = ['id', 'title', 'text', 'options', 'theme']
            for field in required:
                if field not in fallback_event:
                    print(f"✗ Missing field in event: {field}")
                    return False
            
            print("✓ Event has all required fields")
            
            # Verify options
            if len(fallback_event['options']) != 2:
                print(f"✗ Expected 2 options, got {len(fallback_event['options'])}")
                return False
            
            print("✓ Event has 2 options")
            
            # Check mechanics
            mechanics_a = fallback_event['options'][0]['effect']
            mechanics_b = fallback_event['options'][1]['effect']
            
            print(f"  Option A effects: {mechanics_a}")
            print(f"  Option B effects: {mechanics_b}")
            
            return True
        else:
            print("✗ Failed to generate fallback event")
            return False
            
    except ImportError as e:
        print(f"✗ Could not import DynamicGenerator: {e}")
        return False
    except Exception as e:
        print(f"✗ Generator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_director_integration(loaded_data):
    """Test the EnhancedIntelligentDirector."""
    print("\n" + "="*60)
    print("DIRECTOR INTEGRATION TEST")
    print("="*60)
    
    try:
        from src.director_integration import EnhancedIntelligentDirector
        
        # Load some static events for testing
        events_file = Path('data') / 'events.json'
        if not events_file.exists():
            print("✗ events.json not found")
            return False
        
        with open(events_file, 'r', encoding='utf-8') as f:
            static_events = json.load(f)
        
        print(f"✓ Loaded {len(static_events)} static events")
        
        # Create director without dynamic generator
        director = EnhancedIntelligentDirector(
            event_list=static_events,
            dynamic_generator=None
        )
        
        print("✓ EnhancedIntelligentDirector initialized")
        
        # Test static selection
        gamestate = create_mock_gamestate()
        
        # Mock the LLMDecisionEngine to avoid actual LLM calls
        class MockLLM:
            def __call__(self, *args, **kwargs):
                return {'choices': [{'text': 'Choice: #1'}]}
        
        mock_llm = MockLLM()
        
        event = director.choose_event(mock_llm, gamestate)
        
        if event:
            print(f"✓ Director selected event: {event['title']}")
            print(f"  ID: {event['id']}")
            print(f"  Theme: {event.get('theme', 'N/A')}")
            
            # Check director stats
            stats = director.get_stats()
            print(f"  Director stats: {stats['static_events_selected']} static, "
                  f"{stats['dynamic_events_selected']} dynamic")
            
            return True
        else:
            print("✗ Director failed to select event")
            return False
            
    except ImportError as e:
        print(f"✗ Could not import EnhancedIntelligentDirector: {e}")
        return False
    except Exception as e:
        print(f"✗ Director test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_complete_pipeline(loaded_data):
    """Test the complete pipeline from archetype to event."""
    print("\n" + "="*60)
    print("COMPLETE PIPELINE TEST")
    print("="*60)
    
    try:
        from src.dynamic_generator import DynamicGenerator
        
        # Create generator
        generator = DynamicGenerator(
            llm_instance=None,  # No LLM for testing
            lexicon=loaded_data['lexicon'],
            frameworks=loaded_data['frameworks'],
            characters=loaded_data['characters'],
            locations=loaded_data['locations']
        )
        
        gamestate = create_mock_gamestate()
        
        # Step 1: Generate event through main method
        print("Step 1: Generating complete event...")
        event = generator.generate_event(gamestate)
        
        if not event:
            print("✗ Failed to generate event")
            return False
        
        print(f"✓ Generated event: {event['title']}")
        print(f"  Archetype: {event.get('_archetype_id', 'Unknown')}")
        print(f"  Generated: {event.get('_generated', False)}")
        print(f"  Fallback: {event.get('_fallback', False)}")
        
        # Step 2: Verify event structure
        print("\nStep 2: Verifying event structure...")
        
        required_fields = ['id', 'title', 'text', 'options', 'theme', 'drama_weight']
        missing_fields = [f for f in required_fields if f not in event]
        
        if missing_fields:
            print(f"✗ Missing fields: {missing_fields}")
            return False
        
        print("✓ All required fields present")
        
        # Step 3: Verify options
        print("\nStep 3: Verifying options...")
        
        if len(event['options']) != 2:
            print(f"✗ Expected 2 options, got {len(event['options'])}")
            return False
        
        print(f"✓ Has 2 options: {event['options'][0]['id']} and {event['options'][1]['id']}")
        
        # Check option structure
        for option in event['options']:
            opt_required = ['id', 'text', 'effect', 'response']
            if not all(field in option for field in opt_required):
                print(f"✗ Option {option['id']} missing required fields")
                return False
        
        print("✓ All options have required fields")
        
        # Step 4: Check mechanics are valid
        print("\nStep 4: Checking mechanics...")
        
        for option in event['options']:
            effects = option['effect']
            if not isinstance(effects, dict):
                print(f"✗ Option {option['id']} effects not a dict")
                return False
            
            # Check effect values are integers
            for stat, value in effects.items():
                if not isinstance(value, (int, float)):
                    print(f"✗ Option {option['id']} effect {stat}={value} not numeric")
                    return False
        
        print("✓ All effects are valid numeric dictionaries")
        
        # Step 5: Check tags
        print("\nStep 5: Checking tags...")
        
        for option in event['options']:
            if 'effect_tags' in option:
                tags = option['effect_tags']
                if not isinstance(tags, list):
                    print(f"✗ Option {option['id']} tags not a list")
                    return False
        
        print("✓ Tags are valid lists")
        
        # Step 6: Test serialization (can be converted to JSON)
        print("\nStep 6: Testing JSON serialization...")
        
        try:
            json_str = json.dumps(event, ensure_ascii=False)
            parsed_back = json.loads(json_str)
            
            if parsed_back['id'] == event['id']:
                print("✓ Event can be serialized/deserialized")
            else:
                print("✗ Serialization changed event ID")
                return False
        except Exception as e:
            print(f"✗ JSON serialization failed: {e}")
            return False
        
        print("\n" + "="*60)
        print("PIPELINE TEST COMPLETE - SUCCESS!")
        print("="*60)
        
        # Print final event summary
        print(f"\nEVENT SUMMARY:")
        print(f"Title: {event['title']}")
        print(f"Description: {event['text'][:100]}...")
        print(f"\nOption A: {event['options'][0]['text']}")
        print(f"  Effects: {event['options'][0]['effect']}")
        print(f"  Tags: {event['options'][0].get('effect_tags', [])}")
        
        print(f"\nOption B: {event['options'][1]['text']}")
        print(f"  Effects: {event['options'][1]['effect']}")
        print(f"  Tags: {event['options'][1].get('effect_tags', [])}")
        
        return True
        
    except Exception as e:
        print(f"✗ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("SOVEREIGN DYNAMIC GENERATOR TEST SUITE")
    print("="*60)
    
    # Load data first
    print("\nLoading test data...")
    loaded_data = load_test_data()
    
    if not all(loaded_data.values()):
        print("\n✗ Some data files failed to load. Please check:")
        for key, data in loaded_data.items():
            if not data:
                print(f"  - {key}")
        return False
    
    # Run tests
    tests = [
        ("Data Integrity", lambda: test_data_integrity(loaded_data)),
        ("Generator (No LLM)", lambda: test_generator_without_llm(loaded_data)),
        ("Director Integration", lambda: test_director_integration(loaded_data)),
        ("Complete Pipeline", lambda: test_complete_pipeline(loaded_data))
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\nRunning: {test_name}")
            success = test_func()
            results.append((test_name, success))
            
            if success:
                print(f"✓ {test_name}: PASSED")
            else:
                print(f"✗ {test_name}: FAILED")
                
        except Exception as e:
            print(f"✗ {test_name}: ERROR - {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! DynamicGenerator is ready.")
        print("\nNext steps:")
        print("1. Start the server: python main.py")
        print("2. Play a few turns to see dynamic events (30% chance)")
        print("3. Monitor logs for: '>>> DYNAMIC EVENT:' messages")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    # Create a simple mock if LLMDecisionEngine isn't available
    try:
        from src.inference import LLMDecisionEngine
    except ImportError:
        print("Note: LLMDecisionEngine not available, using mocks")
    
    success = run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)