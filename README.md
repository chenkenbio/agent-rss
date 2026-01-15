# agent-rss

RSS feed screening system for academic papers using LLM APIs.

## Features

- **Multi-provider LLM support**: Claude, OpenAI, Gemini (configurable model)
- **Grouped feeds**: Different screening criteria per group
  - High-quality journals: Field OR Method match
  - Other journals: Field AND Method match
- **Example-based learning**: Provide liked/disliked paper examples to improve screening
- **Structured summaries**: Problem, Method, Data, Highlights
- **Email notifications**: Gmail-friendly HTML format
- **SQLite tracking**: Avoid re-screening processed papers

## Installation

```bash
pip install -e .
```

## Configuration

1. Copy template and edit:
```bash
cp config.yaml.template config.yaml
```

2. Set your API keys and email settings in `config.yaml`

3. Configure RSS feeds in `rss_list.md`:
```markdown
# High-quality
- https://www.nature.com/subjects/computational-biology-and-bioinformatics/ncomms.rss

# Other journals
- https://academic.oup.com/rss/site_5127/advanceAccess_3091.xml
```

4. Set research interests in `interests.md`

5. (Optional) Add paper examples in `examples.md`:
```markdown
# Liked Papers
## Example 1
- **Title**: Deep learning predicts RNA splicing
- **Reason**: Combines DL with RNA biology

# Disliked Papers
## Example 1
- **Title**: Clinical trial results for cancer drug
- **Reason**: Pure clinical study, no computational methods
```

6. (Optional) Configure specific model in `config.yaml`:
```yaml
llm:
  provider: openai
  model: gpt-4o-mini  # defaults: gpt-4o-mini, claude-sonnet-4-20250514, gemini-2.0-flash
```

## Usage

```bash
# Screen papers (dry run)
python -m agent_rss run --days 10 --dry-run

# Screen with limit per feed (debug mode)
python -m agent_rss run --days 10 --max-per-feed 20 --dry-run

# Run and send email
python -m agent_rss run --days 10

# Send report from database
python -m agent_rss send-report --days 7

# List configured feeds
python -m agent_rss list-feeds

# View statistics
python -m agent_rss stats
```

## Cron Setup

```bash
# Daily at 8 AM
0 8 * * * source ~/.bashrc && python -m agent_rss run --days 1
```

## License

MIT
