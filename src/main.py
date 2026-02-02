"""Main entry point for metrics collection agent"""

import sys
import argparse
from pathlib import Path

from src.config.settings import load_config
from src.utils.logger import setup_logger
from src.agent import Agent


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Metrics Collection Agent for System Resource Monitoring'
    )

    parser.add_argument(
        '--config',
        '-c',
        type=str,
        default=None,
        help='Path to configuration file (YAML)'
    )

    parser.add_argument(
        '--log-level',
        '-l',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default=None,
        help='Override log level'
    )

    parser.add_argument(
        '--version',
        '-v',
        action='version',
        version='Metrics Agent v1.0.0'
    )

    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()

    try:
        # Load configuration
        config = load_config(args.config)

        # Override log level from command line
        if args.log_level:
            config['agent']['log_level'] = args.log_level

        # Setup logger
        logger = setup_logger(config)
        logger.info("=" * 60)
        logger.info("Metrics Collection Agent v1.0.0")
        logger.info("=" * 60)

        if args.config:
            logger.info(f"Loaded configuration from: {args.config}")
        else:
            logger.info("Using default configuration")

        # Create and start agent
        agent = Agent(config)
        agent.start()

        return 0

    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        return 0
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
