from typing import Any, Optional, List
import httpx
import logging
from livekit.agents import RunContext
from pydantic import Field

from shared.voice_agents.tools.base.auth_config import GoogleAuthConfig
from shared.voice_agents.tools.base.base_tool import (
    BaseConfig,
    BaseSensitiveConfig,
    BaseTool,
    ToolMetadata,
)

logger = logging.getLogger(__name__)


class GoogleSheetsTool(BaseTool):
    class AuthConfig(GoogleAuthConfig):
        scopes: list[str] = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive.metadata.readonly",
        ]
        auth_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
        token_url: str = "https://oauth2.googleapis.com/token"

    class Config(BaseConfig):
        spreadsheet_id: str = Field(
            default="",
            description="Default Google Spreadsheet ID to use for operations",
        )
        default_range: str = Field(
            default="Sheet1!A1:Z1000",
            description="Default range for sheet operations (e.g., 'Sheet1!A1:B10')",
        )

    class SensitiveConfig(BaseSensitiveConfig):
        access_token: str = ""
        refresh_token: Optional[str] = None
        token_expiry: Optional[str] = None

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="Google_Sheets",
            description=(
                "Read, write, and manage Google Sheets data. "
                "Supports reading values, appending rows, updating cells, "
                "searching data, and creating spreadsheets."
            ),
            requires_auth=True,
            auth_type="oauth2",
            auth_config=self.AuthConfig().model_dump(),
            config_schema=self.Config.model_json_schema(),
        )

    async def get_sheet_values(
        self,
        context: RunContext,
        spreadsheet_id: str,
        range: str,
    ) -> dict[str, Any]:
        """
        Description:
            Read data from a Google Sheet within a specified range for internal analysis.

        Instructions:
            - Use A1 notation for ranges (e.g., 'Sheet1!A1:B10')
            - If no range specified, defaults to 'Sheet1!A1:Z1000'
            - Returns data as arrays of values

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            spreadsheet_id: The ID of the Google Spreadsheet
            range: Range in A1 notation (e.g., 'Sheet1!A1:B10')

        Returns:
            Dict containing values from the specified range (for internal use only)
        """
        # Log function call for debugging
        logger.info(f"get_sheet_values called with spreadsheet_id={spreadsheet_id[:15] if spreadsheet_id else 'EMPTY'}..., range={range}")

        if not spreadsheet_id:
            logger.error("get_sheet_values: spreadsheet_id is empty or missing")
            raise ValueError("spreadsheet_id is required")

        if not range:
            logger.error("get_sheet_values: range is empty or missing")
            raise ValueError("range is required")

        if not self.sensitive_config or not self.sensitive_config.access_token:
            logger.error("get_sheet_values: No access token found")
            raise ValueError("No access token found in sensitive config")

        # Extract just the ID if a full URL was passed
        if "/spreadsheets/d/" in spreadsheet_id:
            # Extract ID from URL like https://docs.google.com/spreadsheets/d/ID/edit
            parts = spreadsheet_id.split("/spreadsheets/d/")
            if len(parts) > 1:
                spreadsheet_id = parts[1].split("/")[0].split("?")[0]
                logger.info(f"get_sheet_values: Extracted ID from URL: {spreadsheet_id[:15]}...")

        # Validate spreadsheet_id format (should be alphanumeric with some special chars)
        if len(spreadsheet_id) < 10 or " " in spreadsheet_id:
            logger.error(f"get_sheet_values: Invalid spreadsheet_id format: {spreadsheet_id}")
            return {
                "error": True,
                "message": "Invalid spreadsheet ID format. Please provide a valid spreadsheet ID."
            }

        # Validate range format - basic check for A1 notation
        if "!" not in range and range != "":
            # If no sheet specified, default to Sheet1
            logger.warning(f"get_sheet_values: No sheet specified in range '{range}', defaulting to Sheet1")
            range = f"Sheet1!{range}"

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range}"
        logger.info(f"get_sheet_values: Calling URL: {url}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

                return {
                    "values": data.get("values", []),
                    "range": data.get("range", range),
                    "major_dimension": data.get("majorDimension", "ROWS"),
                }
            except httpx.HTTPStatusError as e:
                error_body = ""
                try:
                    error_body = e.response.text
                except Exception:
                    pass
                logger.error(
                    f"get_sheet_values: HTTP {e.response.status_code} error. "
                    f"URL: {url}, "
                    f"Response: {error_body[:500]}"
                )
                return self._handle_api_error(e, "get_sheet_values")

    async def append_row(
        self,
        context: RunContext,
        spreadsheet_id: str,
        range: str,
        values: List[Any],
    ) -> dict[str, Any]:
        """
        Description:
            Append a new row of data to a Google Sheet.

        Instructions:
            - Values should be provided as a list of values for each column
            - Use A1 notation for range (e.g., 'Sheet1!A1:Z1')
            - Row will be appended to the end of the specified range

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            spreadsheet_id: The ID of the Google Spreadsheet
            range: Range in A1 notation where to append (e.g., 'Sheet1!A1:Z1')
            values: List of values to append as a new row

        Returns:
            Dict containing information about the append operation
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
            "Content-Type": "application/json",
        }

        body = {
            "values": [values],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range}:append",
                headers=headers,
                json=body,
                params={
                    "valueInputOption": "RAW",
                    "insertDataOption": "INSERT_ROWS",
                },
            )
            response.raise_for_status()
            data = response.json()

            return {
                "spreadsheet_id": spreadsheet_id,
                "updated_range": data.get("updates", {}).get("updatedRange"),
                "updated_rows": data.get("updates", {}).get("updatedRows"),
                "values_appended": values,
            }

    async def update_cell(
        self,
        context: RunContext,
        spreadsheet_id: str,
        range: str,
        values: List[List[Any]],
    ) -> dict[str, Any]:
        """
        Description:
            Update specific cells in a Google Sheet with new values.

        Instructions:
            - Values should be provided as a 2D array [[value1], [value2]]
            - Use A1 notation for range (e.g., 'Sheet1!A1', 'Sheet1!A1:B2')
            - Updates cells in the specified range

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            spreadsheet_id: The ID of the Google Spreadsheet
            range: Range in A1 notation to update (e.g., 'Sheet1!A1', 'Sheet1!A1:B2')
            values: 2D array of values to update [[value1], [value2]]

        Returns:
            Dict containing information about the update operation
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
            "Content-Type": "application/json",
        }

        body = {
            "values": values,
        }

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range}",
                headers=headers,
                json=body,
                params={
                    "valueInputOption": "RAW",
                },
            )
            response.raise_for_status()
            data = response.json()

            return {
                "spreadsheet_id": spreadsheet_id,
                "updated_range": data.get("updatedRange"),
                "updated_cells": data.get("updatedCells"),
                "updated_rows": data.get("updatedRows"),
            }

    async def search_in_sheet(
        self,
        context: RunContext,
        spreadsheet_id: str,
        search_term: str,
        range: str = "",
    ) -> dict[str, Any]:
        """
        Description:
            Search for a specific term within a Google Sheet for internal analysis.

        Instructions:
            - If no range specified, searches the entire spreadsheet
            - Returns all matching cells with their coordinates
            - Case-insensitive search

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            spreadsheet_id: The ID of the Google Spreadsheet
            search_term: Term to search for in the sheet
            range: Optional range in A1 notation to search within (e.g., 'Sheet1!A1:Z100')

        Returns:
            Dict containing matching cells with their values and coordinates (for internal use only)
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        # First, get all values from the specified range or entire sheet
        search_range = range if range else "Sheet1!A1:Z1000"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{search_range}",
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            values = data.get("values", [])
            matches = []

            search_lower = search_term.lower()

            for row_idx, row in enumerate(values):
                for col_idx, cell_value in enumerate(row):
                    if search_lower in str(cell_value).lower():
                        matches.append({
                            "row": row_idx + 1,  # 1-indexed for A1 notation
                            "column": chr(65 + col_idx),  # A, B, C, etc.
                            "cell": f"{chr(65 + col_idx)}{row_idx + 1}",
                            "value": cell_value,
                        })

            return {
                "matches": matches,
                "total_matches": len(matches),
                "search_term": search_term,
                "range": search_range,
            }

    async def create_spreadsheet(
        self,
        context: RunContext,
        title: str,
        sheet_names: List[str] = None,
    ) -> dict[str, Any]:
        """
        Description:
            Create a new Google Spreadsheet with specified title and sheets.

        Instructions:
            - Provide a meaningful title for the spreadsheet
            - Optionally specify multiple sheet names
            - Returns the new spreadsheet ID for future operations

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            title: Title for the new spreadsheet
            sheet_names: List of sheet names to create (default: ["Sheet1"])

        Returns:
            Dict containing the new spreadsheet ID and details
        """
        if sheet_names is None:
            sheet_names = ["Sheet1"]

        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
            "Content-Type": "application/json",
        }

        # Prepare sheet properties
        sheets = []
        for i, name in enumerate(sheet_names):
            sheets.append({
                "properties": {
                    "title": name,
                    "sheetId": i + 1,
                }
            })

        body = {
            "properties": {
                "title": title,
            },
            "sheets": sheets,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://sheets.googleapis.com/v4/spreadsheets",
                headers=headers,
                json=body,
            )
            response.raise_for_status()
            data = response.json()

            return {
                "spreadsheet_id": data.get("spreadsheetId"),
                "title": data.get("properties", {}).get("title"),
                "sheets": [
                    sheet["properties"]["title"]
                    for sheet in data.get("sheets", [])
                ],
            }

    def _handle_api_error(self, error: httpx.HTTPStatusError, operation: str = "API call") -> dict[str, Any]:
        """Handle API errors and return user-friendly error messages.

        Args:
            error: The HTTP error that occurred
            operation: Description of the operation being performed

        Returns:
            Dict with error information and guidance
        """
        status_code = error.response.status_code
        error_detail = ""
        error_code = ""
        try:
            error_data = error.response.json()
            error_detail = error_data.get("error", {}).get("message", str(error))
            error_code = error_data.get("error", {}).get("code", "")
        except Exception:
            error_detail = str(error)

        # Log the full error for debugging
        logger.error(
            f"Google Sheets {operation} failed: "
            f"status={status_code}, "
            f"error_code={error_code}, "
            f"detail={error_detail}, "
            f"url={error.request.url if error.request else 'N/A'}"
        )

        if status_code == 403:
            # Check if it's a scope/permission issue
            scope_error = "insufficientPermissions" in str(error_detail) or "scope" in str(error_detail).lower()

            if scope_error:
                logger.error(
                    "Google Sheets authorization error: "
                    "The access token is missing required Google Drive scopes. "
                    "User needs to re-authenticate with 'drive.metadata.readonly' and 'drive.file' scopes."
                )

            return {
                "error": True,
                "status_code": 403,
                "message": (
                    "AUTHORIZATION ERROR: Google Sheets access denied. "
                    "The access token lacks required Google Drive permissions.\n\n"
                    "YOUR ACTION REQUIRED:\n"
                    "1. DO NOT mention this error to the caller\n"
                    "2. Use your available communication tools (email/text) to notify the owner\n"
                    "3. Inform the owner that Google Sheets re-authentication is needed\n"
                    "4. Provide the owner with this reference: 'Google Sheets authorization failed'\n\n"
                    "For your reference only - Technical details: " + error_detail
                ),
            }
        elif status_code == 401:
            logger.error(
                "Google Sheets authentication error: "
                "The access token has expired or is invalid."
            )
            return {
                "error": True,
                "status_code": 401,
                "message": (
                    "AUTHENTICATION ERROR: Google Sheets access token expired or invalid.\n\n"
                    "YOUR ACTION REQUIRED:\n"
                    "1. DO NOT mention this error to the caller\n"
                    "2. Use your available communication tools (email/text) to notify the owner\n"
                    "3. Inform the owner that Google Sheets re-authentication is needed\n"
                    "4. Provide the owner with this reference: 'Google Sheets authentication failed'"
                ),
            }
        elif status_code == 404:
            return {
                "error": True,
                "status_code": 404,
                "message": (
                    "NOT FOUND: The specified spreadsheet or resource was not found.\n\n"
                    "YOUR ACTION REQUIRED:\n"
                    "1. DO NOT mention specific error details to the caller\n"
                    "2. If this persists, use communication tools to notify the owner\n"
                    "3. Simply inform the caller you're unable to access that information"
                ),
            }
        else:
            return {
                "error": True,
                "status_code": status_code,
                "message": (
                    f"API ERROR: An error occurred while accessing Google Sheets (status {status_code}).\n\n"
                    "YOUR ACTION REQUIRED:\n"
                    "1. DO NOT share technical error details with the caller\n"
                    "2. Use your best judgment to provide a helpful response without revealing sources\n"
                    "3. If this persists, notify the owner via communication tools"
                ),
            }

    async def list_user_spreadsheets(
        self,
        context: RunContext,
        query: str = "",
        max_results: int = 50,
    ) -> dict[str, Any]:
        """
        Description:
            List all Google Spreadsheets available to the user for internal discovery.

        Instructions:
            - Use this to discover what spreadsheets are available in the user's account
            - Optionally filter by search query (title, owner, etc.)
            - Returns spreadsheet IDs, titles, and metadata for selection
            - Essential for navigating user's spreadsheet collection

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            query: Optional search query to filter spreadsheets (e.g., "title:'Sales Report'")
            max_results: Maximum number of results to return (default: 50, max: 1000)

        Returns:
            Dict containing list of available spreadsheets with their properties (for internal use only)
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        # Log token info for debugging (token prefix only for security)
        token_preview = self.sensitive_config.access_token[:20] + "..." if len(self.sensitive_config.access_token) > 20 else "invalid"
        logger.info(f"list_user_spreadsheets called with access_token prefix: {token_preview}")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        # Use Google Drive API to search for spreadsheets
        params = {
            "q": "mimeType='application/vnd.google-apps.spreadsheet'",
            "pageSize": min(max_results, 1000),
            "fields": "files(id,name,owners,createdTime,modifiedTime,lastModifyingUser,description,size,parents)",
        }

        logger.debug(f"Calling Drive API with params: {params}")

        # Add query filter if provided
        if query:
            params["q"] = f"mimeType='application/vnd.google-apps.spreadsheet' and {query}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://www.googleapis.com/drive/v3/files",
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                spreadsheets = []
                for file in data.get("files", []):
                    spreadsheet_info = {
                        "spreadsheet_id": file.get("id"),
                        "title": file.get("name"),
                        "created_time": file.get("createdTime"),
                        "modified_time": file.get("modifiedTime"),
                        "last_modified_by": file.get("lastModifyingUser", {}).get("displayName") if file.get("lastModifyingUser") else None,
                        "owners": [owner.get("displayName") for owner in file.get("owners", [])],
                        "description": file.get("description"),
                    }

                    # Add parent folders if available
                    parents = file.get("parents", [])
                    if parents:
                        spreadsheet_info["parent_folder_ids"] = parents

                    spreadsheets.append(spreadsheet_info)

                return {
                    "total_spreadsheets": len(spreadsheets),
                    "spreadsheets": spreadsheets,
                    "query_used": query if query else "all spreadsheets",
                }
            except httpx.HTTPStatusError as e:
                return self._handle_api_error(e, "list_user_spreadsheets")

    async def search_spreadsheets_by_title(
        self,
        context: RunContext,
        title: str,
        max_results: int = 20,
    ) -> dict[str, Any]:
        """
        Description:
            Search for Google Spreadsheets by title.

        Instructions:
            - Use this to find specific spreadsheets when you know part of the title
            - Returns matching spreadsheets with their IDs and metadata
            - Case-insensitive search on spreadsheet titles
            - Useful for locating specific reports, databases, or documents

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            title: Title or partial title to search for
            max_results: Maximum number of results to return (default: 20)

        Returns:
            Dict containing matching spreadsheets with their properties
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        # Create search query for title
        search_query = f"name contains '{title}' and mimeType='application/vnd.google-apps.spreadsheet'"

        params = {
            "q": search_query,
            "pageSize": min(max_results, 1000),
            "fields": "files(id,name,owners,createdTime,modifiedTime,lastModifyingUser,description,size,parents)",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://www.googleapis.com/drive/v3/files",
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                spreadsheets = []
                for file in data.get("files", []):
                    spreadsheet_info = {
                        "spreadsheet_id": file.get("id"),
                        "title": file.get("name"),
                        "created_time": file.get("createdTime"),
                        "modified_time": file.get("modifiedTime"),
                        "last_modified_by": file.get("lastModifyingUser", {}).get("displayName") if file.get("lastModifyingUser") else None,
                        "owners": [owner.get("displayName") for owner in file.get("owners", [])],
                        "description": file.get("description"),
                    }

                    # Add parent folders if available
                    parents = file.get("parents", [])
                    if parents:
                        spreadsheet_info["parent_folder_ids"] = parents

                    spreadsheets.append(spreadsheet_info)

                return {
                    "search_term": title,
                    "total_matches": len(spreadsheets),
                    "matching_spreadsheets": spreadsheets,
                }
            except httpx.HTTPStatusError as e:
                return self._handle_api_error(e, "search_spreadsheets_by_title")

    async def get_spreadsheet_details(
        self,
        context: RunContext,
        spreadsheet_id: str,
    ) -> dict[str, Any]:
        """
        Description:
            Get detailed information about a specific Google Spreadsheet.

        Instructions:
            - Use this to get comprehensive details about a specific spreadsheet
            - Returns metadata, sharing info, and basic properties
            - Useful for understanding spreadsheet context before operations

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            spreadsheet_id: The ID of the Google Spreadsheet

        Returns:
            Dict containing detailed spreadsheet information
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        # First get spreadsheet details from Drive API
        drive_params = {
            "fields": "id,name,owners,mimeType,createdTime,modifiedTime,lastModifyingUser,description,parents,webViewLink,iconLink,size"
        }

        async with httpx.AsyncClient() as client:
            try:
                drive_response = await client.get(
                    f"https://www.googleapis.com/drive/v3/files/{spreadsheet_id}",
                    headers=headers,
                    params=drive_params,
                )
                drive_response.raise_for_status()
                drive_data = drive_response.json()

                # Also get sheet structure from Sheets API
                sheets_response = await client.get(
                    f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}",
                    headers=headers,
                )
                sheets_response.raise_for_status()
                sheets_data = sheets_response.json()

                # Combine information
                result = {
                    "spreadsheet_id": drive_data.get("id"),
                    "title": drive_data.get("name"),
                    "mime_type": drive_data.get("mimeType"),
                    "created_time": drive_data.get("createdTime"),
                    "modified_time": drive_data.get("modifiedTime"),
                    "last_modified_by": drive_data.get("lastModifyingUser", {}).get("displayName") if drive_data.get("lastModifyingUser") else None,
                    "owners": [owner.get("displayName") for owner in drive_data.get("owners", [])],
                    "description": drive_data.get("description"),
                    "web_view_link": drive_data.get("webViewLink"),
                    "icon_link": drive_data.get("iconLink"),
                    "size_bytes": drive_data.get("size"),
                    "parent_folder_ids": drive_data.get("parents", []),
                    "sheet_count": len(sheets_data.get("sheets", [])),
                    "sheets": [
                        {
                            "sheet_id": sheet["properties"]["sheetId"],
                            "title": sheet["properties"]["title"],
                            "index": sheet["properties"]["index"],
                            "sheet_type": sheet["properties"].get("sheetType", "GRID"),
                        }
                        for sheet in sheets_data.get("sheets", [])
                    ],
                }

                return result
            except httpx.HTTPStatusError as e:
                return self._handle_api_error(e, "get_spreadsheet_details")

    async def get_spreadsheet_info(
        self,
        context: RunContext,
        spreadsheet_id: str,
    ) -> dict[str, Any]:
        """
        Description:
            Get detailed information about a Google Spreadsheet.

        Instructions:
            - Returns spreadsheet properties, sheets, and basic info
            - Useful for understanding the structure before operations
            - Lists all available sheet names and their IDs

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            spreadsheet_id: The ID of the Google Spreadsheet (from list_user_spreadsheets)

        Returns:
            Dict containing spreadsheet properties and sheet information (for internal use only)
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        # Extract just the ID if a full URL was passed
        if "/spreadsheets/d/" in spreadsheet_id:
            parts = spreadsheet_id.split("/spreadsheets/d/")
            if len(parts) > 1:
                spreadsheet_id = parts[1].split("/")[0].split("?")[0]
                logger.info(f"get_spreadsheet_info: Extracted ID from URL: {spreadsheet_id[:15]}...")

        if len(spreadsheet_id) < 10 or " " in spreadsheet_id:
            logger.error(f"get_spreadsheet_info: Invalid spreadsheet_id format: {spreadsheet_id}")
            return {
                "error": True,
                "message": "Invalid spreadsheet ID format. Please provide a valid spreadsheet ID from list_user_spreadsheets."
            }

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
        logger.info(f"get_spreadsheet_info: Calling URL: {url}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

                return {
                    "spreadsheet_id": spreadsheet_id,
                    "title": data.get("properties", {}).get("title"),
                    "sheets": [
                        {
                            "sheet_id": sheet["properties"]["sheetId"],
                            "title": sheet["properties"]["title"],
                            "index": sheet["properties"]["index"],
                            "grid_properties": sheet["properties"].get("gridProperties", {}),
                        }
                        for sheet in data.get("sheets", [])
                    ],
                }
            except httpx.HTTPStatusError as e:
                error_body = ""
                try:
                    error_body = e.response.text
                except Exception:
                    pass
                logger.error(
                    f"get_spreadsheet_info: HTTP {e.response.status_code} error. "
                    f"URL: {url}, "
                    f"Response: {error_body[:500]}"
                )
                return self._handle_api_error(e, "get_spreadsheet_info")

    async def list_spreadsheet_sheets(
        self,
        context: RunContext,
        spreadsheet_id: str,
    ) -> dict[str, Any]:
        """
        Description:
            List all available sheets within a Google Spreadsheet.

        Instructions:
            - Use this to discover what sheets are available before working with specific data
            - Returns sheet titles, IDs, and indices to help identify the correct sheet
            - Essential for navigating spreadsheets with multiple sheets

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            spreadsheet_id: The ID of the Google Spreadsheet

        Returns:
            Dict containing list of available sheets with their properties
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}",
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            sheets = data.get("sheets", [])
            sheet_list = []

            for sheet in sheets:
                properties = sheet.get("properties", {})
                sheet_info = {
                    "sheet_id": properties.get("sheetId"),
                    "title": properties.get("title"),
                    "index": properties.get("index"),
                    "sheet_type": properties.get("sheetType", "GRID"),
                }

                # Add grid properties if available
                grid_props = properties.get("gridProperties", {})
                if grid_props:
                    sheet_info["grid_properties"] = {
                        "row_count": grid_props.get("rowCount"),
                        "column_count": grid_props.get("columnCount"),
                    }

                sheet_list.append(sheet_info)

            return {
                "spreadsheet_id": spreadsheet_id,
                "total_sheets": len(sheet_list),
                "sheets": sheet_list,
            }

    async def find_sheet_by_title(
        self,
        context: RunContext,
        spreadsheet_id: str,
        sheet_title: str,
    ) -> dict[str, Any]:
        """
        Description:
            Find a specific sheet by its title within a Google Spreadsheet.

        Instructions:
            - Use this to locate a specific sheet when you know its name
            - Returns the sheet's ID and properties for use in other operations
            - Case-insensitive search for sheet titles

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            spreadsheet_id: The ID of the Google Spreadsheet
            sheet_title: The title/name of the sheet to find

        Returns:
            Dict containing sheet information if found, or error message if not found
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}",
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            target_sheet = None
            all_sheets = []

            for sheet in data.get("sheets", []):
                properties = sheet.get("properties", {})
                sheet_title_prop = properties.get("title", "")
                all_sheets.append({
                    "sheet_id": properties.get("sheetId"),
                    "title": sheet_title_prop,
                    "index": properties.get("index"),
                })

                # Case-insensitive match
                if sheet_title_prop.lower() == sheet_title.lower():
                    target_sheet = {
                        "sheet_id": properties.get("sheetId"),
                        "title": sheet_title_prop,
                        "index": properties.get("index"),
                        "grid_properties": properties.get("gridProperties", {}),
                    }
                    break

            if target_sheet:
                return {
                    "found": True,
                    "sheet": target_sheet,
                    "all_sheets_in_spreadsheet": all_sheets,
                }
            else:
                return {
                    "found": False,
                    "sheet_title_searched": sheet_title,
                    "all_sheets_in_spreadsheet": all_sheets,
                    "message": f"Sheet with title '{sheet_title}' not found in spreadsheet",
                }

    async def get_sheet_metadata(
        self,
        context: RunContext,
        spreadsheet_id: str,
        sheet_id: int,
    ) -> dict[str, Any]:
        """
        Description:
            Get detailed metadata about a specific sheet within a Google Spreadsheet.

        Instructions:
            - Use this to get detailed information about a specific sheet
            - Requires the numeric sheet ID (not title) - use list_spreadsheet_sheets to get sheet IDs
            - Returns grid properties, protection settings, and other sheet details

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            spreadsheet_id: The ID of the Google Spreadsheet
            sheet_id: The numeric ID of the specific sheet

        Returns:
            Dict containing detailed sheet metadata
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            try:
                # Get spreadsheet data without range filter - filter manually after
                response = await client.get(
                    f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}",
                    headers=headers,
                    params={"includeGridData": "false"}
                )
                response.raise_for_status()
                data = response.json()

                # Find the specific sheet by its numeric ID
                sheet_info = None
                for sheet in data.get("sheets", []):
                    if sheet.get("properties", {}).get("sheetId") == sheet_id:
                        properties = sheet.get("properties", {})
                        sheet_info = {
                            "sheet_id": properties.get("sheetId"),
                            "title": properties.get("title"),
                            "index": properties.get("index"),
                            "sheet_type": properties.get("sheetType"),
                            "grid_properties": properties.get("gridProperties", {}),
                            "protected_ranges": sheet.get("protectedRanges", []),
                            "basic_filter": sheet.get("basicFilter"),
                            "conditional_formats": len(sheet.get("conditionalFormats", [])),
                            "data_validations": len(sheet.get("dataValidations", {}).get("dataValidationRanges", [])),
                        }
                        break

                if sheet_info:
                    return {
                        "spreadsheet_id": spreadsheet_id,
                        "sheet_metadata": sheet_info,
                    }
                else:
                    return {
                        "spreadsheet_id": spreadsheet_id,
                        "sheet_id": sheet_id,
                        "found": False,
                        "message": f"Sheet with ID {sheet_id} not found in spreadsheet",
                    }
            except httpx.HTTPStatusError as e:
                error_body = ""
                try:
                    error_body = e.response.text
                except Exception:
                    pass
                logger.error(
                    f"get_sheet_metadata: HTTP {e.response.status_code} error. "
                    f"spreadsheet_id={spreadsheet_id}, sheet_id={sheet_id}, "
                    f"Response: {error_body[:500]}"
                )
                return self._handle_api_error(e, "get_sheet_metadata")

    async def clear_range(
        self,
        context: RunContext,
        spreadsheet_id: str,
        range: str,
    ) -> dict[str, Any]:
        """
        Description:
            Clear all values from a specified range in a Google Sheet.

        Instructions:
            - Use A1 notation for range (e.g., 'Sheet1!A1:B10')
            - This will remove all data from the specified cells
            - Requires explicit confirmation for large ranges

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            spreadsheet_id: The ID of the Google Spreadsheet
            range: Range in A1 notation to clear (e.g., 'Sheet1!A1:B10')

        Returns:
            Dict containing information about the clear operation
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range}:clear",
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            return {
                "spreadsheet_id": spreadsheet_id,
                "cleared_range": data.get("clearedRange"),
                "success": True,
            }

    async def batch_update_values(
        self,
        context: RunContext,
        spreadsheet_id: str,
        updates: List[dict],
    ) -> dict[str, Any]:
        """
        Description:
            Perform multiple updates to a Google Sheet in a single request.

        Instructions:
            - Provide a list of updates with range and values
            - More efficient than multiple individual updates
            - Each update should have 'range' and 'values' keys

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            spreadsheet_id: The ID of the Google Spreadsheet
            updates: List of dictionaries with 'range' and 'values' keys

        Returns:
            Dict containing information about the batch update operation
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
            "Content-Type": "application/json",
        }

        body = {
            "valueInputOption": "RAW",
            "data": [
                {
                    "range": update["range"],
                    "values": update["values"],
                }
                for update in updates
            ],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values:batchUpdate",
                headers=headers,
                json=body,
            )
            response.raise_for_status()
            data = response.json()

            return {
                "spreadsheet_id": spreadsheet_id,
                "total_updated_ranges": data.get("totalUpdatedRanges"),
                "total_updated_cells": data.get("totalUpdatedCells"),
                "updates_applied": len(updates),
            }
