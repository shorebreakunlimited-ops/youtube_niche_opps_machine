"""Unit tests for body-cam source triage ingest."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from ingest.fts_index import VideoDoc, VideoFTSIndex, _fts_query_for_term, load_keywords
from ingest.hits_csv import (
    filter_downloadable_rows,
    read_keyword_hit_rows,
    write_keyword_hits,
    write_target_urls,
)
from ingest.sources import Source, load_sources, select_sources
from ingest import channel_ingest


def test_load_sources_and_default_enabled_only(tmp_path: Path):
    path = tmp_path / "sources.csv"
    path.write_text(
        "source_name,source_url,source_type,priority,notes,enabled\n"
        "KHON News,https://www.youtube.com/@KHONNewsHawaii,channel,2,local,false\n"
        "Smoke Test Videos,config/channels.smoke.txt,video_list,1,controlled,true\n",
        encoding="utf-8",
    )
    sources = load_sources(path)
    selected = select_sources(sources)
    assert len(selected) == 1
    assert selected[0].source_name == "Smoke Test Videos"
    assert selected[0].enabled is True


def test_include_disabled_requires_explicit_source():
    sources = [
        Source("KHON News", "https://x", "channel", 2, "", False),
        Source("Smoke", "config/x.txt", "video_list", 1, "", True),
    ]
    with pytest.raises(ValueError, match="requires explicit --source"):
        select_sources(sources, include_disabled=True)


def test_include_disabled_with_source_allows_channel():
    sources = [
        Source("KHON News", "https://x", "channel", 2, "", False),
        Source("Smoke", "config/x.txt", "video_list", 1, "", True),
    ]
    selected = select_sources(
        sources, include_disabled=True, source_names=["KHON News"]
    )
    assert [s.source_name for s in selected] == ["KHON News"]


def test_disabled_source_without_flag_is_explicit_error():
    sources = [
        Source("KHON News", "https://x", "channel", 2, "", False),
        Source("Smoke", "config/x.txt", "video_list", 1, "", True),
    ]
    with pytest.raises(ValueError, match="Source\\(s\\) disabled"):
        select_sources(sources, source_names=["KHON News"])


def test_fts_stem_query_and_search(tmp_path: Path):
    assert "body" in _fts_query_for_term("body*")
    db = tmp_path / "t.sqlite3"
    docs = [
        VideoDoc(
            video_id="aaa",
            url="https://www.youtube.com/watch?v=aaa",
            title="Police bodycam footage of chase",
            description="Officer arrests suspect after pursuit",
            channel="News",
            source_name="Smoke",
        ),
        VideoDoc(
            video_id="bbb",
            url="https://www.youtube.com/watch?v=bbb",
            title="Cooking show episode",
            description="Pasta recipes",
            channel="Food",
            source_name="Smoke",
        ),
    ]
    with VideoFTSIndex(db) as index:
        index.upsert_many(docs)
        hits = index.search_keywords(["body*", "officer", "pasta"], max_search_hits=10)
    ids = {h.video_id for h in hits}
    assert "aaa" in ids
    # pasta may match bbb; body/officer should not require phrases
    assert any(h.matched_keyword == "body*" for h in hits)


def test_keyword_hits_preserve_review_status(tmp_path: Path):
    from ingest.fts_index import KeywordHit

    path = tmp_path / "keyword_hits.csv"
    hits = [
        KeywordHit(
            video_id="aaa",
            url="https://www.youtube.com/watch?v=aaa",
            title="Bodycam",
            description="",
            channel="N",
            source_name="S",
            upload_date="",
            matched_keyword="body*",
            snippet="[Bodycam]",
        )
    ]
    write_keyword_hits(path, hits)
    # Human marks download
    rows = read_keyword_hit_rows(path)
    rows[0]["review_status"] = "download"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    write_keyword_hits(path, hits, preserve_existing=True)
    preserved = read_keyword_hit_rows(path)
    assert preserved[0]["review_status"] == "download"

    downloadable = filter_downloadable_rows(preserved)
    assert len(downloadable) == 1
    urls = write_target_urls(tmp_path / "target_urls.txt", downloadable, max_target_urls=1)
    assert urls == ["https://www.youtube.com/watch?v=aaa"]


def test_reject_status_not_downloadable():
    rows = [
        {"url": "https://x", "review_status": "new"},
        {"url": "https://y", "review_status": "reject"},
        {"url": "https://z", "review_status": "watch"},
        {"url": "https://a", "review_status": "episode_candidate"},
    ]
    out = filter_downloadable_rows(rows)
    assert [r["url"] for r in out] == ["https://a"]


def test_deprecated_limit_flag_rejected():
    with pytest.raises(SystemExit, match="--limit is deprecated"):
        channel_ingest.run(["--limit", "10", "--channels-file", "missing.txt"])


def test_load_keywords_skips_comments(tmp_path: Path):
    path = tmp_path / "kw.txt"
    path.write_text("# comment\nbody*\n\nofficer\n", encoding="utf-8")
    assert load_keywords(path) == ["body*", "officer"]


def test_oembed_fallback_builds_doc(monkeypatch):
    from ingest import extract

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return (
                b'{"title":"Police bodycam footage of chase",'
                b'"author_name":"Hawaii News Now"}'
            )

    monkeypatch.setattr(
        extract.urllib.request,
        "urlopen",
        lambda *a, **k: _Resp(),
    )
    doc = extract.fetch_oembed_doc(
        "https://www.youtube.com/watch?v=aaaaaaaaaaa",
        source_name="Smoke",
    )
    assert doc is not None
    assert doc.video_id == "aaaaaaaaaaa"
    assert "bodycam" in doc.title.lower()
    assert doc.channel == "Hawaii News Now"
