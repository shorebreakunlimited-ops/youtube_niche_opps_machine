"""Terminal scorecard and rich console visualizations."""

from typing import Any, Dict, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.models import ValidationResult
from src.simulation.sensitivity import SensitivityReport

console = Console()


def print_validation_scorecard(result: ValidationResult) -> None:
    """Print complete executive scorecard for a validated YouTube niche."""
    # 1. Header & Recommendation
    rec_colors = {
        "STRONG OPPORTUNITY": "bold green",
        "PROMISING": "bold cyan",
        "HIGH POTENTIAL (RISKY)": "bold yellow",
        "SATURATED": "bold red",
        "WEAK DEMAND": "bold red",
        "VIRAL OUTLIER": "bold magenta",
        "HIGH RIGHTS RISK": "bold red",
        "HIGH PRODUCTION RISK": "bold red",
        "INSUFFICIENT EVIDENCE": "dim yellow",
        "WATCHLIST": "bold blue",
    }
    rec_style = rec_colors.get(result.recommendation, "bold white")

    console.print()
    console.print(
        Panel(
            f"[bold white]Target Niche:[/bold white] [bold cyan]{result.niche_name}[/bold cyan]\n"
            f"[bold white]Recommendation:[/bold white] [{rec_style}]{result.recommendation}[/{rec_style}]\n"
            f"[dim]Evidence Confidence:[/dim] [bold]{result.confidence_score}/100[/bold]  |  "
            f"[dim]Sample Size:[/dim] [bold]{result.sample_size} videos[/bold] ({result.eligible_breakout_videos} eligible small channels)",
            title="🎯 YOUTUBE NICHE VALIDATION SCORECARD (v2.2 Architecture)",
            border_style="cyan",
        )
    )

    # 2. Decoupled Core Scores Table
    score_table = Table(title="Decoupled Performance & Feasibility Scores", show_header=True, header_style="bold magenta")
    score_table.add_column("Score Metric", style="cyan", width=34)
    score_table.add_column("Value / 100", justify="right", style="bold white", width=14)
    score_table.add_column("Classification / Purpose", style="dim", width=38)

    score_table.add_row(
        "Content Opportunity (Pure Market)",
        f"{result.content_opportunity_score:.1f}",
        "Discovery Ranking Metric (Demand vs Supply)",
    )
    score_table.add_row(
        "Creator-Adjusted Opportunity",
        f"{result.creator_adjusted_opportunity:.1f}",
        "Decision Metric (Adjusted for Execution Load)",
    )
    score_table.add_row(
        "Commercial Attractiveness",
        f"{result.commercial_attractiveness_score:.1f}",
        "Sponsor Affinity & CPM Index",
    )
    score_table.add_row(
        "Production Feasibility (100 - ProdRisk)",
        f"{result.production_feasibility:.1f}",
        "Solo Creator Workload Viability",
    )
    score_table.add_row(
        "Rights Safety (100 - RightsRisk)",
        f"{result.rights_safety:.1f}",
        "Fair Use / Copyright Clearance Safety",
    )
    score_table.add_row(
        "Evidence Confidence",
        f"{result.confidence_score:.1f}",
        "Multi-source sample & temporal depth",
    )
    console.print(score_table)

    # 3. Component Factor Breakdown Table
    factor_table = Table(title="Sub-Factor Market Breakdown", show_header=True, header_style="bold blue")
    factor_table.add_column("Factor", style="cyan", width=26)
    factor_table.add_column("Score", justify="right", style="bold", width=10)
    factor_table.add_column("Weight", justify="right", style="dim", width=10)
    factor_table.add_column("Description", style="white", width=40)

    factor_table.add_row("Demand Velocity", f"{result.demand_score:.1f}", "25%", "Audience search volume & median velocity")
    factor_table.add_row("Supply Scarcity", f"{result.supply_scarcity:.1f}", "20%", "HHI concentration & breakout-neutralized barriers")
    factor_table.add_row("Breakout Potential", f"{result.breakout_score:.1f}", "20%", "Bayesian small-channel breakout rate & diversity")
    factor_table.add_row("Growth Acceleration", f"{result.acceleration_score:.1f}", "18%", "Centered tanh recent vs historical velocity")
    factor_table.add_row("Topic Runway", f"{result.repeatability_score:.1f}", "10%", "15-axis content breadth & video expansion")
    factor_table.add_row("Trend Durability", f"{result.durability_score:.1f}", "7%", "Long-term evergreen view retention")
    factor_table.add_row("Outlier Penalty", f"-{result.outlier_risk_score:.1f}", "Deduction", "Continuous sigmoid Top-1/Top-3 share penalty")
    console.print(factor_table)

    # 4. Breakout Evidence
    if result.breakout_evidence:
        ev_table = Table(title="Small-Channel Breakout Evidence (Leave-One-Out Baselines)", show_header=True, header_style="bold green")
        ev_table.add_column("Channel", style="cyan", width=22)
        ev_table.add_column("Subs", justify="right", style="dim", width=10)
        ev_table.add_column("Breakout Video Title", style="white", width=34)
        ev_table.add_column("Views", justify="right", style="bold green", width=12)
        ev_table.add_column("LOO Base", justify="right", style="dim", width=10)
        ev_table.add_column("Ratio", justify="right", style="bold yellow", width=8)
        ev_table.add_column("Tier", justify="center", style="magenta", width=6)

        for ev in result.breakout_evidence[:5]:
            ev_table.add_row(
                ev.channel_title[:20],
                f"{ev.subscribers:,}" if ev.subscribers is not None else "Unknown",
                ev.video_title[:32],
                f"{ev.views:,}",
                f"{ev.baseline_views:,.0f}",
                f"{ev.breakout_ratio:.1f}x",
                ev.baseline_tier,
            )
        console.print(ev_table)

    # 5. Top Competitors
    if result.top_competitors:
        comp_table = Table(title="Top Competitor Channels in Niche", show_header=True, header_style="bold yellow")
        comp_table.add_column("Channel Name", style="cyan", width=28)
        comp_table.add_column("Subscribers", justify="right", style="dim", width=14)
        comp_table.add_column("Views in Niche", justify="right", style="bold", width=16)
        comp_table.add_column("Niche View Share", justify="right", style="yellow", width=16)

        for comp in result.top_competitors[:5]:
            comp_table.add_row(
                comp["title"][:26],
                f"{comp['subscribers']:,}" if comp.get("subscribers") else "Hidden",
                f"{comp['views_in_niche']:,}",
                f"{comp['view_share_pct']:.1f}%",
            )
        console.print(comp_table)

    # 6. Strategic Reasoning & Risks
    if result.reasoning:
        console.print("\n[bold white]Strategic Evaluation Reasoning:[/bold white]")
        for reason in result.reasoning:
            console.print(f"  • {reason}")

    if result.risks:
        console.print("\n[bold red]Key Vulnerabilities & Identified Risks:[/bold red]")
        for risk in result.risks:
            console.print(f"  ⚠ [yellow]{risk}[/yellow]")

    if result.video_ideas:
        console.print("\n[bold cyan]Actionable Video Content Angles (15-Axis Runway):[/bold cyan]")
        for idea in result.video_ideas[:5]:
            console.print(f"  🎬 {idea}")
    console.print()


def print_discovery_leaderboard(leaderboard: List[Dict[str, Any]], seed_topic: str) -> None:
    """Print the Mode A automated discovery leaderboard."""
    console.print()
    table = Table(
        title=f"🚀 DISCOVERY LEADERBOARD for '{seed_topic.title()}' (Ranked strictly by Content Opportunity)",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Rank", justify="center", style="bold", width=6)
    table.add_column("Subniche Candidate", style="bold white", width=30)
    table.add_column("Content Opp", justify="right", style="bold green", width=12)
    table.add_column("Confidence", justify="right", style="dim", width=12)
    table.add_column("Breakout", justify="right", style="cyan", width=10)
    table.add_column("Scarcity", justify="right", style="blue", width=10)
    table.add_column("Demand", justify="right", style="magenta", width=10)
    table.add_column("Recommendation", style="yellow", width=22)
    table.add_column("Creator-Adjusted*", justify="right", style="dim italic", width=16)

    for entry in leaderboard:
        table.add_row(
            str(entry["rank"]),
            entry["niche_name"][:28],
            f"{entry['content_opportunity_score']:.1f}",
            f"{entry['confidence_score']:.1f}",
            f"{entry['breakout_score']:.1f}",
            f"{entry['supply_scarcity']:.1f}",
            f"{entry['demand_score']:.1f}",
            entry["recommendation"],
            f"{entry['creator_adjusted_opportunity']:.1f}",
        )
    console.print(table)
    console.print("[dim]* Note: Discovery ranks purely on Content Opportunity + Confidence gating. Creator-Adjusted score is reserved for creator decisions.[/dim]\n")


def print_sensitivity_report(report: SensitivityReport) -> None:
    """Print Monte Carlo sensitivity analysis report."""
    console.print()
    console.print(
        Panel(
            f"[bold white]Iterations:[/bold white] {report.iterations:,} draws  |  "
            f"[bold white]Perturbation:[/bold white] ±{report.perturbation_pct * 100:.0f}%  |  "
            f"[bold white]Avg Spearman Rank Correlation:[/bold white] [bold green]{report.average_spearman_rank_correlation:.4f}[/bold green]",
            title="🎲 MONTE CARLO SCORING WEIGHT SENSITIVITY SIMULATION",
            border_style="magenta",
        )
    )

    table = Table(title="Candidate Rank & Score Stability Distribution", show_header=True, header_style="bold magenta")
    table.add_column("Candidate Niche", style="cyan", width=26)
    table.add_column("Base Rank", justify="center", style="bold", width=10)
    table.add_column("Base Score", justify="right", style="white", width=12)
    table.add_column("Mean ± Std", justify="right", style="dim", width=14)
    table.add_column("90% CI [P05, P95]", justify="center", style="yellow", width=18)
    table.add_column("Mean Rank", justify="right", style="white", width=10)
    table.add_column("Top-1 %", justify="right", style="bold green", width=10)
    table.add_column("Top-3 %", justify="right", style="green", width=10)

    for m in report.candidate_metrics:
        table.add_row(
            m.name[:24],
            str(m.baseline_rank),
            f"{m.baseline_score:.1f}",
            f"{m.mean_score:.1f} ± {m.std_score:.1f}",
            f"[{m.p05_score:.1f}, {m.p95_score:.1f}]",
            f"{m.mean_rank:.2f}",
            f"{m.top1_probability * 100:.1f}%",
            f"{m.top3_probability * 100:.1f}%",
        )
    console.print(table)
    console.print()
