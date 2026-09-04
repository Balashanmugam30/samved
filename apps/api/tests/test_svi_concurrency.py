import concurrent.futures
import pytest
from app.services.svi_engine import SVIEngine


@pytest.fixture
def engine():
    return SVIEngine()


def test_svi_concurrent_evaluations(engine):
    """Executes 50 concurrent evaluations across multiple threads to verify thread-safety."""
    turns_variations = [
        [{"speaker": "caller", "text": "He locked me in room and took my phone.", "language": "en-IN"}],
        [{"speaker": "caller", "text": "நான் ரொம்ப பயந்து போய் இருக்கேன், உதவிக்கு யாரும் இல்ல.", "language": "ta-IN"}],
        [{"speaker": "caller", "text": "मुझे कमरे में बंद कर दिया है, भागने की कोई जगह नहीं.", "language": "hi-IN"}],
        [{"speaker": "caller", "text": "Safe now, mother is with me and police arrived.", "language": "en-IN"}],
        [{"speaker": "caller", "text": "Hello, I just need legal consultation.", "language": "en-IN"}],
    ]

    def run_eval(idx: int):
        turns = turns_variations[idx % len(turns_variations)]
        res = engine.evaluate_session(
            call_id=f"concurrent-call-{idx}",
            session_id=f"concurrent-sess-{idx}",
            turns=turns,
            previous_score=30,
            turn_index=idx,
        )
        assert 0 <= res.score <= 100
        assert res.band in ("LOW", "MODERATE", "HIGH", "CRITICAL")
        assert res.disclaimer is not None
        return res.score

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(run_eval, i) for i in range(50)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 50
