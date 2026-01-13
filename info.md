# Trados Cloud Integration

Keep track of your Trados Cloud translation assignments directly from your Home Assistant dashboard.

## Who Is This For?

- **Freelance translators** managing assignments across multiple projects
- **Translation project managers** monitoring team workload
- **Language service providers** tracking operational metrics
- **Anyone using Trados Cloud** who wants task visibility in their home automation setup

## Features

- **Total Tasks** - Count of all assigned tasks across all projects
- **Tasks by Status** - Separate sensors for Created, In Progress, and Completed tasks
- **Overdue Tasks** - Immediate visibility into tasks past their due date
- **Total Words** - Total word count across all your active assignments
- **Next Due Date** - Track your most urgent deadline
- **Configurable Polling** - Set update frequency from 5 to 120 minutes (default: 15)
- **Multi-account Support** - Monitor multiple Trados Cloud accounts/tenants

## Prerequisites

- Home Assistant 2025.12 or newer
- Trados Cloud account with API access
- Administrator access to create service users and applications

## Getting Started

### Step 1: Create Service Credentials

You'll need to create a **Service User** and **Application** in Trados Cloud to get your API credentials:

1. Log in to [Trados Cloud](https://cloud.trados.com) as an administrator
2. Go to **Users** → **Service Users** → **New Service User**
3. Create a service user with appropriate permissions
4. Go to account menu → **Integrations** → **Applications**
5. Click **New Application** and assign your service user
6. Copy your **Client ID** and **Client Secret** from the API Access page

📖 [Detailed setup guide](https://eu.cloud.trados.com/lc/api-docs/service-credentials)

### Step 2: Configure in Home Assistant

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration** (+ button)
3. Search for "Trados Cloud"
4. Enter your **Client ID** and **Client Secret**
5. Click the authorization link to sign in
6. Authorize the application in your browser
7. Select your tenant/account
8. (Optional) Configure update interval

## What You'll Get

The integration creates sensors for monitoring your translation workload:

- `sensor.trados_cloud_total_tasks` - All assigned tasks
- `sensor.trados_cloud_tasks_created` - Tasks in "Created" status
- `sensor.trados_cloud_tasks_in_progress` - Tasks being worked on
- `sensor.trados_cloud_tasks_completed` - Completed tasks
- `sensor.trados_cloud_overdue_tasks` - Overdue tasks with details
- `sensor.trados_cloud_total_words` - Total word count
- `sensor.trados_cloud_next_due_date` - Your next deadline

Each sensor includes rich attributes with task details, project names, due dates, and more.

## Automation Ideas

- Get mobile notifications when tasks become overdue
- Display your daily task count on smart displays
- Morning briefings with your translation workload
- Visual indicators (smart lights) for urgent deadlines
- Track productivity metrics over time

## Support

- **Documentation**: [Full README](https://github.com/RWSTimP/trados-cloud-for-home-assistant#readme)
- **Issues**: [Report a bug](https://github.com/RWSTimP/trados-cloud-for-home-assistant/issues)
- **Discussions**: [Get help or share ideas](https://github.com/RWSTimP/trados-cloud-for-home-assistant/discussions)
