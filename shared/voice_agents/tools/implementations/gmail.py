import base64
from math import log
import re
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Any, Optional
from venv import logger

import httpx
from bs4 import BeautifulSoup
from livekit.agents import RunContext
from pydantic import Field

from shared.voice_agents.tools.base.auth_config import GoogleAuthConfig
from shared.voice_agents.tools.base.base_tool import (
    BaseConfig,
    BaseSensitiveConfig,
    BaseTool,
    ToolMetadata,
)


def validate_email(email: str) -> bool:
    """Validate email format."""
    email = email.strip()
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


class GmailTool(BaseTool):
    class AuthConfig(GoogleAuthConfig):
        scopes: list[str] = [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.compose",
        ]
        auth_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
        token_url: str = "https://oauth2.googleapis.com/token"

    class Config(BaseConfig):
        user_id: str = Field(
            default="me",
            description="Gmail user ID (default 'me' for authenticated user)",
        )
        max_results_default: int = Field(
            default=10, description="Default max results for queries"
        )

    class SensitiveConfig(BaseSensitiveConfig):
        access_token: str = ""
        refresh_token: Optional[str] = None
        token_expiry: Optional[str] = None

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="Gmail",
            description=(
                "Read, compose, and manage Gmail emails. "
                "Supports searching emails, sending emails, "
                "managing labels, and email thread operations."
            ),
            requires_auth=True,
            auth_type="oauth2",
            auth_config=self.AuthConfig().model_dump(),
            config_schema=self.Config.model_json_schema(),
        )

    async def get_latest_emails(
        self,
        context: RunContext,
        count: int = 5,
    ) -> dict[str, Any]:
        """
        Get the latest emails from the user's inbox.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            count: Number of latest emails to retrieve (default: 5, max: 10)

        Returns:
            Dict containing list of emails with details
        """
        count = min(count, 10)
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/messages",  # noqa: E501
                headers=headers,
                params={
                    "maxResults": count,
                },
            )
            response.raise_for_status()
            data = response.json()

            messages = data.get("messages", [])
            emails = []
            for msg in messages:
                email_details = await self._get_message_details(context, msg["id"])
                emails.append(email_details)

            return {"emails": emails}

    async def get_emails_from_user(
        self,
        context: RunContext,
        user: str,
        count: int = 5,
    ) -> dict[str, Any]:
        """
        Get emails from a specific user (name or email).

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            user: Name or email address of the sender
            count: Maximum number of emails to retrieve (default: 5, max: 10)

        Returns:
            Dict containing list of emails from the specified user
        """
        count = min(count, 10)
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        query = f"from:{user}" if "@" in user else f"from:{user}*"

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/messages",  # noqa: E501
                headers=headers,
                params={
                    "q": query,
                    "maxResults": count,
                },
            )
            response.raise_for_status()
            data = response.json()

            messages = data.get("messages", [])
            emails = []
            for msg in messages:
                email_details = await self._get_message_details(context, msg["id"])
                emails.append(email_details)

            return {"emails": emails}

    async def get_unread_emails(
        self,
        context: RunContext,
        count: int = 5,
    ) -> dict[str, Any]:
        """
        Get unread emails from the user's inbox.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            count: Maximum number of unread emails to retrieve (default: 5, max: 10)

        Returns:
            Dict containing list of unread emails
        """
        count = min(count, 10)
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/messages",  # noqa: E501
                headers=headers,
                params={
                    "q": "is:unread",
                    "maxResults": count,
                },
            )
            response.raise_for_status()
            data = response.json()

            messages = data.get("messages", [])
            emails = []
            for msg in messages:
                email_details = await self._get_message_details(context, msg["id"])
                emails.append(email_details)

            return {"emails": emails}

    async def get_starred_emails(
        self,
        context: RunContext,
        count: int = 5,
    ) -> dict[str, Any]:
        """
        Get starred emails from the user's inbox.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            count: Maximum number of starred emails to retrieve (default: 5, max: 10)

        Returns:
            Dict containing list of starred emails
        """
        count = min(count, 10)
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/messages",  # noqa: E501
                headers=headers,
                params={
                    "q": "is:starred",
                    "maxResults": count,
                },
            )
            response.raise_for_status()
            data = response.json()

            messages = data.get("messages", [])
            emails = []
            for msg in messages:
                email_details = await self._get_message_details(context, msg["id"])
                emails.append(email_details)

            return {"emails": emails}

    async def get_emails_by_context(
        self,
        context: RunContext,
        query: str,
        count: int = 5,
    ) -> dict[str, Any]:
        """
        Get emails matching a specific context or search term.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            query: Search query for filtering emails
            count: Maximum number of emails to retrieve (default: 5, max: 10)

        Returns:
            Dict containing list of emails matching the context
        """
        count = min(count, 10)
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/messages",  # noqa: E501
                headers=headers,
                params={
                    "q": query,
                    "maxResults": count,
                },
            )
            response.raise_for_status()
            data = response.json()

            messages = data.get("messages", [])
            emails = []
            for msg in messages:
                email_details = await self._get_message_details(context, msg["id"])
                emails.append(email_details)

            return {"emails": emails}

    async def get_emails_by_date(
        self,
        context: RunContext,
        start_date: int,
        range_in_days: Optional[int] = None,
        num_emails: int = 10,
    ) -> dict[str, Any]:
        """
        Get emails based on date range. start_date is a unix timestamp.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            start_date: Unix timestamp for start date
            range_in_days: Number of days to include in the range (optional)
            num_emails: Maximum number of emails to retrieve (default: 10)

        Returns:
            Dict containing list of emails within date range
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        start_date_dt = datetime.fromtimestamp(start_date)
        if range_in_days:
            end_date = start_date_dt + timedelta(days=range_in_days)
            query = f"after:{start_date_dt.strftime('%Y/%m/%d')} before:{end_date.strftime('%Y/%m/%d')}"  # noqa: E501
        else:
            query = f"after:{start_date_dt.strftime('%Y/%m/%d')}"

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/messages",  # noqa: E501
                headers=headers,
                params={
                    "q": query,
                    "maxResults": num_emails,
                },
            )
            response.raise_for_status()
            data = response.json()

            messages = data.get("messages", [])
            emails = []
            for msg in messages:
                email_details = await self._get_message_details(context, msg["id"])
                emails.append(email_details)

            return {"emails": emails}

    async def get_emails_by_thread(
        self,
        context: RunContext,
        thread_id: str,
    ) -> dict[str, Any]:
        """
        Retrieve all emails from a specific thread.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            thread_id: The ID of the email thread

        Returns:
            Dict containing all emails in the thread
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/threads/{thread_id}",  # noqa: E501
                headers=headers,
            )
            response.raise_for_status()
            thread_data = response.json()

            messages = thread_data.get("messages", [])
            emails = []
            for msg in messages:
                email_details = await self._get_message_details(context, msg["id"])
                emails.append(email_details)

            return {"emails": emails, "thread_id": thread_id}

    async def search_emails(
        self,
        context: RunContext,
        query: str,
        count: int = 5,
    ) -> dict[str, Any]:
        """
        Search emails based on a given query.
        Searches in to, from, cc, subject and email body contents.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            query: Natural language query to search for
            count: Number of emails to retrieve (default: 5, max: 10)

        Returns:
            Dict containing list of matching emails
        """
        count = min(count, 10)
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/messages",  # noqa: E501
                headers=headers,
                params={
                    "q": query,
                    "maxResults": count,
                },
            )
            response.raise_for_status()
            data = response.json()

            messages = data.get("messages", [])
            emails = []
            for msg in messages:
                email_details = await self._get_message_details(context, msg["id"])
                emails.append(email_details)

            return {"emails": emails}

    async def create_draft_email(
        self,
        context: RunContext,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create and save a draft email. to and cc are comma separated string of email ids.  # noqa: E501

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            to: Comma separated string of recipient email addresses
            subject: Email subject
            body: Email body content
            cc: Comma separated string of CC email addresses (optional)

        Returns:
            Dict containing draft email details including id
        """
        self._validate_email_params(to, subject, body)

        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        message = self._create_message(
            to.split(","), subject, body, cc.split(",") if cc else None
        )

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/drafts",  # noqa: E501
                headers=headers,
                json={"message": message},
            )
            response.raise_for_status()
            return response.json()

    async def send_email(
        self,
        context: RunContext,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Send an email immediately. to and cc are comma separated string of email ids.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            to: Comma separated string of recipient email addresses
            subject: Email subject
            body: Email body content
            cc: Comma separated string of CC email addresses (optional)

        Returns:
            Dict containing sent email details including id
        """
        self._validate_email_params(to, subject, body)

        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        body = body.replace("\n", "<br>")
        message = self._create_message(
            to.split(","), subject, body, cc.split(",") if cc else None
        )

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/messages/send",  # noqa: E501
                headers=headers,
                json=message,
            )
            response.raise_for_status()
            return response.json()

    async def send_email_reply(
        self,
        context: RunContext,
        thread_id: str,
        message_id: str,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Respond to an existing email thread.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            thread_id: The ID of the email thread to reply to
            message_id: The ID of the email being replied to
            to: Comma-separated recipient email addresses
            subject: Email subject (prefixed with "Re:" if not already)
            body: Email body content
            cc: Comma-separated CC email addresses (optional)

        Returns:
            Dict containing sent email details including id
        """
        self._validate_email_params(to, subject, body)

        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        body = body.replace("\n", "<br>")
        message = self._create_message(
            to.split(","),
            subject,
            body,
            cc.split(",") if cc else None,
            thread_id,
            message_id,
        )

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/messages/send",  # noqa: E501
                headers=headers,
                json=message,
            )
            response.raise_for_status()
            return response.json()

    async def mark_email_as_read(
        self,
        context: RunContext,
        message_id: str,
    ) -> dict[str, Any]:
        """
        Mark a specific email as read by removing the 'UNREAD' label.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            message_id: The ID of the message to mark as read

        Returns:
            Dict with success status
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/messages/{message_id}/modify",  # noqa: E501
                headers=headers,
                json={"removeLabelIds": ["UNREAD"]},
            )
            response.raise_for_status()
            return {"success": True, "message_id": message_id}

    async def mark_email_as_unread(
        self,
        context: RunContext,
        message_id: str,
    ) -> dict[str, Any]:
        """
        Mark a specific email as unread by adding the 'UNREAD' label.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            message_id: The ID of the message to mark as unread

        Returns:
            Dict with success status
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/messages/{message_id}/modify",  # noqa: E501
                headers=headers,
                json={"addLabelIds": ["UNREAD"]},
            )
            response.raise_for_status()
            return {"success": True, "message_id": message_id}

    async def list_custom_labels(
        self,
        context: RunContext,
    ) -> dict[str, Any]:
        """
        List only user-created custom labels (filters out system labels).

        Returns:
            Dict containing list of custom labels
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/labels",  # noqa: E501
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            labels = data.get("labels", [])
            custom_labels = [
                label["name"] for label in labels if label.get("type") == "user"
            ]

            return {"labels": custom_labels}

    async def apply_label(
        self,
        context: RunContext,
        query: str,
        label_name: str,
        count: int = 5,
    ) -> dict[str, Any]:
        """
        Find emails matching a query and apply a label, creating it if necessary.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            query: Gmail search query to find emails
            label_name: Name of the label to apply
            count: Number of emails to process (default: 5, max: 10)

        Returns:
            Dict containing the number of emails processed
        """
        count = min(count, 10)
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/messages",  # noqa: E501
                headers=headers,
                params={
                    "q": query,
                    "maxResults": count,
                },
            )
            response.raise_for_status()
            data = response.json()

            messages = data.get("messages", [])
            if not messages:
                return {"message": f"No emails found matching: '{query}'"}

            response = await client.get(
                f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/labels",  # noqa: E501
                headers=headers,
            )
            response.raise_for_status()
            labels = response.json().get("labels", [])

            label_id = None
            for label in labels:
                if label["name"].lower() == label_name.lower():
                    label_id = label["id"]
                    break

            if not label_id:
                create_response = await client.post(
                    f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/labels",  # noqa: E501
                    headers=headers,
                    json={
                        "name": label_name,
                        "labelListVisibility": "labelShow",
                        "messageListVisibility": "show",
                    },
                )
                create_response.raise_for_status()
                label_data = create_response.json()
                label_id = label_data["id"]

            for msg in messages:
                await client.post(
                    f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/messages/{msg['id']}/modify",  # noqa: E501
                    headers=headers,
                    json={"addLabelIds": [label_id]},
                )

            return {
                "message": f"Applied label '{label_name}' to {len(messages)} emails matching '{query}'"  # noqa: E501
            }

    async def remove_label(
        self,
        context: RunContext,
        query: str,
        label_name: str,
        count: int = 5,
    ) -> dict[str, Any]:
        """
        Remove a label from emails matching a query.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            query: Gmail search query to find emails
            label_name: Name of the label to remove
            count: Number of emails to process (default: 5, max: 10)

        Returns:
            Dict containing the number of emails processed
        """
        count = min(count, 10)
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/messages",  # noqa: E501
                headers=headers,
                params={
                    "q": query,
                    "maxResults": count,
                },
            )
            response.raise_for_status()
            labels = response.json().get("labels", [])

            label_id = None
            for label in labels:
                if label["name"].lower() == label_name.lower():
                    label_id = label["id"]
                    break

            if not label_id:
                return {"message": f"Label '{label_name}' not found"}

            response = await client.get(
                f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/messages",  # noqa: E501
                headers=headers,
                params={"q": f"{query} label:{label_name}", "maxResults": count},
            )
            response.raise_for_status()
            data = response.json()

            messages = data.get("messages", [])
            if not messages:
                return {
                    "message": f"No emails found matching: '{query}' with label '{label_name}'"  # noqa: E501
                }

            removed_count = 0
            for msg in messages:
                await client.post(
                    f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/messages/{msg['id']}/modify",  # noqa: E501
                    headers=headers,
                    json={"removeLabelIds": [label_id]},
                )
                removed_count += 1

            return {
                "message": f"Removed label '{label_name}' from {removed_count} emails matching '{query}'"  # noqa: E501
            }

    async def delete_email(
        self,
        context: RunContext,
        message_id: str,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """
        Permanently delete an email.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            message_id: ID of the message to delete
            confirm: Must be True to actually delete the email

        Returns:
            Dict with confirmation message
        """
        if not confirm:
            return {
                "message": f"EMAIL DELETION REQUIRES CONFIRMATION. This will permanently delete email '{message_id}'. Set confirm=True to proceed.",  # noqa: E501
                "requires_confirmation": True,
            }

        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/messages/{message_id}/trash",  # noqa: E501
                headers=headers,
            )
            response.raise_for_status()

            return {
                "message_id": message_id,
                "message": f"Email '{message_id}' moved to trash. Note: Messages in trash are permanently deleted after 30 days.",  # noqa: E501
            }

    async def delete_custom_label(
        self,
        context: RunContext,
        label_name: str,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """
        Delete a custom label (with safety confirmation).

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            label_name: Name of label to delete
            confirm: Must be True to actually delete label

        Returns:
            Dict with confirmation message or warning
        """
        if not confirm:
            return {
                "message": f"LABEL DELETION REQUIRES CONFIRMATION. This will permanently delete label '{label_name}' from all emails. Set confirm=True to proceed.",  # noqa: E501
                "requires_confirmation": True,
            }

        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/labels",  # noqa: E501
                headers=headers,
            )
            response.raise_for_status()
            labels = response.json().get("labels", [])

            target_label = None
            for label in labels:
                if label["name"].lower() == label_name.lower():
                    target_label = label
                    break

            if not target_label:
                return {"message": f"Label '{label_name}' not found"}

            if target_label.get("type") != "user":
                return {
                    "message": f"Cannot delete system label '{label_name}'. Only user-created labels can be deleted"  # noqa: E501
                }

            response = await client.delete(
                f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/labels/{target_label['id']}",  # noqa: E501
                headers=headers,
            )
            response.raise_for_status()

            return {
                "message": f"Successfully deleted label '{label_name}'. This label has been removed from all emails"  # noqa: E501
            }

    def _validate_email_params(self, to: str, subject: str, body: str) -> None:
        """Validate email parameters."""
        if not to:
            raise ValueError("Recipient email cannot be empty")

        for email in to.split(","):
            if not validate_email(email.strip()):
                raise ValueError(f"Invalid recipient email format: {email}")

        if not subject or not subject.strip():
            raise ValueError("Subject cannot be empty")

        if body is None:
            raise ValueError("Email body cannot be None")

    def _create_message(
        self,
        to: list[str],
        subject: str,
        body: str,
        cc: Optional[list[str]] = None,
        thread_id: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> dict[str, str]:
        """Create a Gmail message from parameters."""
        body = body.replace("\\n", "\n")

        message = EmailMessage()
        message.set_content(body, subtype="html")
        message["to"] = ", ".join(to)
        message["from"] = "me"
        message["subject"] = subject

        if cc:
            message["Cc"] = ", ".join(cc)

        if thread_id and message_id:
            message["In-Reply-To"] = message_id
            message["References"] = message_id

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        email_data: dict[str, str] = {"raw": raw_message}

        if thread_id:
            email_data["threadId"] = thread_id

        return email_data

    async def _get_message_details(
        self, context: RunContext, message_id: str
    ) -> dict[str, Any]:
        """Get detailed information about a specific message."""
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/gmail/v1/users/{self.config.user_id}/messages/{message_id}",  # noqa: E501
                headers=headers,
                params={"format": "full"},
            )
            response.raise_for_status()
            msg_data = response.json()

            return {
                "id": msg_data["id"],
                "thread_id": msg_data.get("threadId"),
                "subject": next(
                    (
                        header["value"]
                        for header in msg_data["payload"]["headers"]
                        if header["name"] == "Subject"
                    ),
                    None,
                ),
                "from": next(
                    (
                        header["value"]
                        for header in msg_data["payload"]["headers"]
                        if header["name"] == "From"
                    ),
                    None,
                ),
                "to": next(
                    (
                        header["value"]
                        for header in msg_data["payload"]["headers"]
                        if header["name"] == "To"
                    ),
                    None,
                ),
                "date": next(
                    (
                        header["value"]
                        for header in msg_data["payload"]["headers"]
                        if header["name"] == "Date"
                    ),
                    None,
                ),
                "in_reply_to": next(
                    (
                        header["value"]
                        for header in msg_data["payload"]["headers"]
                        if header["name"] == "In-Reply-To"
                    ),
                    None,
                ),
                "references": next(
                    (
                        header["value"]
                        for header in msg_data["payload"]["headers"]
                        if header["name"] == "References"
                    ),
                    None,
                ),
                "body": self._get_message_body(msg_data),
            }

    async def read_email(
        self, context: RunContext, message_id: str, fetch_body: bool = True
    ) -> dict[str, Any]:
        """
        Read a specific email by ID.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            message_id: ID of the email to read
            fetch_body: Whether to fetch the email body (default: True)

        Returns:
            Dict with email details including subject, from, to, date, and body
        """
        return await self._get_message_details(context, message_id)

    def _get_message_body(self, msg_data: dict[str, Any]) -> str:
        """Extract message body from message data, stripping HTML tags to return plain text."""
        body = ""
        content_type = ""
        try:
            if "parts" in msg_data["payload"]:
                for part in msg_data["payload"]["parts"]:
                    if part["mimeType"] == "text/plain":
                        if "data" in part["body"]:
                            body = base64.urlsafe_b64decode(
                                part["body"]["data"]
                            ).decode()
                            content_type = "text/plain"
                            break  # Prefer plain text over HTML
                    elif part["mimeType"] == "text/html" and not body:
                        if "data" in part["body"]:
                            body = base64.urlsafe_b64decode(
                                part["body"]["data"]
                            ).decode()
                            content_type = "text/html"
            elif (
                "body" in msg_data["payload"] and "data" in msg_data["payload"]["body"]
            ):
                body = base64.urlsafe_b64decode(
                    msg_data["payload"]["body"]["data"]
                ).decode()
                # Check if the payload has a mimeType
                content_type = msg_data["payload"].get("mimeType", "text/plain")
        except Exception:
            return "Unable to decode message body"

        # Strip HTML tags if content is HTML
        if content_type == "text/html" and body:
            try:
                soup = BeautifulSoup(body, "html.parser")
                body = soup.get_text(separator=" ")
                # Clean up extra whitespace
                body = " ".join(body.split())
            except Exception:
                # If HTML parsing fails, return the original body
                pass

        if len(body) > 2000:
            body = body[:2000] + "..."

        logger.info(f"Extracted message body: {body}")
        return body
