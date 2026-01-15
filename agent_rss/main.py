"""CLI entry point for agent-rss."""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import click

from .config import load_config, load_interests, parse_examples, parse_rss_list, parse_rss_list_grouped
from .db import PaperDatabase
from .email_sender import send_email, send_test_email
from .feed import fetch_feed
from .llm import get_llm

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Get the project root directory."""
    # Try to find the project root by looking for rss_list.md
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / "rss_list.md").exists():
            return parent
    return current


@click.group()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True),
    default=None,
    help="Path to config.yaml file",
)
@click.pass_context
def cli(ctx, config):
    """agent-rss: RSS feed screening for academic papers."""
    ctx.ensure_object(dict)

    project_root = get_project_root()

    # Find config file
    if config:
        config_path = Path(config)
    else:
        config_path = project_root / "config.yaml"
        if not config_path.exists():
            config_path = Path.home() / ".agent-rss" / "config.yaml"

    if config_path.exists():
        ctx.obj["config"] = load_config(config_path)
    else:
        ctx.obj["config"] = None

    ctx.obj["project_root"] = project_root


@cli.command()
@click.option("--dry-run", is_flag=True, help="Run without sending email")
@click.option("--days", "-d", type=int, default=10, help="Only screen papers from the last N days (default: 10)")
@click.option("--max-per-feed", "-m", type=int, default=0, help="Max papers to screen per feed (0=unlimited, useful for debug)")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def run(ctx, dry_run, days, max_per_feed, verbose):
    """Fetch feeds, screen papers, and send email notification."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    config = ctx.obj.get("config")
    project_root = ctx.obj["project_root"]

    if not config:
        click.echo("Error: No config.yaml found. Create one from config.yaml.template")
        sys.exit(1)

    # Load RSS feeds (grouped), interests, and examples
    try:
        feed_groups = parse_rss_list_grouped(project_root / "rss_list.md")
        interests = load_interests(project_root / "interests.md")
        examples = parse_examples(project_root / "examples.md")  # Optional file
    except FileNotFoundError as e:
        click.echo(f"Error: {e}")
        sys.exit(1)

    total_feeds = sum(len(urls) for urls in feed_groups.values())
    click.echo(f"Found {total_feeds} RSS feed(s) in {len(feed_groups)} group(s)")
    for group, urls in feed_groups.items():
        click.echo(f"  [{group}]: {len(urls)} feed(s)")
    click.echo(f"Research interests: {interests[:100]}...")
    if examples["liked"] or examples["disliked"]:
        click.echo(f"Examples: {len(examples['liked'])} liked, {len(examples['disliked'])} disliked")

    # Initialize database
    db_path = config.get("database", {}).get("path", "~/.agent-rss/papers.db")
    db = PaperDatabase(db_path)

    # Initialize LLM
    provider = config["llm"]["provider"]
    api_key_map = {
        "claude": config["api_keys"].get("anthropic"),
        "openai": config["api_keys"].get("openai"),
        "gemini": config["api_keys"].get("google"),
    }
    api_key = api_key_map.get(provider)

    if not api_key or api_key.startswith("${"):
        click.echo(f"Error: API key for {provider} not configured")
        sys.exit(1)

    model = config["llm"].get("model")  # Optional, uses provider default if not set
    llm = get_llm(provider, api_key, model=model)
    click.echo(f"Using LLM: {provider}" + (f" ({model})" if model else ""))

    # Fetch papers from all feeds, tracking group membership
    # Build url -> group mapping
    url_to_group = {}
    for group, urls in feed_groups.items():
        for url in urls:
            url_to_group[url] = group

    all_papers = []
    for group, urls in feed_groups.items():
        for url in urls:
            papers = fetch_feed(url)
            for p in papers:
                p.feed_group = group  # Add group info to paper
            all_papers.extend(papers)

    click.echo(f"Fetched {len(all_papers)} total paper(s)")

    # Filter by publication date (only papers within the last N days)
    cutoff_date = datetime.now() - timedelta(days=days)
    recent_papers = []
    skipped_old = 0
    for p in all_papers:
        if p.published and p.published >= cutoff_date:
            recent_papers.append(p)
        elif p.published is None:
            recent_papers.append(p)
        else:
            skipped_old += 1

    if skipped_old > 0:
        click.echo(f"Skipped {skipped_old} paper(s) older than {days} days")

    # Filter unprocessed papers
    new_papers = [p for p in recent_papers if not db.is_processed(p.link)]
    click.echo(f"Found {len(new_papers)} new paper(s) to screen (within {days} days)")

    # Limit papers per feed if specified (useful for debug mode)
    if max_per_feed > 0:
        from collections import defaultdict
        feed_counts = defaultdict(int)
        limited_papers = []
        for p in new_papers:
            if feed_counts[p.feed_url] < max_per_feed:
                limited_papers.append(p)
                feed_counts[p.feed_url] += 1
        if len(limited_papers) < len(new_papers):
            click.echo(f"Limited to {max_per_feed} paper(s) per feed: {len(limited_papers)} paper(s) to screen")
        new_papers = limited_papers

    if not new_papers:
        click.echo("No new papers to process")
        return

    # Screen papers with group-based criteria
    # high-quality: field OR method match
    # other groups: field AND method match
    relevant_papers = []
    for paper in new_papers:
        group = getattr(paper, 'feed_group', url_to_group.get(paper.feed_url, 'default'))
        click.echo(f"Screening [{group}]: {paper.title[:55]}...")
        try:
            result = llm.screen_paper(
                title=paper.title,
                authors=paper.authors,
                abstract=paper.abstract,
                source=paper.source,
                interests=interests,
                examples=examples,
            )

            # Apply group-specific criteria
            is_high_quality = 'high' in group.lower() or 'quality' in group.lower()
            if is_high_quality:
                # High-quality: field OR method match
                is_relevant = result.field_match or result.method_match
            else:
                # Other: field AND method match
                is_relevant = result.field_match and result.method_match

            db.mark_processed(
                feed_url=paper.feed_url,
                paper_url=paper.link,
                title=paper.title,
                is_relevant=is_relevant,
                summary=result.summary,
                authors=paper.authors,
                source=paper.source,
                feed_group=group,
                field_match=result.field_match,
                method_match=result.method_match,
            )

            # Show match status
            match_status = f"F:{'✓' if result.field_match else '✗'} M:{'✓' if result.method_match else '✗'}"
            if is_relevant:
                relevant_papers.append({
                    "title": paper.title,
                    "source": paper.source,
                    "authors": paper.authors,
                    "link": paper.link,
                    "group": group,
                    "summary": result.summary,
                })
                click.echo(f"  -> [{match_status}] RELEVANT")
            else:
                click.echo(f"  -> [{match_status}] Skipped")

        except Exception as e:
            logger.error(f"Error screening paper: {e}")
            click.echo(f"  -> Error: {e}")

    click.echo(f"\nFound {len(relevant_papers)} relevant paper(s)")

    # Send email
    if relevant_papers and not dry_run:
        email_config = config.get("email", {})
        success = send_email(
            smtp_server=email_config.get("smtp_server", "smtp.gmail.com"),
            smtp_port=email_config.get("smtp_port", 587),
            username=email_config.get("username"),
            password=email_config.get("password"),
            recipient=email_config.get("recipient"),
            papers=relevant_papers,
            sender_name=email_config.get("sender_name", "agent-rss"),
        )
        if success:
            click.echo("Email notification sent!")
        else:
            click.echo("Failed to send email notification")
    elif dry_run and relevant_papers:
        click.echo("\n[DRY RUN] Would send email with:")
        for p in relevant_papers:
            click.echo(f"  - {p['title']}")


@cli.command("list-feeds")
@click.pass_context
def list_feeds(ctx):
    """List configured RSS feeds."""
    project_root = ctx.obj["project_root"]

    try:
        feed_urls = parse_rss_list(project_root / "rss_list.md")
    except FileNotFoundError as e:
        click.echo(f"Error: {e}")
        sys.exit(1)

    click.echo(f"Configured RSS feeds ({len(feed_urls)}):")
    for url in feed_urls:
        click.echo(f"  - {url}")


@cli.command("test-email")
@click.pass_context
def test_email(ctx):
    """Send a test email to verify configuration."""
    config = ctx.obj.get("config")

    if not config:
        click.echo("Error: No config.yaml found")
        sys.exit(1)

    email_config = config.get("email", {})
    required = ["smtp_server", "smtp_port", "username", "password", "recipient"]
    missing = [k for k in required if not email_config.get(k)]

    if missing:
        click.echo(f"Error: Missing email config: {missing}")
        sys.exit(1)

    click.echo("Sending test email...")
    success = send_test_email(
        smtp_server=email_config["smtp_server"],
        smtp_port=email_config["smtp_port"],
        username=email_config["username"],
        password=email_config["password"],
        recipient=email_config["recipient"],
        sender_name=email_config.get("sender_name", "agent-rss"),
    )

    if success:
        click.echo(f"Test email sent to {email_config['recipient']}")
    else:
        click.echo("Failed to send test email")
        sys.exit(1)


@cli.command()
@click.pass_context
def stats(ctx):
    """Show database statistics."""
    config = ctx.obj.get("config")
    db_path = "~/.agent-rss/papers.db"
    if config:
        db_path = config.get("database", {}).get("path", db_path)

    db = PaperDatabase(db_path)
    stats = db.get_stats()

    click.echo("Database Statistics:")
    click.echo(f"  Total papers processed: {stats['total_papers']}")
    click.echo(f"  Relevant papers: {stats['relevant_papers']}")
    click.echo(f"  Irrelevant papers: {stats['irrelevant_papers']}")


@cli.command("send-report")
@click.option("--days", "-d", type=int, default=7, help="Include papers from the last N days (default: 7)")
@click.option("--dry-run", is_flag=True, help="Show report without sending email")
@click.pass_context
def send_report(ctx, days, dry_run):
    """Send email report of recent relevant papers from database."""
    config = ctx.obj.get("config")

    if not config:
        click.echo("Error: No config.yaml found")
        sys.exit(1)

    db_path = config.get("database", {}).get("path", "~/.agent-rss/papers.db")
    db = PaperDatabase(db_path)

    # Get recent relevant papers
    papers = db.get_recent_relevant(days=days)

    if not papers:
        click.echo(f"No relevant papers found in the last {days} days")
        return

    # Get stats for email
    stats = db.get_stats(days=days)
    stats["total_screened"] = stats["total_papers"]

    click.echo(f"Found {len(papers)} relevant paper(s) from the last {days} days")
    click.echo(f"  Period: {stats['date_from']} to {stats['date_to']}")
    click.echo(f"  Feeds: {stats['num_feeds']}, Screened: {stats['total_screened']}")

    # Format for email
    email_papers = []
    for p in papers:
        email_papers.append({
            "title": p["title"],
            "source": p.get("source") or "Unknown",
            "authors": p.get("authors") or "Unknown",
            "link": p["paper_url"],
            "summary": p["summary"],
        })

    if dry_run:
        click.echo("\n[DRY RUN] Would send email with:")
        for p in email_papers:
            click.echo(f"  - {p['title']}")
            click.echo(f"    {p['link']}")
        return

    email_config = config.get("email", {})
    required = ["smtp_server", "smtp_port", "username", "password", "recipient"]
    missing = [k for k in required if not email_config.get(k)]

    if missing:
        click.echo(f"Error: Missing email config: {missing}")
        sys.exit(1)

    success = send_email(
        smtp_server=email_config["smtp_server"],
        smtp_port=email_config["smtp_port"],
        username=email_config["username"],
        password=email_config["password"],
        recipient=email_config["recipient"],
        papers=email_papers,
        sender_name=email_config.get("sender_name", "agent-rss"),
        stats=stats,
    )

    if success:
        click.echo(f"Report sent to {email_config['recipient']}")
    else:
        click.echo("Failed to send report")
        sys.exit(1)


if __name__ == "__main__":
    cli()
