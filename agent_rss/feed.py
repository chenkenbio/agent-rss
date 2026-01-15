"""RSS feed fetching and parsing."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import feedparser

logger = logging.getLogger(__name__)


@dataclass
class Paper:
    """Represents an academic paper from an RSS feed."""

    title: str
    link: str
    authors: str
    abstract: str
    published: Optional[datetime]
    source: str  # Journal/conference name
    feed_url: str
    feed_group: str = "default"  # Group name from rss_list.md

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "link": self.link,
            "authors": self.authors,
            "abstract": self.abstract,
            "published": self.published.isoformat() if self.published else None,
            "source": self.source,
            "feed_url": self.feed_url,
        }


def parse_date(entry: dict) -> Optional[datetime]:
    """Parse publication date from feed entry."""
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        try:
            return datetime(*entry.published_parsed[:6])
        except (TypeError, ValueError):
            pass
    if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
        try:
            return datetime(*entry.updated_parsed[:6])
        except (TypeError, ValueError):
            pass
    return None


def extract_authors(entry: dict) -> str:
    """Extract authors from feed entry."""
    # Try different author fields
    if hasattr(entry, 'authors') and entry.authors:
        names = [a.get('name', '') for a in entry.authors if a.get('name')]
        if names:
            return ', '.join(names)
    if hasattr(entry, 'author') and entry.author:
        return entry.author
    if hasattr(entry, 'author_detail') and entry.author_detail:
        return entry.author_detail.get('name', 'Unknown')
    return 'Unknown'


def extract_abstract(entry: dict) -> str:
    """Extract abstract/summary from feed entry."""
    # Try summary first
    if hasattr(entry, 'summary') and entry.summary:
        return entry.summary
    # Try description
    if hasattr(entry, 'description') and entry.description:
        return entry.description
    # Try content
    if hasattr(entry, 'content') and entry.content:
        for content in entry.content:
            if content.get('value'):
                return content['value']
    return ''


def fetch_feed(feed_url: str) -> list[Paper]:
    """
    Fetch and parse an RSS feed.

    Parameters
    ----------
    feed_url : str
        URL of the RSS feed

    Returns
    -------
    list[Paper]
        List of papers from the feed
    """
    logger.info(f"Fetching feed: {feed_url}")

    try:
        feed = feedparser.parse(feed_url)
    except Exception as e:
        logger.error(f"Failed to fetch feed {feed_url}: {e}")
        return []

    if feed.bozo and feed.bozo_exception:
        logger.warning(f"Feed parsing warning for {feed_url}: {feed.bozo_exception}")

    # Get feed title as source
    source = feed.feed.get('title', 'Unknown Source') if hasattr(feed, 'feed') else 'Unknown Source'

    papers = []
    for entry in feed.entries:
        try:
            paper = Paper(
                title=entry.get('title', 'No Title'),
                link=entry.get('link', ''),
                authors=extract_authors(entry),
                abstract=extract_abstract(entry),
                published=parse_date(entry),
                source=source,
                feed_url=feed_url,
            )
            papers.append(paper)
        except Exception as e:
            logger.error(f"Failed to parse entry: {e}")
            continue

    logger.info(f"Found {len(papers)} papers from {source}")
    return papers


def fetch_all_feeds(feed_urls: list[str]) -> list[Paper]:
    """
    Fetch papers from multiple RSS feeds.

    Parameters
    ----------
    feed_urls : list[str]
        List of RSS feed URLs

    Returns
    -------
    list[Paper]
        Combined list of papers from all feeds
    """
    all_papers = []
    for url in feed_urls:
        papers = fetch_feed(url)
        all_papers.extend(papers)
    return all_papers
