# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**agent-rss** is an RSS feed screening system for academic papers. It monitors RSS feeds from journals, preprint servers, and conference proceedings, then filters papers based on research interests using LLM APIs.

**Domain**: Deep learning and genomics/biology

## Environment
- python: /opt/miniforge3.202506/envs/agent-rss/bin/python

## Configuration Files

- `rss_list.md` - RSS feed URLs to monitor
- `interests.md` - Research interests and keywords for filtering
- `PLAN.md` - Project requirements and vision

## Planned Technology Stack

- **Language**: Python 3.8+
- **RSS Processing**: feedparser
- **LLM APIs**: Claude (Anthropic), OpenAI, or Gemini for content screening
- **Scheduling**: cron or APScheduler for periodic checks
- **Storage**: SQLite for tracking processed articles

## Architecture Requirements

- **Lightweight**: No heavy infrastructure
- **Scalable**: Handle hundreds of papers daily
- **Periodic**: Daily/weekly RSS feed checks
- **Output format**: Concise summaries with:
  - Journal/conference name
  - Paper title
  - First author / corresponding author and institution
  - Brief abstract highlighting relevance

## Development Commands

Once implemented, typical commands will include:

```bash
# Install dependencies
pip install -e .

# Run feed check manually
python -m agent_rss.main

# Run tests
pytest tests/
```
