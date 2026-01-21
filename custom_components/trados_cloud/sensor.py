"""Sensor platform for Trados Enterprise integration."""
from datetime import datetime, timezone
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass, SensorDeviceClass
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
    SENSOR_NEXT_DUE_DATE,
)
from .coordinator import TradosDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Trados Enterprise sensors from a config entry."""
    coordinators: list[TradosDataCoordinator] = hass.data[DOMAIN][entry.entry_id]["coordinators"]

    # Create sensor entities for each coordinator (tenant)
    entities = []
    for coordinator in coordinators:
        entities.extend([
            TradosTotalTasksSensor(coordinator, entry),
            TradosTasksByStatusSensor(coordinator, entry, "created", SENSOR_TASKS_CREATED),
            TradosTasksByStatusSensor(coordinator, entry, "inProgress", SENSOR_TASKS_IN_PROGRESS),
            TradosTasksByStatusSensor(coordinator, entry, "completed", SENSOR_TASKS_COMPLETED),
            TradosOverdueTasksSensor(coordinator, entry),
            TradosTotalWordsSensor(coordinator, entry),
            TradosNextDueDateSensor(coordinator, entry),
        ])
    
    # Create user-level aggregate sensors (sum across all tenants)
    if coordinators:
        entities.extend([
            TradosUserTotalTasksSensor(coordinators, entry),
            TradosUserTasksByStatusSensor(coordinators, entry, "created", SENSOR_TASKS_CREATED),
            TradosUserTasksByStatusSensor(coordinators, entry, "inProgress", SENSOR_TASKS_IN_PROGRESS),
            TradosUserTasksByStatusSensor(coordinators, entry, "completed", SENSOR_TASKS_COMPLETED),
            TradosUserOverdueTasksSensor(coordinators, entry),
            TradosUserTotalWordsSensor(coordinators, entry),
            TradosUserNextDueDateSensor(coordinators, entry),
        ])

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
        tenant_id = coordinator.client.tenant_id
        tenant_name = coordinator.tenant_name or "Trados Cloud"
        region = coordinator.client.region
        
        self._attr_unique_id = f"{entry.entry_id}_{tenant_id}_{sensor_type}"
        self._attr_has_entity_name = True
        self._attr_name = name
        self._sensor_type = sensor_type

        config_url = TRADOS_PORTAL_URL_TEMPLATE.format(region=region, tenant_id=tenant_id)

        # Device info - create a device per tenant
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry.entry_id}_{tenant_id}")},
            "name": tenant_name,
            "manufacturer": "RWS",
            "model": "Trados Assignments",
            "entry_type": "service",
            "configuration_url": config_url,
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None


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
        return int(self.coordinator.data.get("total_tasks", 0))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        tasks = self.coordinator.data.get("tasks", [])
        last_update = self.coordinator.data.get("last_update")

        # Count upcoming tasks (due in next 48 hours)
        now = datetime.now(timezone.utc)
        upcoming_count = 0

        for task in tasks:
            if task["status"] not in ["completed", "canceled", "skipped"]:
                if task.get("due_by"):
                    try:
                        due_date = datetime.fromisoformat(task["due_by"].replace("Z", "+00:00"))
                        hours_until_due = (due_date - now).total_seconds() / 3600
                        if 0 < hours_until_due <= 48:
                            upcoming_count += 1
                    except (ValueError, AttributeError):
                        pass

        return {
            "last_update": last_update,
            "upcoming_tasks_count": upcoming_count,
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
        return int(tasks_by_status.get(self._status, 0))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        tasks = self.coordinator.data.get("tasks", [])

        # Count tasks with this status
        task_count = sum(1 for task in tasks if task["status"] == self._status)

        return {
            "total_count": task_count,
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
        return int(self.coordinator.data.get("overdue_tasks", 0))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        tasks = self.coordinator.data.get("tasks", [])
        now = datetime.now(timezone.utc)

        overdue_count = 0
        max_hours_overdue = 0

        for task in tasks:
            if task["status"] not in ["completed", "canceled", "skipped"]:
                if task.get("due_by"):
                    try:
                        due_date = datetime.fromisoformat(task["due_by"].replace("Z", "+00:00"))
                        if due_date < now:
                            hours_overdue = (now - due_date).total_seconds() / 3600
                            overdue_count += 1
                            max_hours_overdue = max(max_hours_overdue, hours_overdue)
                    except (ValueError, AttributeError):
                        pass

        return {
            "total_count": overdue_count,
            "max_hours_overdue": round(max_hours_overdue, 1) if max_hours_overdue > 0 else 0,
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
        return int(self.coordinator.data.get("total_words", 0))

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
            word_count = int(task.get("word_count", 0) or 0)
            if status in words_by_status and word_count:
                words_by_status[status] += word_count

        return {
            "words_pending": words_by_status["created"],
            "words_in_progress": words_by_status["inProgress"],
            "words_completed": words_by_status["completed"],
        }


class TradosNextDueDateSensor(TradosBaseSensor):
    """Sensor for next task due date."""

    def __init__(self, coordinator: TradosDataCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, SENSOR_NEXT_DUE_DATE, "Next Due Date")
        self._attr_icon = "mdi:calendar-clock"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        """Return the earliest due date for non-completed tasks."""
        tasks = self.coordinator.data.get("tasks", [])
        earliest_due = None

        for task in tasks:
            status = task.get("status")
            if status not in ["completed", "canceled", "skipped"]:
                due_by = task.get("due_by")
                if due_by:
                    try:
                        due_date = datetime.fromisoformat(due_by.replace("Z", "+00:00"))
                        if earliest_due is None or due_date < earliest_due:
                            earliest_due = due_date
                    except (ValueError, AttributeError):
                        pass

        return earliest_due

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        tasks = self.coordinator.data.get("tasks", [])
        
        # Count tasks due in next 24, 48, and 72 hours
        now = datetime.now(timezone.utc)
        due_24h = 0
        due_48h = 0
        due_72h = 0

        for task in tasks:
            status = task.get("status")
            if status not in ["completed", "canceled", "skipped"]:
                due_by = task.get("due_by")
                if due_by:
                    try:
                        due_date = datetime.fromisoformat(due_by.replace("Z", "+00:00"))
                        hours_until_due = (due_date - now).total_seconds() / 3600
                        
                        if 0 < hours_until_due <= 24:
                            due_24h += 1
                        if 0 < hours_until_due <= 48:
                            due_48h += 1
                        if 0 < hours_until_due <= 72:
                            due_72h += 1
                    except (ValueError, AttributeError):
                        pass

        return {
            "due_within_24h": due_24h,
            "due_within_48h": due_48h,
            "due_within_72h": due_72h,
        }


# User-level aggregate sensors (sum across all tenants)

class TradosUserBaseSensor(SensorEntity):
    """Base class for user-level aggregate Trados sensors."""

    def __init__(
        self,
        coordinators: list[TradosDataCoordinator],
        entry: ConfigEntry,
        sensor_type: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        self.coordinators = coordinators
        self._attr_unique_id = f"{entry.entry_id}_user_{sensor_type}"
        self._attr_has_entity_name = True
        self._attr_name = name
        self._sensor_type = sensor_type

        # Device info - create a user-level device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry.entry_id}_user")},
            "name": "All Inboxes",
            "manufacturer": "RWS",
            "model": "Trados Assignments Summary",
            "entry_type": "service",
        }

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass, track all coordinators."""
        for coordinator in self.coordinators:
            self.async_on_remove(
                coordinator.async_add_listener(self.async_write_ha_state)
            )
        await super().async_added_to_hass()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return any(coordinator.last_update_success for coordinator in self.coordinators)


class TradosUserTotalTasksSensor(TradosUserBaseSensor):
    """User-level sensor for total assigned tasks across all tenants."""

    def __init__(self, coordinators: list[TradosDataCoordinator], entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinators, entry, SENSOR_TOTAL_TASKS, "Total Tasks")
        self._attr_icon = "mdi:clipboard-list"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the sum of tasks across all tenants."""
        total = sum(
            int(coordinator.data.get("total_tasks", 0))
            for coordinator in self.coordinators
            if coordinator.data
        )
        return total

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        tenant_counts = {}
        for coordinator in self.coordinators:
            if coordinator.data and coordinator.tenant_name:
                tenant_counts[coordinator.tenant_name] = int(coordinator.data.get("total_tasks", 0))
        
        return {"by_tenant": tenant_counts}


class TradosUserTasksByStatusSensor(TradosUserBaseSensor):
    """User-level sensor for tasks by status across all tenants."""

    def __init__(
        self,
        coordinators: list[TradosDataCoordinator],
        entry: ConfigEntry,
        status: str,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        status_name = status.replace("inProgress", "In Progress").title()
        super().__init__(coordinators, entry, sensor_type, f"Tasks {status_name}")
        self._status = status
        self._attr_icon = self._get_icon_for_status(status)
        self._attr_state_class = SensorStateClass.MEASUREMENT

    def _get_icon_for_status(self, status: str) -> str:
        """Get icon based on status."""
        icons = {
            "created": "mdi:clipboard-outline",
            "inProgress": "mdi:clipboard-edit",
            "completed": "mdi:clipboard-check",
        }
        return icons.get(status, "mdi:clipboard")

    @property
    def native_value(self) -> int:
        """Return the sum of tasks with this status across all tenants."""
        total = sum(
            int(coordinator.data.get("tasks_by_status", {}).get(self._status, 0))
            for coordinator in self.coordinators
            if coordinator.data
        )
        return total

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        tenant_counts = {}
        for coordinator in self.coordinators:
            if coordinator.data and coordinator.tenant_name:
                count = int(coordinator.data.get("tasks_by_status", {}).get(self._status, 0))
                tenant_counts[coordinator.tenant_name] = count
        
        return {"by_tenant": tenant_counts}


class TradosUserOverdueTasksSensor(TradosUserBaseSensor):
    """User-level sensor for overdue tasks across all tenants."""

    def __init__(self, coordinators: list[TradosDataCoordinator], entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinators, entry, SENSOR_OVERDUE_TASKS, "Overdue Tasks")
        self._attr_icon = "mdi:alert-circle"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the sum of overdue tasks across all tenants."""
        total = sum(
            int(coordinator.data.get("overdue_tasks", 0))
            for coordinator in self.coordinators
            if coordinator.data
        )
        return total

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        tenant_counts = {}
        for coordinator in self.coordinators:
            if coordinator.data and coordinator.tenant_name:
                count = int(coordinator.data.get("overdue_tasks", 0))
                tenant_counts[coordinator.tenant_name] = count
        
        return {"by_tenant": tenant_counts}


class TradosUserTotalWordsSensor(TradosUserBaseSensor):
    """User-level sensor for total word count across all tenants."""

    def __init__(self, coordinators: list[TradosDataCoordinator], entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinators, entry, SENSOR_TOTAL_WORDS, "Total Words")
        self._attr_icon = "mdi:text-box-outline"
        self._attr_native_unit_of_measurement = "words"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the sum of words across all tenants."""
        total = sum(
            int(coordinator.data.get("total_words", 0))
            for coordinator in self.coordinators
            if coordinator.data
        )
        return total

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        tenant_counts = {}
        for coordinator in self.coordinators:
            if coordinator.data and coordinator.tenant_name:
                count = int(coordinator.data.get("total_words", 0))
                tenant_counts[coordinator.tenant_name] = count
        
        return {"by_tenant": tenant_counts}


class TradosUserNextDueDateSensor(TradosUserBaseSensor):
    """User-level sensor for earliest due date across all tenants."""

    def __init__(self, coordinators: list[TradosDataCoordinator], entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinators, entry, SENSOR_NEXT_DUE_DATE, "Next Due Date")
        self._attr_icon = "mdi:calendar-clock"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        """Return the earliest due date across all tenants."""
        earliest_due = None

        for coordinator in self.coordinators:
            if not coordinator.data:
                continue
            
            tasks = coordinator.data.get("tasks", [])
            for task in tasks:
                status = task.get("status")
                if status not in ["completed", "canceled", "skipped"]:
                    due_by = task.get("due_by")
                    if due_by:
                        try:
                            due_date = datetime.fromisoformat(due_by.replace("Z", "+00:00"))
                            if earliest_due is None or due_date < earliest_due:
                                earliest_due = due_date
                        except (ValueError, AttributeError):
                            pass

        return earliest_due

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        now = datetime.now(timezone.utc)
        due_24h = 0
        due_48h = 0
        due_72h = 0

        for coordinator in self.coordinators:
            if not coordinator.data:
                continue
            
            tasks = coordinator.data.get("tasks", [])
            for task in tasks:
                status = task.get("status")
                if status not in ["completed", "canceled", "skipped"]:
                    due_by = task.get("due_by")
                    if due_by:
                        try:
                            due_date = datetime.fromisoformat(due_by.replace("Z", "+00:00"))
                            hours_until_due = (due_date - now).total_seconds() / 3600
                            
                            if 0 < hours_until_due <= 24:
                                due_24h += 1
                            if 0 < hours_until_due <= 48:
                                due_48h += 1
                            if 0 < hours_until_due <= 72:
                                due_72h += 1
                        except (ValueError, AttributeError):
                            pass

        return {
            "due_within_24h": due_24h,
            "due_within_48h": due_48h,
            "due_within_72h": due_72h,
        }
