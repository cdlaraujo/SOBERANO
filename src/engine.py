# [file name]: src/engine.py
# src/engine.py

from engine.core import GameEngine

# The old monolithic engine.py is now just a wrapper that uses the refactored engine module
# This maintains backward compatibility while using the modular architecture

# Simply export the GameEngine class from the engine.core module
# All functionality is now delegated to the modular components