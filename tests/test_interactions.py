"""Tests for factor interactions and correlated-factor amplification."""

from src.models import Channel, Video
from src.scoring.breakout import compute_breakout_score
from src.scoring.supply import compute_supply_scarcity_score
from src.scoring.opportunity import compute_content_opportunity


def test_high_hhi_breakout_interaction_does_not_double_count_excessively():
    """Verify breakout interaction neutralizes HHI barrier appropriately without overpowering weak demand/runway.
    
    Fixtures:
    1. HIGH_BREAKOUT_HIGH_HHI: 1 incumbent dominates views, but 5 small channels have breakouts.
    2. HIGH_BREAKOUT_LOW_HHI: Views distributed among many channels, multiple small channel breakouts.
    3. LOW_BREAKOUT_HIGH_HHI: 1 incumbent dominates views, no newcomer breakouts.
    4. LOW_BREAKOUT_LOW_HHI: Views distributed among channels, no breakouts.
    """
    # 1. HIGH_BREAKOUT_HIGH_HHI
    ch_incumbent = Channel(channel_id="c_inc", title="Giant Incumbent", subscribers=1000000)
    small_channels = {
        f"c_s{i}": Channel(
            channel_id=f"c_s{i}",
            title=f"Small {i}",
            subscribers=5000,
            median_recent_views=1000.0,
        )
        for i in range(5)
    }
    tail_channels = {
        f"c_t{i}": Channel(
            channel_id=f"c_t{i}",
            title=f"Tail {i}",
            subscribers=2000,
            median_recent_views=1000.0,
        )
        for i in range(10)
    }
    all_channels_high_hhi = {"c_inc": ch_incumbent, **small_channels, **tail_channels}

    # Incumbent video has 100,000 views. 5 small channel breakout videos have 30,000 views each.
    v_inc = Video(video_id="v_inc", channel_id="c_inc", title="Incumbent Video", published_at="2026-08-01T00:00:00Z", views=100000)
    v_small_breakouts = [
        Video(video_id=f"v_b{i}", channel_id=f"c_s{i}", title=f"Breakout {i}", published_at="2026-08-01T00:00:00Z", views=30000)
        for i in range(5)
    ]
    v_tail = [
        Video(video_id=f"v_t{i}", channel_id=f"c_t{i}", title=f"Tail {i}", published_at="2026-08-01T00:00:00Z", views=1000)
        for i in range(10)
    ]
    videos_hb_hh = [v_inc] + v_small_breakouts + v_tail

    # Breakout scores
    b_score_hb, p_hat_hb, _, _, _, _, _ = compute_breakout_score(videos_hb_hh, all_channels_high_hhi)
    assert p_hat_hb > 0.15

    # Supply scarcity with high breakout (should neutralize HHI penalty)
    s_score_hb_hh, hhi_hb_hh, inc_share_hb_hh, gamma_hb_hh = compute_supply_scarcity_score(
        videos_hb_hh, all_channels_high_hhi, p_hat_breakout=p_hat_hb, p_neutralize=0.20
    )
    # Gamma should be small or 0 because breakout is high (~0.20)
    assert gamma_hb_hh <= 0.25

    # 3. LOW_BREAKOUT_HIGH_HHI: Incumbent dominates, small channels do not break out (only 500 views each)
    v_small_flats = [
        Video(video_id=f"v_f{i}", channel_id=f"c_s{i}", title=f"Flat {i}", published_at="2026-08-01T00:00:00Z", views=500)
        for i in range(5)
    ]
    videos_lb_hh = [v_inc] + v_small_flats + v_tail
    b_score_lb, p_hat_lb, _, _, _, _, _ = compute_breakout_score(videos_lb_hh, all_channels_high_hhi)
    assert p_hat_lb < 0.08

    s_score_lb_hh, _, _, gamma_lb_hh = compute_supply_scarcity_score(
        videos_lb_hh, all_channels_high_hhi, p_hat_breakout=p_hat_lb, p_neutralize=0.20
    )
    # Low breakout means incumbent barrier remains rigid (gamma near 1.0)
    assert gamma_lb_hh >= 0.60
    # Consequently, supply scarcity score is much lower for low-breakout incumbent market
    assert s_score_hb_hh > s_score_lb_hh

    # Verify that high breakout does NOT overpower weak demand and poor runway:
    # If demand = 20, runway = 10, acceleration = 30, even with B = 90 and S = 70:
    content_opp, raw_co = compute_content_opportunity(
        demand_score=20.0,
        supply_scarcity_score=s_score_hb_hh,
        acceleration_score=30.0,
        breakout_score=b_score_hb,
        repeatability_score=10.0,
        durability_score=50.0,
        outlier_penalty=0.0,
    )
    # Content opportunity should NOT reach strong opportunity territory (>70) when core demand & runway are weak!
    assert content_opp < 60.0
