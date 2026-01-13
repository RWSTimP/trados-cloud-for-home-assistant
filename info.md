# Trados Cloud Integration

Monitor your Trados Cloud translation tasks directly in Home Assistant.

## Features

- **Total Tasks** - Count of all assigned tasks
- **Tasks by Status** - Separate sensors for Created, In Progress, and Completed tasks
- **Overdue Tasks** - Count and details of overdue tasks
- **Total Words** - Total word count across all your tasks
- **Configurable Polling** - Set update frequency (5-120 minutes, default: 15)
- **Multi-user Support** - Each config entry supports a different user/service account

## Setup

You'll need:
1. **Client ID** - From your Trados application
2. **Client Secret** - From your Trados application  
3. **Tenant ID** - Your Trados Account ID

### Getting Credentials

1. Log in to Trados Cloud
2. Go to **Manage Account** → **Integrations** → **Applications**
3. Create a new application or use an existing one
4. Note the **Client ID** and **Client Secret**
5. Find your **Tenant ID** in Account Information

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Trados Cloud"
4. Follow the OAuth flow to authorize Home Assistant
5. Select your tenant/account
6. Configure update interval (optional)

## Sensors

- `sensor.trados_cloud_total_tasks` - Total assigned tasks
- `sensor.trados_cloud_tasks_created` - Tasks in "Created" status
- `sensor.trados_cloud_tasks_in_progress` - Tasks currently being worked on
- `sensor.trados_cloud_tasks_completed` - Completed tasks
- `sensor.trados_cloud_overdue_tasks` - Tasks past their due date
- `sensor.trados_cloud_total_words` - Total word count across all tasks

Each sensor includes detailed attributes with task information, project names, due dates, and more.

## Support

For issues and feature requests, please visit the [GitHub repository](https://github.com/RWSTimP/trados-cloud-for-home-assistant).
