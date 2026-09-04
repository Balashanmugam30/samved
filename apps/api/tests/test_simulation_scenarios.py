import asyncio
import pytest
from app.realtime.simulation import SCENARIOS, run_simulated_conversation
from app.realtime.session_manager import telephony_session_manager


@pytest.mark.asyncio
async def test_run_simulated_conversation_tamil():
    result = await run_simulated_conversation(scenario_key="tamil_help")
    assert result["status"] == "simulation_started"
    assert result["scenario"] == "tamil_help"
    assert result["turns_count"] == 2
    session_id = result["session_id"]

    # Verify session is created and active
    session = await telephony_session_manager.get_session(session_id)
    assert session is not None
    assert session.orchestrator is not None

    # Wait for simulation to complete cleanly
    for _ in range(30):
        session_after = await telephony_session_manager.get_session(session_id)
        if session_after is None:
            break
        await asyncio.sleep(0.1)

    assert session_after is None  # Cleanly ended and removed from active registry


@pytest.mark.asyncio
async def test_run_simulated_conversation_interruption():
    result = await run_simulated_conversation(scenario_key="interruption")
    assert result["status"] == "simulation_started"
    session_id = result["session_id"]

    for _ in range(30):
        session_after = await telephony_session_manager.get_session(session_id)
        if session_after is None:
            break
        await asyncio.sleep(0.1)

    assert session_after is None