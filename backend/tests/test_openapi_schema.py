"""OpenAPI schema regression tests (hotfix: future annotations in routes).

FastAPI inspects route annotations through decorator wrappers whose
module globals cannot resolve stringified models. A route module using
``from __future__ import annotations`` therefore silently demotes body
models to query params and breaks ``GET /openapi.json`` with a
PydanticUserError at runtime — while every direct-invocation unit test
keeps passing. Building the real app and generating the schema is the
only faithful gate.
"""

import pytest


@pytest.fixture(scope="module")
def openapi_spec():
    """Build the production app once and generate its OpenAPI schema."""
    from main import create_app

    return create_app().openapi()


class TestOpenApiSchema:
    def test_schema_generates(self, openapi_spec):
        """Schema generation must not raise (previously PydanticUserError)."""
        assert len(openapi_spec["paths"]) > 100

    def test_public_leads_post_takes_a_body(self, openapi_spec):
        """Interest submission binds a JSON body, not query params."""
        operation = openapi_spec["paths"]["/api/v1/public/leads"]["post"]
        assert "parameters" not in operation
        body_ref = operation["requestBody"]["content"]["application/json"]["schema"][
            "$ref"
        ]
        assert "InterestLeadCreate" in body_ref

    def test_escalation_write_endpoints_take_bodies(self, openapi_spec):
        """Escalation create/patch bind JSON bodies, not query params."""
        collection = openapi_spec["paths"]["/api/v1/organizations/{org_id}/escalations"]
        post = collection["post"]
        assert post["requestBody"]["content"]["application/json"]["schema"][
            "$ref"
        ].endswith("EscalationCreate")
        assert "body" not in [param.get("name") for param in post.get("parameters", [])]
        item = openapi_spec["paths"][
            "/api/v1/organizations/{org_id}/escalations/{escalation_id}"
        ]
        assert "body" not in [
            param.get("name") for param in item["patch"].get("parameters", [])
        ]
