import { LifeBuoy, MessagesSquare, ShieldCheck, UserRound, Users } from 'lucide-react'
import { lazy } from 'react'
import { createBrowserRouter, Navigate } from 'react-router'

import { RedirectIfSignedIn, RequireRole } from './guards'
import { HomeRedirect } from './HomeRedirect'
import { RouteError } from './RouteError'
import { AppLayout, type NavItem } from './layouts/AppLayout'

// Every page is its own chunk: the login page never downloads chat, markdown or staff code.
const CustomerLoginPage = lazy(() => import('@/features/auth/view/CustomerLoginPage'))
const SignupPage = lazy(() => import('@/features/auth/view/SignupPage'))
const StaffLoginPage = lazy(() => import('@/features/auth/view/StaffLoginPage'))
const AccountPage = lazy(() => import('@/features/auth/view/AccountPage'))
const ChatPage = lazy(() => import('@/features/chat/view/ChatPage'))
const TicketsPage = lazy(() => import('@/features/tickets/view/TicketsPage'))
const NewTicketPage = lazy(() => import('@/features/tickets/view/NewTicketPage'))
const TicketDetailPage = lazy(() => import('@/features/tickets/view/TicketDetailPage'))
const ApprovalsPage = lazy(() => import('@/features/staff/view/ApprovalsPage'))
const CustomersPage = lazy(() => import('@/features/staff/view/CustomersPage'))
const NotFoundPage = lazy(() => import('./NotFoundPage'))

const CUSTOMER_NAV: NavItem[] = [
  { to: '/chat', label: 'Chat', icon: MessagesSquare },
  { to: '/tickets', label: 'Tickets', icon: LifeBuoy },
  { to: '/account', label: 'Account', icon: UserRound },
]

const STAFF_NAV: NavItem[] = [
  { to: '/staff/approvals', label: 'Approvals', icon: ShieldCheck },
  { to: '/staff/customers', label: 'Customers', icon: Users },
]

export const router = createBrowserRouter([
  {
    errorElement: <RouteError />,
    children: [
      { index: true, element: <HomeRedirect /> },
      {
        element: <RedirectIfSignedIn />,
        children: [
          { path: 'staff/login', element: <StaffLoginPage /> },
          { path: ':tenantSlug/login', element: <CustomerLoginPage /> },
          { path: ':tenantSlug/signup', element: <SignupPage /> },
        ],
      },
      {
        element: <RequireRole role="customer" />,
        children: [
          {
            element: <AppLayout nav={CUSTOMER_NAV} area="Customer" fullHeight />,
            children: [{ path: 'chat/:conversationId?', element: <ChatPage /> }],
          },
          {
            element: <AppLayout nav={CUSTOMER_NAV} area="Customer" />,
            children: [
              { path: 'tickets', element: <TicketsPage /> },
              { path: 'tickets/new', element: <NewTicketPage /> },
              { path: 'tickets/:ticketId', element: <TicketDetailPage /> },
              { path: 'account', element: <AccountPage /> },
            ],
          },
        ],
      },
      {
        element: <RequireRole role="staff" />,
        children: [
          {
            element: <AppLayout nav={STAFF_NAV} area="Staff" />,
            children: [
              { path: 'staff', element: <Navigate to="/staff/approvals" replace /> },
              { path: 'staff/approvals', element: <ApprovalsPage /> },
              { path: 'staff/customers', element: <CustomersPage /> },
            ],
          },
        ],
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
