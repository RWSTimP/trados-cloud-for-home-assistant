# Trados Cloud Integration for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Default-orange.svg)](https://hacs.xyz)
[![License](https://img.shields.io/github/license/RWSTimP/trados-cloud-for-home-assistant)](LICENSE)

Keep track of your Trados Cloud translation assignments directly from your Home Assistant dashboard. This integration brings your translation workflow into your smart home, helping you stay on top of deadlines and manage your workload efficiently.

## Overview

This integration connects Home Assistant to the [Trados Cloud](https://www.rws.com/translation/trados/trados-cloud/) platform, providing real-time visibility into your translation task queue. It's designed for:

- **Freelance translators** managing assignments across multiple projects
- **Translation project managers** monitoring team workload
- **Language service providers** tracking operational metrics
- **Anyone using Trados Cloud** who wants task visibility in their home automation setup

### What You Get

Monitor your translation workload with dedicated sensors that track:

- **Total Tasks** - Count of all assigned tasks across all projects
- **Tasks by Status** - Separate sensors for Created, In Progress, and Completed tasks
- **Overdue Tasks** - Immediate visibility into tasks past their due date
- **Total Words** - Total word count across all your active assignments
- **Next Due Date** - Track your most urgent deadline
- **Configurable Polling** - Set update frequency from 5 to 120 minutes (default: 15)
- **Multi-account Support** - Monitor multiple Trados Cloud accounts/tenants

### Automation Ideas

Integrate your translation workflow with Home Assistant automations:

- Get mobile notifications when tasks become overdue
- Display your daily task count on smart displays
- Set up morning briefings with your translation workload
- Create visual indicators (smart lights) for urgent deadlines
- Track productivity metrics over time with long-term statistics

### Planned Features

- 🔄 Webhook support for real-time updates
- 🔄 Per-project task breakdown
- 🔄 Proactive due date notifications
- 🔄 Task acceptance automation

## Installation

### Prerequisites

Before you begin, you'll need:

#### ⚠️ You will Need RWS Support to enable OAuth 2.0 Device-Code Authentication for your Application ⚠️
- The OAuth 2.0 application created by Trados does not have the required authentication flows enabled. You'll need to raise a ticket with support to arrange for the application to enabled for Device-Code authentication. We hope to remove this step in the future.

- **Home Assistant** 2025.12 or newer
- **Trados Cloud account** with API access
- **Administrator access** to create an application in Trados Cloud


### Getting API Credentials

This integration uses OAuth 2.0 authentication to obtain access to Trados Cloud. You'll need a **Client ID** and **Client Secret** from Trados Cloud.

> **Note:** If you're not the account administrator, ask your Trados Cloud administrator to create these credentials for you.

#### Step 1: Create a Trados Application

1. Log in to [Trados Cloud](https://cloud.trados.com) as an administrator
2. Expand the account menu on the top right-hand corner and select Integrations.
3. Select the Applications sub-tab.
4. Select New Application and enter the following information:
  - **Name** – Enter a unique name for your custom application.
  - (Optional) **URL** – Enter your custom application URL.
  - (Optional) **Description** – Enter any other relevant details.
  - **Service User** – Select a service user from the dropdown menu.
5. Select Add.
6. Back in the Applications sub-tab, select the check box corresponding to your application.
7. Select Edit.
8. On the Overall Information page you can change any of the following, if necessary: name, URL, description.

📖 **Detailed instructions:** [Trados Cloud Service Credentials Guide](https://eu.cloud.trados.com/lc/api-docs/service-credentials)

### Setup in Home Assistant

#### Option 1: HACS
1. Open HACS
2. Go to Integrations
3. Search for "Trados Cloud"
4. Click Install

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=RWSTimP&repository=trados-cloud-for-home-assistant&category=Integration)

#### Option 2: Manual Installation
1. Download the latest release from GitHub
2. Extract the `custom_components/trados_cloud` folder
3. Copy it to your Home Assistant `config/custom_components/` directory
4. Restart Home Assistant

### Configuration

1. In Home Assistant, go to **Settings** → **Devices & Services**
2. Click **Add Integration** (+ button in bottom right)
3. Search for "Trados Cloud"
4. Enter your **Client ID** and **Client Secret** (from Step 3 above)
5. Click the authorization link to sign in to Trados Cloud
6. Authorize the application in your browser
7. Return to Home Assistant and click **Submit**
8. Select which **tenant/account** to monitor (if you have multiple)
9. (Optional) Configure the update interval (default: 15 minutes)

The integration will create a device for each tenant with all sensors automatically configured.


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

The recommended way to test this integration locally is using Docker:

#### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed
- Git to clone the repository

#### Quick Start

1. Clone this repository:
   ```bash
   git clone https://github.com/RWSTimP/trados-cloud-for-home-assistant.git
   cd trados-cloud-for-home-assistant
   ```

2. Run the Docker startup script:
   ```powershell
   .\start_docker_ha.ps1
   ```

This script will:
- Check if Docker is running (and start it if needed)
- Create or start a Home Assistant container
- Mount the `config/` directory with the integration pre-installed
- Expose Home Assistant on http://localhost:8123

3. Wait for Home Assistant to start (2-3 minutes on first run)
4. Open http://localhost:8123 in your browser
5. Complete the onboarding wizard
6. Add the Trados Cloud integration via **Settings** → **Devices & Services**

#### Useful Commands

```powershell
# View live logs
docker logs -f homeassistant

# Restart after making code changes
docker restart homeassistant

# Stop the container
docker stop homeassistant

# Remove the container (keeps config data)
docker rm -f homeassistant
```

#### Updating Integration Code

After making changes to the integration:

1. Copy updated files to the container:
   ```powershell
   Copy-Item -Path "custom_components\trados_cloud" -Destination "config\custom_components\trados_cloud" -Recurse -Force
   ```

2. Restart Home Assistant:
   ```powershell
   docker restart homeassistant
   ```
### Project Structure

```
custom_components/trados_cloud/
├── __init__.py          # Integration setup
├── manifest.json        # Integration metadata
├── const.py             # Constants and configuration
├── config_flow.py       # UI configuration flow
├── api.py               # Trados API client
├── coordinator.py       # Data update coordinator
├── sensor.py            # Sensor platform
├── strings.json         # UI translations
└── translations/
    └── en.json          # English configuration flow
```

## Troubleshooting

**Problem:** "Authentication failed" during setup

**Solutions:**
- Verify your Client ID and Client Secret are exactly as shown in Trados Cloud

### No Tasks Showing

**Problem:** Sensors show zero tasks, but you have assignments

**Solutions:**
- Review Home Assistant logs (`Settings` → `System` → `Logs`) for API errors
- Ensure tasks are actually assigned to the service user or visible to its groups

### Authorization Timeout

**Problem:** "Authorization timed out" error

**Solutions:**
- Make sure you complete the authorization in the browser within 5 minutes
- Check your browser isn't blocking pop-ups from Trados Cloud
- Try the setup process again with a fresh start

### Slow Updates or Rate Limits

**Problem:** Data updates slowly or you see rate limit errors

**Solutions:**
- Increase the update interval in integration options (recommended: 15-30 minutes)
- Trados Cloud has API rate limits - see [API Rate Limits documentation](https://eu.cloud.trados.com/lc/api-docs/api-rate-limits)
- This integration caches authentication tokens for 24 hours to minimize API calls
- If you have multiple integrations using the same credentials, they share token limits

### Integration Won't Load

**Problem:** Integration doesn't appear or fails to load

**Solutions:**
- Ensure you're running Home Assistant 2025.12 or newer
- Check Home Assistant logs for specific error messages
- Verify the integration files are in the correct location: `config/custom_components/trados_cloud/`
- Restart Home Assistant after installation
- Tokens are cached for 24 hours
- This integration respects these limits

## Support

- **Issues**: [GitHub Issues](https://github.com/RWSTimP/trados-cloud-for-home-assistant/issues)
- **Discussions**: [GitHub Discussions](https://github.com/RWSTimP/trados-cloud-for-home-assistant/discussions)
- **Trados API Documentation**: [Trados API Docs](https://eu.cloud.trados.com/lc/api-docs/)

## License

MIT License - See LICENSE file for details

## Credits

Built for the Home Assistant community
