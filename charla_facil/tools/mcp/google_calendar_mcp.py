from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from pathlib import Path

google_calendar_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=[
                "-y",
                "@cocal/google-calendar-mcp",
            ],
            env={
                "GOOGLE_OAUTH_CREDENTIALS": str(Path(__file__).resolve().parents[2] / "gcp-oauth.keys.json")
            }
        ),
        timeout=30,
    )
)
