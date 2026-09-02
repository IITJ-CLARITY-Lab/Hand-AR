"""
Standalone Explore Mode for Point Cloud Roaming.
Thin wrapper for backward compatibility — delegates to handarm.engine.explore_standalone.

Usage:
    python3 explore.py [path/to/cloud.csv]
"""
from handarm.engine.explore_standalone import main

if __name__ == "__main__":
    main()