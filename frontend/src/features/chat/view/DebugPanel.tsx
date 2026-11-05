import { Activity, Clock, Coins, ShieldAlert, Wrench } from 'lucide-react'
import type { ReactNode } from 'react'

import { formatMs } from '@/shared/lib/format'

import type { ChatMessage } from '../model/types'
import { RoutingChips } from './RoutingChips'

function Row({ icon, label, children }: { icon: ReactNode; label: string; children: ReactNode }) {
  return (
    <div className="space-y-1.5">
      <p className="flex items-center gap-1.5 text-xs font-medium tracking-wide text-fg-muted uppercase">
        {icon}
        {label}
      </p>
      <div className="text-sm text-fg">{children}</div>
    </div>
  )
}

/** Agent internals for the latest reply (routing, tools, guards, cost), so the demo shows what happened behind the answer. */
export function DebugPanel({ message }: { message: ChatMessage | undefined }) {
  const meta = message?.meta
  return (
    <aside className="hidden w-80 shrink-0 flex-col gap-5 overflow-y-auto border-l border-line bg-surface p-4 lg:flex" aria-label="Agent details">
      <h2 className="flex items-center gap-2 text-sm font-semibold">
        <Activity className="size-4 text-primary" />
        Agent details
      </h2>
      {!meta ? (
        <p className="text-sm text-fg-muted">Send a message to see which specialists answer, which tools they call and how long it takes.</p>
      ) : (
        <>
          <Row icon={<Activity className="size-3.5" />} label="Specialists">
            {meta.routes.length ? <RoutingChips routes={meta.routes} /> : <span className="text-fg-muted">None (answered by a guard)</span>}
          </Row>
          <Row icon={<Wrench className="size-3.5" />} label={`Tool calls (${meta.toolCalls.length})`}>
            {meta.toolCalls.length === 0 ? (
              <span className="text-fg-muted">No tools used</span>
            ) : (
              <ul className="space-y-2">
                {meta.toolCalls.map((call, index) => (
                  <li key={`${call.name}-${index}`} className="rounded-lg border border-line bg-surface-2 p-2">
                    <p className="font-mono text-xs font-semibold text-primary">{call.name}</p>
                    {Object.keys(call.args).length > 0 && <pre className="mt-1 overflow-x-auto font-mono text-[11px] text-fg-muted">{JSON.stringify(call.args, null, 2)}</pre>}
                  </li>
                ))}
              </ul>
            )}
          </Row>
          <Row icon={<ShieldAlert className="size-3.5" />} label="Guardrails">
            {meta.blockedReason ? (
              <span className="text-danger-500">Blocked: {meta.blockedReason.replaceAll('_', ' ')}</span>
            ) : meta.guardRewrites > 0 ? (
              <span className="text-warning-500">Output guard asked for {meta.guardRewrites} rewrite(s)</span>
            ) : (
              <span className="text-success-500">Passed</span>
            )}
          </Row>
          <div className="grid grid-cols-2 gap-3">
            <Row icon={<Clock className="size-3.5" />} label="Latency">
              {meta.latencyMs !== undefined ? formatMs(meta.latencyMs) : '…'}
            </Row>
            <Row icon={<Coins className="size-3.5" />} label="Tokens">
              {meta.tokens !== undefined ? `${meta.tokens.toLocaleString()} · ${meta.llmCalls} calls` : <span className="text-fg-muted">stream</span>}
            </Row>
          </div>
        </>
      )}
    </aside>
  )
}
