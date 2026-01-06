# Quick Start Guide - Trados Enterprise HA Integration

## You've successfully created the integration! 🎉

All Phase 1 features are implemented and ready to test.

## What You Have

✅ **6 Sensors Ready:**
1. Total Tasks
2. Tasks Created (pending)
3. Tasks In Progress
4. Tasks Completed
5. Overdue Tasks
6. Total Words

✅ **Features:**
- Auth0 authentication with token caching
- Configurable polling (5-120 minutes, default 15)
- Multi-user support (multiple config entries)
- Rich sensor attributes with task details
- Proper error handling and logging

## Testing Your Integration

### 1. Start Home Assistant

```powershell
# Make sure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Start Home Assistant
E:/HomeAssistant/.venv/Scripts/python.exe -m homeassistant --config d:\Code\HomeAssistant\config --verbose
```

### 2. Access the UI

Open your browser to: **http://localhost:8123**

### 3. Complete Onboarding

- Create an owner account
- Set your location (optional)
- Configure basic settings

### 4. Add the Trados Integration

1. Go to **Settings** → **Devices & Services**
2. Click the **+ ADD INTEGRATION** button (bottom right)
3. Search for **"Trados Enterprise"**
4. Enter your credentials:
   - **Client ID**: From your Trados application
   - **Client Secret**: From your Trados application
   - **Tenant ID**: Your Trados Account ID (e.g., `2ef3c10e74fc39104e633c11`)
   - **Region**: `eu` (or your region)
   - **Scan Interval**: `15` (minutes)

### 5. View Your Sensors

After configuration, you'll see 6 new sensors. Go to:
- **Developer Tools** → **States**
- Filter by `trados_enterprise`

You should see sensors like:
- `sensor.trados_enterprise_total_tasks`
- `sensor.trados_enterprise_tasks_in_progress`
- `sensor.trados_enterprise_overdue_tasks`
- etc.

## Troubleshooting

### Integration Not Found

If you don't see "Trados Enterprise" in the integration list:
1. Stop Home Assistant
2. Check that `custom_components/trados_enterprise/` exists with all files
3. Restart Home Assistant with `--verbose` flag
4. Check logs for errors

### Authentication Errors

Check the Home Assistant logs:
```powershell
# Logs are in: config/home-assistant.log
# Or watch real-time in the console when running with --verbose
```

Common issues:
- **Wrong Client ID/Secret**: Double-check from Trados UI
- **Wrong Tenant ID**: Should be from Account Information
- **Wrong Region**: Must match your Trados instance (`eu`, `us`, etc.)

### No Data Appearing

1. Check sensor states in Developer Tools
2. Look at sensor attributes for error messages
3. Verify API permissions for your service user
4. Check Home Assistant logs for API errors

## Next Steps

### Create Automations

Example automation to alert on overdue tasks:

```yaml
# In config/automations.yaml
- alias: "Alert on Overdue Trados Tasks"
  trigger:
    - platform: state
      entity_id: sensor.trados_enterprise_overdue_tasks
  condition:
    - condition: numeric_state
      entity_id: sensor.trados_enterprise_overdue_tasks
      above: 0
  action:
    - service: persistent_notification.create
      data:
        title: "Overdue Tasks!"
        message: "You have {{ states('sensor.trados_enterprise_overdue_tasks') }} overdue translation tasks."
```

### View in Dashboard

Add sensors to your dashboard (Lovelace):

```yaml
# Example card
type: entities
title: Trados Tasks
entities:
  - sensor.trados_enterprise_total_tasks
  - sensor.trados_enterprise_tasks_in_progress
  - sensor.trados_enterprise_overdue_tasks
  - sensor.trados_enterprise_total_words
```

### Phase 2 Features (Coming Next)

When ready, we can add:
- 🔄 Webhook support for real-time updates
- 🔄 Per-project sensors
- 🔄 Calendar integration for due dates
- 🔄 Task completion notifications

## File Structure

```
d:\Code\HomeAssistant\
├── custom_components/
│   └── trados_enterprise/
│       ├── __init__.py           # Integration setup
│       ├── api.py                # Trados API client
│       ├── config_flow.py        # UI configuration
│       ├── const.py              # Constants
│       ├── coordinator.py        # Data coordinator
│       ├── manifest.json         # Integration metadata
│       ├── sensor.py             # Sensor platform
│       └── strings.json          # UI strings
├── config/
│   ├── configuration.yaml        # HA config
│   └── home-assistant.log        # Logs
├── venv/                         # Python virtual env
├── README.md                     # Documentation
└── test_integration.py           # Test script
```

## Development Workflow

### Making Changes

1. Edit files in `custom_components/trados_enterprise/`
2. Restart Home Assistant to reload the integration
3. Check logs for errors
4. Test with your Trados credentials

### Debugging

Enable debug logging in `config/configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.trados_enterprise: debug
```

### Testing Without HA Running

```powershell
# Quick validation
E:/HomeAssistant/.venv/Scripts/python.exe test_integration.py
```

## Support

- 📖 **README**: See `README.md` for full documentation
- 🐛 **Issues**: Check Home Assistant logs first
- 📝 **API Docs**: https://eu.cloud.trados.com/lc/api-docs/

## You're All Set! 🚀

Your Trados Enterprise Home Assistant integration is ready to use. Start Home Assistant and configure it with your credentials to see your translation tasks!
