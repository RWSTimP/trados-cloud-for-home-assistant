"""Data coordinator for Trados Enterprise integration."""
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TradosAPIClient, TradosAPIError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class TradosDataCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Trados Enterprise data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: TradosAPIClient,
        update_interval: timedelta,
        tenant_name: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.client = client
        self.tenant_name = tenant_name

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Trados API."""
        try:
            tasks = await self.client.get_assigned_tasks()

            # Process and organize the task data
            processed_data = self._process_tasks(tasks)
            
            # Detect new tasks and fire events
            if self.data:  # Only if we have previous data to compare
                old_task_ids = {t["id"] for t in self.data.get("tasks", [])}
                new_task_ids = {t["id"] for t in processed_data["tasks"]}
                newly_arrived = new_task_ids - old_task_ids
                
                if newly_arrived:
                    _LOGGER.info("Detected %d new task(s) for tenant %s", len(newly_arrived), self.tenant_name)
                    
                    for task_id in newly_arrived:
                        task = next(t for t in processed_data["tasks"] if t["id"] == task_id)
                        self.hass.bus.fire(
                            f"{DOMAIN}_new_task",
                            {
                                "task_id": task_id,
                                "task_name": task.get("name"),
                                "tenant_id": self.client.tenant_id,
                                "tenant_name": self.tenant_name,
                                "status": task.get("status"),
                                "due_by": task.get("due_by"),
                                "project_name": task.get("project_name"),
                                "task_type": task.get("task_type"),
                                "word_count": task.get("word_count", 0),
                            }
                        )

            _LOGGER.debug("Coordinator updated with %s tasks", len(tasks))
            return processed_data

        except TradosAPIError as err:
            raise UpdateFailed(f"Error communicating with Trados API: {err}") from err

    def _process_tasks(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        """Process raw task data into organized structure."""
        now = datetime.now(timezone.utc)

        # Initialize counters
        total_tasks = len(tasks)
        tasks_by_status = {
            "created": 0,
            "inProgress": 0,
            "completed": 0,
            "failed": 0,
            "skipped": 0,
            "canceled": 0,
        }
        overdue_count = 0
        total_words = 0

        # Store individual tasks
        task_list = []

        for task in tasks:
            # Count by status
            status = task.get("status", "unknown")
            if status in tasks_by_status:
                tasks_by_status[status] += 1

            # Check if overdue
            due_by = task.get("dueBy")
            if due_by:
                try:
                    due_date = datetime.fromisoformat(due_by.replace("Z", "+00:00"))
                    if due_date < now and status not in ["completed", "canceled", "skipped"]:
                        overdue_count += 1
                except (ValueError, AttributeError):
                    _LOGGER.warning("Invalid due date format for task %s: %s", task.get("id"), due_by)

            # Calculate word count from task input
            word_count = self._extract_word_count(task)
            if word_count:
                total_words += word_count

            # Add processed task to list
            task_list.append({
                "id": task.get("id"),
                "name": task.get("name"),
                "status": status,
                "due_by": due_by,
                "created_at": task.get("createdAt"),
                "task_type": task.get("taskType", {}).get("name"),
                "project_name": task.get("project", {}).get("name"),
                "word_count": word_count,
            })

        return {
            "total_tasks": total_tasks,
            "tasks_by_status": tasks_by_status,
            "overdue_tasks": overdue_count,
            "total_words": total_words,
            "tasks": task_list,
            "last_update": now.isoformat(),
        }

    def _extract_word_count(self, task: dict[str, Any]) -> int:
        """Extract word count from task input data."""
        # Get totalWords from input.targetFile.totalWords when input.type = "targetFile"
        try:
            input_data = task.get("input", {})
            input_type = input_data.get("type")
            
            if input_type == "targetFile":
                target_file = input_data.get("targetFile", {})
                total_words = target_file.get("totalWords", 0)
                return int(total_words) if total_words else 0
            
            return 0

        except (KeyError, TypeError, AttributeError, ValueError) as err:
            _LOGGER.debug("Could not extract word count from task %s: %s", task.get("id"), err)
            return 0
