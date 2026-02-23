"""Policy enforcement endpoint"""
import fnmatch

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_agent
from app.database import get_db
from app.models.agent import Agent
from app.models.policy import Policy
from app.schemas.policy import EnforceRequest, EnforceResponse
from app.utils.logger import logger

router = APIRouter(prefix="/enforce", tags=["enforcement"])


def normalize_action(action: str) -> str:
    """
    Intelligently normalize action strings to verb:noun pattern.

    Supports multiple user-friendly input formats:
    - Standard: "read:file" → "read:file"
    - Spaces: "read file" → "read:file"
    - Hyphens: "read-file" → "read:file"
    - Underscores: "read_file" → "read:file"
    - CamelCase: "readFile" → "read:file"
    - Natural: "Read File" → "read:file"
    - Mixed: "Read-File" → "read:file"
    - Single word: "read" → "read" (for wildcard matching)
    - Wildcards preserved: "delete *" → "delete:*"

    Examples:
    - "read file" → "read:file"
    - "Read File" → "read:file"
    - "readFile" → "read:file"
    - "read-file" → "read:file"
    - "read_file" → "read:file"
    - "send email" → "send:email"
    - "query database" → "query:database"
    - "delete *" → "delete:*"
    - "read" → "read"
    """
    import re

    # Strip whitespace first
    action = action.strip()

    # If already in correct format (verb:noun), just lowercase and return
    if ":" in action:
        return action.lower()

    # Handle CamelCase BEFORE lowercasing by inserting space before capitals
    # e.g., "readFile" → "read File"
    action = re.sub(r'([a-z])([A-Z])', r'\1 \2', action)

    # Now lowercase everything
    action = action.lower()

    # Replace hyphens and underscores with spaces
    # e.g., "read-file" → "read file", "read_file" → "read file"
    action = action.replace("-", " ").replace("_", " ")

    # Split by whitespace and filter empty strings
    parts = [p for p in action.split() if p]

    # If single word, return as-is (for simple actions or wildcards)
    if len(parts) == 1:
        return parts[0]

    # If two or more words, join first two with colon
    # e.g., ["read", "file", "system"] → "read:file"
    # This handles cases like "send email notification" → "send:email"
    verb = parts[0]
    noun = parts[1]

    return f"{verb}:{noun}"


def matches_rule(action: str, resource: str, rule_action: str, rule_resource: str) -> bool:
    """
    Check if action/resource matches a policy rule

    Case-insensitive matching with wildcards and flexible patterns:
    - "read" matches "read:*" (simple action matches pattern)
    - "Read:File" matches "read:*" (case-insensitive)
    - "READ" matches "read" (exact match, case-insensitive)
    - resource: "s3://bucket/*" matches any resource in bucket
    """
    # Normalize both action and rule to lowercase for case-insensitive comparison
    normalized_action = normalize_action(action)
    normalized_rule = normalize_action(rule_action)

    # Direct match with wildcards
    if fnmatch.fnmatch(normalized_action, normalized_rule):
        # Check resource if rule has resource constraint
        if not rule_resource or rule_resource == "*":
            return True
        return fnmatch.fnmatch(resource.lower() if resource else "", rule_resource.lower())

    # If action is simple (no colon) and rule has pattern (has colon), try matching base verb
    # e.g., "read" should match "read:*"
    if ":" not in normalized_action and ":" in normalized_rule:
        rule_verb = normalized_rule.split(":")[0]
        if normalized_action == rule_verb or fnmatch.fnmatch(normalized_action, rule_verb):
            # Check resource constraint
            if not rule_resource or rule_resource == "*":
                return True
            return fnmatch.fnmatch(resource.lower() if resource else "", rule_resource.lower())

    return False


def enforce_policy(agent_id: str, action: str, resource: str, db: Session) -> tuple[bool, str]:
    """
    Enforce policy for an agent action

    Returns:
        Tuple of (allowed: bool, reason: str)

    Policy logic:
    1. If no policy exists, deny by default
    2. Check deny rules first - if matched, deny
    3. Check allow rules - if matched, allow
    4. If no rules match, deny by default
    """
    # Get policy
    policy = db.query(Policy).filter(Policy.agent_id == agent_id).first()

    if not policy:
        return False, "No policy defined for agent (default deny)"

    # Check deny rules first
    for rule in policy.deny_rules:
        if matches_rule(action, resource or "", rule.get("action", ""), rule.get("resource", "*")):
            return False, f"Denied by rule: {rule.get('action')} on {rule.get('resource', '*')}"

    # Check allow rules
    for rule in policy.allow_rules:
        if matches_rule(action, resource or "", rule.get("action", ""), rule.get("resource", "*")):
            return True, f"Allowed by rule: {rule.get('action')} on {rule.get('resource', '*')}"

    # Default deny
    return False, "No matching allow rule (default deny)"


@router.post("", response_model=EnforceResponse)
def enforce(
    request: EnforceRequest,
    agent: Agent = Depends(require_agent),
    db: Session = Depends(get_db)
):
    """
    Check if agent is allowed to perform an action (Agent auth)

    Returns whether action is allowed and explanation
    """
    allowed, reason = enforce_policy(
        agent_id=agent.agent_id,
        action=request.action,
        resource=request.resource or "",
        db=db
    )

    logger.info(
        f"Enforcement check: {agent.agent_id} - {request.action} - {'allowed' if allowed else 'denied'}",
        extra={
            "agent_id": agent.agent_id,
            "action": request.action,
            "resource": request.resource,
            "allowed": allowed
        }
    )

    return EnforceResponse(allowed=allowed, reason=reason)


def enforce_or_raise(
    agent_id: str,
    action: str,
    resource: str,
    db: Session
) -> None:
    """
    Helper function to enforce policy and raise exception if denied

    Raises:
        HTTPException: If action is not allowed
    """
    allowed, reason = enforce_policy(agent_id, action, resource, db)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Action not allowed: {reason}"
        )
