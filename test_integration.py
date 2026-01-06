"""Test script to validate the Trados Enterprise integration."""
import sys
import os

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

try:
    # Test imports
    from trados_enterprise import const
    from trados_enterprise import api
    from trados_enterprise import coordinator
    from trados_enterprise import sensor
    from trados_enterprise import config_flow
    
    print("✅ All modules imported successfully!")
    print(f"   Domain: {const.DOMAIN}")
    print(f"   Default scan interval: {const.DEFAULT_SCAN_INTERVAL}")
    print(f"   API Base URL: {const.API_BASE_URL}")
    print(f"   Sensors: {const.SENSOR_TOTAL_TASKS}, {const.SENSOR_TASKS_CREATED}, etc.")
    print()
    print("🎉 Integration structure is valid!")
    print()
    print("Next steps:")
    print("1. Start Home Assistant: hass --config config/ --verbose")
    print("2. Open browser to http://localhost:8123")
    print("3. Complete onboarding")
    print("4. Go to Settings → Devices & Services")
    print("5. Click 'Add Integration' and search for 'Trados Enterprise'")
    print("6. Enter your Trados credentials")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
