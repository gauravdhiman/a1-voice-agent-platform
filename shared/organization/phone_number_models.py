"""
Pydantic models for Phone Number functionality shared across backend and worker.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PhoneNumberProvider(str, Enum):
    """Phone number provider enumeration."""

    TWILIO = "twilio"


class PhoneNumberStatus(str, Enum):
    """Phone number status enumeration."""

    AVAILABLE = "available"
    PROVISIONING = "provisioning"
    PURCHASED = "purchased"
    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"
    VERIFICATION_REQUIRED = "verification_required"
    RELEASE_PENDING = "release_pending"
    DISCONNECTED = "disconnected"


class PhoneNumberProvisioningSource(str, Enum):
    """How a phone number first entered the platform."""

    PLATFORM = "platform"
    CUSTOMER = "customer"


class PhoneNumberManagementMode(str, Enum):
    """What provider actions the platform is authorized to perform."""

    PLATFORM = "platform_managed"
    CUSTOMER = "customer_managed"


class PhoneNumberConfigurationStatus(str, Enum):
    """State of the Twilio webhook configuration handshake."""

    PENDING = "pending"
    CONFIGURED = "configured"
    VERIFICATION_REQUIRED = "verification_required"
    FAILED = "failed"


class PhoneNumberBillingMode(str, Enum):
    """Whether the platform charges recurring rental credits."""

    PLATFORM_RENTAL = "platform_rental"
    NONE = "none"


class PhoneNumberBillingStatus(str, Enum):
    """Credit-rental state for an owned phone number."""

    ACTIVE = "active"
    PAST_DUE = "past_due"


class PhoneNumberType(str, Enum):
    """Phone number type enumeration."""

    LOCAL = "local"
    TOLL_FREE = "toll_free"
    MOBILE = "mobile"


class PhoneNumberSearchMode(str, Enum):
    """Match mode used when searching provider phone-number inventory."""

    CONTAINS = "contains"
    BEGINS_WITH = "begins_with"
    ENDS_WITH = "ends_with"


class PhoneNumberBase(BaseModel):
    """Base model for phone numbers."""

    phone_number: str = Field(
        ..., min_length=1, max_length=20, description="Phone number in E.164 format"
    )
    provider: PhoneNumberProvider = Field(..., description="Provider (twilio)")
    provider_sid: Optional[str] = Field(
        None, max_length=255, description="Provider's SID for the phone number"
    )
    phone_number_type: PhoneNumberType = Field(
        ..., description="Type of phone number (local, toll_free, mobile)"
    )
    country_code: str = Field(
        ..., min_length=2, max_length=2, description="Country code (e.g., US)"
    )
    area_code: Optional[str] = Field(
        None, max_length=10, description="Area code for local numbers"
    )
    monthly_cost_credits: int = Field(
        default=0, ge=0, description="Monthly cost in credits"
    )
    is_included_in_plan: bool = Field(
        default=False,
        description="Whether this is the organization's included US local number",
    )
    status: PhoneNumberStatus = Field(
        default=PhoneNumberStatus.PURCHASED, description="Current status"
    )
    assigned_agent_id: Optional[UUID] = Field(
        None, description="UUID of the agent this number is assigned to"
    )
    is_incoming_enabled: bool = Field(
        default=True, description="Whether incoming calls are enabled"
    )
    is_outgoing_enabled: bool = Field(
        default=False, description="Whether outgoing calls are enabled"
    )
    billing_status: PhoneNumberBillingStatus = Field(
        default=PhoneNumberBillingStatus.ACTIVE,
        description="Monthly credit-rental state",
    )
    next_billing_at: Optional[datetime] = Field(
        None, description="When the next monthly rental is due"
    )
    billing_grace_ends_at: Optional[datetime] = Field(
        None, description="When an unpaid rental is released"
    )
    provisioning_source: PhoneNumberProvisioningSource = Field(
        default=PhoneNumberProvisioningSource.PLATFORM,
        description="How the number entered the platform",
    )
    management_mode: PhoneNumberManagementMode = Field(
        default=PhoneNumberManagementMode.PLATFORM,
        description="Whether provider management is authorized",
    )
    configuration_status: PhoneNumberConfigurationStatus = Field(
        default=PhoneNumberConfigurationStatus.CONFIGURED,
        description="Webhook configuration state",
    )
    billing_mode: PhoneNumberBillingMode = Field(
        default=PhoneNumberBillingMode.PLATFORM_RENTAL,
        description="Whether recurring platform rental credits apply",
    )
    configuration_error: Optional[str] = Field(
        None, max_length=1000, description="Most recent configuration error"
    )
    last_verified_at: Optional[datetime] = Field(
        None, description="When provider webhook connectivity was last verified"
    )


class PhoneNumberCreate(PhoneNumberBase):
    """Model for creating a new phone number record."""

    organization_id: UUID = Field(..., description="Organization that owns this number")
    provider_sid: Optional[str] = Field(
        None, description="Provider's SID for the phone number"
    )
    connection_token_hash: Optional[str] = Field(
        None, max_length=64, description="Hash of a customer webhook verification token"
    )
    connection_token_encrypted: Optional[str] = Field(
        None,
        description="Encrypted customer webhook verification token for pending setup",
    )
    provisioning_idempotency_key: Optional[str] = Field(
        None,
        max_length=255,
        description="Stable retry key for a platform provisioning attempt",
    )


class PhoneNumberUpdate(BaseModel):
    """Model for updating a phone number."""

    status: Optional[PhoneNumberStatus] = None
    assigned_agent_id: Optional[UUID] = None
    is_incoming_enabled: Optional[bool] = None
    is_outgoing_enabled: Optional[bool] = None


class PhoneNumber(PhoneNumberBase):
    """Complete phone number model."""

    id: UUID = Field(..., description="Phone number ID")
    organization_id: UUID = Field(..., description="Organization that owns this number")
    purchased_at: datetime = Field(..., description="When the number was purchased")
    cancelled_at: Optional[datetime] = Field(
        None, description="When the number was cancelled (if applicable)"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class PhoneNumberWithAgent(PhoneNumber):
    """Phone number with agent details for display."""

    agent_name: Optional[str] = Field(None, description="Name of assigned agent")


class AvailablePhoneNumber(BaseModel):
    """Model for available phone numbers from provider search."""

    phone_number: str = Field(..., description="Phone number in E.164 format")
    phone_number_type: PhoneNumberType = Field(..., description="Type of phone number")
    country_code: str = Field(..., description="Country code")
    area_code: Optional[str] = Field(None, description="Area code")
    monthly_cost_credits: int = Field(..., description="Monthly cost in credits")
    is_included_in_plan: bool = Field(
        default=False,
        description="Whether this would use the included US local number allowance",
    )
    capabilities: dict[str, bool] = Field(
        default_factory=dict,
        description="Capabilities (voice, sms, mms)",
    )
    locality: Optional[str] = Field(None, description="City or locality")
    postal_code: Optional[str] = Field(None, description="Postal code")


class PhoneNumberSearchRequest(BaseModel):
    """Request model for searching available phone numbers."""

    country_code: str = Field(
        default="US", min_length=2, max_length=2, description="Country code"
    )
    phone_number_type: PhoneNumberType = Field(
        default=PhoneNumberType.LOCAL, description="Type of phone number"
    )
    area_code: Optional[str] = Field(
        None, max_length=10, description="Filter by area code"
    )
    contains: Optional[str] = Field(
        None, max_length=16, description="Pattern to search for in number"
    )
    search_mode: PhoneNumberSearchMode = Field(
        default=PhoneNumberSearchMode.CONTAINS,
        description="Whether the pattern can occur anywhere, at the beginning, or at the end",
    )
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(
        default=50, ge=1, le=50, description="Results per page (max 50)"
    )


class PhoneNumberPurchaseRequest(BaseModel):
    """Request model for purchasing a phone number."""

    phone_number: str = Field(..., description="Phone number to purchase")
    country_code: str = Field(
        default="US", min_length=2, max_length=2, description="Country code"
    )
    phone_number_type: PhoneNumberType = Field(
        default=PhoneNumberType.LOCAL, description="Type of phone number"
    )
    expected_included_in_plan: bool = Field(
        default=False,
        description="Whether search showed this as the included US local number",
    )


class PhoneNumberImportRequest(BaseModel):
    """Request to connect a customer-owned Twilio number."""

    phone_number: str = Field(..., min_length=1, max_length=32)
    country_code: str = Field(
        default="US", min_length=2, max_length=2, description="Country code"
    )
    phone_number_type: PhoneNumberType = Field(
        default=PhoneNumberType.LOCAL, description="Number type"
    )
    agent_id: Optional[UUID] = Field(
        None, description="Optional agent to assign after verification"
    )


class PhoneNumberImportResponse(BaseModel):
    """Response containing tokenized webhook URLs for an imported number."""

    success: bool
    phone_number: PhoneNumber
    voice_url: str
    status_callback: str
    message: str


class PhoneNumberWebhookDetailsResponse(BaseModel):
    """Tokenized webhook URLs for a customer number awaiting verification."""

    phone_number_id: UUID
    phone_number: str
    voice_url: str
    status_callback: str
    message: str


class PhoneNumberAssignRequest(BaseModel):
    """Request model for assigning a phone number to an agent."""

    agent_id: UUID = Field(..., description="UUID of the agent to assign")


class PhoneNumberSearchResponse(BaseModel):
    """Response model for phone number search."""

    items: list[AvailablePhoneNumber]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class PhoneNumberPurchaseResponse(BaseModel):
    """Response model for phone number purchase."""

    success: bool
    phone_number: PhoneNumber
    message: str
    credit_balance_after: int


class PhoneNumberListResponse(BaseModel):
    """Response model for listing owned phone numbers."""

    items: list[PhoneNumberWithAgent]
    total_count: int
    unused_count: int
