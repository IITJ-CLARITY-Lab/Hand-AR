"""
Configuration module for Hand-AR project.
Loads settings from .env file or uses defaults.
"""

import os
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()

# Try to load .env file
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
    except ImportError:
        print("ℹ python-dotenv not installed. Install with: pip install python-dotenv")
        print("  For now, using defaults. .env file will be ignored.")
else:
    print(f"ℹ No .env file found. Using defaults. Copy .env.example to .env to customize.")

# Camera Settings
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
MIN_DETECTION_CONFIDENCE = float(os.getenv("MIN_DETECTION_CONFIDENCE", "0.8"))
MIN_TRACKING_CONFIDENCE = float(os.getenv("MIN_TRACKING_CONFIDENCE", "0.8"))

# Camera Feed Resolution
FEED_WIDTH = int(os.getenv("FEED_WIDTH", "320"))
FEED_HEIGHT = int(os.getenv("FEED_HEIGHT", "240"))

# Gesture Smoothing
SMOOTHING_ALPHA = float(os.getenv("SMOOTHING_ALPHA", "0.25"))

# Paths
SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "./screenshots")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
MODELS_COMPRESSED_DIR = os.path.join(PROJECT_ROOT, "models_compressed")

# Debug
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

# Validation
def validate_config() -> list:
    """
    Validates loaded configuration values against allowed ranges and constraints.

    Returns:
        list: List of string error messages describing configuration validation failures.
    """
    errors = []
    
    if CAMERA_INDEX < 0:
        errors.append("CAMERA_INDEX must be >= 0")
    
    if not (0 < MIN_DETECTION_CONFIDENCE <= 1):
        errors.append("MIN_DETECTION_CONFIDENCE must be between 0 and 1")
    
    if not (0 < MIN_TRACKING_CONFIDENCE <= 1):
        errors.append("MIN_TRACKING_CONFIDENCE must be between 0 and 1")
    
    if FEED_WIDTH < 100 or FEED_HEIGHT < 100:
        errors.append("Feed resolution minimum is 100x100")
    
    if not (0 <= SMOOTHING_ALPHA <= 1):
        errors.append("SMOOTHING_ALPHA must be between 0 and 1")
    
    return errors

# Check for validation errors
config_errors = validate_config()
if config_errors:
    print("⚠️  Configuration errors found:")
    for error in config_errors:
        print(f"  - {error}")
    print("\nPlease check your .env file or use .env.example as reference.")

if DEBUG:
    print("=" * 50)
    print("DEBUG MODE ENABLED")
    print("Configuration:")
    print(f"  Camera Index: {CAMERA_INDEX}")
    print(f"  Detection Confidence: {MIN_DETECTION_CONFIDENCE}")
    print(f"  Feed Resolution: {FEED_WIDTH}x{FEED_HEIGHT}")
    print(f"  Models Directory: {MODELS_DIR}")
    print("=" * 50)
