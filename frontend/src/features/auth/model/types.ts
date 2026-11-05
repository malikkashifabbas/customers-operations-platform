export type Role = 'customer' | 'staff'

export type Tokens = {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export type AccessToken = Omit<Tokens, 'refresh_token'>

export type Me = {
  role: Role
  name: string
  tenant_public_id: string
  customer_public_id: string | null
  staff_public_id: string | null
}

export type TenantPublic = {
  public_id: string
  name: string
  slug: string
}
