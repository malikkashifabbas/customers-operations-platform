import { zodResolver } from '@hookform/resolvers/zod'
import { ArrowLeft, Send } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router'

import { Button, Card, TextAreaField, TextField } from '@/shared/ui'

import { useCreateTicket } from '../controller/useTickets'
import { newTicketSchema, type NewTicketValues } from '../model/schemas'

export default function NewTicketPage() {
  const create = useCreateTicket()
  const { register, handleSubmit, formState } = useForm<NewTicketValues>({ resolver: zodResolver(newTicketSchema) })

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6 px-4 py-8">
      <Link to="/tickets" className="inline-flex items-center gap-1.5 text-sm text-fg-muted hover:text-fg">
        <ArrowLeft className="size-4" />
        All tickets
      </Link>
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">New support ticket</h1>
        <p className="mt-1 text-sm text-fg-muted">Mention the order number (like ORD-1001) if it is about an order.</p>
      </div>
      <Card className="p-5">
        <form onSubmit={handleSubmit((values) => create.mutate(values))} className="space-y-4" noValidate>
          <TextField label="Subject" placeholder="Refund for ORD-1001" error={formState.errors.subject?.message} {...register('subject')} />
          <TextAreaField label="What happened?" rows={6} error={formState.errors.body?.message} {...register('body')} />
          <div className="flex justify-end">
            <Button type="submit" icon={<Send className="size-4" />} loading={create.isPending}>
              Submit ticket
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}
