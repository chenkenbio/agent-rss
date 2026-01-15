"""Configuration loading for agent-rss."""

import os
import re
from pathlib import Path
from typing import Any

import yaml


def expand_env_vars(value: str) -> str:
    """Expand environment variables in a string."""
    pattern = r'\$\{(\w+)\}'

    def replace(match):
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    return re.sub(pattern, replace, value)


def expand_config(obj: Any) -> Any:
    """Recursively expand environment variables in config."""
    if isinstance(obj, str):
        return expand_env_vars(obj)
    elif isinstance(obj, dict):
        return {k: expand_config(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [expand_config(item) for item in obj]
    return obj


def load_config(config_path: Path | str) -> dict:
    """
    Load configuration from YAML file.

    Parameters
    ----------
    config_path : Path | str
        Path to config.yaml file

    Returns
    -------
    dict
        Configuration dictionary with environment variables expanded
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    return expand_config(config)


def parse_rss_list(rss_list_path: Path | str) -> list[str]:
    """
    Parse RSS feed URLs from rss_list.md (simple list, no groups).

    Parameters
    ----------
    rss_list_path : Path | str
        Path to rss_list.md file

    Returns
    -------
    list[str]
        List of RSS feed URLs
    """
    grouped = parse_rss_list_grouped(rss_list_path)
    # Flatten all groups into a single list
    urls = []
    for group_urls in grouped.values():
        urls.extend(group_urls)
    return urls


def parse_rss_list_grouped(rss_list_path: Path | str) -> dict[str, list[str]]:
    """
    Parse RSS feed URLs from rss_list.md with group support.

    Format:
    ```
    # Group Name
    - url1
    - url2

    # Another Group
    - url3
    ```

    Parameters
    ----------
    rss_list_path : Path | str
        Path to rss_list.md file

    Returns
    -------
    dict[str, list[str]]
        Dictionary mapping group names to list of URLs.
        Default group is "default" for URLs without a group header.
    """
    rss_list_path = Path(rss_list_path)
    if not rss_list_path.exists():
        raise FileNotFoundError(f"RSS list file not found: {rss_list_path}")

    groups: dict[str, list[str]] = {}
    current_group = "default"

    with open(rss_list_path) as f:
        for line in f:
            line = line.strip()
            # Skip empty lines
            if not line:
                continue
            # Check for group header (# Group Name)
            if line.startswith('#'):
                current_group = line[1:].strip().lower()
                if current_group not in groups:
                    groups[current_group] = []
                continue
            # Extract URLs (handle markdown list format)
            if line.startswith('- '):
                line = line[2:].strip()
            if line.startswith('http'):
                if current_group not in groups:
                    groups[current_group] = []
                groups[current_group].append(line)

    return groups


def load_interests(interests_path: Path | str) -> str:
    """
    Load research interests from interests.md.

    Parameters
    ----------
    interests_path : Path | str
        Path to interests.md file

    Returns
    -------
    str
        Research interests as a string
    """
    interests_path = Path(interests_path)
    if not interests_path.exists():
        raise FileNotFoundError(f"Interests file not found: {interests_path}")

    with open(interests_path) as f:
        return f.read().strip()
