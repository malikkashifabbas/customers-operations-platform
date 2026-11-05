import { z } from 'zod'

export const newCustomerSchema = z.object({
  full_name: z.string().trim().min(1, 'Enter a name').max(200),
  phone: z
    .string()
    .trim()
    .min(7, 'Enter the full phone number')
    .max(32)
    .regex(/^\+?[\d\s-]+$/, 'Digits only, with an optional + at the start'),
  email: z.union([z.email('Enter a valid email'), z.literal('')]),
  password: z.union([z.string().min(8, 'At least 8 characters').max(128), z.literal('')]),
})
export type NewCustomerValues = z.infer<typeof newCustomerSchema>
