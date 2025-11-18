#!/usr/bin/env python3
"""
Check CBORG API budget spending and warn if over threshold.

This script queries the CBORG API to get current spending information
and outputs a warning if spending exceeds 75% of the budget.

Environment variables:
    ANTHROPIC_API_KEY: Anthropic API key managed by CBORG (required)

Exit codes:
    0: Success (budget checked, under threshold or warning printed)
    1: Error (could not check budget)

Output format (if > 75%):
    WARNING: XX.X%
    $XXX.XX / $XXX.XX
"""

import os
import sys
import json

def check_budget():
    """
    Check the CBORG API budget and return spending information.

    Returns:
        dict or None: Dictionary with 'spend', 'max_budget', and 'percent' keys,
                     or None if budget check failed or API key not available.
    """
    # Check for API key - prefer ANTHROPIC_API_KEY (GitHub Actions), fall back to CBORG_API_KEY (local dev)
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CBORG_API_KEY")
    if not api_key:
        print("Warning: Neither ANTHROPIC_API_KEY nor CBORG_API_KEY set, skipping budget check", file=sys.stderr)
        return None

    try:
        # Use requests if available, otherwise fall back to urllib
        try:
            import requests
            response = requests.get(
                "https://api.cborg.lbl.gov/key/info",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
        except ImportError:
            # Fallback to urllib if requests not available
            import urllib.request
            import urllib.error

            req = urllib.request.Request(
                "https://api.cborg.lbl.gov/key/info",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())

        spend = data["info"]["spend"]
        max_budget = data["info"]["max_budget"]
        percent = (spend / max_budget) * 100

        return {
            "spend": spend,
            "max_budget": max_budget,
            "percent": percent
        }
    except Exception as e:
        print(f"Warning: Could not check budget: {e}", file=sys.stderr)
        return None


def format_budget_warning(budget_info):
    """
    Format budget information as a warning message.

    Args:
        budget_info (dict): Budget information with spend, max_budget, and percent

    Returns:
        str: Formatted warning message for GitHub comments
    """
    return f"""---
⚠️ **Budget Alert**: D4D Assistant CBORG API spending is at {budget_info['percent']:.1f}% of budget (${budget_info['spend']:.2f} / ${budget_info['max_budget']:.2f})

Please notify the maintainers to review CBORG API budget.
"""


def main():
    """Main entry point for budget checking script."""
    result = check_budget()

    if result is None:
        # Could not check budget, exit silently (already warned to stderr)
        sys.exit(0)

    # Print budget info to stderr for logging
    print(f"Budget check: ${result['spend']:.2f} / ${result['max_budget']:.2f} ({result['percent']:.1f}%)",
          file=sys.stderr)

    # If over threshold, print warning to stdout for capture
    if result["percent"] > 75:
        print(format_budget_warning(result))
        sys.exit(0)

    # Under threshold, no output needed
    sys.exit(0)


if __name__ == "__main__":
    main()
