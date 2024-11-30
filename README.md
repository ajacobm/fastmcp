# FastMCP

> **Note**: This is experimental software. The Model Context Protocol itself is only a few days old and the specification is still evolving.

A fast, pythonic way to build Model Context Protocol (MCP) servers.

Anthropic's new [Model Context Protocol](https://modelcontextprotocol.io) is powerful way to give broadcast new functionality and context to LLMs. However, developing MCP servers can be cumbersome. FastMCP provides a simple, intuitive interface for creating MCP servers in Python.

## Installation

MCP servers require you to use [uv](https://github.com/astral-sh/uv) as your dependency manager.


Install uv with brew:
```bash
brew install uv
```
*(Editor's note: I was unable to get MCP servers working unless uv was installed with brew.)*

Install FastMCP:
```bash
uv pip install fastmcp
```



## Quick Start

Here's a simple example that exposes your desktop directory as a resource and provides a basic addition tool:

```python
from pathlib import Path
from fastmcp import FastMCP

# Create server
mcp = FastMCP("Demo")

@mcp.resource("dir://desktop")
def desktop() -> list[str]:
    """List the files in the user's desktop"""
    desktop = Path.home() / "Desktop"
    return [str(f) for f in desktop.iterdir()]

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

if __name__ == "__main__":
    mcp.run()
```

## Features

### Resources

Resources are data sources that can be accessed by the LLM. They can be files, directories, or any other data source. Resources are defined using the `@resource` decorator:

```python
@mcp.resource("file://config.json")
def get_config() -> str:
    """Read the config file"""
    return Path("config.json").read_text()
```

### Tools

Tools are functions that can be called by the LLM. They are defined using the `@tool` decorator:

```python
@mcp.tool()
def calculate(x: int, y: int) -> int:
    """Perform a calculation"""
    return x + y
```

## Development

### Running the Dev Inspector

FastMCP includes a development server with the MCP Inspector for testing your server:

```bash
# Basic usage
fastmcp dev your_server.py

# Install package in editable mode from current directory
fastmcp dev your_server.py --with-editable .

# Install additional packages
fastmcp dev your_server.py --with pandas --with numpy

# Combine both
fastmcp dev your_server.py --with-editable . --with pandas --with numpy
```

The `--with` flag automatically includes `fastmcp` and any additional packages you specify. The `--with-editable` flag installs the package from the specified directory in editable mode, which is useful during development.

### Installing in Claude

To use your server with Claude Desktop:

```bash
# Basic usage
fastmcp install your_server.py --name "My Server"

# Install package in editable mode
fastmcp install your_server.py --with-editable .

# Install additional packages
fastmcp install your_server.py --with pandas --with numpy

# Combine options
fastmcp install your_server.py --with-editable . --with pandas --with numpy
```


FastMCP can be configured via environment variables with the prefix `FASTMCP_`:
