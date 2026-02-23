"""AgentGuard client implementation"""
from typing import Any, Dict, List, Optional

import requests


class AgentGuardClient:
    """Client for interacting with AgentGuard API"""

    def __init__(
        self,
        base_url: str,
        admin_key: Optional[str] = None,
        agent_key: Optional[str] = None
    ):
        """
        Initialize AgentGuard client

        Args:
            base_url: Base URL of AgentGuard backend
            admin_key: Admin API key (for management operations)
            agent_key: Agent API key (for enforcement and logging)
        """
        self.base_url = base_url.rstrip("/")
        self.admin_key = admin_key
        self.agent_key = agent_key
        self.session = requests.Session()

    def _request(
        self,
        method: str,
        endpoint: str,
        auth_type: str = "admin",
        **kwargs
    ) -> requests.Response:
        """
        Make HTTP request to AgentGuard API

        Args:
            method: HTTP method
            endpoint: API endpoint
            auth_type: 'admin' or 'agent'
            **kwargs: Additional arguments for requests

        Returns:
            Response object

        Raises:
            ValueError: If required authentication key is missing
            requests.HTTPError: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop("headers", {})

        # Add authentication header
        if auth_type == "admin":
            if not self.admin_key:
                raise ValueError("Admin key required for this operation")
            headers["X-Admin-Key"] = self.admin_key
        elif auth_type == "agent":
            if not self.agent_key:
                raise ValueError("Agent key required for this operation")
            headers["X-Agent-Key"] = self.agent_key

        response = self.session.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response

    # ========== Admin Methods ==========

    def create_agent(
        self,
        name: str,
        owner_team: str,
        environment: str
    ) -> Dict[str, Any]:
        """
        Create a new agent (Admin only)

        Args:
            name: Agent name
            owner_team: Team that owns this agent
            environment: Environment (dev, stage, prod)

        Returns:
            Agent details including API key (only shown once)
        """
        response = self._request(
            "POST",
            "/agents",
            auth_type="admin",
            json={
                "name": name,
                "owner_team": owner_team,
                "environment": environment
            }
        )
        return response.json()

    def list_agents(
        self,
        environment: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all agents (Admin only)

        Args:
            environment: Filter by environment
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of agents
        """
        params = {"skip": skip, "limit": limit}
        if environment:
            params["environment"] = environment

        response = self._request(
            "GET",
            "/agents",
            auth_type="admin",
            params=params
        )
        return response.json()

    def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Get agent by ID (Admin only)

        Args:
            agent_id: Agent ID

        Returns:
            Agent details
        """
        response = self._request(
            "GET",
            f"/agents/{agent_id}",
            auth_type="admin"
        )
        return response.json()

    def delete_agent(self, agent_id: str) -> None:
        """
        Delete agent (Admin only)

        Args:
            agent_id: Agent ID
        """
        self._request(
            "DELETE",
            f"/agents/{agent_id}",
            auth_type="admin"
        )

    def set_policy(
        self,
        agent_id: str,
        allow: List[Dict[str, str]],
        deny: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Set or update policy for an agent (Admin only)

        Args:
            agent_id: Agent ID
            allow: List of allow rules
            deny: List of deny rules

        Returns:
            Policy details
        """
        response = self._request(
            "PUT",
            f"/agents/{agent_id}/policy",
            auth_type="admin",
            json={
                "allow": allow,
                "deny": deny or []
            }
        )
        return response.json()

    def get_policy(self, agent_id: str) -> Dict[str, Any]:
        """
        Get policy for an agent (Admin only)

        Args:
            agent_id: Agent ID

        Returns:
            Policy details
        """
        response = self._request(
            "GET",
            f"/agents/{agent_id}/policy",
            auth_type="admin"
        )
        return response.json()

    # ========== Agent Methods ==========

    def enforce(
        self,
        action: str,
        resource: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Check if action is allowed (Agent auth)

        Args:
            action: Action to check
            resource: Resource to check
            context: Additional context

        Returns:
            Dictionary with 'allowed' (bool) and 'reason' (str)
        """
        response = self._request(
            "POST",
            "/enforce",
            auth_type="agent",
            json={
                "action": action,
                "resource": resource,
                "context": context
            }
        )
        return response.json()

    def log_action(
        self,
        action: str,
        allowed: bool,
        result: str,
        resource: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit an audit log entry (Agent auth)

        Args:
            action: Action performed
            allowed: Whether action was allowed
            result: Result of action ('success' or 'error')
            resource: Resource accessed
            context: Additional context
            metadata: Additional metadata
            request_id: Request ID for correlation

        Returns:
            Log details
        """
        response = self._request(
            "POST",
            "/logs",
            auth_type="agent",
            json={
                "action": action,
                "resource": resource,
                "context": context,
                "allowed": allowed,
                "result": result,
                "metadata": metadata,
                "request_id": request_id
            }
        )
        return response.json()

    def query_logs(
        self,
        agent_id: Optional[str] = None,
        action: Optional[str] = None,
        allowed: Optional[bool] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Query audit logs (Admin or Agent auth)

        - Admin can query all logs
        - Agent can only query their own logs

        Args:
            agent_id: Filter by agent ID (admin only)
            action: Filter by action
            allowed: Filter by allowed status
            start_time: Filter by start time (ISO 8601)
            end_time: Filter by end time (ISO 8601)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of logs
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if agent_id:
            params["agent_id"] = agent_id
        if action:
            params["action"] = action
        if allowed is not None:
            params["allowed"] = str(allowed).lower()
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time

        auth_type = "admin" if self.admin_key else "agent"
        response = self._request(
            "GET",
            "/logs",
            auth_type=auth_type,
            params=params
        )
        return response.json()
