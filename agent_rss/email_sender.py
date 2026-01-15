"""Email notification module."""

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

logger = logging.getLogger(__name__)


def format_paper_plain(papers: list[dict[str, Any]], stats: dict[str, Any] | None = None) -> str:
    """Format papers as plain text."""
    if not papers:
        return "No relevant papers found today."

    lines = []

    # Add summary stats if provided
    if stats:
        lines.append("Summary")
        lines.append("-" * 40)
        lines.append(f"Period: {stats.get('date_from', 'N/A')} to {stats.get('date_to', 'N/A')}")
        lines.append(f"Journals/Feeds: {stats.get('num_feeds', 'N/A')}")
        lines.append(f"Papers screened: {stats.get('total_screened', 'N/A')}")
        lines.append(f"Relevant papers: {len(papers)}")
        lines.append("")

    lines.extend(["Relevant Papers", "=" * 40, ""])

    for i, paper in enumerate(papers, 1):
        lines.append(f"{i}. {paper['title']}")
        lines.append(f"   Source: {paper.get('source', 'Unknown')}")
        if paper.get('authors') and paper.get('authors') != 'Unknown':
            lines.append(f"   Authors: {paper.get('authors')}")
        lines.append(f"   Link: {paper.get('link', 'N/A')}")
        if paper.get('summary'):
            lines.append(f"   Relevance: {paper['summary']}")
        lines.append("")

    return "\n".join(lines)


def format_paper_html(papers: list[dict[str, Any]], stats: dict[str, Any] | None = None) -> str:
    """Format papers as Gmail-friendly HTML."""
    if not papers:
        return "<p>No relevant papers found today.</p>"

    html = ['<div style="font-family: Arial, sans-serif; font-size: 14px;">']

    # Add summary stats if provided
    if stats:
        html.append('<div style="margin-bottom: 20px; padding: 12px; background: #e8f0fe; border-radius: 8px;">')
        html.append('<h3 style="margin: 0 0 8px 0; color: #1a73e8;">Summary</h3>')
        html.append(f'<p style="margin: 4px 0;"><b>Period:</b> {stats.get("date_from", "N/A")} to {stats.get("date_to", "N/A")}</p>')
        html.append(f'<p style="margin: 4px 0;"><b>Journals/Feeds:</b> {stats.get("num_feeds", "N/A")}</p>')
        html.append(f'<p style="margin: 4px 0;"><b>Papers screened:</b> {stats.get("total_screened", "N/A")}</p>')
        html.append(f'<p style="margin: 4px 0;"><b>Relevant papers:</b> {len(papers)}</p>')
        html.append('</div>')

    html.append('<h2 style="color: #1a73e8;">Relevant Papers</h2>')

    for i, paper in enumerate(papers, 1):
        html.append('<div style="margin-bottom: 20px; padding: 12px; border-left: 3px solid #1a73e8; background: #f8f9fa;">')
        # Bold title
        html.append(f'<p style="margin: 0 0 8px 0;"><b style="font-size: 15px;">{i}. {paper["title"]}</b></p>')
        # Source
        html.append(f'<p style="margin: 4px 0;"><b>Source:</b> {paper.get("source", "Unknown")}</p>')
        # Authors (only if available)
        if paper.get('authors') and paper.get('authors') != 'Unknown':
            html.append(f'<p style="margin: 4px 0;"><b>Authors:</b> {paper.get("authors")}</p>')
        # Link
        link = paper.get('link', '#')
        html.append(f'<p style="margin: 4px 0;"><b>Link:</b> <a href="{link}" style="color: #1a73e8;">{link}</a></p>')
        # Relevance
        if paper.get('summary'):
            html.append(f'<p style="margin: 4px 0;"><b>Relevance:</b> {paper["summary"]}</p>')
        html.append('</div>')

    html.append('</div>')
    return '\n'.join(html)


def send_email(
    smtp_server: str,
    smtp_port: int,
    username: str,
    password: str,
    recipient: str,
    papers: list[dict[str, Any]],
    sender_name: str = "agent-rss",
    stats: dict[str, Any] | None = None,
) -> bool:
    """
    Send email notification with paper summaries.

    Parameters
    ----------
    smtp_server : str
        SMTP server address
    smtp_port : int
        SMTP server port
    username : str
        SMTP username
    password : str
        SMTP password
    recipient : str
        Recipient email address
    papers : list[dict]
        List of relevant papers
    sender_name : str
        Sender display name
    stats : dict, optional
        Summary statistics (num_feeds, total_screened, date_from, date_to)

    Returns
    -------
    bool
        True if email sent successfully
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    subject = f"[{sender_name}] {len(papers)} relevant paper(s) found ({date_str})"

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"{sender_name} <{username}>"
    msg['To'] = recipient

    # Plain text version
    plain_body = format_paper_plain(papers, stats)
    msg.attach(MIMEText(plain_body, 'plain'))

    # HTML version (Gmail-friendly)
    html_body = format_paper_html(papers, stats)
    msg.attach(MIMEText(f"<html><body>{html_body}</body></html>", 'html'))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(username, password)
            server.sendmail(username, recipient, msg.as_string())
        logger.info(f"Email sent successfully to {recipient}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def send_test_email(
    smtp_server: str,
    smtp_port: int,
    username: str,
    password: str,
    recipient: str,
    sender_name: str = "agent-rss",
) -> bool:
    """
    Send a test email to verify configuration.

    Parameters
    ----------
    smtp_server : str
        SMTP server address
    smtp_port : int
        SMTP server port
    username : str
        SMTP username
    password : str
        SMTP password
    recipient : str
        Recipient email address
    sender_name : str
        Sender display name

    Returns
    -------
    bool
        True if email sent successfully
    """
    test_papers = [{
        "title": "Test Paper: This is a test notification",
        "source": "Test Journal",
        "authors": "Test Author (Test Institution)",
        "link": "https://example.com/test-paper",
        "summary": "This is a test email to verify your agent-rss configuration is working correctly.",
    }]

    return send_email(
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        username=username,
        password=password,
        recipient=recipient,
        papers=test_papers,
        sender_name=sender_name,
    )
