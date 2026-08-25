from __future__ import annotations

from slidecraft.orchestration.pipeline import _render_exact_content


def test_exact_content_renderer_accepts_non_architecture_content() -> None:
    rendered = _render_exact_content({"exact_content": {"title": "Market outlook", "claims": ["Demand rises", "Costs fall"]}})
    assert "Market outlook" in rendered
    assert "Demand rises" in rendered
    assert "stages" not in rendered
