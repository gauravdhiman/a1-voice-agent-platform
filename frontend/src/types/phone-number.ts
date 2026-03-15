/**
 * Phone Number-related type definitions
 */

export type PhoneNumberProvider = "twilio";

export type PhoneNumberStatus =
  | "available"
  | "purchased"
  | "active"
  | "inactive"
  | "cancelled";

export type PhoneNumberType = "local" | "toll_free" | "mobile";

export interface PhoneNumberBase {
  phone_number: string;
  provider: PhoneNumberProvider;
  provider_sid: string | null;
  phone_number_type: PhoneNumberType;
  country_code: string;
  area_code: string | null;
  monthly_cost_credits: number;
  status: PhoneNumberStatus;
  assigned_agent_id: string | null;
  is_incoming_enabled: boolean;
  is_outgoing_enabled: boolean;
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
  capabilities: {
    voice?: boolean;
    sms?: boolean;
    mms?: boolean;
  };
  locality: string | null;
  postal_code: string | null;
}

export interface PhoneNumberSearchRequest {
  country_code?: string;
  phone_number_type?: PhoneNumberType;
  area_code?: string | null;
  contains?: string | null;
  page?: number;
  page_size?: number;
}

export interface PhoneNumberPurchaseRequest {
  phone_number: string;
  country_code?: string;
  phone_number_type?: PhoneNumberType;
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
    purchased: "green",
    active: "green",
    inactive: "gray",
    cancelled: "red",
  };
  return colors[status] || "gray";
};

export const getPhoneNumberStatusLabel = (status: PhoneNumberStatus): string => {
  const labels: Record<PhoneNumberStatus, string> = {
    available: "Available",
    purchased: "Purchased",
    active: "Active",
    inactive: "Inactive",
    cancelled: "Cancelled",
  };
  return labels[status] || status;
};

export const getCreditsForType = (type: PhoneNumberType): number => {
  const costs: Record<PhoneNumberType, number> = {
    local: 200,
    toll_free: 500,
    mobile: 200,
  };
  return costs[type] || 200;
};
