# Aegis Cloud-to-Couch — Zero-Keyboard FinOps & Incident Commander

**Hackathon:** Build, Ship, Shape: Amazon Developer Hackathon (2026)  
**Tracks:** Alexa+ (Agentic AI & MCP Track) + AWS Builder Mini Challenge

## Overview
**Aegis Cloud-to-Couch** connects the **Living Room (Alexa+ & Fire TV)**, the **Front Door (Ring physical 2FA presence handshake)**, and the **Cloud (AWS Bedrock + Strands Agents SDK)** into an autonomous, stateful, transactional FinOps and Incident Commander.

When an uncached LLM retry loop causes a +3,410% AWS Bedrock spend spike ($842.50/hr), on-call engineers no longer need to scramble for a laptop. Using voice and multimodal Fire TV Adaptive Carousels, engineers can inspect the blast radius, complete a physical Ring front-door 2FA check to unlock production write permissions, roll back to a stable deployment (`$24.00/hr`), and execute a 1-click transactional purchase for a Bedrock Reserved Capacity Savings Bundle (`$16.50/hr`).

## Technical Architecture
1. **`mcp_server.py` (Self-Hosted MCP `2025-11-25` Streamable HTTP Server on `:8000/mcp`):**
   - **Tools (5):** `inspect_blast_radius`, `verify_ring_front_door_2fa`, `execute_deployment_rollback`, `purchase_bedrock_savings_bundle`, `reset_incident_simulation`
   - **Resources (2):** `aegis://telemetry/live-burn-rate`, `aegis://incidents/active-timeline`
   - **Prompts (1):** `living_room_incident_commander`
2. **`agent_bridge.py` (AWS Strands Agents SDK + Amazon Bedrock Host on `:8001`):**
   - Integrates `strands.Agent`, `strands.models.BedrockModel`, and `strands.tools.mcp.MCPClient`.
   - Streams live `2025-11-25` JSON-RPC 2.0 request and response frames over Streamable HTTP (`POST /mcp`) with `Mcp-Session-Id` state tracking.
3. **`index.html` (Alexa+ / Fire TV / Ring Multimodal Web Simulator):**
   - Renders `AlexaPlus.AdaptiveCarousel`, `AlexaPlus.SecurityGateCard`, `AlexaPlus.RingSecurityCard`, `AlexaPlus.RemediationCard`, and `AlexaPlus.TransactionReceiptCard` alongside a real-time JSON-RPC Protocol Inspector.

## How to Run Locally
```bash
pip install -r requirements.txt

# Terminal 1: Start the Streamable HTTP MCP Server on port 8000
python mcp_server.py

# Terminal 2: Start the AWS Strands Host & Simulator on port 8001
python agent_bridge.py