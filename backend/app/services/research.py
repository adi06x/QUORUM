from __future__ import annotations

import asyncio
import hashlib
import html
import logging
import re
import xml.etree.ElementTree as ET
from collections import OrderedDict
from typing import Any

import httpx

from app.schemas import InvestigationStep, SourceRecord

logger = logging.getLogger(__name__)

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

# Simple HTML tag stripper for CrossRef abstracts
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(value: str) -> str:
    return html.unescape(_HTML_TAG_RE.sub("", value)).strip()


class ResearchRetriever:
    def __init__(
        self,
        *,
        semantic_scholar_api_key: str | None,
        max_sources_per_provider: int,
        enable_demo_mode: bool,
    ) -> None:
        self.semantic_scholar_api_key = semantic_scholar_api_key
        self.max_sources_per_provider = max_sources_per_provider
        self.enable_demo_mode = enable_demo_mode

    async def gather_sources(
        self,
        question: str,
        investigation_plan: list[InvestigationStep],
        pass_index: int,
    ) -> tuple[list[SourceRecord], str, bool, list[str]]:
        queries = [step.search_query for step in investigation_plan if step.search_query][:2]
        if not queries:
            queries = [question]

        live_sources: list[SourceRecord] = []
        provider_notes: list[str] = []

        for query in queries:
            tasks = [
                self.search_semantic_scholar(query, limit=self.max_sources_per_provider),
                self.search_arxiv(query, limit=self.max_sources_per_provider),
                self.search_crossref(query, limit=self.max_sources_per_provider),
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for provider_result in results:
                if isinstance(provider_result, Exception):
                    provider_notes.append(str(provider_result))
                    logger.warning("Provider error during gather_sources: %s", provider_result)
                    continue
                live_sources.extend(provider_result)
            if len(live_sources) >= self.max_sources_per_provider * 3:
                break

        deduped_sources = self._dedupe_sources(live_sources)
        if deduped_sources:
            logger.info("gather_sources: collected %d deduped sources for query '%s'", len(deduped_sources), question[:60])
            return deduped_sources[:8], "live", False, provider_notes

        if self.enable_demo_mode:
            logger.warning("gather_sources: live APIs returned nothing; falling back to demo mode")
            provider_notes.append("Live academic APIs were unavailable. Using simulated academic results.")
            return self._build_demo_sources(question, pass_index), "demo", True, provider_notes

        return [], "unavailable", False, provider_notes

    async def search_semantic_scholar(self, query: str, limit: int) -> list[SourceRecord]:
        logger.info("search_semantic_scholar: query='%s' limit=%d", query[:60], limit)
        try:
            headers = {}
            if self.semantic_scholar_api_key:
                headers["x-api-key"] = self.semantic_scholar_api_key
            params = {
                "query": query,
                "limit": limit,
                "fields": ",".join(
                    [
                        "title",
                        "abstract",
                        "authors",
                        "year",
                        "venue",
                        "url",
                        "citationCount",
                        "openAccessPdf",
                    ]
                ),
            }
            async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=10.0)) as client:
                response = await client.get(
                    "https://api.semanticscholar.org/graph/v1/paper/search",
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()

            records: list[SourceRecord] = []
            for index, item in enumerate(payload.get("data", [])):
                abstract = (item.get("abstract") or "").strip()
                if not abstract:
                    continue
                paper_id = item.get("paperId") or self._stable_id(f"s2:{query}:{index}:{item.get('title', '')}")
                records.append(
                    SourceRecord(
                        id=f"s2-{paper_id}",
                        title=item.get("title", "Untitled paper"),
                        abstract=abstract,
                        authors=[author.get("name", "") for author in item.get("authors", []) if author.get("name")],
                        year=item.get("year"),
                        venue=item.get("venue"),
                        url=item.get("url"),
                        pdf_url=(item.get("openAccessPdf") or {}).get("url"),
                        provider="semantic_scholar",
                        citation_count=item.get("citationCount"),
                        relevance_score=max(0.0, 1.0 - (index * 0.08)),
                        simulated=False,
                    )
                )
            logger.info("search_semantic_scholar: returned %d records", len(records))
            return records
        except Exception as exc:
            logger.warning("search_semantic_scholar failed: %s", exc)
            raise

    async def search_arxiv(self, query: str, limit: int) -> list[SourceRecord]:
        logger.info("search_arxiv: query='%s' limit=%d", query[:60], limit)
        try:
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": limit,
                "sortBy": "relevance",
                "sortOrder": "descending",
            }
            async with httpx.AsyncClient(timeout=httpx.Timeout(25.0, connect=10.0)) as client:
                response = await client.get("https://export.arxiv.org/api/query", params=params)
                response.raise_for_status()
                payload = response.text

            root = ET.fromstring(payload)
            records: list[SourceRecord] = []
            for index, entry in enumerate(root.findall("atom:entry", namespaces=ATOM_NS)):
                title = self._clean_text(entry.findtext("atom:title", default="", namespaces=ATOM_NS))
                abstract = self._clean_text(entry.findtext("atom:summary", default="", namespaces=ATOM_NS))
                if not abstract:
                    continue
                authors = [
                    self._clean_text(author.findtext("atom:name", default="", namespaces=ATOM_NS))
                    for author in entry.findall("atom:author", namespaces=ATOM_NS)
                ]
                pdf_url = None
                for link in entry.findall("atom:link", namespaces=ATOM_NS):
                    if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                        pdf_url = link.attrib.get("href")
                        break
                raw_id = self._clean_text(entry.findtext("atom:id", default="", namespaces=ATOM_NS))
                published = self._clean_text(entry.findtext("atom:published", default="", namespaces=ATOM_NS))
                year = int(published[:4]) if published[:4].isdigit() else None
                records.append(
                    SourceRecord(
                        id=f"arxiv-{self._stable_id(raw_id or title)}",
                        title=title,
                        abstract=abstract,
                        authors=[author for author in authors if author],
                        year=year,
                        venue="arXiv",
                        url=raw_id or None,
                        pdf_url=pdf_url,
                        provider="arxiv",
                        citation_count=None,
                        relevance_score=max(0.0, 0.96 - (index * 0.07)),
                        simulated=False,
                    )
                )
            logger.info("search_arxiv: returned %d records", len(records))
            return records
        except Exception as exc:
            logger.warning("search_arxiv failed: %s", exc)
            raise

    async def search_crossref(self, query: str, limit: int) -> list[SourceRecord]:
        """Search CrossRef for peer-reviewed papers."""
        logger.info("search_crossref: query='%s' limit=%d", query[:60], limit)
        try:
            params = {
                "query": query,
                "rows": limit,
                "select": "title,abstract,author,published-print,URL,DOI,container-title,is-referenced-by-count",
            }
            async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=10.0)) as client:
                response = await client.get(
                    "https://api.crossref.org/works",
                    params=params,
                    headers={"User-Agent": "QUORUM-ResearchCouncil/1.0 (mailto:hello@quorum.ai)"},
                )
                response.raise_for_status()
                payload = response.json()

            records: list[SourceRecord] = []
            items = payload.get("message", {}).get("items", [])
            for index, item in enumerate(items):
                title_list = item.get("title", [])
                if not title_list:
                    continue
                title = title_list[0].strip()

                raw_abstract = item.get("abstract", "")
                abstract = _strip_html(raw_abstract).strip() if raw_abstract else ""
                if not abstract:
                    continue

                authors_raw = item.get("author", [])
                authors = [
                    f"{a.get('given', '')} {a.get('family', '')}".strip()
                    for a in authors_raw
                    if a.get("family")
                ]

                year_parts = item.get("published-print", {}).get("date-parts", [[None]])
                year = year_parts[0][0] if year_parts and year_parts[0] else None

                url = item.get("URL")
                venue = (item.get("container-title") or [""])[0]
                citation_count = item.get("is-referenced-by-count")
                doi = item.get("DOI", "")

                records.append(
                    SourceRecord(
                        id=f"crossref-{self._stable_id(doi or title)}",
                        title=title,
                        abstract=abstract,
                        authors=authors,
                        year=year,
                        venue=venue or None,
                        url=url,
                        pdf_url=None,
                        provider="crossref",
                        citation_count=citation_count,
                        relevance_score=max(0.0, 0.88 - (index * 0.07)),
                        simulated=False,
                    )
                )
            logger.info("search_crossref: returned %d records", len(records))
            return records
        except Exception as exc:
            logger.warning("search_crossref failed: %s", exc)
            raise

    def _dedupe_sources(self, sources: list[SourceRecord]) -> list[SourceRecord]:
        ranked = sorted(
            sources,
            key=lambda source: (
                source.provider not in {"semantic_scholar", "crossref"},
                -(source.citation_count or 0),
                -(source.year or 0),
                -source.relevance_score,
            ),
        )
        deduped: OrderedDict[str, SourceRecord] = OrderedDict()
        for source in ranked:
            title_key = re.sub(r"\W+", "", source.title.lower())
            if title_key not in deduped:
                deduped[title_key] = source
        return list(deduped.values())

    def _build_demo_sources(self, question: str, pass_index: int) -> list[SourceRecord]:
        topic = " ".join(question.strip().split()[:10])
        demo_templates = [
            (
                "Simulated evidence brief",
                "A synthesis-style overview describing the strongest supportive signals reported across representative studies.",
            ),
            (
                "Simulated contradiction brief",
                "A counter-position summary highlighting settings where the effect is smaller, delayed, or absent.",
            ),
            (
                "Simulated methods brief",
                "A methodology-focused summary comparing randomized, observational, and benchmark-style evidence.",
            ),
            (
                "Simulated limitations brief",
                "A gap analysis noting sample bias, missing longitudinal follow-up, and publication lag.",
            ),
        ]
        records: list[SourceRecord] = []
        for index, (label, abstract) in enumerate(demo_templates, start=1):
            title = f"{label} #{index} for '{topic}'"
            records.append(
                SourceRecord(
                    id=f"demo-{pass_index}-{index}-{self._stable_id(title)}",
                    title=title,
                    abstract=(
                        f"{abstract} This simulated academic result was generated for demo mode only and must not be treated as a real citation. "
                        f"It frames the research question '{question.strip()}' from a distinct committee perspective."
                    ),
                    authors=["QUORUM Demo Mode"],
                    year=None,
                    venue="Simulated academic result",
                    url=None,
                    pdf_url=None,
                    provider="simulated",
                    citation_count=None,
                    relevance_score=0.9 - (index * 0.08),
                    simulated=True,
                )
            )
        return records

    def _stable_id(self, value: str) -> str:
        return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]

    def _clean_text(self, value: str) -> str:
        compact = re.sub(r"\s+", " ", html.unescape(value or "")).strip()
        return compact
