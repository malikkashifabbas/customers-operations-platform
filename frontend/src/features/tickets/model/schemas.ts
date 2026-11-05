import { z } from 'zod'

export const newTicketSchema = z.object({
  subject: z.string().trim().min(3, 'Give the ticket a short subject').max(200),
  body: z.string().trim().min(10, 'Describe the problem in a sentence or two').max(5000),
})
export type NewTicketValues = z.infer<typeof newTicketSchema>
