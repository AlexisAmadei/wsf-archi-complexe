#!/usr/bin/env python3
"""
Generate JWT tokens for MCP authentication.

This script creates JWT tokens that can be used in MCP client configurations
to authenticate with the LLM Task Manager MCP server.

Usage:
    python scripts/generate_mcp_token.py --user-id "user@example.com" --role "admin"
    python scripts/generate_mcp_token.py --user-id "alice" --role "contributor" --expires 7
"""

import argparse
import sys
from datetime import timedelta
from pathlib import Path

# Add parent directory to Python path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.security import create_access_token


def generate_token(user_id: str, role: str = "contributor", expires_days: int = 30) -> str:
    """
    Generate a JWT token for MCP authentication.

    Args:
        user_id: User identifier (email or username)
        role: User role (admin, contributor, viewer)
        expires_days: Token expiration in days

    Returns:
        JWT token string
    """
    # Define permissions based on role
    permissions_map = {
        "admin": [
            "projects:create",
            "projects:read",
            "projects:update",
            "projects:delete",
            "epics:*",
            "stories:*",
            "sprints:*",
            "comments:*",
            "documents:*",
        ],
        "contributor": [
            "projects:read",
            "epics:read",
            "stories:create",
            "stories:read",
            "stories:update",
            "sprints:read",
            "comments:create",
            "comments:read",
            "documents:create",
            "documents:read",
        ],
        "viewer": [
            "projects:read",
            "epics:read",
            "stories:read",
            "sprints:read",
            "comments:read",
            "documents:read",
        ],
    }

    # Create token payload
    payload = {
        "sub": user_id,
        "role": role,
        "permissions": permissions_map.get(role, permissions_map["contributor"]),
        "type": "mcp",  # Mark as MCP token
    }

    # Generate token
    token = create_access_token(
        data=payload,
        expires_delta=timedelta(days=expires_days),
    )

    return token


def main():
    parser = argparse.ArgumentParser(
        description="Generate JWT tokens for MCP authentication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate admin token for 30 days (default)
  python scripts/generate_mcp_token.py --user-id "admin@example.com" --role admin

  # Generate contributor token for 7 days
  python scripts/generate_mcp_token.py --user-id "alice" --role contributor --expires 7

  # Generate viewer token
  python scripts/generate_mcp_token.py --user-id "john" --role viewer
        """,
    )

    parser.add_argument(
        "--user-id",
        required=True,
        help="User identifier (email or username)",
    )

    parser.add_argument(
        "--role",
        choices=["admin", "contributor", "viewer"],
        default="contributor",
        help="User role (default: contributor)",
    )

    parser.add_argument(
        "--expires",
        type=int,
        default=30,
        help="Token expiration in days (default: 30)",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format for mcp.json",
    )

    args = parser.parse_args()

    # Generate token
    token = generate_token(
        user_id=args.user_id,
        role=args.role,
        expires_days=args.expires,
    )

    # Output
    if args.json:
        print(f"""{{
  "servers": {{
    "llmTaskManager": {{
      "type": "sse",
      "url": "https://llm-task-manager-mcp-1086023562571.europe-west1.run.app/sse",
      "headers": {{
        "Authorization": "Bearer {token}"
      }}
    }}
  }}
}}""")
    else:
        print("\n" + "=" * 80)
        print(f"JWT Token for MCP Authentication")
        print("=" * 80)
        print(f"\nUser ID:   {args.user_id}")
        print(f"Role:      {args.role}")
        print(f"Expires:   {args.expires} days")
        print("\n" + "-" * 80)
        print(f"Token:\n{token}")
        print("-" * 80)
        print("\n✓ Add this to your .vscode/mcp.json:")
        print("""
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
        """.replace("YOUR_TOKEN_HERE", token))
        print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
