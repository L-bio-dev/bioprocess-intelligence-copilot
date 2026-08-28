"""Smoke test for the Streamlit dashboard."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def test_demo_dashboard_loads_without_exceptions() -> None:
    app = AppTest.from_file(
        APP_PATH,
        default_timeout=60,
    ).run()

    assert not app.exception

    assert any(
        "passed all blocking validation checks" in message.value
        for message in app.success
    )

    assert len(app.download_button) == 2