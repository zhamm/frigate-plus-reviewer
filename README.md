# Frigate Plus Reviewer (FPR)

Automatic review and submission of Frigate detection events using vision-capable AI models.

## Overview

FPR is a standalone Python application that automatically reviews Frigate NVR detection events using vision AI (Google Gemini or OpenAI-compatible models) and submits structured feedback to Frigate+ for model fine-tuning.

The application:
- Pulls detection events from your Frigate instance
- Retrieves the associated snapshot images
- Sends images to a vision model for analysis
- Determines if detections are valid, invalid, or mislabeled
- Submits results to Frigate+ using official APIs
- Tracks processed events to prevent duplicates

## Features

- ✅ **Multiple Vision Model Support**: Works with Google Gemini and OpenAI-compatible endpoints
- ✅ **Flexible Submission**: Supports both snapshot and event submission methods
- ✅ **Configurable Filtering**: Filter events by confidence, labels, cameras, and time
- ✅ **State Management**: JSON-based tracking to prevent duplicate submissions
- ✅ **Daemon Mode**: Run continuously or as a one-shot task
- ✅ **Dry Run**: Test without actually submitting to Frigate+ (events NOT marked as processed)
- ✅ **Comprehensive Logging**: Structured logging with file and console output

## Quick Start

```bash
# 1. Run setup script
./setup.sh

# 2. Activate virtual environment
source venv/bin/activate

# 3. Edit config.yaml with your API keys
nano config.yaml

# 4. Test with dry-run
python main.py --once --dry-run --verbose

# 5. Run for real
python main.py --once
```

## Prerequisites

1. **Frigate NVR** with:
   - Snapshots enabled
   - Clean snapshots enabled (recommended)
   - Frigate+ configured with valid API key

2. **Vision Model Access**:
   - Google Gemini API key (recommended: `gemini-2.0-flash-exp`), OR
   - OpenAI-compatible API endpoint and key

3. **Python 3.10+**

## Installation

### Quick Setup (Ubuntu 24.04 / Debian)

1. Clone or download this repository:

```bash
cd frigate-plus-reviewer
```

2. Run the setup script (creates venv and installs dependencies):

```bash
./setup.sh
```

3. Activate the virtual environment:

```bash
source venv/bin/activate
```

4. Edit `config.yaml` with your API keys and settings:

```bash
nano config.yaml
```

### Manual Installation

If you prefer not to use the setup script:

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Edit configuration
nano config.yaml
```

**Note**: On Ubuntu 24.04+, you must use a virtual environment (venv) as system-wide pip installs are restricted.

## Configuration

Edit `config.yaml` with your settings:

### Frigate Settings

```yaml
frigate:
  base_url: "http://localhost:5000"  # Your Frigate URL
  plus_api_key: "YOUR_FRIGATE_PLUS_API_KEY"
  poll_interval_seconds: 60  # How often to check for new events
  event_lookback_minutes: 10  # How far back to look for events
```

### Vision Model Settings

For **Google Gemini**:

```yaml
vision_model:
  provider: "gemini"
  api_key: "YOUR_GOOGLE_API_KEY"
  model_name: "gemini-2.0-flash-exp"
  timeout_seconds: 30
```

For **OpenAI-compatible** endpoints:

```yaml
vision_model:
  provider: "openai_compatible"
  api_key: "YOUR_OPENAI_API_KEY"
  model_name: "gpt-4-vision-preview"
  endpoint_url: "https://api.openai.com/v1"
  timeout_seconds: 30
```

### Review Rules

```yaml
review_rules:
  min_confidence: 0.5  # Minimum detection confidence
  
  # Only review these labels (empty = all)
  allowed_labels:
    - person
    - car
    - dog
    - cat
  
  # Never review these labels
  reject_labels:
    - shadow
    - reflection
  
  # Optional camera filters
  # include_cameras:
  #   - front_door
  # exclude_cameras:
  #   - backyard
```

### Processing Settings

```yaml
processing:
  max_events_per_run: 20  # Max events per cycle
  dry_run: false  # Set to true to test without submitting
  state_file: "state.json"  # Track processed events
  submission_method: "snapshot"  # or "event"
  mark_as_reviewed: true  # Mark events as reviewed in Frigate UI
```

**Important:** `mark_as_reviewed` controls whether events are marked as reviewed in your local Frigate NVR after successful submission to Frigate+. When `true`, processed events are removed from the review queue in Frigate's UI, preventing duplicate manual reviews.

## Usage

### Basic Usage

**Important**: Always activate the virtual environment first:

```bash
source venv/bin/activate
```

Run once and exit:

```bash
python main.py --once
```

Run continuously (daemon mode):

```bash
python main.py --daemon
# or simply:
python main.py
```

### Command-Line Options

| Option | Description |
|--------|-------------|
| `--once` | Run once and exit (instead of continuous daemon mode) |
| `--daemon` | Run continuously (default behavior if no flags specified) |
| `--dry-run` | Review events but don't submit to Frigate+ (for testing) |
| `--config FILE` | Use custom configuration file (default: config.yaml) |
| `--log FILE` | Log to specified file (in addition to console output) |
| `--verbose` | Enable verbose (DEBUG level) logging |

### Common Usage Examples

```bash
# Test configuration without submitting
python main.py --once --dry-run --verbose

# Process events once with logging
python main.py --once --log fpr.log

# Run continuously with verbose logging
python main.py --daemon --verbose --log fpr.log

# Use custom config file
python main.py --config production.yaml --once
```

### Important: Dry-Run Behavior

When using `--dry-run`:
- Events are reviewed and analyzed by the vision model
- Decisions are logged (valid/invalid/corrected)
- **Events are NOT submitted to Frigate+**
- **Events are NOT marked as processed** (can be processed again later)

This allows you to test the application safely without affecting your Frigate+ data. Once you remove the `--dry-run` flag, events will be submitted and marked as processed to prevent duplicates.

### Running as a Service

**Important**: Ensure the virtual environment is referenced in the service file.

Create a systemd service file `/etc/systemd/system/fpr.service`:

```ini
[Unit]
Description=Frigate Plus Reviewer
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/frigate-plus-reviewer
ExecStart=/path/to/frigate-plus-reviewer/venv/bin/python /path/to/frigate-plus-reviewer/main.py --daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable fpr
sudo systemctl start fpr
sudo systemctl status fpr

# View logs
sudo journalctl -u fpr -f
```

### Running with Cron

For periodic execution (activate venv in the command):

```bash
# Run every 5 minutes
*/5 * * * * cd /path/to/frigate-plus-reviewer && /path/to/frigate-plus-reviewer/venv/bin/python main.py --once >> fpr-cron.log 2>&1
```

## How It Works

### Understanding Frigate vs Frigate+

**Frigate (Local NVR)**: Your local network video recorder that detects objects
**Frigate+ (Cloud Service)**: Cloud-based model training service that improves detection accuracy

This application does **both**:
1. Submits feedback to **Frigate+** (cloud) for model training
2. Marks events as reviewed in **Frigate** (local) to clear your review queue

### Workflow

1. **Event Retrieval**: FPR queries Frigate for recent detection events within the configured lookback window

2. **Filtering**: Events are filtered based on:
   - Already processed (tracked in state.json)
   - Minimum confidence threshold
   - Allowed/rejected labels
   - Camera inclusion/exclusion
   - Snapshot availability

3. **Vision Analysis**: Each snapshot is sent to the vision model with a structured prompt asking:
   - Is a real object present?
   - What is the correct label?
   - What is the confidence level?

4. **Decision Making**:
   - **No object** → Mark as invalid (false positive)
   - **Same label** → Mark as valid
   - **Different label** → Mark as corrected with new label
   - **Low confidence** → Skip submission

5. **Submission to Frigate+**: Results are submitted to Frigate+ cloud using either:
   - Snapshot submission: `/api/:camera/plus/:frame_time` (default)
   - Event submission: `/api/events/:event_id/plus`

6. **Mark as Reviewed in Frigate**: If `mark_as_reviewed: true`, events are marked as reviewed in your local Frigate, removing them from the review queue

7. **State Tracking**: Processed events are recorded in `state.json` to prevent duplicates

## Project Structure

```
frigate-plus-reviewer/
├── main.py              # CLI entry point and orchestration
├── frigate_client.py    # Frigate API client
├── vision_client.py     # Vision model clients (Gemini/OpenAI)
├── submitter.py         # Frigate+ submission client
├── reviewer.py          # Core review logic
├── state_manager.py     # State tracking
├── config.yaml          # Configuration file
├── requirements.txt     # Python dependencies
├── README.md           # This file
└── tests/              # Optional test files
```

## Troubleshooting

### Installation Issues

**"Command 'pip' not found" on Ubuntu 24.04:**
- Use the provided `setup.sh` script instead
- Or manually create a venv: `python3 -m venv venv && source venv/bin/activate`

**Import errors when running:**
- Ensure virtual environment is activated: `source venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

### Connection Issues

```bash
# Test Frigate connection
curl http://localhost:5000/api/stats

# Check Frigate+ API key
# View in Frigate UI: Settings → Frigate+ → API Key
```

### Vision Model Issues

**Gemini Errors:**
- Verify API key is valid: https://aistudio.google.com/apikey
- Check quota limits: https://console.cloud.google.com/apis/api/generativeai.googleapis.com
- Try using `gemini-2.0-flash-exp` or `gemini-2.5-flash-lite` models

**OpenAI Errors:**
- Verify endpoint URL and API key
- Ensure model supports vision capabilities

### "All events already processed"

If you ran with `--dry-run` before version 1.0.1, the state file may incorrectly mark events as processed:

```bash
# Delete the state file to start fresh
rm state.json

# Then run without dry-run
python main.py --once
```

**Note**: As of version 1.0.1, dry-run mode no longer marks events as processed in the state file.

### Logging

Enable verbose logging to see detailed information:

```bash
source venv/bin/activate
python main.py --verbose --log debug.log
```

Check the log file for:
- Event filtering decisions
- Vision model responses
- Submission results
- Error details

### State File Issues

**To reprocess events:**

```bash
# Backup current state (optional)
cp state.json state.json.backup

# Reset state (will reprocess all events in lookback window)
rm state.json

# Run again
source venv/bin/activate
python main.py --once
```

**Understanding state.json:**
- Tracks which events have been submitted to Frigate+
- Prevents duplicate submissions
- Only updated when events are actually submitted (not in dry-run mode)
- Can be safely deleted to start fresh

## Testing

Run the application in dry-run mode to test without submitting:

```bash
source venv/bin/activate
python main.py --once --dry-run --verbose
```

Optional unit tests (if available):

```bash
source venv/bin/activate
pytest tests/
```

## API References

- [Frigate Documentation](https://docs.frigate.video/)
- [Frigate+ API - Submit Snapshot](https://docs.frigate.video/integrations/api/submit-recording-snapshot-to-plus-camera-name-plus-frame-time-post/)
- [Frigate+ API - Submit Event](https://docs.frigate.video/integrations/api/send-to-plus-events-event-id-plus-post/)
- [Google Gemini API](https://ai.google.dev/docs)
- [OpenAI Vision API](https://platform.openai.com/docs/guides/vision)

## Performance Considerations

- **Rate Limiting**: The application processes events sequentially to respect API rate limits
- **Image Size**: Large snapshots may increase processing time and API costs
- **Lookback Window**: Shorter windows reduce processing load
- **Max Events**: Limit batch size to control processing time per cycle

## Security Notes

- Store API keys securely (use environment variables or secure vaults in production)
- Use HTTPS for Frigate if exposed to untrusted networks
- Review the state file permissions (`state.json`) as it contains processing history
- Consider running as a dedicated user with minimal permissions

## Limitations

- No UI or web interface
- No database server requirement (JSON-based state)
- No human-in-the-loop review workflow
- Sequential processing (no parallel vision model calls)

## Changelog

### Version 1.0.2 (2026-01-01)
- **Added**: Automatic marking of events as reviewed in Frigate NVR (configurable with `mark_as_reviewed`)
- **Added**: `mark_event_reviewed()` method in FrigateClient
- **Improved**: Events now removed from Frigate review queue after successful submission
- **Improved**: Documentation explaining difference between Frigate (local) and Frigate+ (cloud)

### Version 1.0.1 (2026-01-01)
- **Fixed**: Dry-run mode no longer marks events as processed in state.json
- **Added**: Ubuntu 24.04 support with automatic venv setup via `setup.sh`
- **Added**: `--log` command-line flag for file logging
- **Improved**: Documentation with clearer setup and usage instructions

### Version 1.0.0 (2026-01-01)
- Initial release
- Support for Google Gemini and OpenAI-compatible vision models
- Snapshot and event submission methods
- Configurable event filtering
- State management to prevent duplicates
- Dry-run mode for testing
- Daemon and one-shot execution modes

## License

This project is provided as-is for use with Frigate NVR and Frigate+ services.

## Contributing

Feel free to submit issues, feature requests, or pull requests.

## Support

For issues related to:
- **Frigate**: See [Frigate GitHub](https://github.com/blakeblackshear/frigate)
- **Frigate+**: See [Frigate+ Documentation](https://docs.frigate.video/frigate+)
- **This Application**: Open an issue in this repository
