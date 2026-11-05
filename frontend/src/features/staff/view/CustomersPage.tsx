import { zodResolver } from '@hookform/resolvers/zod'
import { ChevronLeft, ChevronRight, KeyRound, UserPlus, Users } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'

import { friendlyMessage } from '@/shared/api/errors'
import { formatRelative } from '@/shared/lib/format'
import { Button, Card, CardHeader, EmptyState, ErrorState, PageSpinner, TextField } from '@/shared/ui'

import { useCreateCustomer, useCustomers, useSetCustomerPassword } from '../controller/useStaff'
import { newCustomerSchema, type NewCustomerValues } from '../model/schemas'
import { PAGE_SIZE } from '../model/staffApi'
import type { Customer } from '../model/types'

export default function CustomersPage() {
  const [offset, setOffset] = useState(0)
  const customers = useCustomers(offset)
  const total = customers.data?.count ?? 0

  return (
    <div className="mx-auto grid w-full max-w-6xl gap-6 px-4 py-8 lg:grid-cols-[1fr_22rem]">
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold tracking-tight">Customers</h1>
        {customers.isPending && <PageSpinner />}
        {customers.isError && <ErrorState message={friendlyMessage(customers.error)} onRetry={() => customers.refetch()} />}
        {customers.data && (
          <Card className="overflow-hidden">
            {customers.data.items.length === 0 ? (
              <EmptyState icon={<Users className="size-6" />} title="No customers yet" />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-surface-2 text-xs tracking-wide text-fg-muted uppercase">
                    <tr>
                      <th className="px-4 py-3 font-medium">Name</th>
                      <th className="px-4 py-3 font-medium">Phone</th>
                      <th className="hidden px-4 py-3 font-medium md:table-cell">Email</th>
                      <th className="hidden px-4 py-3 font-medium sm:table-cell">Joined</th>
                      <th className="px-4 py-3" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {customers.data.items.map((customer) => (
                      <CustomerRow key={customer.public_id} customer={customer} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div className="flex items-center justify-between border-t border-line px-4 py-2.5 text-sm text-fg-muted">
              <span>
                {total === 0 ? 0 : offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
              </span>
              <div className="flex gap-1">
                <Button variant="ghost" size="icon" aria-label="Previous page" disabled={offset === 0} onClick={() => setOffset(offset - PAGE_SIZE)}>
                  <ChevronLeft className="size-4" />
                </Button>
                <Button variant="ghost" size="icon" aria-label="Next page" disabled={offset + PAGE_SIZE >= total} onClick={() => setOffset(offset + PAGE_SIZE)}>
                  <ChevronRight className="size-4" />
                </Button>
              </div>
            </div>
          </Card>
        )}
      </div>
      <NewCustomerCard />
    </div>
  )
}

function CustomerRow({ customer }: { customer: Customer }) {
  const setPassword = useSetCustomerPassword()
  const [editing, setEditing] = useState(false)
  const [password, setPasswordValue] = useState('')

  return (
    <tr className="align-top">
      <td className="px-4 py-3 font-medium">{customer.full_name}</td>
      <td className="px-4 py-3 font-mono text-xs">{customer.phone}</td>
      <td className="hidden px-4 py-3 text-fg-muted md:table-cell">{customer.email ?? '—'}</td>
      <td className="hidden px-4 py-3 text-fg-muted sm:table-cell">{formatRelative(customer.created_at)}</td>
      <td className="px-4 py-3 text-right">
        {editing ? (
          <form
            className="flex justify-end gap-1.5"
            onSubmit={(event) => {
              event.preventDefault()
              setPassword.mutate({ id: customer.public_id, password }, { onSuccess: () => setEditing(false) })
            }}
          >
            <input
              type="password"
              value={password}
              minLength={8}
              required
              autoFocus
              aria-label={`New password for ${customer.full_name}`}
              onChange={(event) => setPasswordValue(event.target.value)}
              className="h-8 w-32 rounded-lg border border-line bg-surface px-2 text-sm focus:border-ring focus:outline-none"
            />
            <Button type="submit" size="sm" loading={setPassword.isPending}>
              Save
            </Button>
          </form>
        ) : (
          <Button variant="ghost" size="sm" icon={<KeyRound className="size-3.5" />} onClick={() => setEditing(true)}>
            Set password
          </Button>
        )}
      </td>
    </tr>
  )
}

function NewCustomerCard() {
  const create = useCreateCustomer()
  const { register, handleSubmit, formState, reset } = useForm<NewCustomerValues>({
    resolver: zodResolver(newCustomerSchema),
    defaultValues: { email: '', password: '' },
  })

  return (
    <Card className="h-fit">
      <CardHeader title="Add customer" description="Without a password they cannot sign in yet." />
      <form noValidate className="space-y-3 px-5 py-4" onSubmit={handleSubmit((values) => create.mutate(values, { onSuccess: () => reset() }))}>
        <TextField label="Full name" error={formState.errors.full_name?.message} {...register('full_name')} />
        <TextField label="Phone" type="tel" error={formState.errors.phone?.message} {...register('phone')} />
        <TextField label="Email (optional)" type="email" error={formState.errors.email?.message} {...register('email')} />
        <TextField label="Password (optional)" type="password" autoComplete="new-password" error={formState.errors.password?.message} {...register('password')} />
        <Button type="submit" className="w-full" icon={<UserPlus className="size-4" />} loading={create.isPending}>
          Add customer
        </Button>
      </form>
    </Card>
  )
}
