#!/usr/bin/env python3
"""
Frigate Plus Reviewer (FPR)
Automatic review and submission of Frigate detection events using vision AI.
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Optional

import yaml

from frigate_client import FrigateClient
from vision_client import create_vision_client
from submitter import FrigatePlusSubmitter
from state_manager import StateManager
from reviewer import EventReviewer


def setup_logging(log_level: str, log_file: Optional[str] = None, json_format: bool = False):
    """
    Configure logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        json_format: Use JSON format for logs
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create formatter
    if json_format:
        formatter = logging.Formatter(
            '{"time": "%(asctime)s", "level": "%(levelname)s", '
            '"module": "%(name)s", "message": "%(message)s"}'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        logging.info(f"Logging to file: {log_file}")


def load_config(config_path: str) -> dict:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config.yaml
        
    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logging.info(f"Loaded configuration from {config_path}")
        return config
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logging.error(f"Invalid YAML in configuration file: {e}")
        sys.exit(1)


def validate_config(config: dict) -> bool:
    """
    Validate configuration has required fields.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if valid, exits otherwise
    """
    required_sections = ['frigate', 'vision_model', 'review_rules', 'processing']
    
    for section in required_sections:
        if section not in config:
            logging.error(f"Missing required configuration section: {section}")
            return False
    
    # Validate Frigate config
    frigate_config = config['frigate']
    if not frigate_config.get('base_url'):
        logging.error("Missing frigate.base_url in configuration")
        return False
    if not frigate_config.get('plus_api_key'):
        logging.error("Missing frigate.plus_api_key in configuration")
        return False
    
    # Validate vision model config
    vision_config = config['vision_model']
    if not vision_config.get('provider'):
        logging.error("Missing vision_model.provider in configuration")
        return False
    if not vision_config.get('api_key'):
        logging.error("Missing vision_model.api_key in configuration")
        return False
    
    return True


def run_once(config: dict, dry_run: bool = False):
    """
    Run a single review cycle.
    
    Args:
        config: Configuration dictionary
        dry_run: If True, don't actually submit to Frigate+
    """
    logging.info("Starting single review cycle")
    
    # Initialize clients
    frigate_client = FrigateClient(
        base_url=config['frigate']['base_url'],
        timeout=30
    )
    
    vision_client = create_vision_client(
        provider=config['vision_model']['provider'],
        api_key=config['vision_model']['api_key'],
        model_name=config['vision_model']['model_name'],
        endpoint_url=config['vision_model'].get('endpoint_url'),
        timeout=config['vision_model'].get('timeout_seconds', 30)
    )
    
    submitter = FrigatePlusSubmitter(
        base_url=config['frigate']['base_url'],
        plus_api_key=config['frigate']['plus_api_key'],
        timeout=30
    )
    
    state_manager = StateManager(
        state_file=config['processing'].get('state_file', 'state.json')
    )
    
    # Test connection
    if not frigate_client.test_connection():
        logging.error("Cannot connect to Frigate. Exiting.")
        sys.exit(1)
    
    # Initialize reviewer
    reviewer = EventReviewer(
        frigate_client=frigate_client,
        vision_client=vision_client,
        submitter=submitter,
        state_manager=state_manager,
        min_confidence=config['review_rules'].get('min_confidence', 0.5),
        dry_run=dry_run or config['processing'].get('dry_run', False),
        submission_method=config['processing'].get('submission_method', 'snapshot')
    )
    
    # Get events
    lookback_minutes = config['frigate'].get('event_lookback_minutes', 10)
    events = frigate_client.get_events(
        lookback_minutes=lookback_minutes,
        has_snapshot=True
    )
    
    if not events:
        logging.info("No events found")
        return
    
    # Filter events
    filtered_events = frigate_client.filter_events(
        events=events,
        min_confidence=config['review_rules'].get('min_confidence', 0.0),
        allowed_labels=config['review_rules'].get('allowed_labels'),
        reject_labels=config['review_rules'].get('reject_labels'),
        exclude_cameras=config['review_rules'].get('exclude_cameras'),
        include_cameras=config['review_rules'].get('include_cameras')
    )
    
    # Limit batch size
    max_events = config['processing'].get('max_events_per_run', 20)
    if len(filtered_events) > max_events:
        logging.info(f"Limiting to {max_events} events (found {len(filtered_events)})")
        filtered_events = filtered_events[:max_events]
    
    # Review batch
    stats = reviewer.review_batch(filtered_events)
    
    logging.info(f"Review cycle complete: {stats}")


def run_daemon(config: dict, dry_run: bool = False):
    """
    Run continuously in daemon mode.
    
    Args:
        config: Configuration dictionary
        dry_run: If True, don't actually submit to Frigate+
    """
    logging.info("Starting daemon mode")
    
    poll_interval = config['frigate'].get('poll_interval_seconds', 60)
    
    try:
        while True:
            try:
                run_once(config, dry_run)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logging.error(f"Error in review cycle: {e}", exc_info=True)
            
            logging.info(f"Sleeping for {poll_interval} seconds...")
            time.sleep(poll_interval)
    
    except KeyboardInterrupt:
        logging.info("Received interrupt signal, shutting down")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Frigate Plus Reviewer - Automatic review and submission of detection events'
    )
    
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run once and exit (default is continuous daemon mode)'
    )
    
    parser.add_argument(
        '--daemon',
        action='store_true',
        help='Run continuously in daemon mode (default behavior)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Review events but do not submit to Frigate+'
    )
    
    parser.add_argument(
        '--log',
        help='Log to specified file (in addition to console)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose (DEBUG) logging'
    )
    
    args = parser.parse_args()
    
    # Load config
    config = load_config(args.config)
    
    # Setup logging
    log_level = 'DEBUG' if args.verbose else config.get('logging', {}).get('level', 'INFO')
    log_file = args.log or config.get('logging', {}).get('file')
    json_format = config.get('logging', {}).get('json_format', False)
    
    setup_logging(log_level, log_file, json_format)
    
    # Validate config
    if not validate_config(config):
        logging.error("Configuration validation failed")
        sys.exit(1)
    
    # Determine run mode
    if args.once:
        run_once(config, args.dry_run)
    else:
        # Default to daemon mode
        run_daemon(config, args.dry_run)


if __name__ == '__main__':
    main()
