# Example Configuration Templates

## Minimal Configuration (Gemini)

```yaml
frigate:
  base_url: "http://192.168.1.100:5000"
  plus_api_key: "fp_abc123xyz"
  
vision_model:
  provider: "gemini"
  api_key: "AIzaSyABC123..."
  model_name: "gemini-2.0-flash-exp"

review_rules:
  min_confidence: 0.5
  
processing:
  dry_run: false
  submission_method: "snapshot"
```

## Full Configuration (All Options)

```yaml
frigate:
  base_url: "http://192.168.1.100:5000"
  plus_api_key: "fp_abc123xyz"
  poll_interval_seconds: 60
  event_lookback_minutes: 10

vision_model:
  provider: "gemini"
  api_key: "AIzaSyABC123..."
  model_name: "gemini-2.0-flash-exp"
  timeout_seconds: 30

review_rules:
  min_confidence: 0.5
  allowed_labels:
    - person
    - car
    - dog
    - cat
    - bicycle
  reject_labels:
    - shadow
    - reflection
  include_cameras:
    - front_door
    - driveway
  # exclude_cameras:
  #   - backyard

processing:
  max_events_per_run: 20
  dry_run: false
  state_file: "state.json"
  submission_method: "snapshot"

logging:
  level: "INFO"
  file: "fpr.log"
  json_format: false
```

## OpenAI Configuration

```yaml
frigate:
  base_url: "http://192.168.1.100:5000"
  plus_api_key: "fp_abc123xyz"

vision_model:
  provider: "openai_compatible"
  api_key: "sk-abc123..."
  model_name: "gpt-4-vision-preview"
  endpoint_url: "https://api.openai.com/v1"
  timeout_seconds: 30

review_rules:
  min_confidence: 0.5

processing:
  dry_run: false
  submission_method: "snapshot"
```

## Custom Vision Endpoint

```yaml
frigate:
  base_url: "http://192.168.1.100:5000"
  plus_api_key: "fp_abc123xyz"

vision_model:
  provider: "openai_compatible"
  api_key: "your-api-key"
  model_name: "qwen-vl-plus"
  endpoint_url: "https://your-custom-endpoint.com/v1"
  timeout_seconds: 60

review_rules:
  min_confidence: 0.6

processing:
  dry_run: false
  submission_method: "snapshot"
```

## Production Configuration (Restrictive)

```yaml
frigate:
  base_url: "http://192.168.1.100:5000"
  plus_api_key: "fp_abc123xyz"
  poll_interval_seconds: 300  # Every 5 minutes
  event_lookback_minutes: 10

vision_model:
  provider: "gemini"
  api_key: "AIzaSyABC123..."
  model_name: "gemini-2.5-flash-lite"
  timeout_seconds: 45

review_rules:
  min_confidence: 0.7  # Higher threshold
  allowed_labels:
    - person
    - car
  reject_labels:
    - shadow
    - reflection
    - glare
  include_cameras:
    - front_door
    - driveway
    - back_door

processing:
  max_events_per_run: 10
  dry_run: false
  state_file: "/var/lib/fpr/state.json"
  submission_method: "snapshot"

logging:
  level: "WARNING"
  file: "/var/log/fpr/fpr.log"
  json_format: true
```

## Development Configuration

```yaml
frigate:
  base_url: "http://localhost:5000"
  plus_api_key: "fp_dev_key"
  poll_interval_seconds: 30
  event_lookback_minutes: 5

vision_model:
  provider: "gemini"
  api_key: "AIzaSyABC123..."
  model_name: "gemini-2.0-flash-exp"
  timeout_seconds: 30

review_rules:
  min_confidence: 0.3  # Lower for testing
  # No label restrictions

processing:
  max_events_per_run: 5
  dry_run: true  # Safe for development
  state_file: "state-dev.json"
  submission_method: "snapshot"

logging:
  level: "DEBUG"
  file: "fpr-dev.log"
  json_format: false
```
