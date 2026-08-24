export type Department = {
  id: string;
  name: string;
  code: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type Permission = {
  id: string;
  code: string;
  name: string;
  description: string | null;
};

export type Role = {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  created_at: string;
  updated_at: string;
  permissions: Permission[];
};

export type User = {
  id: string;
  email: string;
  full_name: string;
  employee_code: string | null;
  username: string | null;
  department_id: string | null;
  department: { id: string; name: string; code: string } | null;
  manager_id: string | null;
  is_active: boolean;
  is_verified: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
  roles: string[];
  permissions?: string[];
  team_ids?: string[];
};

export type TeamMember = {
  user_id: string;
  full_name: string;
  email: string;
  is_lead: boolean;
};

export type Team = {
  id: string;
  name: string;
  code: string;
  description: string | null;
  department_id: string;
  department: { id: string; name: string; code: string } | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  members: TeamMember[] | null;
};

export type Page<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
};
