import { LogOut, type LucideIcon } from 'lucide-react'
import { Suspense } from 'react'
import { NavLink, Outlet } from 'react-router'

import { useLogout, useMe } from '@/features/auth/controller/useAuth'
import { cn } from '@/shared/lib/cn'
import { Button, Logo, PageSpinner, ThemeToggle } from '@/shared/ui'

export type NavItem = { to: string; label: string; icon: LucideIcon }

/** Shared shell for customer and staff areas: top bar on wide screens, bottom tab bar on phones. */
export function AppLayout({ nav, area, fullHeight = false }: { nav: NavItem[]; area: string; fullHeight?: boolean }) {
  const me = useMe()
  const logout = useLogout()

  return (
    <div className="flex h-full flex-col">
      <header className="sticky top-0 z-20 border-b border-line bg-surface/85 backdrop-blur">
        <div className="flex h-14 items-center gap-4 px-4">
          <Logo />
          <span className="hidden rounded-md bg-beacon-100 px-2 py-0.5 text-xs font-semibold text-beacon-700 sm:inline dark:bg-beacon-700/30 dark:text-beacon-200">
            {area}
          </span>
          <nav className="ml-4 hidden items-center gap-1 sm:flex" aria-label="Main">
            {nav.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  cn(
                    'inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors',
                    isActive ? 'bg-brand-50 text-brand-800 dark:bg-brand-950 dark:text-brand-200' : 'text-fg-muted hover:bg-surface-2 hover:text-fg',
                  )
                }
              >
                <Icon className="size-4" />
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-1">
            {me.data && <span className="mr-2 hidden text-sm text-fg-muted md:inline">{me.data.name}</span>}
            <ThemeToggle />
            <Button variant="ghost" size="icon" onClick={() => logout.mutate()} loading={logout.isPending} aria-label="Sign out">
              {!logout.isPending && <LogOut className="size-4.5" />}
            </Button>
          </div>
        </div>
      </header>

      <main className={cn('min-h-0 flex-1 pb-16 sm:pb-0', fullHeight ? 'overflow-hidden' : 'overflow-y-auto')}>
        <Suspense fallback={<PageSpinner />}>
          <Outlet />
        </Suspense>
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-20 flex border-t border-line bg-surface sm:hidden" aria-label="Main">
        {nav.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => cn('flex flex-1 flex-col items-center gap-0.5 py-2 text-xs', isActive ? 'text-primary' : 'text-fg-muted')}
          >
            <Icon className="size-5" />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
