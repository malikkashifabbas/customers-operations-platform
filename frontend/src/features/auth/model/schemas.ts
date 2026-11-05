import { z } from 'zod'

// Same limits as the Django schemas, so the form rejects what the API would reject, before the request.
const phone = z
  .string()
  .trim()
  .min(7, 'Enter your full phone number')
  .max(32)
  .regex(/^\+?[\d\s-]+$/, 'Digits only, with an optional + at the start')
const password = z.string().min(1, 'Enter your password').max(128)
const newPassword = z.string().min(8, 'At least 8 characters').max(128)

export const customerLoginSchema = z.object({ phone, password })
export type CustomerLoginValues = z.infer<typeof customerLoginSchema>

export const signupSchema = z.object({
  full_name: z.string().trim().min(1, 'Enter your name').max(200),
  phone,
  email: z.union([z.email('Enter a valid email'), z.literal('')]),
  password: newPassword,
})
export type SignupValues = z.infer<typeof signupSchema>

export const staffLoginSchema = z.object({ username: z.string().trim().min(1, 'Enter your username').max(150), password })
export type StaffLoginValues = z.infer<typeof staffLoginSchema>

export const changePasswordSchema = z
  .object({ current_password: password, new_password: newPassword, confirm: z.string() })
  .refine((v) => v.new_password === v.confirm, { path: ['confirm'], message: 'Passwords do not match' })
export type ChangePasswordValues = z.infer<typeof changePasswordSchema>
