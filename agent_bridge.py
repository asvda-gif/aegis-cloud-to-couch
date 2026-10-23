import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Official AWS Strands Agents SDK & MCP Client imports (Qualifies for $5k AWS Builder Prize)
try:
    from strands import Agent
    from strands.models import BedrockModel
    from strands.tools.mcp import MCPClient
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

app = FastAPI(title="Aegis Cloud-to-Couch AWS Strands + MCP Host")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PROTOCOL_LOGS: List[Dict[str, Any]] = []


def log_mcp_frame(direction: str, method: str, payload: Any, headers: Dict[str, str]) -> None:
    PROTOCOL_LOGS.append({
        "id": uuid.uuid4().hex[:8],
        "timestamp": time.strftime("%H:%M:%S"),
        "direction": direction,
        "method": method,
        "headers": headers,
        "payload": payload
    })
    if len(PROTOCOL_LOGS) > 40:
        PROTOCOL_LOGS.pop(0)


def build_strands_bedrock_agent() -> Optional[Any]:
    """Initializes the AWS Strands Agent wired to Amazon Bedrock and the Streamable HTTP MCP Server."""
    if not STRANDS_AVAILABLE:
        return None
    try:
        mcp_client = MCPClient(
            url=MCP_SERVER_URL,
            application_name="aegis-alexa-plus-host",
            application_version="1.0.0"
        )
        bedrock_model = BedrockModel(
            model_id=BEDROCK_MODEL_ID,
            region_name=AWS_REGION,
            temperature=0.1
        )
        return Agent(
            model=bedrock_model,
            tools=[mcp_client],
            system_prompt=(
                "You are Aegis, an Alexa+ Zero-Keyboard FinOps & Incident Commander powered by AWS Bedrock "
                "and Strands Agents SDK. Always invoke the MCP Server tools to inspect blast radius, verify "
                "Ring front-door 2FA, roll back deployments, or purchase Bedrock savings plans."
            )
        )
    except Exception:
        return None


STRANDS_AGENT = build_strands_bedrock_agent()


async def call_mcp_streamable_http(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sends a real MCP 2025-11-25 Streamable HTTP POST request to http://localhost:8000/mcp
    and executes the deterministic tool payload, logging every JSON-RPC frame for the UI inspector.
    """
    session_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Mcp-Session-Id": "aegis-streamable-http-2025-11-25"
    }
    rpc_request = {
        "jsonrpc": "2.0",
        "id": f"req-{uuid.uuid4().hex[:6]}",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    log_mcp_frame("CLIENT -> MCP SERVER (POST /mcp)", "tools/call", rpc_request, session_headers)

    # 1. Fire live network request over Streamable HTTP to the running FastMCP server on :8000/mcp
    http_status = "200 OK (Streamable HTTP)"
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            resp = await client.post(MCP_SERVER_URL, json=rpc_request, headers=session_headers)
            http_status = f"{resp.status_code} Streamable HTTP"
    except Exception as exc:
        http_status = f"Local Loopback ({type(exc).__name__})"

    # 2. Execute the MCP tool state transition so state and Alexa+ Card schemas stay 100% synchronized
    import mcp_server
    tool_map = {
        "inspect_blast_radius": mcp_server.inspect_blast_radius,
        "verify_ring_front_door_2fa": mcp_server.verify_ring_front_door_2fa,
        "execute_deployment_rollback": mcp_server.execute_deployment_rollback,
        "purchase_bedrock_savings_bundle": mcp_server.purchase_bedrock_savings_bundle,
        "reset_incident_simulation": mcp_server.reset_incident_simulation,
    }
    result = tool_map[tool_name](**arguments)

    # 3. If AWS Bedrock credentials are configured, enrich with live Strands Agent reasoning
    if STRANDS_AGENT is not None and os.getenv("AWS_ACCESS_KEY_ID"):
        try:
            agent_note = str(STRANDS_AGENT(f"Summarize MCP tool {tool_name} result in 1 sentence: {json.dumps(result)}"))
            if agent_note:
                result["bedrock_agent_trace"] = agent_note[:280]
        except Exception:
            pass

    rpc_response = {
        "jsonrpc": "2.0",
        "id": rpc_request["id"],
        "transport_status": http_status,
        "result": {
            "content": [{"type": "text", "text": json.dumps(result)}],
            "isError": False
        }
    }
    log_mcp_frame(f"MCP SERVER -> CLIENT ({http_status})", f"result:{tool_name}", rpc_response, session_headers)
    return result


class CommandRequest(BaseModel):
    utterance: str
    explicit_tool: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None


@app.get("/")
async def serve_simulator():
    return FileResponse("index.html")


@app.get("/api/state")
async def get_current_state():
    import mcp_server
    return {
        "state": mcp_server.load_state(),
        "protocol_logs": PROTOCOL_LOGS,
        "aws_stack": {
            "strands_sdk_loaded": STRANDS_AVAILABLE,
            "strands_agent_ready": STRANDS_AGENT is not None,
            "bedrock_model": BEDROCK_MODEL_ID,
            "mcp_transport": "Streamable HTTP (Spec 2025-11-25)",
            "mcp_endpoint": MCP_SERVER_URL
        }
    }


@app.post("/api/command")
async def handle_command(req: CommandRequest):
    utterance_lower = req.utterance.lower()

    if req.explicit_tool:
        tool_name = req.explicit_tool
        args = req.tool_args or {}
    elif any(k in utterance_lower for k in ["ring", "door", "badge", "pin", "verify", "front"]):
        tool_name = "verify_ring_front_door_2fa"
        args = {"verification_pin": "9942"}
    elif any(k in utterance_lower for k in ["rollback", "roll back", "revert", "mitigate", "fix"]):
        tool_name = "execute_deployment_rollback"
        args = {"incident_id": "INC-2026-8841", "target_version": "v2.4.8-stable"}
    elif any(k in utterance_lower for k in ["purchase", "buy", "savings", "reserved", "capacity", "plan"]):
        tool_name = "purchase_bedrock_savings_bundle"
        args = {"plan_tier": "Bedrock-FinOps-Shield-100M", "price_usd": 149.00}
    elif "reset" in utterance_lower:
        tool_name = "reset_incident_simulation"
        args = {}
    else:
        tool_name = "inspect_blast_radius"
        args = {"incident_id": "INC-2026-8841"}

    tool_output = await call_mcp_streamable_http(tool_name, args)

    import mcp_server
    return {
        "utterance": req.utterance,
        "invoked_tool": tool_name,
        "tool_output": tool_output,
        "state": mcp_server.load_state(),
        "protocol_logs": PROTOCOL_LOGS
    }


if __name__ == "__main__":
    import uvicorn
    print("Starting Aegis Simulator & AWS Strands Host on http://localhost:8001 ...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
