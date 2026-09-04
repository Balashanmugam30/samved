# SAMVED Docker MCP Runbook

This runbook covers configuring, managing, and verifying the **Docker Model Context Protocol (MCP) Toolkit** for SAMVED development and agentic tool integration.

---

## 1. Overview of Docker MCP Toolkit

The Docker MCP Toolkit allows local AI agents, IDEs, and CLI tools to discover, configure, and communicate with specialized MCP server containers safely isolated within Docker.

---

## 2. Docker MCP CLI Commands

### 2.1 Checking Version and Help
```bash
docker mcp --help
```

### 2.2 Profile Management
Profiles group related MCP servers and tool configurations.

```bash
# List all active MCP profiles
docker mcp profile list

# Create the dedicated SAMVED development profile
docker mcp profile create --name samved-dev

# View details and configured servers of the samved-dev profile
docker mcp profile show samved_dev
```

### 2.3 Adding Servers & Catalogs
You can attach MCP servers to the `samved_dev` profile:
```bash
# Add an OCI-packaged MCP server
docker mcp profile server add samved_dev docker://<server-image>:latest

# View server list in profile
docker mcp profile server list samved_dev
```

---

## 3. Connecting to AI Coding Clients

The Docker MCP Toolkit supports connecting to AI coding assistants:
- Cursor
- VS Code
- Gemini / Claude Desktop

```bash
# Connect samved_dev profile to client
docker mcp profile config samved_dev --connect cursor
```
