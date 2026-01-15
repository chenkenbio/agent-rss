"""Base class for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ScreeningResult:
    """Result of paper screening."""

    is_relevant: bool
    summary: str
    field_match: bool = False
    method_match: bool = False
    relevance_score: Optional[float] = None


class BaseLLM(ABC):
    """Abstract base class for LLM providers."""

    SCREENING_PROMPT = """You are an academic paper screening assistant. Determine if a paper is relevant to the researcher's interests.

## Research Interests
{interests}
{examples_section}
## Paper Information
- **Title**: {title}
- **Authors**: {authors}
- **Abstract**: {abstract}
- **Source**: {source}

## Instructions
1. Determine if the research FIELD matches the interests (genomics, biology, bioinformatics, etc.)
2. Determine if the METHOD matches the interests (deep learning, machine learning, AI, etc.)
3. If relevant (field OR method matches), provide structured summary:
   - Problem: [research field/problem in short phrase]
   - Method: [computational/experimental methods used]
   - Data: [new dataset/resource if any, otherwise skip]
   - Highlights: [other key points, comma-separated]
4. If no abstract (title only), just list keywords
5. Learn from user's liked/disliked examples if provided - they show specific preferences

## Response Format
FIELD_MATCH: [yes/no]
METHOD_MATCH: [yes/no]
SUMMARY: [structured summary or keywords, or "Not related" if neither matches]

## Example 1 (both match)
FIELD_MATCH: yes
METHOD_MATCH: yes
SUMMARY: Problem: protein structure prediction | Method: transformer, deep learning | Data: new benchmark dataset | Highlights: state-of-the-art accuracy

## Example 2 (field matches, method doesn't)
FIELD_MATCH: yes
METHOD_MATCH: no
SUMMARY: Problem: gene regulation | Method: experimental (CRISPR screen) | Highlights: novel targets identified

## Example 3 (method matches, field doesn't)
FIELD_MATCH: no
METHOD_MATCH: yes
SUMMARY: Problem: image classification | Method: CNN, deep learning | Highlights: new architecture

## Example 4 (neither matches)
FIELD_MATCH: no
METHOD_MATCH: no
SUMMARY: Not related
"""

    def __init__(self, api_key: str):
        """Initialize with API key."""
        self.api_key = api_key

    @abstractmethod
    def _call_api(self, prompt: str) -> str:
        """
        Call the LLM API with a prompt.

        Parameters
        ----------
        prompt : str
            The prompt to send to the LLM

        Returns
        -------
        str
            The LLM's response
        """
        pass

    def _format_examples_section(self, examples: dict | None) -> str:
        """Format examples into prompt section."""
        if not examples:
            return ""

        liked = examples.get("liked", [])
        disliked = examples.get("disliked", [])

        if not liked and not disliked:
            return ""

        sections = []

        if liked:
            sections.append("\n## User's Liked Paper Examples (screen IN papers like these)")
            for i, ex in enumerate(liked, 1):
                parts = [f"- Title: {ex.get('title', 'N/A')}"]
                if ex.get('abstract'):
                    parts.append(f"  Abstract: {ex['abstract'][:200]}...")
                if ex.get('reason'):
                    parts.append(f"  Reason: {ex['reason']}")
                sections.append(f"{i}. " + "\n   ".join(parts))

        if disliked:
            sections.append("\n## User's Disliked Paper Examples (screen OUT papers like these)")
            for i, ex in enumerate(disliked, 1):
                parts = [f"- Title: {ex.get('title', 'N/A')}"]
                if ex.get('reason'):
                    parts.append(f"  Reason: {ex['reason']}")
                sections.append(f"{i}. " + "\n   ".join(parts))

        return "\n".join(sections) + "\n"

    def screen_paper(
        self,
        title: str,
        authors: str,
        abstract: str,
        source: str,
        interests: str,
        examples: dict | None = None,
    ) -> ScreeningResult:
        """
        Screen a paper against research interests.

        Parameters
        ----------
        title : str
            Paper title
        authors : str
            Paper authors
        abstract : str
            Paper abstract
        source : str
            Journal/conference name
        interests : str
            Research interests to match against
        examples : dict | None
            Optional dict with "liked" and "disliked" paper examples

        Returns
        -------
        ScreeningResult
            Screening result with relevance and summary
        """
        examples_section = self._format_examples_section(examples)

        prompt = self.SCREENING_PROMPT.format(
            interests=interests,
            examples_section=examples_section,
            title=title,
            authors=authors,
            abstract=abstract,
            source=source,
        )

        response = self._call_api(prompt)
        return self._parse_response(response)

    def _parse_response(self, response: str) -> ScreeningResult:
        """Parse LLM response into ScreeningResult."""
        lines = response.strip().split('\n')

        field_match = False
        method_match = False
        summary = ""

        for line in lines:
            line = line.strip()
            if line.upper().startswith('FIELD_MATCH:'):
                value = line.split(':', 1)[1].strip().lower()
                field_match = value in ('yes', 'true', '1')
            elif line.upper().startswith('METHOD_MATCH:'):
                value = line.split(':', 1)[1].strip().lower()
                method_match = value in ('yes', 'true', '1')
            elif line.upper().startswith('SUMMARY:'):
                summary = line.split(':', 1)[1].strip()

        # If summary spans multiple lines, capture everything after SUMMARY:
        if 'SUMMARY:' in response:
            summary = response.split('SUMMARY:', 1)[1].strip()

        # is_relevant = True if either field or method matches
        is_relevant = field_match or method_match

        return ScreeningResult(
            is_relevant=is_relevant,
            summary=summary,
            field_match=field_match,
            method_match=method_match,
        )
