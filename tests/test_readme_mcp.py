"""Phase 9 Task 2 — the README documents how to connect an MCP client.

Guards the one thing a reader will copy-paste and that can silently break: the
client config snippet must be VALID JSON, name the server, and launch it the way
`mcp_server/server.py` actually runs.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"


def _readme() -> str:
    return README.read_text(encoding="utf-8")


def test_has_connect_via_mcp_section():
    assert "## Connect via MCP" in _readme()


def test_config_snippet_is_valid_json_and_names_the_server():
    blocks = re.findall(r"```json\n(.*?)```", _readme(), re.DOTALL)
    cfg = next((json.loads(b) for b in blocks if "mcpServers" in b), None)
    assert cfg is not None, "a JSON mcpServers config snippet must be present"

    servers = cfg["mcpServers"]
    assert "calmline-policy" in servers, "the snippet must name the calmline-policy server"
    entry = servers["calmline-policy"]
    assert entry["command"], "the snippet must give a launch command"
    assert any("mcp_server.server" in str(a) for a in entry["args"]), (
        "the snippet must launch mcp_server.server, matching how the module runs"
    )


def test_section_names_the_tool_and_is_honest_about_the_gate():
    text = _readme()
    section = text[text.index("## Connect via MCP") :]
    assert "policy_lookup" in section, "name the tool a client will call"
    # honest: live retrieval needs keys + seeded data (the operator gate)
    assert re.search(r"key|seed|Supabase", section), "note that live use needs keys / seeded data"
