"""Universal 15-axis topic depth and guarded runway analysis."""

from typing import Any, Dict, List, Set
from src.scoring.statistics import guarded_entropy_ratio, guarded_inter_cluster_distance

# The 15 Universal Domain-Neutral Axes for YouTube Topic Exploration
UNIVERSAL_15_AXES: Dict[str, Dict[str, Any]] = {
    "fundamentals": {
        "axis_id": "axis_01",
        "name": "Fundamentals & Getting Started",
        "keywords": ["beginner", "basics", "101", "getting started", "introduction", "fundamentals", "for beginners"],
        "template": "Complete Beginner Guide to {seed}",
    },
    "advanced_mastery": {
        "axis_id": "axis_02",
        "name": "Advanced Mastery & Deep Dives",
        "keywords": ["advanced", "masterclass", "deep dive", "expert", "pro level", "mastery"],
        "template": "Advanced {seed} Techniques Only Pros Use",
    },
    "step_by_step_workflow": {
        "axis_id": "axis_03",
        "name": "Step-by-Step Practical Workflow",
        "keywords": ["workflow", "step by step", "tutorial", "walkthrough", "how to build", "full guide"],
        "template": "Step-by-Step {seed} Workflow from Zero",
    },
    "comparisons_alternatives": {
        "axis_id": "axis_04",
        "name": "Comparisons & Direct Alternatives",
        "keywords": ["vs", "versus", "alternative", "comparison", "compared to", "better than"],
        "template": "{seed} vs Top Alternatives: Which is Actually Better?",
    },
    "pitfalls_mistakes": {
        "axis_id": "axis_05",
        "name": "Common Pitfalls & Costly Mistakes",
        "keywords": ["mistakes", "pitfalls", "avoid", "what not to do", "stop doing", "errors"],
        "template": "5 Fatal {seed} Mistakes You Must Avoid",
    },
    "tools_ecosystem": {
        "axis_id": "axis_06",
        "name": "Tools, Software & Gear Ecosystem",
        "keywords": ["tools", "setup", "gear", "software stack", "stack", "hardware", "apps"],
        "template": "The Ultimate Tech Stack and Tools for {seed}",
    },
    "case_studies_examples": {
        "axis_id": "axis_07",
        "name": "Real-World Case Studies & Proofs",
        "keywords": ["case study", "real world", "example", "how i built", "breakdown", "results"],
        "template": "How I Built a Real-World {seed} Project (Case Study)",
    },
    "automation_efficiency": {
        "axis_id": "axis_08",
        "name": "Automation, Speed & Productivity",
        "keywords": ["automation", "automate", "speed up", "shortcuts", "fastest", "templates", "efficiency"],
        "template": "How to Automate 80% of Your {seed} Pipeline",
    },
    "best_practices": {
        "axis_id": "axis_09",
        "name": "Industry Best Practices & Architecture",
        "keywords": ["best practices", "architecture", "clean", "rules", "standards", "guidelines"],
        "template": "{seed} Best Practices and Clean Architecture Principles",
    },
    "troubleshooting_fixes": {
        "axis_id": "axis_10",
        "name": "Troubleshooting & Problem Solving",
        "keywords": ["troubleshooting", "how to fix", "debug", "solved", "common issues", "fix"],
        "template": "How to Fix the Most Annoying {seed} Issues Fast",
    },
    "cost_budget": {
        "axis_id": "axis_11",
        "name": "Cost, Budget & Free Alternatives",
        "keywords": ["free", "paid", "budget", "pricing", "cost", "cheap", "open source"],
        "template": "Building with {seed} on a $0 Budget (Free & Open Source)",
    },
    "reviews_benchmarks": {
        "axis_id": "axis_12",
        "name": "Honest Reviews & Rigorous Benchmarks",
        "keywords": ["review", "honest review", "benchmark", "tested", "pros and cons", "worth it"],
        "template": "Is {seed} Still Worth It in 2026? Honest Benchmark Review",
    },
    "future_trends": {
        "axis_id": "axis_13",
        "name": "Future Trends & Algorithm/Tech Updates",
        "keywords": ["future", "2026", "updates", "roadmap", "trends", "what is next", "new"],
        "template": "The Future of {seed}: What's Changing in 2026 and Beyond",
    },
    "monetization_business": {
        "axis_id": "axis_14",
        "name": "Monetization, Career & Commercial Value",
        "keywords": ["monetize", "make money", "freelance", "business", "career", "clients", "income"],
        "template": "How to Turn Your {seed} Skills Into a Profitable Business",
    },
    "experiments_challenges": {
        "axis_id": "axis_15",
        "name": "Experiments, Stunts & 30-Day Challenges",
        "keywords": ["challenge", "experiment", "30 days", "i tried", "what happens if", "tested for"],
        "template": "I Used {seed} Exclusively for 30 Days (Here's What Happened)",
    },
}


def evaluate_topic_depth_and_runway(
    seed_topic: str,
    video_titles: List[str],
    autocomplete_suggestions: List[str],
) -> Dict[str, Any]:
    """Analyze topic depth across the 15 universal axes and calculate mathematically guarded runway metrics."""
    seed_clean = seed_topic.strip()
    all_content = [t.lower() for t in video_titles] + [s.lower() for s in autocomplete_suggestions]

    axis_matches: Dict[str, List[str]] = {axis_key: [] for axis_key in UNIVERSAL_15_AXES}
    covered_axes: Set[str] = set()

    for text in all_content:
        for axis_key, axis_meta in UNIVERSAL_15_AXES.items():
            if any(kw in text for kw in axis_meta["keywords"]):
                axis_matches[axis_key].append(text)
                covered_axes.add(axis_key)

    cluster_sizes = [len(matches) for matches in axis_matches.values()]
    # Guarded Shannon entropy ratio across axes
    entropy_ratio = guarded_entropy_ratio(cluster_sizes)

    # Simulated centroid vectors for each covered axis to test inter-cluster distance
    active_centroids = []
    for idx, (axis_key, matches) in enumerate(axis_matches.items()):
        if matches:
            # 2D coordinate representation of axis distribution
            active_centroids.append([float(idx), float(len(matches))])

    inter_cluster_dist = guarded_inter_cluster_distance(active_centroids)

    # Compute runway: distinct video angles generated across all 15 axes
    generated_ideas = []
    for axis_key, axis_meta in UNIVERSAL_15_AXES.items():
        title = axis_meta["template"].format(seed=seed_clean.title())
        generated_ideas.append(
            {
                "axis_id": axis_meta["axis_id"],
                "axis_name": axis_meta["name"],
                "title": title,
                "existing_market_density": len(axis_matches[axis_key]),
            }
        )

    # Total viable video runway estimate
    total_runway = len(generated_ideas) + len(set(autocomplete_suggestions))
    
    # Repeatability score based on runway scale thresholds:
    # <15: weak (<30)
    # 15-35: limited (30-50)
    # 35-70: workable (50-75)
    # 70-120+: strong (75-100)
    if total_runway >= 120:
        repeatability_score = 100.0
    elif total_runway >= 70:
        repeatability_score = 75.0 + 25.0 * ((total_runway - 70) / 50.0)
    elif total_runway >= 35:
        repeatability_score = 50.0 + 25.0 * ((total_runway - 35) / 35.0)
    elif total_runway >= 15:
        repeatability_score = 30.0 + 20.0 * ((total_runway - 15) / 20.0)
    else:
        repeatability_score = max(5.0, total_runway * 2.0)

    return {
        "seed_topic": seed_clean,
        "axes_covered_count": len(covered_axes),
        "total_axes": len(UNIVERSAL_15_AXES),
        "entropy_ratio": round(entropy_ratio, 4),
        "inter_cluster_distance": round(inter_cluster_dist, 4),
        "estimated_video_runway": total_runway,
        "repeatability_score": round(repeatability_score, 2),
        "generated_video_angles": generated_ideas,
        "axis_coverage_distribution": {k: len(v) for k, v in axis_matches.items()},
    }
