"""Smoke test dashboard: dijalankan headless untuk setiap pilihan platform."""
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from acs_sentiment import config  # noqa: E402

APP = str(Path(__file__).resolve().parents[1] / "dashboard" / "app.py")

pytestmark = pytest.mark.skipif(
    not config.WORD_SENTIMENT_FILE.exists(), reason="jalankan pipeline dulu untuk membuat output/"
)


@pytest.mark.parametrize("platform", ["Semua platform", "Steam", "Reddit", "YouTube"])
def test_dashboard_renders_without_errors(platform):
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.sidebar.radio[0].set_value(platform).run()
    assert not at.exception
    assert at.title[0].value == "Sentimen Pemain Assassin's Creed Shadows"
    assert len(at.metric) >= 8


def test_word_search_shows_metrics():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.selectbox[0].set_value("combat").run()
    assert not at.exception
    labels = [m.label for m in at.metric]
    assert "Skor PMI" in labels
