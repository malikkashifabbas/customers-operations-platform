import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Link, Navigate, useParams } from 'react-router'

import { friendlyMessage } from '@/shared/api/errors'
import { config } from '@/shared/config'
import { Button, ErrorState, PageSpinner, TextField } from '@/shared/ui'

import { useSignup, useTenant } from '../controller/useAuth'
import { signupSchema, type SignupValues } from '../model/schemas'
import { AuthShell } from './AuthShell'

export default function SignupPage() {
  const { tenantSlug = config.defaultTenant } = useParams()
  const tenant = useTenant(tenantSlug)
  const signup = useSignup(tenant.data)
  const { register, handleSubmit, formState } = useForm<SignupValues>({
    resolver: zodResolver(signupSchema),
    defaultValues: { email: '' },
  })

  if (tenant.isPending) return <PageSpinner />
  if (tenant.isError) return <Navigate to={`/${tenantSlug}/login`} replace />

  return (
    <AuthShell
      title={`Join ${tenant.data.name}`}
      subtitle="Your phone number is your account."
      footer={
        <>
          Already have an account?{' '}
          <Link to={`/${tenantSlug}/login`} className="font-medium text-primary">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit((values) => signup.mutate(values))} className="space-y-4" noValidate>
        {signup.isError && <ErrorState message={friendlyMessage(signup.error)} />}
        <TextField label="Full name" autoComplete="name" error={formState.errors.full_name?.message} {...register('full_name')} />
        <TextField label="Phone number" type="tel" autoComplete="tel" error={formState.errors.phone?.message} {...register('phone')} />
        <TextField label="Email (optional)" type="email" autoComplete="email" error={formState.errors.email?.message} {...register('email')} />
        <TextField label="Password" type="password" autoComplete="new-password" hint="At least 8 characters." error={formState.errors.password?.message} {...register('password')} />
        <Button type="submit" size="lg" className="w-full" loading={signup.isPending}>
          Create account
        </Button>
      </form>
    </AuthShell>
  )
}
