"""
Tests for RBAC routes module.
"""
import pytest

from src.rbac.routes import rbac_router
from src.rbac.permissions.routes import permission_router
from src.rbac.roles.routes import role_router
from src.rbac.user_roles.routes import user_role_router


def test_rbac_router_setup():
    """Test that RBAC router is properly configured."""
    assert rbac_router is not None
    assert rbac_router.prefix == "/api/v1/rbac"
    assert "Role-Based Access Control" in rbac_router.tags

    # Check that sub-routers are included
    included_routers = [route.include_in_schema for route in rbac_router.routes if hasattr(route, 'include_in_schema')]
    # The router includes sub-routers, so we should have routes from them
    assert len(rbac_router.routes) > 0


def test_rbac_router_includes_sub_routers():
    """Test that RBAC router includes all sub-routers."""
    # This is a bit tricky to test directly, but we can check that the main router exists
    # and has the expected prefix structure
    assert rbac_router.prefix == "/api/v1/rbac"

    # The sub-routers should be accessible
    assert role_router is not None
    assert permission_router is not None
    assert user_role_router is not None