import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Link, useParams } from 'react-router'

import { friendlyMessage } from '@/shared/api/errors'
import { config } from '@/shared/config'
import { Button, ErrorState, PageSpinner, TextField } from '@/shared/ui'

import { useCustomerLogin, useTenant } from '../controller/useAuth'
import { customerLoginSchema, type CustomerLoginValues } from '../model/schemas'
import { AuthShell } from './AuthShell'

export default function CustomerLoginPage() {
  const { tenantSlug = config.defaultTenant } = useParams()
  const tenant = useTenant(tenantSlug)
  const login = useCustomerLogin(tenant.data)
  const { register, handleSubmit, formState } = useForm<CustomerLoginValues>({ resolver: zodResolver(customerLoginSchema) })

  if (tenant.isPending) return <PageSpinner />
  if (tenant.isError) {
    return (
      <AuthShell title="Company not found" subtitle={`No company uses the address "${tenantSlug}".`}>
        <Link to={`/${config.defaultTenant}/login`} className="text-sm font-medium text-primary">
          Go to the demo company
        </Link>
      </AuthShell>
    )
  }

  return (
    <AuthShell
      title={`Sign in to ${tenant.data.name}`}
      subtitle="Use the phone number on your account."
      footer={
        <>
          New here?{' '}
          <Link to={`/${tenantSlug}/signup`} className="font-medium text-primary">
            Create an account
          </Link>
          <span className="mx-2">·</span>
          <Link to="/staff/login" className="font-medium text-primary">
            Staff sign in
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit((values) => login.mutate(values))} className="space-y-4" noValidate>
        {login.isError && <ErrorState message={friendlyMessage(login.error)} />}
        <TextField label="Phone number" type="tel" autoComplete="tel" placeholder="+92 300 1234567" error={formState.errors.phone?.message} {...register('phone')} />
        <TextField label="Password" type="password" autoComplete="current-password" error={formState.errors.password?.message} {...register('password')} />
        <Button type="submit" size="lg" className="w-full" loading={login.isPending}>
          Sign in
        </Button>
      </form>
    </AuthShell>
  )
}
