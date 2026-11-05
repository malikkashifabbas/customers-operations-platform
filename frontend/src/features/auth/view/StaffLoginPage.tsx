import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router'

import { friendlyMessage } from '@/shared/api/errors'
import { config } from '@/shared/config'
import { Button, ErrorState, TextField } from '@/shared/ui'

import { useStaffLogin } from '../controller/useAuth'
import { staffLoginSchema, type StaffLoginValues } from '../model/schemas'
import { AuthShell } from './AuthShell'

export default function StaffLoginPage() {
  const login = useStaffLogin()
  const { register, handleSubmit, formState } = useForm<StaffLoginValues>({ resolver: zodResolver(staffLoginSchema) })

  return (
    <AuthShell
      title="Staff sign in"
      subtitle="Approve refunds and manage customers."
      footer={
        <Link to={`/${config.defaultTenant}/login`} className="font-medium text-primary">
          Customer sign in
        </Link>
      }
    >
      <form onSubmit={handleSubmit((values) => login.mutate(values))} className="space-y-4" noValidate>
        {login.isError && <ErrorState message={friendlyMessage(login.error)} />}
        <TextField label="Username" autoComplete="username" error={formState.errors.username?.message} {...register('username')} />
        <TextField label="Password" type="password" autoComplete="current-password" error={formState.errors.password?.message} {...register('password')} />
        <Button type="submit" size="lg" className="w-full" loading={login.isPending}>
          Sign in
        </Button>
      </form>
    </AuthShell>
  )
}
