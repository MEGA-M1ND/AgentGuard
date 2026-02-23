'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { LayoutDashboard, Users, Shield, ScrollText, Play, Zap } from 'lucide-react'

const navigation = [
  { name: 'Dashboard',    href: '/',        icon: LayoutDashboard, highlight: false },
  { name: 'Live Demo',    href: '/demo',    icon: Zap,             highlight: true  },
  { name: 'Agents',       href: '/agents',  icon: Users,           highlight: false },
  { name: 'Policies',     href: '/policies',icon: Shield,          highlight: false },
  { name: 'Test Actions', href: '/test',    icon: Play,            highlight: false },
  { name: 'Audit Logs',   href: '/logs',    icon: ScrollText,      highlight: false },
]

export function Navigation() {
  const pathname = usePathname()

  return (
    <div className="flex flex-col w-64 bg-gray-900 text-white">
      {/* Logo */}
      <div className="flex items-center h-16 px-6 border-b border-gray-800">
        <Shield className="h-8 w-8 text-blue-500" />
        <span className="ml-3 text-xl font-bold">AgentGuard</span>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-4 py-6 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors',
                isActive
                  ? 'bg-blue-600 text-white'
                  : item.highlight
                  ? 'text-yellow-300 hover:bg-gray-800 hover:text-yellow-200 ring-1 ring-yellow-600/40'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              )}
            >
              <item.icon className="h-5 w-5 mr-3" />
              {item.name}
              {item.highlight && !isActive && (
                <span className="ml-auto text-xs bg-yellow-600 text-yellow-100 px-1.5 py-0.5 rounded">
                  demo
                </span>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-6 py-4 border-t border-gray-800">
        <p className="text-xs text-gray-400">AgentGuard v0.1.0</p>
        <p className="text-xs text-gray-500 mt-1">Enterprise AI Governance</p>
      </div>
    </div>
  )
}
