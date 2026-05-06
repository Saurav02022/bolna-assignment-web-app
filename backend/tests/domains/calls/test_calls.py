from datetime import datetime, timezone
from typing import Any

import pytest
from starlette.testclient import TestClient

from app.core.deps import get_bolna_client
from app.domains.calls.mutator import (
    _extract_from_transcript,
    extract_extractions,
    normalise_outcome_tag,
)
from app.domains.calls.schemas import BolnaWebhookPayload
from app.domains.orders.mutator import outcome_to_status
from app.domains.orders.schemas import OrderStatus
from app.main import app


class FakeBolnaClient:
    """Captures the last call args; returns a deterministic execution_id."""

    def __init__(self, execution_id: str = "EXEC-TEST-001") -> None:
        self.execution_id = execution_id
        self.last_call: dict[str, Any] | None = None

    async def place_call(self, **kwargs: Any) -> dict[str, Any]:
        self.last_call = kwargs
        return {
            "message": "done",
            "status": "queued",
            "execution_id": self.execution_id,
        }


@pytest.fixture
def fake_bolna() -> FakeBolnaClient:
    return FakeBolnaClient()


@pytest.fixture
def client_with_fake_bolna(client: TestClient, fake_bolna: FakeBolnaClient) -> TestClient:
    app.dependency_overrides[get_bolna_client] = lambda: fake_bolna
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_bolna_client, None)


def test_outcome_to_status_mapping_covers_all_known_tags() -> None:
    assert outcome_to_status("confirmed") == OrderStatus.ship_approved
    assert outcome_to_status("address_correction") == OrderStatus.address_correction_requested
    assert outcome_to_status("reschedule") == OrderStatus.reschedule_requested
    assert outcome_to_status("cancel_requested") == OrderStatus.cancelled
    assert outcome_to_status("needs_followup") == OrderStatus.needs_followup
    assert outcome_to_status("unreachable") == OrderStatus.unreachable
    assert outcome_to_status(None) == OrderStatus.needs_followup
    assert outcome_to_status("garbage") == OrderStatus.needs_followup


def test_transcript_mining_extracts_outcome_when_extractions_missing() -> None:
    transcript = (
        "assistant: Aapne Cotton Kurta size L confirm kiya?\n"
        "user: Haan confirm hai\n"
        "assistant: Bahut acche, sab confirm ho gaya. Outcome tag: confirmed N"
    )
    mined = _extract_from_transcript(transcript)
    assert mined["outcome_tag"] == "confirmed"


def test_transcript_mining_extracts_capture_fields() -> None:
    transcript = (
        "assistant: Address change kar diya.\n"
        "outcome_tag: address_correction\n"
        "new_address_landmark: grocery shop downstairs"
    )
    mined = _extract_from_transcript(transcript)
    assert mined["outcome_tag"] == "address_correction"
    assert mined["new_address_landmark"] == "grocery shop downstairs"


def test_extract_extractions_falls_back_to_transcript() -> None:
    payload = BolnaWebhookPayload(
        id="exec-1",
        status="call-disconnected",
        extracted_data=None,
        custom_extractions=None,
        transcript=(
            "assistant: Sab confirm ho gaya. Have a great day! "
            "Outcome tag: confirmed"
        ),
    )
    result = extract_extractions(payload)
    assert result == {"outcome_tag": "confirmed"}


def test_extract_extractions_prefers_structured_over_transcript() -> None:
    payload = BolnaWebhookPayload(
        id="exec-2",
        status="completed",
        custom_extractions={"outcome_tag": "reschedule"},
        transcript="Outcome tag: confirmed",
    )
    result = extract_extractions(payload)
    assert result == {"outcome_tag": "reschedule"}


def test_normalise_outcome_tag_filters_invalid_values() -> None:
    assert normalise_outcome_tag("CONFIRMED") == "confirmed"
    assert normalise_outcome_tag(" Reschedule ") == "reschedule"
    assert normalise_outcome_tag("not_a_tag") == "needs_followup"
    assert normalise_outcome_tag(None) is None
    assert normalise_outcome_tag("null") is None


def test_verify_order_triggers_call_and_marks_verifying(
    client_with_fake_bolna: TestClient,
    fake_bolna: FakeBolnaClient,
) -> None:
    listed = client_with_fake_bolna.get("/orders").json()
    order_id = listed["items"][0]["id"]

    response = client_with_fake_bolna.post(f"/orders/{order_id}/verify")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["call_id"] == "EXEC-TEST-001"
    assert body["order"]["status"] == "verifying"
    assert body["order"]["last_call_id"] == "EXEC-TEST-001"

    assert fake_bolna.last_call is not None
    user_data = fake_bolna.last_call["user_data"]
    assert user_data["order_id"] == order_id
    assert user_data["customer_name"]
    assert user_data["product_summary"]


def _completion_payload(call_id: str, order_id: str, outcome: str = "confirmed") -> dict[str, Any]:
    return {
        "execution_id": call_id,
        "agent_id": "agent-test",
        "status": "completed",
        "user_data": {"order_id": order_id},
        "transcript_url": "https://bolna.example/transcript.txt",
        "recording_url": "https://bolna.example/recording.mp3",
        "summary": "Customer confirmed the order.",
        "duration_sec": 47,
        "language_detected": "hi-IN",
        "sentiment": "neutral",
        "extracted_data": {
            "outcome_tag": outcome,
            "new_address_landmark": None,
            "new_slot": None,
            "cancel_reason": None,
            "followup_question": None,
        },
    }


def test_webhook_applies_outcome_and_is_idempotent(
    client_with_fake_bolna: TestClient,
    fake_bolna: FakeBolnaClient,
) -> None:
    listed = client_with_fake_bolna.get("/orders").json()
    order_id = listed["items"][0]["id"]
    client_with_fake_bolna.post(f"/orders/{order_id}/verify")

    payload = _completion_payload("EXEC-TEST-001", order_id, outcome="confirmed")

    first = client_with_fake_bolna.post("/webhooks/bolna", json=payload).json()
    assert first["received"] is True
    assert first["applied"] is True
    assert first["order_id"] == order_id

    order_after = client_with_fake_bolna.get(f"/orders/{order_id}").json()
    assert order_after["status"] == "ship_approved"
    assert order_after["last_call_outcome"] == "confirmed"
    assert order_after["last_summary"] == "Customer confirmed the order."

    second = client_with_fake_bolna.post("/webhooks/bolna", json=payload).json()
    assert second["applied"] is False
    assert second["reason"] == "duplicate"


def test_webhook_routes_address_correction_to_correct_status(
    client_with_fake_bolna: TestClient,
) -> None:
    listed = client_with_fake_bolna.get("/orders").json()
    order_id = listed["items"][1]["id"]
    client_with_fake_bolna.post(f"/orders/{order_id}/verify")

    payload = _completion_payload("EXEC-TEST-001", order_id, outcome="address_correction")
    payload["extracted_data"]["new_address_landmark"] = "grocery shop downstairs"

    client_with_fake_bolna.post("/webhooks/bolna", json=payload)

    order_after = client_with_fake_bolna.get(f"/orders/{order_id}").json()
    assert order_after["status"] == "address_correction_requested"
    assert order_after["captured_address_landmark"] == "grocery shop downstairs"


def test_webhook_without_call_id_is_silently_acked(client: TestClient) -> None:
    response = client.post("/webhooks/bolna", json={"status": "completed"})
    assert response.status_code == 200
    body = response.json()
    assert body["received"] is True
    assert body["applied"] is False
    assert body["reason"] == "missing_call_id"
