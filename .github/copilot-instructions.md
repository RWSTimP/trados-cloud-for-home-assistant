# Home Assistant Development Instructions

## Project: Trados Enterprise Integration

This is a Home Assistant custom integration for monitoring Trados Enterprise translation tasks. The integration polls the Trados API to retrieve assigned tasks and displays them as sensors in Home Assistant.

### Key Components

- **API Client** (`api.py`) - Handles Auth0 authentication and Trados API requests
- **Coordinator** (`coordinator.py`) - Manages data fetching and caching with configurable polling
- **Sensors** (`sensor.py`) - Exposes task data as HA sensors
- **Config Flow** (`config_flow.py`) - UI-based configuration for user credentials

## Project Architecture

This is a Home Assistant custom component/integration project. Home Assistant follows a modular architecture with:

- **Integrations** (`custom_components/`) - Core functionality organized by platform/service
- **Configuration** (`config/`) - YAML configuration files and secrets  
- **Frontend** (`www/`) - Custom Lovelace cards and resources
- **Automations** (`config/automations/`) - Event-driven automation logic

## Key Development Patterns

### Integration Structure
```
custom_components/your_integration/
├── __init__.py          # Component setup and platforms
├── manifest.json        # Integration metadata and dependencies  
├── config_flow.py       # Configuration UI flow
├── const.py             # Constants and domain definitions
├── sensor.py            # Sensor platform implementation
├── switch.py            # Switch platform implementation
└── services.yaml        # Service definitions
```

### Configuration Flow
- Use `config_flow.py` for UI-based configuration
- Follow async patterns with `async def async_setup_entry()`
- Implement `async_unload_entry()` for proper cleanup
- Use `ConfigEntry` for storing integration data

### Entity Implementation
- Extend platform base classes (`SensorEntity`, `SwitchEntity`, etc.)
- Use `@property` decorators for entity attributes
- Implement `async_update()` for data fetching
- Follow naming convention: `{domain}.{platform}_{entity_name}`

### State Management
- Use `coordinator` pattern for shared data updates
- Implement `DataUpdateCoordinator` for API polling
- Use `async_add_entities()` for entity registration
- Store entity state in `self._attr_*` properties

## Development Workflow

### Setup Commands
```bash
# Install dependencies
pip install homeassistant
pip install -r requirements_dev.txt

# Run development instance
hass --config config/ --verbose
```

### Testing Patterns
- Use `pytest` with `homeassistant[test]` fixtures
- Mock external APIs with `aioresponses` or `responses`
- Test config flows with `MockConfigEntry`
- Use `assert_setup_component()` for integration tests

### Configuration Examples
```yaml
# Example sensor configuration
sensor:
  - platform: your_integration
    name: "My Sensor"
    host: "192.168.1.100"
    scan_interval: 30
```

## Critical Files

- `manifest.json` - Integration metadata, dependencies, IoT class
- `const.py` - Domain constants, attribute names, default values
- `config_flow.py` - User configuration interface
- `__init__.py` - Integration setup, platform loading, services

## Common Integrations Patterns

### API Client Pattern
- Create dedicated API client class in separate module
- Use `aiohttp.ClientSession` for async HTTP requests
- Implement retry logic and proper error handling
- Store API credentials securely in config entry

### Error Handling
- Use `_LOGGER = logging.getLogger(__name__)` for logging
- Catch specific exceptions (`HomeAssistantError`, `ConfigEntryNotReady`)
- Use `async_create_task()` for background operations
- Implement proper timeout handling for external calls

### Service Calls
- Define services in `services.yaml` with schema validation
- Register services in `async_setup_entry()` 
- Use `@callback` decorator for synchronous service handlers
- Validate service data with voluptuous schemas

## Data Flow Patterns

1. **Config Entry** → **Coordinator** → **Entities**
2. **API Client** ← **Coordinator** (polling/webhooks)  
3. **Entities** → **State Machine** → **Frontend**
4. **Automations** ← **State Changes** → **Events**

## Debugging Tips

- Enable debug logging: `logger.homeassistant.custom_components.your_integration: debug`
- Use Developer Tools → States to inspect entity attributes
- Check `config/home-assistant.log` for error details
- Use `async_fire()` to trigger custom events for testing

## Platform-Specific Notes

### Sensors
- Return appropriate device classes (`temperature`, `humidity`, `power`)
- Implement `native_unit_of_measurement` for units
- Use `state_class="measurement"` for numeric sensors

### Switches  
- Implement `async_turn_on()` and `async_turn_off()`
- Use `is_on` property to return current state
- Consider implementing `async_toggle()` if supported

### Binary Sensors
- Use appropriate device classes (`motion`, `door`, `window`)  
- Return boolean values for `is_on` property
- Consider implementing battery level monitoring