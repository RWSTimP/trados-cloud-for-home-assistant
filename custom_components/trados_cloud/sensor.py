"""Sensor platform for Trados Enterprise integration."""
from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    TRADOS_PORTAL_URL_TEMPLATE,
    SENSOR_OVERDUE_TASKS,
    SENSOR_TASKS_COMPLETED,
    SENSOR_TASKS_CREATED,
    SENSOR_TASKS_IN_PROGRESS,
    SENSOR_TOTAL_TASKS,
    SENSOR_TOTAL_WORDS,
)
from .coordinator import TradosDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Trados Enterprise sensors from a config entry."""
    coordinator: TradosDataCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Create all sensor entities
    entities = [
        TradosTotalTasksSensor(coordinator, entry),
        TradosTasksByStatusSensor(coordinator, entry, "created", SENSOR_TASKS_CREATED),
        TradosTasksByStatusSensor(coordinator, entry, "inProgress", SENSOR_TASKS_IN_PROGRESS),
        TradosTasksByStatusSensor(coordinator, entry, "completed", SENSOR_TASKS_COMPLETED),
        TradosOverdueTasksSensor(coordinator, entry),
        TradosTotalWordsSensor(coordinator, entry),
    ]

    async_add_entities(entities)


class TradosBaseSensor(CoordinatorEntity[TradosDataCoordinator], SensorEntity):
    """Base class for Trados Enterprise sensors."""

    def __init__(
        self,
        coordinator: TradosDataCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        self._attr_has_entity_name = True
        self._attr_name = name
        self._sensor_type = sensor_type

        region = entry.data.get("region", "eu")
        tenant_id = entry.data.get("tenant_id", "")
        tenant_name = entry.data.get("tenant_name") or "Trados Cloud"
        config_url = TRADOS_PORTAL_URL_TEMPLATE.format(region=region, tenant_id=tenant_id)

        # Device info to group all sensors together
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": tenant_name,
            "manufacturer": "RWS",
            "model": "Trados Enterprise",
            "entry_type": "service",
            "configuration_url": config_url,
        }


class TradosTotalTasksSensor(TradosBaseSensor):
    """Sensor for total assigned tasks."""

    def __init__(self, coordinator: TradosDataCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_TOTAL_TASKS, "Total Tasks")
        self._attr_icon = "mdi:clipboard-list"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self.coordinator.data.get("total_tasks", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        tasks = self.coordinator.data.get("tasks", [])
        last_update = self.coordinator.data.get("last_update")

        # Get upcoming tasks (due in next 48 hours)
        now = datetime.now()
        upcoming_tasks = []

        for task in tasks:
            if task["status"] not in ["completed", "canceled", "skipped"]:
                if task.get("due_by"):
                    try:
                        due_date = datetime.fromisoformat(task["due_by"].replace("Z", "+00:00"))
                        hours_until_due = (due_date - now).total_seconds() / 3600
                        if 0 < hours_until_due <= 48:
                            upcoming_tasks.append({
                                "name": task["name"],
                                "due_by": task["due_by"],
                                "project": task["project_name"],
                            })
                    except (ValueError, AttributeError):
                        pass

        return {
            "last_update": last_update,
            "upcoming_tasks": upcoming_tasks[:5],  # Limit to 5
            "tasks_by_project": self._count_by_project(tasks),
        }

    def _count_by_project(self, tasks: list[dict]) -> dict[str, int]:
        """Count tasks by project."""
        counts = {}
        for task in tasks:
            if task["status"] not in ["completed", "canceled", "skipped"]:
                project = task.get("project_name", "Unknown")
                counts[project] = counts.get(project, 0) + 1
        return counts


class TradosTasksByStatusSensor(TradosBaseSensor):
    """Sensor for tasks by specific status."""

    def __init__(
        self,
        coordinator: TradosDataCoordinator,
        entry: ConfigEntry,
        status: str,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        status_name = status.replace("inProgress", "In Progress").title()
        super().__init__(coordinator, entry, sensor_type, f"Tasks {status_name}")
        self._status = status
        self._attr_icon = self._get_icon_for_status(status)
        self._attr_state_class = SensorStateClass.MEASUREMENT

    def _get_icon_for_status(self, status: str) -> str:
        """Get icon based on status."""
        icons = {
            "created": "mdi:clipboard-outline",
            "inProgress": "mdi:clipboard-edit",
            "completed": "mdi:clipboard-check",
            "failed": "mdi:clipboard-alert",
            "skipped": "mdi:clipboard-minus",
            "canceled": "mdi:clipboard-remove",
        }
        return icons.get(status, "mdi:clipboard")

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        tasks_by_status = self.coordinator.data.get("tasks_by_status", {})
        return tasks_by_status.get(self._status, 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        tasks = self.coordinator.data.get("tasks", [])

        # Get tasks with this status
        filtered_tasks = [
            {
                "name": task["name"],
                "project": task["project_name"],
                "due_by": task.get("due_by"),
                "task_type": task.get("task_type"),
            }
            for task in tasks
            if task["status"] == self._status
        ]

        return {
            "tasks": filtered_tasks[:10],  # Limit to 10
            "total_count": len(filtered_tasks),
        }


class TradosOverdueTasksSensor(TradosBaseSensor):
    """Sensor for overdue tasks."""

    def __init__(self, coordinator: TradosDataCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_OVERDUE_TASKS, "Overdue Tasks")
        self._attr_icon = "mdi:alert-circle"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self.coordinator.data.get("overdue_tasks", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        tasks = self.coordinator.data.get("tasks", [])
        now = datetime.now()

        overdue_tasks = []
        for task in tasks:
            if task["status"] not in ["completed", "canceled", "skipped"]:
                if task.get("due_by"):
                    try:
                        due_date = datetime.fromisoformat(task["due_by"].replace("Z", "+00:00"))
                        if due_date < now:
                            hours_overdue = (now - due_date).total_seconds() / 3600
                            overdue_tasks.append({
                                "name": task["name"],
                                "project": task["project_name"],
                                "due_by": task["due_by"],
                                "hours_overdue": round(hours_overdue, 1),
                            })
                    except (ValueError, AttributeError):
                        pass

        # Sort by most overdue first
        overdue_tasks.sort(key=lambda x: x["hours_overdue"], reverse=True)

        return {
            "tasks": overdue_tasks[:10],  # Limit to 10
        }


class TradosTotalWordsSensor(TradosBaseSensor):
    """Sensor for total word count across all tasks."""

    def __init__(self, coordinator: TradosDataCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_TOTAL_WORDS, "Total Words")
        self._attr_icon = "mdi:text-box-outline"
        self._attr_native_unit_of_measurement = "words"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self.coordinator.data.get("total_words", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        tasks = self.coordinator.data.get("tasks", [])

        # Calculate words by status
        words_by_status = {
            "created": 0,
            "inProgress": 0,
            "completed": 0,
        }

        for task in tasks:
            status = task.get("status")
            word_count = task.get("word_count", 0)
            if status in words_by_status and word_count:
                words_by_status[status] += word_count

        return {
            "words_pending": words_by_status["created"],
            "words_in_progress": words_by_status["inProgress"],
            "words_completed": words_by_status["completed"],
        }
