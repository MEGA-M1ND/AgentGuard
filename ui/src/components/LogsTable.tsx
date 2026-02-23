'use client'

interface AuditLog {
  log_id: string
  agent_id: string
  timestamp: string
  action: string
  resource: string | null
  allowed: boolean
  result: string
  context: any
  metadata: any
}

interface LogsTableProps {
  logs: AuditLog[]
}

export default function LogsTable({ logs }: LogsTableProps) {
  if (logs.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
        No logs found. Try adjusting your filters or submit some logs first.
      </div>
    )
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleString()
  }

  const getStatusBadge = (allowed: boolean) => {
    if (allowed) {
      return (
        <span style={{
          padding: '4px 8px',
          background: '#d4edda',
          color: '#155724',
          borderRadius: '4px',
          fontSize: '12px',
          fontWeight: '500'
        }}>
          ALLOWED
        </span>
      )
    } else {
      return (
        <span style={{
          padding: '4px 8px',
          background: '#f8d7da',
          color: '#721c24',
          borderRadius: '4px',
          fontSize: '12px',
          fontWeight: '500'
        }}>
          DENIED
        </span>
      )
    }
  }

  const getResultBadge = (result: string) => {
    if (result === 'success') {
      return (
        <span style={{
          padding: '4px 8px',
          background: '#d1ecf1',
          color: '#0c5460',
          borderRadius: '4px',
          fontSize: '12px',
          fontWeight: '500'
        }}>
          {result.toUpperCase()}
        </span>
      )
    } else {
      return (
        <span style={{
          padding: '4px 8px',
          background: '#fff3cd',
          color: '#856404',
          borderRadius: '4px',
          fontSize: '12px',
          fontWeight: '500'
        }}>
          {result.toUpperCase()}
        </span>
      )
    }
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{
        width: '100%',
        borderCollapse: 'collapse',
        fontSize: '14px'
      }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #dee2e6' }}>
            <th style={{ padding: '12px', textAlign: 'left', fontWeight: '600', color: '#495057' }}>
              Timestamp
            </th>
            <th style={{ padding: '12px', textAlign: 'left', fontWeight: '600', color: '#495057' }}>
              Agent ID
            </th>
            <th style={{ padding: '12px', textAlign: 'left', fontWeight: '600', color: '#495057' }}>
              Action
            </th>
            <th style={{ padding: '12px', textAlign: 'left', fontWeight: '600', color: '#495057' }}>
              Resource
            </th>
            <th style={{ padding: '12px', textAlign: 'left', fontWeight: '600', color: '#495057' }}>
              Status
            </th>
            <th style={{ padding: '12px', textAlign: 'left', fontWeight: '600', color: '#495057' }}>
              Result
            </th>
            <th style={{ padding: '12px', textAlign: 'left', fontWeight: '600', color: '#495057' }}>
              Log ID
            </th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log, index) => (
            <tr
              key={log.log_id}
              style={{
                borderBottom: '1px solid #dee2e6',
                background: index % 2 === 0 ? '#fff' : '#f8f9fa'
              }}
            >
              <td style={{ padding: '12px', fontFamily: 'monospace', fontSize: '13px' }}>
                {formatTimestamp(log.timestamp)}
              </td>
              <td style={{ padding: '12px', fontFamily: 'monospace', fontSize: '13px' }}>
                {log.agent_id}
              </td>
              <td style={{ padding: '12px', fontFamily: 'monospace', fontSize: '13px', fontWeight: '500' }}>
                {log.action}
              </td>
              <td style={{ padding: '12px', fontFamily: 'monospace', fontSize: '13px', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {log.resource || '-'}
              </td>
              <td style={{ padding: '12px' }}>
                {getStatusBadge(log.allowed)}
              </td>
              <td style={{ padding: '12px' }}>
                {getResultBadge(log.result)}
              </td>
              <td style={{ padding: '12px', fontFamily: 'monospace', fontSize: '11px', color: '#6c757d' }}>
                {log.log_id.substring(0, 8)}...
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
