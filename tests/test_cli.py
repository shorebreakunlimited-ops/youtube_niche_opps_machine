"""Tests for Command Line Interface."""

import subprocess
import sys


def test_cli_quota_command():
    res = subprocess.run([sys.executable, "main.py", "quota", "--mock"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "YouTube Data API v3 Quota Utilization" in res.stdout
    assert "search.list calls" in res.stdout


def test_cli_simulate_command():
    res = subprocess.run([sys.executable, "main.py", "simulate", "--iterations", "50", "--json"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "average_spearman_rank_correlation" in res.stdout
    assert "candidates" in res.stdout


def test_cli_validate_mock_command():
    res = subprocess.run(
        [sys.executable, "main.py", "validate", "python fastmcp servers", "--mock", "--max-videos", "10", "--json"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "content_opportunity_score" in res.stdout
    assert "recommendation" in res.stdout


def test_cli_discover_mock_command():
    res = subprocess.run(
        [sys.executable, "main.py", "discover", "fastmcp", "--mock", "--candidates", "3", "--json"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "content_opportunity_score" in res.stdout
