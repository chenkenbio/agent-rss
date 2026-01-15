"""SQLite database for tracking processed papers."""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PaperDatabase:
    """SQLite database for tracking processed papers."""

    def __init__(self, db_path: str | Path):
        """
        Initialize database.

        Parameters
        ----------
        db_path : str | Path
            Path to SQLite database file
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    feed_url TEXT NOT NULL,
                    paper_url TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    authors TEXT,
                    source TEXT,
                    feed_group TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_relevant BOOLEAN DEFAULT FALSE,
                    field_match BOOLEAN DEFAULT FALSE,
                    method_match BOOLEAN DEFAULT FALSE,
                    summary TEXT
                )
            """)
            # Add columns if they don't exist (migration for existing DB)
            for col in ['authors', 'source', 'feed_group', 'field_match', 'method_match']:
                try:
                    col_type = 'BOOLEAN DEFAULT FALSE' if col.endswith('_match') else 'TEXT'
                    conn.execute(f"ALTER TABLE papers ADD COLUMN {col} {col_type}")
                except sqlite3.OperationalError:
                    pass
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_paper_url ON papers(paper_url)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_processed_at ON papers(processed_at)
            """)
            conn.commit()

    def is_processed(self, paper_url: str) -> bool:
        """
        Check if a paper has been processed.

        Parameters
        ----------
        paper_url : str
            URL of the paper

        Returns
        -------
        bool
            True if paper has been processed
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM papers WHERE paper_url = ?",
                (paper_url,)
            )
            return cursor.fetchone() is not None

    def mark_processed(
        self,
        feed_url: str,
        paper_url: str,
        title: str,
        is_relevant: bool,
        summary: Optional[str] = None,
        authors: Optional[str] = None,
        source: Optional[str] = None,
        feed_group: Optional[str] = None,
        field_match: bool = False,
        method_match: bool = False,
    ) -> None:
        """
        Mark a paper as processed.

        Parameters
        ----------
        feed_url : str
            URL of the RSS feed
        paper_url : str
            URL of the paper
        title : str
            Paper title
        is_relevant : bool
            Whether the paper is relevant
        summary : str, optional
            LLM-generated summary
        authors : str, optional
            Paper authors
        source : str, optional
            Journal/conference name
        feed_group : str, optional
            Feed group name (e.g., 'high-quality', 'other')
        field_match : bool
            Whether research field matches interests
        method_match : bool
            Whether method matches interests
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO papers
                (feed_url, paper_url, title, authors, source, feed_group, is_relevant, field_match, method_match, summary, processed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (feed_url, paper_url, title, authors, source, feed_group, is_relevant, field_match, method_match, summary, datetime.now())
            )
            conn.commit()

    def get_recent_relevant(self, days: int = 7) -> list[dict]:
        """
        Get recently processed relevant papers.

        Parameters
        ----------
        days : int
            Number of days to look back

        Returns
        -------
        list[dict]
            List of relevant papers
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM papers
                WHERE is_relevant = TRUE
                AND processed_at >= datetime('now', ?)
                ORDER BY processed_at DESC
                """,
                (f'-{days} days',)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_stats(self, days: int | None = None) -> dict:
        """
        Get database statistics.

        Parameters
        ----------
        days : int, optional
            If provided, only count papers from the last N days

        Returns
        -------
        dict
            Statistics including total papers, relevant papers, date range, etc.
        """
        with sqlite3.connect(self.db_path) as conn:
            if days:
                where_clause = f"WHERE processed_at >= datetime('now', '-{days} days')"
            else:
                where_clause = ""

            total = conn.execute(f"SELECT COUNT(*) FROM papers {where_clause}").fetchone()[0]
            relevant = conn.execute(
                f"SELECT COUNT(*) FROM papers {where_clause} {'AND' if where_clause else 'WHERE'} is_relevant = TRUE"
            ).fetchone()[0]

            # Get date range
            date_from = conn.execute(
                f"SELECT MIN(processed_at) FROM papers {where_clause}"
            ).fetchone()[0]
            date_to = conn.execute(
                f"SELECT MAX(processed_at) FROM papers {where_clause}"
            ).fetchone()[0]

            # Get unique feeds
            num_feeds = conn.execute(
                f"SELECT COUNT(DISTINCT feed_url) FROM papers {where_clause}"
            ).fetchone()[0]

            # Format dates
            if date_from:
                date_from = date_from.split()[0] if ' ' in date_from else date_from[:10]
            if date_to:
                date_to = date_to.split()[0] if ' ' in date_to else date_to[:10]

            return {
                "total_papers": total,
                "relevant_papers": relevant,
                "irrelevant_papers": total - relevant,
                "num_feeds": num_feeds,
                "date_from": date_from,
                "date_to": date_to,
            }
