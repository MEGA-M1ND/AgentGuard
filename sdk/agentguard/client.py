"""AgentGuard client implementation"""
import time
from typing import Any, Dict, List, Optional

import requests


class AgentGuardClient:
    """Client for interacting with AgentGuard API.

    Authentication is handled transparently:
    - Pass ``admin_key`` and/or ``agent_key`` at construction (same as before).
    - On the first request the client exchanges the static key for a signed JWT
      via ``POST /token`` and caches it.
    - The JWT is refreshed automatically 60 seconds before expiry.
    - All API calls use ``Authorization: Bearer <JWT>``; the static key is never
      sent to any endpoint other than ``/token``.

    Backward-compatible: existing code that passes ``admin_key=`` / ``agent_key=``
    requires no changes.
    """

    def __init__(
        self,
        base_url: str,
        admin_key: Optional[str] = None,
        agent_key: Optional[str] = None,
    ):
        """
        Initialize AgentGuard client.

        Args:
            base_url:  Base URL of AgentGuard backend (e.g. ``http://localhost:8000``).
            admin_key: Admin API key — used to exchange for an admin JWT.
            agent_key: Agent API key (``agk_...``) — used to exchange for an agent JWT.
        """
        self.base_url = base_url.rstrip("/")
        self.admin_key = admin_key
        self.agent_key = agent_key
        self.session = requests.Session()

        # JWT cache — keyed by auth_type ("admin" | "agent")
        self._jwt_token: Dict[str, Optional[str]] = {"admin": None, "agent": None}
        self._jwt_expires_at: Dict[str, float] = {"admin": 0.0, "agent": 0.0}

    # ---------------------------------------------------------------------------
    # Internal JWT management
    # ---------------------------------------------------------------------------

    def _ensure_token(self, auth_type: str) -> str:
        """Return a valid JWT for the given auth_type, refreshing if needed.

        Args:
            auth_type: ``"admin"`` or ``"agent"``.

        Returns:
            A valid JWT string.

        Raises:
            ValueError: If the required static key is not set.
            requests.HTTPError: If the /token exchange fails.
        """
        # Refresh if absent or within 60 s of expiry
        if (
            self._jwt_token[auth_type] is None
            or time.time() >= self._jwt_expires_at[auth_type] - 60
        ):
            self._jwt_token[auth_type] = None  # invalidate before refreshing

            if auth_type == "admin":
                if not self.admin_key:
                    raise ValueError("admin_key required for this operation")
                payload = {"admin_key": self.admin_key}
            else:
                if not self.agent_key:
                    raise ValueError("agent_key required for this operation")
                payload = {"agent_key": self.agent_key}

            url = f"{self.base_url}/token"
            resp = self.session.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

            self._jwt_token[auth_type] = data["access_token"]
            self._jwt_expires_at[auth_type] = time.time() + data["expires_in"]

        return self._jwt_token[auth_type]  # type: ignore[return-value]

    def _request(
        self,
        method: str,
        endpoint: str,
        auth_type: str = "admin",
        **kwargs: Any,
    ) -> requests.Response:
        """Make an authenticated HTTP request to the AgentGuard API.

        Obtains a JWT via ``_ensure_token`` and injects it as a Bearer token.

        Args:
            method:    HTTP method (``GET``, ``POST``, etc.).
            endpoint:  API path (e.g. ``/agents``).
            auth_type: ``"admin"`` or ``"agent"``.
            **kwargs:  Forwarded to ``requests.Session.request``.

        Returns:
            The response object.

        Raises:
            ValueError: If the required key is not configured.
            requests.HTTPError: On non-2xx responses.
        """
        token = self._ensure_token(auth_type)

        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        response = self.session.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response

    def revoke_token(self, auth_type: str = "agent") -> None:
        """Revoke the current JWT for the given auth type.

        Calls ``POST /token/revoke`` and clears the local token cache so
        the next request will obtain a fresh token.

        Args:
            auth_type: ``"admin"`` or ``"agent"`` (default ``"agent"``).
        """
        token = self._jwt_token.get(auth_type)
        if not token:
            return  # nothing to revoke

        url = f"{self.base_url}/token/revoke"
        headers = {"Authorization": f"Bearer {token}"}
        resp = self.session.post(url, headers=headers)
        resp.raise_for_status()

        # Clear local cache
        self._jwt_token[auth_type] = None
        self._jwt_expires_at[auth_type] = 0.0

    # ========== Admin Methods ==========

    def create_agent(
        self,
        name: str,
        owner_team: str,
        environment: str,
    ) -> Dict[str, Any]:
        """
        Create a new agent with API key (Admin only).

        Returns agent details including API key (only shown once).
        """
        response = self._request(
            "POST",
            "/agents",
            auth_type="admin",
            json={"name": name, "owner_team": owner_team, "environment": environment},
        )
        return response.json()

    def list_agents(
        self,
        environment: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List all agents (Admin only)."""
        params: Dict[str, Any] = {"skip": skip, "limit": limit}
        if environment:
            params["environment"] = environment
        response = self._request("GET", "/agents", auth_type="admin", params=params)
        return response.json()

    def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get agent by ID (Admin only)."""
        response = self._request("GET", f"/agents/{agent_id}", auth_type="admin")
        return response.json()

    def delete_agent(self, agent_id: str) -> None:
        """Delete agent (Admin only)."""
        self._request("DELETE", f"/agents/{agent_id}", auth_type="admin")

    def set_policy(
        self,
        agent_id: str,
        allow: List[Dict[str, str]],
        deny: Optional[List[Dict[str, str]]] = None,
        require_approval: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Set or update policy for an agent (Admin only).

        Args:
            agent_id:         Agent ID.
            allow:            List of allow rules ``[{action, resource}]``.
            deny:             List of deny rules ``[{action, resource}]``.
            require_approval: List of rules requiring human approval.

        Returns:
            Policy details.
        """
        response = self._request(
            "PUT",
            f"/agents/{agent_id}/policy",
            auth_type="admin",
            json={
                "allow": allow,
                "deny": deny or [],
                "require_approval": require_approval or [],
            },
        )
        return response.json()

    def get_policy(self, agent_id: str) -> Dict[str, Any]:
        """Get policy for an agent (Admin only)."""
        response = self._request("GET", f"/agents/{agent_id}/policy", auth_type="admin")
        return response.json()

    # ---- Approval Management (Admin) ----

    def list_approvals(
        self,
        status: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        List approval requests (Admin only).

        Args:
            status:   Filter by status: ``'pending'``, ``'approved'``, ``'denied'``.
            agent_id: Filter by agent ID.
            limit:    Maximum number of results.
            offset:   Number of results to skip.

        Returns:
            Dict with ``'items'`` list, ``'total'`` count, ``'pending_count'``.
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        if agent_id:
            params["agent_id"] = agent_id
        response = self._request("GET", "/approvals", auth_type="admin", params=params)
        return response.json()

    def get_approval(self, approval_id: str) -> Dict[str, Any]:
        """
        Get a single approval request by ID (Admin only).

        Returns:
            Approval request with current status.
        """
        response = self._request("GET", f"/approvals/{approval_id}", auth_type="admin")
        return response.json()

    def approve_request(self, approval_id: str, reason: str = "") -> Dict[str, Any]:
        """
        Approve a pending approval request (Admin only).

        Args:
            approval_id: Approval request UUID.
            reason:      Optional reason for the decision.
        """
        response = self._request(
            "POST",
            f"/approvals/{approval_id}/approve",
            auth_type="admin",
            json={"reason": reason},
        )
        return response.json()

    def deny_request(self, approval_id: str, reason: str = "") -> Dict[str, Any]:
        """
        Deny a pending approval request (Admin only).

        Args:
            approval_id: Approval request UUID.
            reason:      Reason for denial.
        """
        response = self._request(
            "POST",
            f"/approvals/{approval_id}/deny",
            auth_type="admin",
            json={"reason": reason},
        )
        return response.json()

    # ========== Agent Methods ==========

    def enforce(
        self,
        action: str,
        resource: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Check if action is allowed (Agent auth).

        Args:
            action:   Action to check (e.g. ``'read:file'``).
            resource: Resource to check.
            context:  Additional context.

        Returns:
            Dictionary with:
              - ``allowed`` (bool): True only when status == ``'allowed'``
              - ``status`` (str): ``'allowed'``, ``'denied'``, or ``'pending'``
              - ``reason`` (str): Explanation of the decision
              - ``approval_id`` (str | None): UUID when status == ``'pending'``

        Example::

            result = client.enforce("delete:database", resource="production/users")
            if result["status"] == "pending":
                print(f"Waiting for human approval: {result['approval_id']}")
                final = client.wait_for_approval(result["approval_id"])
            elif result["allowed"]:
                print("Action allowed, proceeding...")
            else:
                print(f"Denied: {result['reason']}")
        """
        response = self._request(
            "POST",
            "/enforce",
            auth_type="agent",
            json={"action": action, "resource": resource, "context": context},
        )
        return response.json()

    def poll_approval(self, approval_id: str) -> Dict[str, Any]:
        """
        Get approval status for an approval created by this agent (Agent auth).

        Unlike ``get_approval`` (which requires admin credentials), this method
        uses the agent's own JWT and only works for approvals the agent created.
        No ``admin_key`` is needed.

        Args:
            approval_id: Approval request UUID from ``enforce()`` response.

        Returns:
            Dict with ``status``, ``decision_reason``, ``decision_by``, ``decision_at``.
        """
        response = self._request("GET", f"/enforce/approval/{approval_id}", auth_type="agent")
        return response.json()

    def wait_for_approval(
        self,
        approval_id: str,
        timeout: int = 300,
        poll_interval: int = 3,
    ) -> Dict[str, Any]:
        """
        Block until a human approves or denies the request.

        Polls using agent auth (``poll_approval``) if ``agent_key`` is set —
        no admin credentials required. Falls back to admin auth (``get_approval``)
        if only ``admin_key`` is configured.

        Args:
            approval_id:   Approval request UUID from ``enforce()`` response.
            timeout:       Max seconds to wait (default 300 s / 5 minutes).
            poll_interval: Seconds between each poll (default 3 s).

        Returns:
            Final approval dict with status ``'approved'`` or ``'denied'``.

        Raises:
            TimeoutError:  If no decision within ``timeout`` seconds.
            ValueError:    If neither ``agent_key`` nor ``admin_key`` is set.

        Example::

            result = client.enforce("delete:database")
            if result["status"] == "pending":
                try:
                    decision = client.wait_for_approval(result["approval_id"], timeout=120)
                    if decision["status"] == "approved":
                        proceed_with_delete()
                    else:
                        print("Request denied:", decision["decision_reason"])
                except TimeoutError:
                    print("No response within 2 minutes")
        """
        if not self.agent_key and not self.admin_key:
            raise ValueError(
                "Either agent_key or admin_key is required to poll approval status."
            )

        deadline = time.time() + timeout
        while time.time() < deadline:
            # Prefer agent auth (polls own approvals without admin creds)
            if self.agent_key:
                approval = self.poll_approval(approval_id)
            else:
                approval = self.get_approval(approval_id)
            if approval["status"] != "pending":
                return approval
            time.sleep(poll_interval)

        raise TimeoutError(
            f"Approval {approval_id} was not decided within {timeout} seconds. "
            "The request is still pending in the AgentGuard approvals queue."
        )

    def log_action(
        self,
        action: str,
        allowed: bool,
        result: str,
        resource: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Submit an audit log entry (Agent auth).

        Args:
            action:     Action performed.
            allowed:    Whether action was allowed.
            result:     Result of action (``'success'`` or ``'error'``).
            resource:   Resource accessed.
            context:    Additional context.
            metadata:   Additional metadata.
            request_id: Request ID for correlation.
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
                "request_id": request_id,
            },
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
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Query audit logs (Admin or Agent auth).

        Admin can query all logs; agents can only query their own.
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
        response = self._request("GET", "/logs", auth_type=auth_type, params=params)
        return response.json()
