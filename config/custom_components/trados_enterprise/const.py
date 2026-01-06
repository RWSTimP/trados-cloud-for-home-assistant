"""Constants for the Trados Enterprise integration."""
from datetime import timedelta

# Domain
DOMAIN = "trados_enterprise"

# Configuration
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_TENANT_ID = "tenant_id"
CONF_REGION = "region"
CONF_SCAN_INTERVAL = "scan_interval"

# Defaults
DEFAULT_SCAN_INTERVAL = timedelta(minutes=15)
DEFAULT_REGION = "eu"

# API Endpoints
AUTH0_TOKEN_URL = "https://sdl-prod.eu.auth0.com/oauth/token"
API_BASE_URL = "https://api.{region}.cloud.trados.com/public-api/v1"
API_AUDIENCE = "https://api.sdl.com"

# Task Statuses
TASK_STATUS_CREATED = "created"
TASK_STATUS_IN_PROGRESS = "inProgress"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_FAILED = "failed"
TASK_STATUS_SKIPPED = "skipped"
TASK_STATUS_CANCELED = "canceled"

# Sensor Types
SENSOR_TOTAL_TASKS = "total_tasks"
SENSOR_TASKS_CREATED = "tasks_created"
SENSOR_TASKS_IN_PROGRESS = "tasks_in_progress"
SENSOR_TASKS_COMPLETED = "tasks_completed"
SENSOR_OVERDUE_TASKS = "overdue_tasks"
SENSOR_TOTAL_WORDS = "total_words"
