# MCP JWT Authentication Guide

This guide explains how to configure JWT Bearer authentication for the LLM Task Manager MCP server.

## Overview

The MCP server requires JWT Bearer authentication for all requests. The JWT token must be passed in the `Authorization` header:

```
Authorization: Bearer <your_jwt_token>
```

## Quick Start

### 1. Generate a JWT Token

Use the provided script to generate a JWT token:

```bash
cd llm-task-manager

# Generate admin token (30 days expiration)
python scripts/generate_mcp_token.py --user-id "admin@example.com" --role admin

# Generate contributor token (7 days expiration)
python scripts/generate_mcp_token.py --user-id "alice" --role contributor --expires 7

# Generate token with JSON output for quick copy-paste
python scripts/generate_mcp_token.py --user-id "john" --role contributor --json
```

### 2. Update MCP Configuration

Add the token to your MCP configuration file:

**For VS Code (`.vscode/mcp.json`):**

```json
{
  "servers": {
    "llmTaskManager": {
      "type": "sse",
      "url": "https://llm-task-manager-mcp-1086023562571.europe-west1.run.app/sse",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN_HERE"
      }
    }
  }
}
```

**For Claude Desktop (`claude_desktop_config.json`):**

```json
{
  "mcpServers": {
    "llm-task-manager": {
      "url": "https://llm-task-manager-mcp-1086023562571.europe-west1.run.app/sse",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN_HERE"
      }
    }
  }
}
```

### 3. Test the Connection

Test that authentication works:

```bash
# With authentication
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  https://llm-task-manager-mcp-1086023562571.europe-west1.run.app/sse

# Without authentication (should return 401)
curl https://llm-task-manager-mcp-1086023562571.europe-west1.run.app/sse
```

## User Roles and Permissions

The system supports three roles with different permission levels:

### Admin
- Full CRUD access to all resources
- Can create and close sprints
- Can manage project configuration
- Can delete resources

Permissions:
- `projects:*`, `epics:*`, `stories:*`, `sprints:*`, `comments:*`, `documents:*`

### Contributor (Default)
- Read access to projects, epics, sprints
- Create and update stories
- Create comments and documents
- Cannot delete resources or manage sprints

Permissions:
- `projects:read`
- `epics:read`
- `stories:create`, `stories:read`, `stories:update`
- `sprints:read`
- `comments:create`, `comments:read`
- `documents:create`, `documents:read`

### Viewer
- Read-only access to all resources
- Cannot create, update, or delete anything

Permissions:
- `projects:read`, `epics:read`, `stories:read`, `sprints:read`, `comments:read`, `documents:read`

## Token Structure

JWT tokens include the following claims:

```json
{
  "sub": "user@example.com",          // User identifier
  "role": "contributor",               // User role
  "permissions": ["stories:create"],   // Array of permissions
  "type": "mcp",                       // Token type marker
  "exp": 1234567890                    // Expiration timestamp
}
```

## Security Best Practices

### Token Storage

- **Never commit tokens to version control**
- Store tokens securely (e.g., in environment variables or secret managers)
- Use different tokens for different environments (dev, staging, prod)

### Token Rotation

- Tokens expire after the specified duration (default: 30 days)
- Regenerate tokens before expiration to avoid service interruptions
- Revoke and regenerate tokens if compromised

### Environment Variables

For local development, you can disable authentication:

```bash
export MCP_DISABLE_AUTH=true
python -m mcp_server --transport sse
```

**⚠️ Warning:** Never disable authentication in production!

## Troubleshooting

### 401 Unauthorized

**Problem:** Request returns `401 Unauthorized`

**Solutions:**
1. Verify the token is correctly copied (no extra spaces or newlines)
2. Check that the token hasn't expired
3. Ensure the `Authorization` header format is correct: `Bearer <token>`
4. Verify the JWT_SECRET_KEY environment variable matches between token generation and server

### Token Expired

**Problem:** Token worked before but now returns `401`

**Solution:** Generate a new token with the script above

### Invalid Token Format

**Problem:** Error message "Invalid authentication scheme"

**Solution:** Ensure the header format is `Authorization: Bearer <token>` (with space after "Bearer")

## Advanced Configuration

### Custom Token Expiration

```bash
# 1 day
python scripts/generate_mcp_token.py --user-id "user" --expires 1

# 90 days
python scripts/generate_mcp_token.py --user-id "user" --expires 90
```

### Programmatic Token Generation

```python
from app.security import create_access_token
from datetime import timedelta

token = create_access_token(
    data={
        "sub": "user@example.com",
        "role": "admin",
        "permissions": ["*"],
        "type": "mcp",
    },
    expires_delta=timedelta(days=30)
)
```

### Multiple MCP Clients

If you use multiple MCP clients (Claude Desktop, VS Code, Cursor), you can:

1. **Use the same token** across all clients (simpler)
2. **Generate separate tokens** for each client (better audit trail)

For separate tokens, use different user IDs:

```bash
python scripts/generate_mcp_token.py --user-id "claude-desktop" --role admin
python scripts/generate_mcp_token.py --user-id "vscode" --role contributor
```

## Cloud Deployment

When deploying to Google Cloud Run, ensure the JWT_SECRET_KEY is properly configured:

```bash
# Store secret
echo -n "your-secret-key" | gcloud secrets create jwt-secret --data-file=-

# Deploy with secret
gcloud run deploy llm-task-manager-mcp \
  --set-secrets="JWT_SECRET_KEY=jwt-secret:latest" \
  ...
```

## API Reference

### Authentication Middleware

The MCP server uses `AuthMiddleware` to validate JWT tokens on every request:

```python
# From mcp_server/auth.py
async def verify_jwt_token(request: Request) -> dict:
    """Verify JWT token from Authorization header."""
```

### Headers Required

```
Authorization: Bearer <jwt_token>
```

### Response Codes

- `200 OK` - Authentication successful
- `401 Unauthorized` - Missing, invalid, or expired token
- `403 Forbidden` - Valid token but insufficient permissions

## Related Files

- [`mcp_server/auth.py`](../llm-task-manager/mcp_server/auth.py) - Authentication middleware
- [`mcp_server/server.py`](../llm-task-manager/mcp_server/server.py) - MCP server with auth
- [`app/security.py`](../llm-task-manager/app/security.py) - JWT utilities
- [`scripts/generate_mcp_token.py`](../llm-task-manager/scripts/generate_mcp_token.py) - Token generation script

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify JWT_SECRET_KEY is consistent across environments
3. Check Cloud Run logs for detailed error messages
