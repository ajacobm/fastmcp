import json

import pytest
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.types import TextContent, TextResourceContents

from fastmcp import FastMCP
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport
from fastmcp.exceptions import NotFoundError


class TestBasicMount:
    """Test basic mounting functionality."""

    async def test_mount_simple_server(self):
        """Test mounting a simple server and accessing its tool."""
        # Create main app and sub-app
        main_app = FastMCP("MainApp")
        sub_app = FastMCP("SubApp")

        # Add a tool to the sub-app
        @sub_app.tool()
        def sub_tool() -> str:
            return "This is from the sub app"

        # Mount the sub-app to the main app
        main_app.mount("sub", sub_app)

        # Get tools from main app, should include sub_app's tools
        tools = await main_app.get_tools()
        assert "sub_sub_tool" in tools

        async with Client(main_app) as client:
            result = await client.call_tool("sub_sub_tool", {})
            assert isinstance(result[0], TextContent)
            assert result[0].text == "This is from the sub app"

    async def test_mount_with_custom_separator(self):
        """Test mounting with a custom tool separator."""
        main_app = FastMCP("MainApp")
        sub_app = FastMCP("SubApp")

        @sub_app.tool()
        def greet(name: str) -> str:
            return f"Hello, {name}!"

        # Mount with custom separator
        main_app.mount("sub", sub_app, tool_separator="-")

        # Tool should be accessible with custom separator
        tools = await main_app.get_tools()
        assert "sub-greet" in tools

        # Call the tool
        result = await main_app._mcp_call_tool("sub-greet", {"name": "World"})
        assert isinstance(result[0], TextContent)
        assert result[0].text == "Hello, World!"

    async def test_unmount_server(self):
        """Test unmounting a server removes access to its tools."""
        main_app = FastMCP("MainApp")
        sub_app = FastMCP("SubApp")

        @sub_app.tool()
        def sub_tool() -> str:
            return "This is from the sub app"

        # Mount the sub-app
        main_app.mount("sub", sub_app)

        # Verify it was mounted
        tools = await main_app.get_tools()
        assert "sub_sub_tool" in tools

        # Unmount the sub-app
        main_app.unmount("sub")

        # Verify it was unmounted
        tools = await main_app.get_tools()
        assert "sub_sub_tool" not in tools

        # Calling the tool should fail
        with pytest.raises(NotFoundError, match="Unknown tool: sub_sub_tool"):
            await main_app._mcp_call_tool("sub_sub_tool", {})


class TestMultipleServerMount:
    """Test mounting multiple servers simultaneously."""

    async def test_mount_multiple_servers(self):
        """Test mounting multiple servers with different prefixes."""
        main_app = FastMCP("MainApp")
        weather_app = FastMCP("WeatherApp")
        news_app = FastMCP("NewsApp")

        @weather_app.tool()
        def get_forecast() -> str:
            return "Weather forecast"

        @news_app.tool()
        def get_headlines() -> str:
            return "News headlines"

        # Mount both apps
        main_app.mount("weather", weather_app)
        main_app.mount("news", news_app)

        # Check both are accessible
        tools = await main_app.get_tools()
        assert "weather_get_forecast" in tools
        assert "news_get_headlines" in tools

        # Call tools from both mounted servers
        result1 = await main_app._mcp_call_tool("weather_get_forecast", {})
        assert isinstance(result1[0], TextContent)
        assert result1[0].text == "Weather forecast"

        result2 = await main_app._mcp_call_tool("news_get_headlines", {})
        assert isinstance(result2[0], TextContent)
        assert result2[0].text == "News headlines"

    async def test_mount_same_prefix(self):
        """Test that mounting with the same prefix replaces the previous mount."""
        main_app = FastMCP("MainApp")
        first_app = FastMCP("FirstApp")
        second_app = FastMCP("SecondApp")

        @first_app.tool()
        def first_tool() -> str:
            return "First app tool"

        @second_app.tool()
        def second_tool() -> str:
            return "Second app tool"

        # Mount first app
        main_app.mount("api", first_app)
        tools = await main_app.get_tools()
        assert "api_first_tool" in tools

        # Mount second app with same prefix
        main_app.mount("api", second_app)
        tools = await main_app.get_tools()

        # First app's tool should no longer be accessible
        assert "api_first_tool" not in tools

        # Second app's tool should be accessible
        assert "api_second_tool" in tools


class TestDynamicChanges:
    """Test that changes to mounted servers are reflected dynamically."""

    async def test_adding_tool_after_mounting(self):
        """Test that tools added after mounting are accessible."""
        main_app = FastMCP("MainApp")
        sub_app = FastMCP("SubApp")

        # Mount the sub-app before adding any tools
        main_app.mount("sub", sub_app)

        # Initially, there should be no tools from sub_app
        tools = await main_app.get_tools()
        assert not any(key.startswith("sub_") for key in tools)

        # Add a tool to the sub-app after mounting
        @sub_app.tool()
        def dynamic_tool() -> str:
            return "Added after mounting"

        # The tool should be accessible through the main app
        tools = await main_app.get_tools()
        assert "sub_dynamic_tool" in tools

        # Call the dynamically added tool
        result = await main_app._mcp_call_tool("sub_dynamic_tool", {})
        assert isinstance(result[0], TextContent)
        assert result[0].text == "Added after mounting"

    async def test_removing_tool_after_mounting(self):
        """Test that tools removed from mounted servers are no longer accessible."""
        main_app = FastMCP("MainApp")
        sub_app = FastMCP("SubApp")

        @sub_app.tool()
        def temp_tool() -> str:
            return "Temporary tool"

        # Mount the sub-app
        main_app.mount("sub", sub_app)

        # Initially, the tool should be accessible
        tools = await main_app.get_tools()
        assert "sub_temp_tool" in tools

        # Remove the tool from sub_app
        sub_app._tool_manager._tools.pop("temp_tool")

        # The tool should no longer be accessible
        # Refresh the cache by clearing it
        main_app._cache.cache.clear()
        tools = await main_app.get_tools()
        assert "sub_temp_tool" not in tools


class TestResourcesAndTemplates:
    """Test mounting with resources and resource templates."""

    async def test_mount_with_resources(self):
        """Test mounting a server with resources."""
        main_app = FastMCP("MainApp")
        data_app = FastMCP("DataApp")

        @data_app.resource(uri="data://users")
        async def get_users():
            return ["user1", "user2"]

        # Mount the data app
        main_app.mount("data", data_app)

        # Resource should be accessible through main app
        resources = await main_app.get_resources()
        assert any("data+data://users" in str(uri) for uri in resources)

        async with Client(main_app) as client:
            resource = await client.read_resource("data+data://users")
            assert isinstance(resource[0], TextResourceContents)
            assert resource[0].text == '["user1", "user2"]'

    async def test_mount_with_resource_templates(self):
        """Test mounting a server with resource templates."""
        main_app = FastMCP("MainApp")
        user_app = FastMCP("UserApp")

        @user_app.resource(uri="users://{user_id}/profile")
        def get_user_profile(user_id: str) -> dict:
            return {"id": user_id, "name": f"User {user_id}"}

        # Mount the user app
        main_app.mount("api", user_app)

        # Template should be accessible through main app
        templates = await main_app.get_resource_templates()
        assert any("api+users://{user_id}/profile" in str(t) for t in templates)

        # Read from the template
        result = await main_app._mcp_read_resource("api+users://123/profile")
        assert isinstance(result[0], ReadResourceContents)
        profile = json.loads(result[0].content)
        assert profile["id"] == "123"
        assert profile["name"] == "User 123"

    async def test_adding_resource_after_mounting(self):
        """Test adding a resource after mounting."""
        main_app = FastMCP("MainApp")
        data_app = FastMCP("DataApp")

        # Mount the data app before adding resources
        main_app.mount("data", data_app)

        # Add a resource after mounting
        @data_app.resource(uri="data://config")
        def get_config():
            return {"version": "1.0"}

        # Resource should be accessible through main app
        resources = await main_app.get_resources()
        assert any("data+data://config" in str(uri) for uri in resources)

        # Read the resource
        result = await main_app._mcp_read_resource("data+data://config")
        assert isinstance(result[0], ReadResourceContents)
        config = json.loads(result[0].content)
        assert config["version"] == "1.0"


class TestPrompts:
    """Test mounting with prompts."""

    async def test_mount_with_prompts(self):
        """Test mounting a server with prompts."""
        main_app = FastMCP("MainApp")
        assistant_app = FastMCP("AssistantApp")

        @assistant_app.prompt()
        def greeting(name: str) -> str:
            return f"Hello, {name}!"

        # Mount the assistant app
        main_app.mount("assistant", assistant_app)

        # Prompt should be accessible through main app
        prompts = await main_app.get_prompts()
        assert "assistant_greeting" in prompts

        # Render the prompt
        result = await main_app._mcp_get_prompt("assistant_greeting", {"name": "World"})
        assert result.messages is not None
        # The message should contain our greeting text

    async def test_adding_prompt_after_mounting(self):
        """Test adding a prompt after mounting."""
        main_app = FastMCP("MainApp")
        assistant_app = FastMCP("AssistantApp")

        # Mount the assistant app before adding prompts
        main_app.mount("assistant", assistant_app)

        # Add a prompt after mounting
        @assistant_app.prompt()
        def farewell(name: str) -> str:
            return f"Goodbye, {name}!"

        # Prompt should be accessible through main app
        prompts = await main_app.get_prompts()
        assert "assistant_farewell" in prompts

        # Render the prompt
        result = await main_app._mcp_get_prompt("assistant_farewell", {"name": "World"})
        assert result.messages is not None
        # The message should contain our farewell text


class TestProxyServer:
    """Test mounting a proxy server."""

    async def test_mount_proxy_server(self):
        """Test mounting a proxy server."""
        # Create original server
        original_server = FastMCP("OriginalServer")

        @original_server.tool()
        def get_data(query: str) -> str:
            return f"Data for {query}"

        # Create proxy server
        proxy_server = FastMCP.from_client(
            Client(transport=FastMCPTransport(original_server))
        )

        # Mount proxy server
        main_app = FastMCP("MainApp")
        main_app.mount("proxy", proxy_server)

        # Tool should be accessible through main app
        tools = await main_app.get_tools()
        assert "proxy_get_data" in tools

        # Call the tool
        result = await main_app._mcp_call_tool("proxy_get_data", {"query": "test"})
        assert isinstance(result[0], TextContent)
        assert result[0].text == "Data for test"

    async def test_dynamically_adding_to_proxied_server(self):
        """Test that changes to the original server are reflected in the mounted proxy."""
        # Create original server
        original_server = FastMCP("OriginalServer")

        # Create proxy server
        proxy_server = FastMCP.from_client(
            Client(transport=FastMCPTransport(original_server))
        )

        # Mount proxy server
        main_app = FastMCP("MainApp")
        main_app.mount("proxy", proxy_server)

        # Add a tool to the original server
        @original_server.tool()
        def dynamic_data() -> str:
            return "Dynamic data"

        # Tool should be accessible through main app via proxy
        tools = await main_app.get_tools()
        assert "proxy_dynamic_data" in tools

        # Call the tool
        result = await main_app._mcp_call_tool("proxy_dynamic_data", {})
        assert isinstance(result[0], TextContent)
        assert result[0].text == "Dynamic data"

    async def test_proxy_server_with_resources(self):
        """Test mounting a proxy server with resources."""
        # Create original server
        original_server = FastMCP("OriginalServer")

        @original_server.resource(uri="config://settings")
        def get_config():
            return {"api_key": "12345"}

        # Create proxy server
        proxy_server = FastMCP.from_client(
            Client(transport=FastMCPTransport(original_server))
        )

        # Mount proxy server
        main_app = FastMCP("MainApp")
        main_app.mount("proxy", proxy_server)

        # Resource should be accessible through main app
        result = await main_app._mcp_read_resource("proxy+config://settings")
        assert isinstance(result[0], ReadResourceContents)
        config = json.loads(result[0].content)
        assert config["api_key"] == "12345"

    async def test_proxy_server_with_prompts(self):
        """Test mounting a proxy server with prompts."""
        # Create original server
        original_server = FastMCP("OriginalServer")

        @original_server.prompt()
        def welcome(name: str) -> str:
            return f"Welcome, {name}!"

        # Create proxy server
        proxy_server = FastMCP.from_client(
            Client(transport=FastMCPTransport(original_server))
        )

        # Mount proxy server
        main_app = FastMCP("MainApp")
        main_app.mount("proxy", proxy_server)

        # Prompt should be accessible through main app
        result = await main_app._mcp_get_prompt("proxy_welcome", {"name": "World"})
        assert result.messages is not None
        # The message should contain our welcome text
