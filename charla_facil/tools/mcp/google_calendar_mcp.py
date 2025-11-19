from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

google_calendar_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=[
                "-y",
                "@cocal/google-calendar-mcp",
            ],
            env={
                "GOOGLE_OAUTH_CREDENTIALS": "F:\Media\Dokumenty\github\hackathon-charla-facil\charla_facil\gcp-oauth.keys.json"
            }
        ),
        timeout=30,
    )
)
