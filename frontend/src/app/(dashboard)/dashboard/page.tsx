'use client';

import React from 'react';
import {
  Users,
  CreditCard,
  Activity,
  ArrowUpRight,
  ArrowDownRight,
  DollarSign,
  BarChart3
} from 'lucide-react';

export default function DashboardPage() {
  const stats = [
    {
      title: 'Total Revenue',
      value: '$45,231.89',
      change: '+20.1% from last month',
      trend: 'up',
      icon: DollarSign,
      color: 'text-green-500',
      bg: 'bg-green-500/10',
    },
    {
      title: 'Active Users',
      value: '+2350',
      change: '+180.1% from last month',
      trend: 'up',
      icon: Users,
      color: 'text-blue-500',
      bg: 'bg-blue-500/10',
    },
    {
      title: 'Sales',
      value: '+12,234',
      change: '+19% from last month',
      trend: 'up',
      icon: CreditCard,
      color: 'text-orange-500',
      bg: 'bg-orange-500/10',
    },
    {
      title: 'Active Now',
      value: '+573',
      change: '+201 since last hour',
      trend: 'up',
      icon: Activity,
      color: 'text-purple-500',
      bg: 'bg-purple-500/10',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Overview of your organization&apos;s performance.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground h-8 px-3 py-2">
            Download Report
          </button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div key={index} className="rounded-xl border border-border bg-card text-card-foreground shadow-sm p-5">
              <div className="flex items-center justify-between space-y-0 pb-2">
                <p className="text-sm font-medium text-muted-foreground">{stat.title}</p>
                <div className={`p-1.5 rounded-full ${stat.bg}`}>
                  <Icon className={`h-4 w-4 ${stat.color}`} />
                </div>
              </div>
              <div className="pt-2">
                <div className="text-2xl font-bold">{stat.value}</div>
                <p className="text-xs text-muted-foreground mt-1 flex items-center">
                  {stat.trend === 'up' ? (
                    <ArrowUpRight className="h-3 w-3 text-green-500 mr-1" />
                  ) : (
                    <ArrowDownRight className="h-3 w-3 text-red-500 mr-1" />
                  )}
                  <span className={stat.trend === 'up' ? 'text-green-500' : 'text-red-500'}>
                    {stat.change}
                  </span>
                </p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <div className="col-span-4 rounded-xl border border-border bg-card text-card-foreground shadow-sm">
          <div className="p-5 flex flex-col space-y-1.5">
            <h3 className="font-semibold leading-none tracking-tight">Overview</h3>
            <p className="text-sm text-muted-foreground">Monthly revenue breakdown.</p>
          </div>
          <div className="p-5 pt-0 pl-2">
            <div className="h-[300px] w-full flex items-center justify-center bg-muted/10 rounded-lg border border-dashed border-border">
              <div className="text-center text-muted-foreground">
                <BarChart3 className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Chart visualization would go here</p>
                <p className="text-xs">(Requires a charting library like Recharts)</p>
              </div>
            </div>
          </div>
        </div>

        <div className="col-span-3 rounded-xl border border-border bg-card text-card-foreground shadow-sm">
          <div className="p-5 flex flex-col space-y-1.5">
            <h3 className="font-semibold leading-none tracking-tight">Recent Sales</h3>
            <p className="text-sm text-muted-foreground">You made 265 sales this month.</p>
          </div>
          <div className="p-5 pt-0">
            <div className="space-y-6">
              {[
                { name: 'Olivia Martin', email: 'olivia.martin@email.com', amount: '+$1,999.00' },
                { name: 'Jackson Lee', email: 'jackson.lee@email.com', amount: '+$39.00' },
                { name: 'Isabella Nguyen', email: 'isabella.nguyen@email.com', amount: '+$299.00' },
                { name: 'William Kim', email: 'will.kim@email.com', amount: '+$99.00' },
                { name: 'Sofia Davis', email: 'sofia.davis@email.com', amount: '+$39.00' },
              ].map((sale, i) => (
                <div key={i} className="flex items-center">
                  <div className="relative flex h-8 w-8 shrink-0 overflow-hidden rounded-full bg-primary/10 items-center justify-center text-primary font-medium text-xs">
                    {sale.name.split(' ').map(n => n[0]).join('')}
                  </div>
                  <div className="ml-4 space-y-1">
                    <p className="text-sm font-medium leading-none">{sale.name}</p>
                    <p className="text-xs text-muted-foreground">{sale.email}</p>
                  </div>
                  <div className="ml-auto font-medium text-sm">{sale.amount}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}