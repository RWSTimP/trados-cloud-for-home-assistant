"""Constants for the Trados Enterprise integration."""
from datetime import timedelta

# Domain
DOMAIN = "trados_cloud"

# Configuration
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_TENANT_ID = "tenant_id"
CONF_REGION = "region"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_TOKEN_EXPIRES = "token_expires"

# Defaults
DEFAULT_SCAN_INTERVAL = timedelta(minutes=15)
DEFAULT_REGION = "eu"

# Auth0 Configuration
AUTH0_DOMAIN = "sdl-prod.eu.auth0.com"
AUTH0_TOKEN_URL = f"https://{AUTH0_DOMAIN}/oauth/token"
AUTH0_DEVICE_CODE_URL = f"https://{AUTH0_DOMAIN}/oauth/device/code"

# API Endpoints
API_BASE_URL = "https://api.{region}.cloud.trados.com/public-api/v1"
GLOBAL_API_BASE_URL = "https://api.cloud.trados.com/public-api/v1"
API_AUDIENCE = "https://api.sdl.com"
TRADOS_PORTAL_URL_TEMPLATE = "https://{region}.cloud.trados.com/lc/t/{tenant_id}/dashboard"

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
SENSOR_NEXT_DUE_DATE = "next_due_date"
