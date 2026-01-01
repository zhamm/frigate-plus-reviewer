# Quick Start Guide

## Setup in 5 Minutes

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure

Edit `config.yaml` and add your keys:

```yaml
frigate:
  base_url: "http://YOUR_FRIGATE_IP:5000"
  plus_api_key: "YOUR_FRIGATE_PLUS_KEY"

vision_model:
  provider: "gemini"
  api_key: "YOUR_GOOGLE_API_KEY"
  model_name: "gemini-2.0-flash-exp"
```

**Get your API keys:**
- Frigate+: Settings → Frigate+ → API Key (in Frigate UI)
- Google Gemini: https://aistudio.google.com/apikey

### 3. Test

Run in dry-run mode to test without submitting:

```bash
python main.py --once --dry-run --verbose
```

### 4. Run

Process events once:

```bash
python main.py --once
```

Run continuously:

```bash
python main.py
```

## Verify It's Working

Check the logs for:
- ✅ "Successfully connected to Frigate"
- ✅ "Retrieved X events from Frigate"
- ✅ "Decision for event..."
- ✅ "Successfully submitted..."

## Common Issues

**"Failed to connect to Frigate"**
→ Check `frigate.base_url` in config.yaml

**"Failed to retrieve events"**
→ Ensure Frigate is running and snapshots are enabled

**Vision model errors**
→ Verify API key and internet connection

**No events found**
→ Events may have already been processed, or check `event_lookback_minutes`

## Next Steps

- Adjust `review_rules` to filter by labels/cameras
- Set `submission_method` to "event" if preferred
- Run as daemon for continuous operation
- Add to systemd or cron for automatic startup

See [README.md](README.md) for full documentation.
