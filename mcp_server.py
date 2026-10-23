import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from mcp.server.fastmcp import FastMCP

STATE_FILE = "aegis_state.json"

DEFAULT_STATE = {
    "session_id": f"mcp-sess-{uuid.uuid4().hex[:8]}",
    "incident_id": "INC-2026-8841",
    "status": "CRITICAL_ANOMALY",
    "service": "prd-bedrock-rag-worker-us-east-1",
    "current_version": "v2.4.9-hotfix",
    "stable_version": "v2.4.8-stable",
    "burn_rate_usd_hr": 842.50,
    "baseline_usd_hr": 24.00,
    "root_cause": "Recursive retry loop in Lambda invoking Claude 3.7 Sonnet with uncached 92k-token context windows.",
    "ring_front_door_verified": False,
    "ring_last_event": "Awaiting physical security key / on-call responder verification at Front Door",
    "reserved_capacity_purchased": False,
    "purchased_plan": None,
    "history": [
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "CloudWatch Anomaly Alarm triggered: Burn rate spiked 3,410% ($842.50/hr)."
        }
    ]
}


def load_state() -> Dict[str, Any]:
    if not os.path.exists(STATE_FILE):
        save_state(DEFAULT_STATE)
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: Dict[str, Any]) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


# Initialize Self-Hosted MCP Server (Spec 2025-11-25+ Streamable HTTP)
mcp = FastMCP(
    name="aegis-cloud-to-couch-mcp",
    host="0.0.0.0",
    port=8000,
)


@mcp.resource("aegis://telemetry/live-burn-rate")
def get_live_burn_rate() -> str:
    """Live AWS FinOps telemetry resource exposing real-time hourly burn rate and active incident status."""
    state = load_state()
    return json.dumps({
        "incident_id": state["incident_id"],
        "status": state["status"],
        "service": state["service"],
        "burn_rate_usd_hr": state["burn_rate_usd_hr"],
        "baseline_usd_hr": state["baseline_usd_hr"],
        "ring_front_door_verified": state["ring_front_door_verified"],
        "reserved_capacity_purchased": state["reserved_capacity_purchased"]
    })


@mcp.resource("aegis://incidents/active-timeline")
def get_incident_timeline() -> str:
    """Cross-session audit trail of all cloud, living room, and front-door events."""
    state = load_state()
    return json.dumps(state["history"])


@mcp.prompt("living_room_incident_commander")
def incident_commander_prompt(incident_id: str = "INC-2026-8841") -> str:
    """Structured multi-turn prompt for Alexa+ voice-first incident triage and FinOps purchasing."""
    return (
        f"You are Aegis, an Alexa+ Zero-Keyboard FinOps & Incident Commander managing {incident_id}. "
        "Keep voice responses under 3 sentences for living-room clarity while emitting rich Alexa+ Adaptive Cards "
        "for Fire TV / Echo Show displays. Require Ring front-door presence verification before production rollbacks, "
        "and offer Bedrock Reserved Capacity savings plans when token spend exceeds baseline."
    )


@mcp.tool(
    name="inspect_blast_radius",
    description="Inspect active AWS cost spike and latency blast radius, returning telemetry and an Alexa+ Adaptive Carousel."
)
def inspect_blast_radius(incident_id: str = "INC-2026-8841") -> Dict[str, Any]:
    state = load_state()
    state["history"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": f"MCP Tool inspect_blast_radius invoked for {incident_id}."
    })
    save_state(state)

    return {
        "protocol_version": "2025-11-25",
        "transport": "streamable-http",
        "incident_id": state["incident_id"],
        "status": state["status"],
        "service": state["service"],
        "burn_rate_usd_hr": state["burn_rate_usd_hr"],
        "root_cause": state["root_cause"],
        "alexa_plus_card": {
            "type": "AlexaPlus.AdaptiveCarousel",
            "title": f"Blast Radius: {state['service']}",
            "subtitle": f"Current Burn: ${state['burn_rate_usd_hr']:.2f}/hr (Baseline: ${state['baseline_usd_hr']:.2f}/hr)",
            "items": [
                {
                    "card_id": "telemetry-1",
                    "badge": "ROOT CAUSE DETECTED",
                    "headline": "Uncached 92K Context Loop",
                    "detail": state["root_cause"],
                    "metric": "$842.50 / hr"
                },
                {
                    "card_id": "remediation-1",
                    "badge": "OPTION 1: ROLLBACK",
                    "headline": f"Rollback to {state['stable_version']}",
                    "detail": "Requires Ring Front-Door Presence/Badge check for zero-keyboard physical 2FA.",
                    "metric": "Est. Recovery: 14s"
                },
                {
                    "card_id": "finops-1",
                    "badge": "OPTION 2: FINOPS COMMIT",
                    "headline": "Purchase Bedrock Savings Plan",
                    "detail": "Lock in 1-Click Provisioned Throughput + Prompt Caching discount (-68% cost).",
                    "metric": "$149.00 / mo commit"
                }
            ]
        },
        "voice_summary": (
            f"Alert on {state['service']}. Burn rate has spiked to {state['burn_rate_usd_hr']} dollars per hour "
            f"due to a recursive retry loop in {state['current_version']}. I have projected the blast radius carousel "
            "onto your Fire TV screen. Would you like to verify your Ring front-door badge to roll back, or purchase "
            "discounted Bedrock Reserved Capacity?"
        )
    }


@mcp.tool(
    name="verify_ring_front_door_2fa",
    description="Verify physical on-call presence or hardware security key delivery via Ring Front Door camera/intercom event."
)
def verify_ring_front_door_2fa(verification_pin: str = "9942") -> Dict[str, Any]:
    state = load_state()
    state["ring_front_door_verified"] = True
    state["ring_last_event"] = f"Verified On-Call Engineer at Front Door via Ring Optical/PIN ({verification_pin})"
    state["history"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": f"Ring Front-Door 2FA verified with PIN {verification_pin}. Production write-lock lifted."
    })
    save_state(state)

    return {
        "protocol_version": "2025-11-25",
        "verified": True,
        "ring_event": state["ring_last_event"],
        "alexa_plus_card": {
            "type": "AlexaPlus.RingSecurityCard",
            "title": "Ring Front-Door Physical 2FA Verified",
            "subtitle": "Living Room + Front Door + Cloud Sync Active",
            "badge": "PRODUCTION UNLOCKED",
            "detail": "Biometric & PIN handshake confirmed at Front Door. Zero-keyboard production rollback and FinOps purchasing are now authorized across this session."
        },
        "voice_summary": (
            "Ring front-door presence verified. Production write-locks are now lifted for your session. "
            "Say 'Execute rollback' or 'Purchase reserved capacity' whenever you are ready."
        )
    }


@mcp.tool(
    name="execute_deployment_rollback",
    description="Roll back the runaway AWS Lambda/Bedrock service to the last known stable version after Ring 2FA verification."
)
def execute_deployment_rollback(incident_id: str = "INC-2026-8841", target_version: str = "v2.4.8-stable") -> Dict[str, Any]:
    state = load_state()
    if not state["ring_front_door_verified"]:
        state["history"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "Blocked unauthorized voice rollback attempt: Ring Front-Door 2FA still LOCKED."
        })
        save_state(state)
        return {
            "protocol_version": "2025-11-25",
            "success": False,
            "error": "RING_2FA_REQUIRED",
            "alexa_plus_card": {
                "type": "AlexaPlus.SecurityGateCard",
                "title": "Physical 2FA Required Before Rollback",
                "subtitle": "Trigger Ring Front-Door Verification First",
                "badge": "WRITE-LOCK ACTIVE",
                "detail": "Zero-trust guardrail blocked this voice rollback because Ring Front-Door presence has not been verified yet."
            },
            "voice_summary": (
                "Production rollback blocked. To prevent unauthorized living-room voice commands, "
                "please verify your Ring front-door badge first."
            )
        }

    state["current_version"] = target_version
    state["status"] = "MITIGATED_STABLE"
    state["burn_rate_usd_hr"] = 24.00
    state["history"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": f"Rolled back {state['service']} to {target_version}. Burn rate normalized to $24.00/hr."
    })
    save_state(state)

    return {
        "protocol_version": "2025-11-25",
        "success": True,
        "incident_id": incident_id,
        "deployed_version": target_version,
        "new_burn_rate_usd_hr": state["burn_rate_usd_hr"],
        "alexa_plus_card": {
            "type": "AlexaPlus.RemediationCard",
            "title": f"Rollback Complete: {target_version}",
            "subtitle": "Hourly Spend Reduced from $842.50/hr to $24.00/hr",
            "badge": "HEALTHY",
            "detail": f"Traffic shifted 100% to {target_version} with Prompt Caching enforced. Estimated monthly savings: $589,320."
        },
        "voice_summary": (
            f"Rollback to {target_version} is complete. Your hourly burn rate has dropped from 842 dollars "
            "down to your 24 dollar baseline. Would you also like to lock in a Bedrock Savings Plan?"
        )
    }


@mcp.tool(
    name="purchase_bedrock_savings_bundle",
    description="Transactional purchasing tool: buys an AWS Bedrock Prompt-Caching & Provisioned Throughput FinOps bundle via Alexa+."
)
def purchase_bedrock_savings_bundle(plan_tier: str = "Bedrock-FinOps-Shield-100M", price_usd: float = 149.00) -> Dict[str, Any]:
    state = load_state()
    order_id = f"AMZ-FINOPS-{uuid.uuid4().hex[:6].upper()}"
    state["reserved_capacity_purchased"] = True
    state["purchased_plan"] = {
        "order_id": order_id,
        "plan_tier": plan_tier,
        "price_usd": price_usd,
        "purchased_at": datetime.now(timezone.utc).isoformat()
    }
    state["burn_rate_usd_hr"] = 16.50
    state["history"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": f"Purchased {plan_tier} (${price_usd}) via Alexa+ Transactional Flow. Order ID: {order_id}."
    })
    save_state(state)

    return {
        "protocol_version": "2025-11-25",
        "transaction_status": "COMPLETED",
        "order_id": order_id,
        "plan_tier": plan_tier,
        "amount_charged_usd": price_usd,
        "new_burn_rate_usd_hr": state["burn_rate_usd_hr"],
        "alexa_plus_card": {
            "type": "AlexaPlus.TransactionReceiptCard",
            "title": f"Order Confirmed: {plan_tier}",
            "subtitle": f"Order #{order_id} • Charged ${price_usd:.2f} to AWS Billing",
            "badge": "PURCHASED",
            "detail": "Provisioned Throughput + Automatic Hard Spend Guardrail activated. Burn rate reduced further to $16.50/hr."
        },
        "voice_summary": (
            f"Transaction confirmed. I have purchased the {plan_tier} bundle for {price_usd} dollars under order "
            f"{order_id}. Your hourly burn rate is now down to 16 dollars and 50 cents."
        )
    }


@mcp.tool(
    name="reset_incident_simulation",
    description="Reset the incident state back to the initial $842.50/hr anomaly for live demo recording."
)
def reset_incident_simulation() -> Dict[str, Any]:
    fresh = json.loads(json.dumps(DEFAULT_STATE))
    fresh["session_id"] = f"mcp-sess-{uuid.uuid4().hex[:8]}"
    save_state(fresh)
    return {
        "protocol_version": "2025-11-25",
        "status": "RESET_COMPLETE",
        "voice_summary": "Simulation reset to initial critical anomaly state at 842 dollars and 50 cents per hour.",
        "alexa_plus_card": {
            "type": "AlexaPlus.AlertCard",
            "title": "prd-bedrock-rag-worker-us-east-1 (v2.4.9-hotfix)",
            "subtitle": "CloudWatch Anomaly Alert • INC-2026-8841 (+3,410% Spend Spike)",
            "badge": "CRITICAL ANOMALY",
            "detail": "Recursive retry loop invoking Claude 3.7 Sonnet with uncached 92k-token context windows."
        }
    }


if __name__ == "__main__":
    print("Starting Aegis Cloud-to-Couch MCP Server (Streamable HTTP) on http://localhost:8000/mcp ...")
    mcp.run(transport="streamable-http", mount_path="/mcp")
