"""Tests for the legal.documents_updated notification template registry entry."""

from src.notifications.templates import (
    LEGAL_DOCUMENTS_UPDATED_TEMPLATE,
    TEMPLATE_REGISTRY,
)

LEGAL_EVENT_KEY = "legal.documents_updated"
EXPECTED_VARIABLES = [
    "user_name",
    "document_title",
    "version_number",
    "summary_of_changes",
    "document_url",
    "app_name",
]


class TestLegalDocumentsUpdatedTemplate:
    def test_registry_entry_is_registered(self):
        assert LEGAL_EVENT_KEY in TEMPLATE_REGISTRY

    def test_subject_renders_document_title_and_app_name(self):
        entry = TEMPLATE_REGISTRY[LEGAL_EVENT_KEY]
        assert entry["subject"] == "Updated {document_title} - {app_name}"
        assert entry["name"] == "Legal Documents Updated"

    def test_variable_list_matches_outbox_payload(self):
        """The registry variables must exactly match what the outbox fills."""
        entry = TEMPLATE_REGISTRY[LEGAL_EVENT_KEY]
        assert entry["variables"] == EXPECTED_VARIABLES

    def test_template_body_references_every_variable(self):
        body = LEGAL_DOCUMENTS_UPDATED_TEMPLATE
        for variable in EXPECTED_VARIABLES:
            assert (
                "{" + variable + "}" in body
            ), f"template body must render {{{variable}}}"
        assert TEMPLATE_REGISTRY[LEGAL_EVENT_KEY]["html_content"] is body
