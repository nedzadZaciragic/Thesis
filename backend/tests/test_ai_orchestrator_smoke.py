import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_orchestrator import StableChatOrchestrator


class DummyCompletions:
    async def create(self, **kwargs):
        raise RuntimeError("simulated model failure")


class DummyClient:
    def __init__(self):
        self.chat = type("Chat", (), {"completions": DummyCompletions()})()


def test_orchestrator_returns_stable_fallback_response():
    orchestrator = StableChatOrchestrator(client=DummyClient())

    result = asyncio.run(
        orchestrator.respond(
            apartment={
                "id": "apt-1",
                "address": "Titova 10, Sarajevo, BiH",
                "description": "Modern apartment near the old town",
                "check_in_time": "15:00",
                "check_out_time": "11:00",
            },
            branding={"brand_name": "My Host IQ"},
            message="Where is the wifi password?",
            session_id="session-123",
        )
    )

    assert result["response"]
    assert result["response"].lower().startswith(("i can help", "ich kann", "puedo ayudar", "je peux", "posso aiutarti", "mogu"))
    assert result["used_fallback"] is True
    assert result["language"] == "en"
