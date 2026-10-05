/**
 * Phone Number-related type definitions
 */

export type PhoneNumberProvider = "twilio";

export type PhoneNumberStatus =
  | "available"
  | "provisioning"
  | "purchased"
  | "active"
  | "inactive"
  | "cancelled"
  | "verification_required"
  | "release_pending"
  | "disconnected";

export type PhoneNumberProvisioningSource = "platform" | "customer";
export type PhoneNumberManagementMode = "platform_managed" | "customer_managed";
export type PhoneNumberConfigurationStatus =
  | "pending"
  | "configured"
  | "verification_required"
  | "failed";
export type PhoneNumberBillingMode = "platform_rental" | "none";
export type PhoneNumberBillingStatus = "active" | "past_due";

export type PhoneNumberType = "local" | "toll_free" | "mobile";
export type PhoneNumberSearchMode =
  | "contains"
  | "begins_with"
  | "ends_with";

export interface PhoneNumberBase {
  phone_number: string;
  provider: PhoneNumberProvider;
  provider_sid: string | null;
  phone_number_type: PhoneNumberType;
  country_code: string;
  area_code: string | null;
  monthly_cost_credits: number;
  is_included_in_plan?: boolean;
  status: PhoneNumberStatus;
  assigned_agent_id: string | null;
  is_incoming_enabled: boolean;
  is_outgoing_enabled: boolean;
  billing_status: PhoneNumberBillingStatus;
  billing_mode: PhoneNumberBillingMode;
  provisioning_source: PhoneNumberProvisioningSource;
  management_mode: PhoneNumberManagementMode;
  configuration_status: PhoneNumberConfigurationStatus;
  configuration_error: string | null;
  last_verified_at: string | null;
  next_billing_at: string | null;
  billing_grace_ends_at: string | null;
}

export interface PhoneNumber extends PhoneNumberBase {
  id: string;
  organization_id: string;
  purchased_at: string;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PhoneNumberWithAgent extends PhoneNumber {
  agent_name: string | null;
}

export interface AvailablePhoneNumber {
  phone_number: string;
  phone_number_type: PhoneNumberType;
  country_code: string;
  area_code: string | null;
  monthly_cost_credits: number;
  is_included_in_plan?: boolean;
  capabilities: {
    voice?: boolean;
    sms?: boolean;
    mms?: boolean;
  };
  locality: string | null;
  postal_code: string | null;
}

export interface PhoneNumberSearchRequest {
  organization_id: string;
  country_code?: string;
  phone_number_type?: PhoneNumberType;
  area_code?: string | null;
  contains?: string | null;
  search_mode?: PhoneNumberSearchMode;
  page?: number;
  page_size?: number;
}

export interface PhoneNumberPurchaseRequest {
  phone_number: string;
  country_code?: string;
  phone_number_type?: PhoneNumberType;
  expected_included_in_plan?: boolean;
}

export interface PhoneNumberAssignRequest {
  agent_id: string;
}

export interface PhoneNumberSearchResponse {
  items: AvailablePhoneNumber[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PhoneNumberPurchaseResponse {
  success: boolean;
  phone_number: PhoneNumber;
  message: string;
  credit_balance_after: number;
}

export interface PhoneNumberImportRequest {
  phone_number: string;
  country_code?: string;
  phone_number_type?: PhoneNumberType;
  agent_id?: string;
}

export interface PhoneNumberImportResponse {
  success: boolean;
  phone_number: PhoneNumber;
  voice_url: string;
  status_callback: string;
  message: string;
}

export interface PhoneNumberWebhookDetailsResponse {
  phone_number_id: string;
  phone_number: string;
  voice_url: string;
  status_callback: string;
  message: string;
}

export interface PhoneNumberListResponse {
  items: PhoneNumberWithAgent[];
  total_count: number;
  unused_count: number;
}

export const formatPhoneNumber = (phoneNumber: string): string => {
  const cleaned = phoneNumber.replace(/\D/g, "");
  if (cleaned.length === 11 && cleaned.startsWith("1")) {
    return `+1 (${cleaned.slice(1, 4)}) ${cleaned.slice(4, 7)}-${cleaned.slice(7)}`;
  }
  if (cleaned.length === 10) {
    return `+1 (${cleaned.slice(0, 3)}) ${cleaned.slice(3, 6)}-${cleaned.slice(6)}`;
  }
  return phoneNumber;
};

export const getPhoneNumberTypeLabel = (type: PhoneNumberType): string => {
  const labels: Record<PhoneNumberType, string> = {
    local: "Local",
    toll_free: "Toll-Free",
    mobile: "Mobile",
  };
  return labels[type] || type;
};

export const getPhoneNumberStatusColor = (status: PhoneNumberStatus): string => {
  const colors: Record<PhoneNumberStatus, string> = {
    available: "blue",
    provisioning: "yellow",
    purchased: "green",
    active: "green",
    inactive: "gray",
    cancelled: "red",
    verification_required: "yellow",
    release_pending: "orange",
    disconnected: "gray",
  };
  return colors[status] || "gray";
};

export const getPhoneNumberStatusLabel = (status: PhoneNumberStatus): string => {
  const labels: Record<PhoneNumberStatus, string> = {
    available: "Available",
    provisioning: "Provisioning",
    purchased: "Purchased",
    active: "Active",
    inactive: "Inactive",
    cancelled: "Cancelled",
    verification_required: "Verification required",
    release_pending: "Release pending",
    disconnected: "Disconnected",
  };
  return labels[status] || status;
};

export const getCreditsForType = (type: PhoneNumberType): number => {
  const costs: Record<PhoneNumberType, number> = {
    local: 80,
    toll_free: 120,
    mobile: 200,
  };
  return costs[type] || 200;
};
