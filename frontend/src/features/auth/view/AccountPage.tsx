import { zodResolver } from '@hookform/resolvers/zod'
import { KeyRound, UserRound } from 'lucide-react'
import { useForm } from 'react-hook-form'

import { Badge, Button, Card, CardHeader, ErrorState, Spinner, TextField } from '@/shared/ui'
import { friendlyMessage } from '@/shared/api/errors'

import { useChangePassword, useMe } from '../controller/useAuth'
import { changePasswordSchema, type ChangePasswordValues } from '../model/schemas'

export default function AccountPage() {
  const me = useMe()
  const change = useChangePassword()
  const { register, handleSubmit, formState, reset } = useForm<ChangePasswordValues>({ resolver: zodResolver(changePasswordSchema) })

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6 px-4 py-8">
      <h1 className="text-2xl font-semibold tracking-tight">Account</h1>

      <Card>
        <CardHeader title="Profile" description="To change your name or email, just ask the assistant." />
        <div className="px-5 py-4">
          {me.isPending && <Spinner />}
          {me.isError && <ErrorState message={friendlyMessage(me.error)} onRetry={() => me.refetch()} />}
          {me.data && (
            <div className="flex items-center gap-4">
              <span className="grid size-12 place-items-center rounded-full bg-brand-100 text-brand-800 dark:bg-brand-900 dark:text-brand-200">
                <UserRound className="size-6" />
              </span>
              <div>
                <p className="font-medium">{me.data.name}</p>
                <Badge tone="brand" className="mt-1 capitalize">
                  {me.data.role}
                </Badge>
              </div>
            </div>
          )}
        </div>
      </Card>

      <Card>
        <CardHeader title="Change password" description="Every other signed-in device is signed out." />
        <form
          noValidate
          className="space-y-4 px-5 py-4"
          onSubmit={handleSubmit((values) => change.mutate(values, { onSuccess: () => reset() }))}
        >
          <TextField label="Current password" type="password" autoComplete="current-password" error={formState.errors.current_password?.message} {...register('current_password')} />
          <TextField label="New password" type="password" autoComplete="new-password" error={formState.errors.new_password?.message} {...register('new_password')} />
          <TextField label="Repeat new password" type="password" autoComplete="new-password" error={formState.errors.confirm?.message} {...register('confirm')} />
          <Button type="submit" icon={<KeyRound className="size-4" />} loading={change.isPending}>
            Update password
          </Button>
        </form>
      </Card>
    </div>
  )
}
