#!/usr/bin/env python3
"""
Test runner script for MCP database operations.
Run this script to execute all tests and generate reports.
"""

import os
import sys
from pathlib import Path

import pytest


def main():
    """Run all tests with detailed reporting."""

    # Set up environment
    test_dir = Path(__file__).parent
    os.chdir(test_dir.parent)  # Change to project root

    # Test arguments
    test_args = [
        str(test_dir),
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--asyncio-mode=auto",  # Auto async mode
        "-s",  # Don't capture output
        "--log-cli-level=INFO",  # Show logs
    ]

    # Add coverage if available
    try:
        import coverage

        test_args.extend(
            ["--cov=src", "--cov-report=html", "--cov-report=term-missing"]
        )
    except ImportError:
        print("Coverage not available, running without coverage report")

    # Run tests
    print("🚀 Starting MCP Database Operation Tests...")
    print("=" * 60)

    exit_code = pytest.main(test_args)

    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code: {exit_code}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
