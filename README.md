# Trados Cloud Integration for Home Assistant

Monitor your Trados Cloud translation tasks directly in Home Assistant.

## Features

### Phase 1 (Current)
- ✅ **Total Tasks** - Count of all assigned tasks
- ✅ **Tasks by Status** - Separate sensors for Created, In Progress, and Completed tasks
- ✅ **Overdue Tasks** - Count and details of overdue tasks
- ✅ **Total Words** - Total word count across all your tasks
- ✅ **Configurable Polling** - Set update frequency (5-120 minutes, default: 15)
- ✅ **Multi-user Support** - Each config entry supports a different user/service account

### Phase 2 (Planned)
- 🔄 Webhook support for real-time updates
- 🔄 Per-project task tracking
- 🔄 Due date notifications/alerts
- 🔄 Task assignment automation

## Installation

### Prerequisites

You need the following from your Trados Cloud account:
1. **Client ID** - From your Trados application
2. **Client Secret** - From your Trados application  
3. **Tenant ID** - Your Trados Account ID (format: `2ef3c10e74fc39104e633c11`)
4. **Region** - Your API region (`eu`, `us`, etc.)

### Getting Credentials

1. Log in to Trados Cloud
2. Go to **Manage Account** → **Integrations** → **Applications**
3. Create a new application or use an existing one
4. Note the **Client ID** and **Client Secret**
5. Find your **Tenant ID** in Account Information (Trados Account ID)

### Setup in Home Assistant

#### Option 1: HACS (Recommended - when published)
1. Open HACS
2. Go to Integrations
3. Search for "Trados Enterprise"
4. Click Install

#### Option 2: Manual Installation
1. Copy the `custom_components/trados_cloud` folder to your HA `custom_components` directory
2. Restart Home Assistant

### Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Trados Enterprise"
4. Enter your credentials:
   - Client ID
   - Client Secret
   - Tenant ID
   - Region (default: `eu`)
   - Update Interval in minutes (default: 15)
5. Click Submit

## Sensors

Once configured, you'll get these sensors:

| Sensor | Entity ID | Description |
|--------|-----------|-------------|
| Total Tasks | `sensor.trados_cloud_total_tasks` | Total assigned tasks |
| Tasks Created | `sensor.trados_cloud_tasks_created` | Tasks in "Created" status |
| Tasks In Progress | `sensor.trados_cloud_tasks_in_progress` | Tasks currently being worked on |
| Tasks Completed | `sensor.trados_cloud_tasks_completed` | Completed tasks |
| Overdue Tasks | `sensor.trados_cloud_overdue_tasks` | Tasks past their due date |
| Total Words | `sensor.trados_cloud_total_words` | Total word count across all tasks |

### Sensor Attributes

Each sensor includes additional attributes with detailed information:

**Total Tasks:**
- List of upcoming tasks (due in next 48 hours)
- Task counts by project
- Last update timestamp

**Tasks by Status:**
- List of tasks with that status (up to 10)
- Project name, due date, task type

**Overdue Tasks:**
- List of overdue tasks with hours overdue
- Sorted by most overdue first

**Total Words:**
- Words pending, in progress, and completed

## Example Automations

### Alert on Overdue Tasks

```yaml
automation:
  - alias: "Trados - Overdue Task Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.trados_cloud_overdue_tasks
        above: 0
    action:
      - service: notify.mobile_app
        data:
          title: "⚠️ Overdue Translation Tasks"
          message: "You have {{ states('sensor.trados_cloud_overdue_tasks') }} overdue tasks!"
```

### Daily Task Summary

```yaml
automation:
  - alias: "Trados - Morning Task Summary"
    trigger:
      - platform: time
        at: "09:00:00"
    action:
      - service: notify.mobile_app
        data:
          title: "📋 Your Trados Tasks Today"
          message: >
            Total: {{ states('sensor.trados_cloud_total_tasks') }}
            In Progress: {{ states('sensor.trados_cloud_tasks_in_progress') }}
            Overdue: {{ states('sensor.trados_cloud_overdue_tasks') }}
```

## Development

### Running Locally

1. Clone this repository
2. Set up Python virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1  # Windows
   source venv/bin/activate     # Linux/Mac
   ```
3. Install Home Assistant:
   ```bash
   pip install homeassistant
   ```
4. Copy integration to custom_components:
   ```bash
   mkdir config\custom_components
   cp -r custom_components\trados_cloud config\custom_components\
   ```
5. Run Home Assistant:
   ```bash
   hass --config config/ --verbose
   ```

### Project Structure

```
custom_components/trados_enterprise/
├── __init__.py          # Integration setup
├── manifest.json        # Integration metadata
├── const.py             # Constants and configuration
├── config_flow.py       # UI configuration flow
├── api.py               # Trados API client
├── coordinator.py       # Data update coordinator
├── sensor.py            # Sensor platform
└── strings.json         # UI translations
```

## Troubleshooting

### Authentication Errors

- Verify your Client ID and Client Secret are correct
- Ensure the service user has access to the account
- Check that the Tenant ID matches your account

### No Data Showing

- Check the Home Assistant logs for errors
- Verify the region is correct (`eu`, `us`, etc.)
- Ensure the API credentials have proper permissions

### Slow Updates

- Increase the update interval in integration options
- Check API rate limits in Trados documentation
- Monitor Home Assistant logs for rate limit errors

## API Rate Limits

Trados Cloud has the following limits:
- Maximum 16 token requests per day
- Tokens are cached for 24 hours
- This integration respects these limits

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/trados-enterprise-ha/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/trados-enterprise-ha/discussions)
- **Documentation**: [Trados API Docs](https://eu.cloud.trados.com/lc/api-docs/)

## License

MIT License - See LICENSE file for details

## Credits

Built for the Home Assistant community by [Your Name]
