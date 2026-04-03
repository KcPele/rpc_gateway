// Backend API Response Types based on actual backend implementation

import { NodeHealth, User } from "./api.types";

// Auth Response Types
export interface AuthLoginResponse {
  success: boolean;
  data: {
    token: string;
    user: {
      id: string;
      email: string;
      isAdmin: boolean;
      isActive: boolean;
      createdAt: string;
      updatedAt: string;
    };
  };
}

export interface AuthRegisterResponse {
  success: boolean;
  data: {
    token: string;
    user: {
      id: string;
      email: string;
      isAdmin: boolean;
      isActive: boolean;
      createdAt: string;
      updatedAt: string;
    };
  };
}

export interface AuthMeResponse {
  success: boolean;
  data: {
    user: {
      id: string;
      email: string;
      isActive: boolean;
      createdAt: string;
      updatedAt: string;
    };
  };
}

// Error Response Type
export interface ErrorResponse {
  error: string;
  details?: any;
}

// Chain Response Types
export interface ChainResponse {
  _id: string;
  name: string;
  chainId: number;
  isEnabled: boolean;
  adminNotes?: string;
  createdAt: string;
  updatedAt: string;
}

export interface AdminSuccessResponse {
  success: boolean;
  message: string;
  data: {};
}

// Node Health Response Types (matching backend controller response)
export interface NodeHealthResponse {
  success: boolean;
  data: NodeHealth;
}

// App Response Types (from app.controller.ts)
export interface AppResponse {
  _id: string;
  userId: string;
  name: string;
  description?: string;
  apiKey?: string; // Optional for security (excluded in listings)
  chainName: string;
  chainId: string;
  isActive: boolean;
  requests: number;
  dailyRequests: number;
  maxRps: number;
  dailyRequestsLimit: number;
  lastResetDate: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateAppRequest {
  name: string;
  description?: string;
  chainName: string;
  chainId: string;
}

export interface UpdateAppRequest {
  name?: string;
  description?: string;
}

export interface CreateAppResponse {
  success: boolean;
  message: string;
  data: AppResponse;
}

export interface GetAppResponse {
  success: boolean;
  data: AppResponse;
}

export interface UpdateAppResponse {
  success: boolean;
  message: string;
  data: AppResponse;
}

export interface DeleteAppResponse {
  success: boolean;
  message: string;
}

export interface RegenerateKeyResponse {
  success: boolean;
  message: string;
  data: string;
}

export interface PaginationInfo {
  currentPage: number;
  totalPages: number;
  totalApps: number;
  hasNextPage: boolean;
  hasPrevPage: boolean;
}

export interface ListAppsResponse {
  success: boolean;
  message: string;
  data: {
    apps: AppResponse[];
    pagination: PaginationInfo;
  };
}

export interface DashboardStats {
  totalApps: number;
  activeApps: number;
  totalRequests: number;
  todaysRequests: number;
  maxApps: number;
}

export interface DashboardStatsResponse {
  success: boolean;
  message: string;
  data: {
    stats: DashboardStats;
  };
}

// Default App Settings Response Types
export interface DefaultAppSettingsResponse {
  _id: string;
  maxRps: number;
  dailyRequestsLimit: number;
  createdAt: string;
  updatedAt: string;
}

// Admin User Management Types
export interface AdminUserResponse {
  _id: string;
  email: string;
  isAdmin: boolean;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface AdminUsersListResponse {
  success: boolean;
  data: {
    users: AdminUserResponse[];
    total: number;
    page: number;
    limit: number;
    totalPages: number;
  };
}

export interface AdminAppsListResponse {
  success: boolean;
  data: {
    apps: AppResponse[];
    total: number;
    page: number;
    limit: number;
    totalPages: number;
  };
}

// Chain List Response
export interface AdminChainsListResponse {
  success: boolean;
  data: ChainResponse[];
}

// Auth Account Management Types
export interface UpdatePasswordRequest {
  currentPassword: string;
  newPassword: string;
}

export interface UpdateEmailRequest {
  email: string;
  password: string;
}

export interface UpdatePasswordResponse {
  success: boolean;
  message: string;
  data: User;
}

export interface UpdateEmailResponse {
  success: boolean;
  message: string;
  data: {
    id: string;
    email: string;
    isActive: boolean;
    createdAt: string;
    updatedAt: string;
  };
}

export interface ExportDataResponse {
  success: boolean;
  data: {
    user: {
      id: string;
      email: string;
      isActive: boolean;
      createdAt: string;
      updatedAt: string;
    };
    apps: Array<{
      id: string;
      name: string;
      description?: string;
      chainName: string;
      chainId: string;
      isActive: boolean;
      requests: number;
      dailyRequests: number;
      maxRps: number;
      dailyRequestsLimit: number;
      createdAt: string;
      updatedAt: string;
    }>;
    exportDate: string;
  };
}

// Usage Analytics Types
export interface HourlyData {
  hour: number;
  requests: number;
}

export interface AppUsageAnalyticsResponse {
  success: boolean;
  message: string;
  data: {
    analytics: {
      app: {
        id: string;
        name: string;
        chainName: string;
      };
      usage: {
        totalRequests: number;
        dailyRequests: number;
        dailyLimit: number;
        usagePercentage: number;
        maxRps: number;
        lastResetDate: string;
      };
      hourlyBreakdown: HourlyData[];
    };
  };
}

export interface AppUsageSummary {
  id: string;
  name: string;
  chainName: string;
  totalRequests: number;
  dailyRequests: number;
  dailyLimit: number;
  usagePercentage: number;
  isActive: boolean;
}

export interface AllAppsUsageAnalyticsResponse {
  success: boolean;
  message: string;
  data: {
    analytics: {
      summary: {
        totalApps: number;
        activeApps: number;
        totalRequests: number;
        dailyRequests: number;
      };
      apps: AppUsageSummary[];
    };
  };
}

// Default App Settings Response
export interface AdminDefaultSettingsResponse {
  success: boolean;
  data: DefaultAppSettingsResponse;
}
