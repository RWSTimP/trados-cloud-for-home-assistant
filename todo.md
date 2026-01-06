# Trados Cloud Integration - TODO

## Branding
- [ ] Submit logo to Home Assistant Brands repository
  - Fork https://github.com/home-assistant/brands
  - Create folder: `core_integrations/trados_cloud/`
  - Add `logo.png` (256x256px)
  - Add `icon.png` (256x256px, same as logo or simplified version)
  - Submit pull request
  - Note: May require HACS submission or core integration acceptance first

## Future Enhancements
- [ ] Phase 2: Webhook support for real-time updates
- [ ] Phase 2: Per-project task sensors
- [ ] Phase 2: Due date notifications/alerts
- [ ] Phase 2: Task assignment automation
- [ ] Calendar integration for task deadlines

## Testing
- [ ] Test with real Trados credentials
- [ ] Test multi-user scenarios
- [ ] Test error handling (invalid credentials, API downtime)
- [ ] Test token refresh after 24 hours

## Documentation
- [ ] Add screenshots to README
- [ ] Create HACS submission (if planning to publish)
- [ ] Document automation examples
