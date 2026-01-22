import React, { useState } from 'react'
import { 
  ArrowLeft,
  Edit,
  Trash2,
  Play,
  Pause,
  Phone,
  Bot,
  Zap,
  Clock,
  MessageSquare,
  Settings,
  Copy,
  ExternalLink,
  Download,
  TrendingUp,
  Calendar,
  Users,
  Activity
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

function App() {
  const [activeTab, setActiveTab] = useState('overview')

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
        <div className="p-6 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg">
              <span className="text-white font-bold text-lg">AI</span>
            </div>
            <div>
              <div className="font-bold text-slate-900">NeuraSaaS</div>
              <div className="text-xs text-slate-500">Voice AI Platform</div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-white border-b border-slate-200 px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button variant="ghost" size="icon" className="h-9 w-9">
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg">
                  <Bot className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-slate-900">Customer Support Bot</h1>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge className="bg-emerald-500/10 text-emerald-700 border-emerald-500/20 text-xs font-medium">
                      Active
                    </Badge>
                    <Badge className="bg-blue-500/10 text-blue-700 border-blue-500/20 text-xs font-medium">
                      Support
                    </Badge>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" className="gap-2">
                <Copy className="w-4 h-4" />
                Clone
              </Button>
              <Button variant="outline" size="sm" className="gap-2">
                <Edit className="w-4 h-4" />
                Edit
              </Button>
              <Button variant="destructive" size="sm" className="gap-2">
                <Trash2 className="w-4 h-4" />
                Delete
              </Button>
            </div>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-8">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
            <TabsList className="grid w-full grid-cols-5 max-w-2xl">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="configuration">Configuration</TabsTrigger>
              <TabsTrigger value="calls">Calls</TabsTrigger>
              <TabsTrigger value="analytics">Analytics</TabsTrigger>
              <TabsTrigger value="logs">Logs</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-6">
              {/* Stats Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard 
                  icon={Phone} 
                  label="Calls Today" 
                  value="247" 
                  change="+12%"
                  trend="up"
                />
                <StatCard 
                  icon={Clock} 
                  label="Avg Duration" 
                  value="4:32" 
                  change="-8%"
                  trend="down"
                />
                <StatCard 
                  icon={MessageSquare} 
                  label="Satisfaction" 
                  value="4.7" 
                  change="+2%"
                  trend="up"
                />
                <StatCard 
                  icon={Zap} 
                  label="Success Rate" 
                  value="94%" 
                  change="+5%"
                  trend="up"
                />
              </div>

              {/* Description */}
              <Card>
                <CardHeader>
                  <CardTitle>Description</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-slate-600">
                    Handles customer inquiries, troubleshooting, and support tickets. The agent is trained to handle common issues, escalate complex problems, and maintain a professional and empathetic tone throughout all interactions.
                  </p>
                </CardContent>
              </Card>

              {/* Quick Actions */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <QuickActionCard
                  icon={Play}
                  title="Test Call"
                  description="Make a test call to verify agent behavior"
                  buttonLabel="Start Test Call"
                />
                <QuickActionCard
                  icon={Settings}
                  title="Quick Settings"
                  description="Adjust voice, prompt, and behavior"
                  buttonLabel="Configure"
                />
                <QuickActionCard
                  icon={Activity}
                  title="Live Monitor"
                  description="View active calls and real-time transcripts"
                  buttonLabel="Monitor"
                />
              </div>
            </TabsContent>

            <TabsContent value="configuration" className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Basic Settings</CardTitle>
                    <CardDescription>Core agent configuration</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Agent Name</label>
                      <input 
                        type="text" 
                        defaultValue="Customer Support Bot"
                        className="w-full px-3 py-2 border rounded-lg border-slate-200"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Voice</label>
                      <select className="w-full px-3 py-2 border rounded-lg border-slate-200">
                        <option>Sarah (Female)</option>
                        <option>John (Male)</option>
                        <option>Emma (Female)</option>
                      </select>
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Agent Type</label>
                      <select className="w-full px-3 py-2 border rounded-lg border-slate-200">
                        <option>Support</option>
                        <option>Sales</option>
                        <option>Operations</option>
                      </select>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>System Prompt</CardTitle>
                    <CardDescription>Agent's personality and behavior</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <textarea 
                      defaultValue="You are a helpful customer service assistant. Be polite, empathetic, and solution-oriented. Always aim to resolve issues efficiently while maintaining a friendly tone."
                      className="w-full h-48 px-3 py-2 border rounded-lg border-slate-200 resize-none"
                    />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Call Settings</CardTitle>
                    <CardDescription>Recording and transcription options</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">Enable Recording</div>
                        <div className="text-xs text-slate-500">Record all calls for quality assurance</div>
                      </div>
                      <div className="w-11 h-6 bg-indigo-600 rounded-full relative">
                        <div className="absolute right-0.5 top-0.5 w-5 h-5 bg-white rounded-full" />
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">Transcribe Calls</div>
                        <div className="text-xs text-slate-500">Generate call transcripts automatically</div>
                      </div>
                      <div className="w-11 h-6 bg-indigo-600 rounded-full relative">
                        <div className="absolute right-0.5 top-0.5 w-5 h-5 bg-white rounded-full" />
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">Auto-Pause</div>
                        <div className="text-xs text-slate-500">Pause agent after long calls</div>
                      </div>
                      <div className="w-11 h-6 bg-slate-300 rounded-full relative">
                        <div className="absolute left-0.5 top-0.5 w-5 h-5 bg-white rounded-full" />
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Advanced Settings</CardTitle>
                    <CardDescription>Fine-tune agent behavior</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <label className="text-sm font-medium">Max Call Duration</label>
                        <input type="number" defaultValue="10" className="w-full px-3 py-2 border rounded-lg border-slate-200" />
                      </div>
                      <div className="space-y-2">
                        <label className="text-sm font-medium">Retry Attempts</label>
                        <input type="number" defaultValue="3" className="w-full px-3 py-2 border rounded-lg border-slate-200" />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Greeting Message</label>
                      <textarea 
                        defaultValue="Hello! How can I help you today?"
                        className="w-full h-24 px-3 py-2 border rounded-lg border-slate-200 resize-none"
                      />
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="calls" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Recent Calls</CardTitle>
                  <CardDescription>Latest interactions with this agent</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {[
                      { phone: '+1 (555) 123-4567', duration: '4:32', status: 'Completed', satisfaction: 5, time: '2 min ago' },
                      { phone: '+1 (555) 987-6543', duration: '3:15', status: 'Completed', satisfaction: 4, time: '15 min ago' },
                      { phone: '+1 (555) 456-7890', duration: '5:45', status: 'Escalated', satisfaction: 3, time: '32 min ago' },
                      { phone: '+1 (555) 321-0987', duration: '2:58', status: 'Completed', satisfaction: 5, time: '45 min ago' },
                    ].map((call, i) => (
                      <div key={i} className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center">
                            <Phone className="w-5 h-5 text-indigo-600" />
                          </div>
                          <div>
                            <div className="font-medium text-slate-900">{call.phone}</div>
                            <div className="text-sm text-slate-500">{call.time} • {call.duration}</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <Badge className={
                            call.status === 'Completed' ? 'bg-emerald-500/10 text-emerald-700 border-emerald-500/20' : 'bg-amber-500/10 text-amber-700 border-amber-500/20'
                          }>
                            {call.status}
                          </Badge>
                          <div className="flex items-center gap-1 text-amber-500">
                            {Array.from({ length: call.satisfaction }).map((_, j) => (
                              <span key={j} className="text-lg">★</span>
                            ))}
                          </div>
                          <Button variant="ghost" size="sm">
                            <ExternalLink className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="analytics" className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card className="lg:col-span-2">
                  <CardHeader>
                    <CardTitle>Call Volume Over Time</CardTitle>
                    <CardDescription>Daily call activity for last 30 days</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="h-64 flex items-end justify-between gap-2">
                      {Array.from({ length: 30 }).map((_, i) => {
                        const height = Math.random() * 80 + 20
                        return (
                          <div 
                            key={i}
                            className="flex-1 bg-indigo-500 rounded-t transition-all hover:bg-indigo-600"
                            style={{ height: `${height}%` }}
                          />
                        )
                      })}
                    </div>
                    <div className="flex justify-between mt-2 text-xs text-slate-500">
                      <span>30 days ago</span>
                      <span>Today</span>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Key Metrics</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <MetricRow label="Total Calls" value="3,847" change="+15%" />
                    <MetricRow label="Avg Duration" value="4:32" change="-8%" />
                    <MetricRow label="Success Rate" value="94%" change="+5%" />
                    <MetricRow label="Escalation Rate" value="6%" change="-3%" />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Satisfaction Trend</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-6xl font-bold text-indigo-600">4.7</div>
                    <div className="flex items-center gap-2 mt-2">
                      <TrendingUp className="w-4 h-4 text-emerald-500" />
                      <span className="text-sm text-emerald-600 font-medium">+0.3 from last month</span>
                    </div>
                    <div className="flex items-center gap-1 mt-4 text-amber-500">
                      {Array.from({ length: 4 }).map((_, i) => (
                        <span key={i} className="text-2xl">★</span>
                      ))}
                      <span className="text-2xl text-slate-300">★</span>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="logs" className="space-y-6">
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>Activity Logs</CardTitle>
                      <CardDescription>Recent agent activity and system events</CardDescription>
                    </div>
                    <Button variant="outline" size="sm" className="gap-2">
                      <Download className="w-4 h-4" />
                      Export
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm font-mono">
                    {[
                      { time: '2024-01-03 14:32:15', event: 'call_started', details: 'Incoming call from +1 (555) 123-4567' },
                      { time: '2024-01-03 14:32:18', event: 'response_generated', details: 'AI response generated in 2.3s' },
                      { time: '2024-01-03 14:36:47', event: 'call_ended', details: 'Call completed successfully, duration: 4:32' },
                      { time: '2024-01-03 14:15:23', event: 'call_started', details: 'Incoming call from +1 (555) 987-6543' },
                      { time: '2024-01-03 14:18:38', event: 'call_escalated', details: 'Call escalated to human agent' },
                      { time: '2024-01-03 13:45:12', event: 'configuration_updated', details: 'System prompt updated by John Doe' },
                    ].map((log, i) => (
                      <div key={i} className="flex gap-4 p-3 bg-slate-50 rounded-lg">
                        <span className="text-slate-400 whitespace-nowrap">{log.time}</span>
                        <Badge variant="outline" className="whitespace-nowrap">{log.event}</Badge>
                        <span className="text-slate-600">{log.details}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </main>
    </div>
  )
}

function StatCard({ icon: Icon, label, value, change, trend }: any) {
  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <Icon className="w-5 h-5 text-slate-400" />
          <span className={`text-sm font-medium ${trend === 'up' ? 'text-emerald-600' : 'text-rose-600'}`}>
            {change}
          </span>
        </div>
        <div className="mt-4">
          <div className="text-2xl font-bold text-slate-900">{value}</div>
          <div className="text-xs text-slate-500 mt-1">{label}</div>
        </div>
      </CardContent>
    </Card>
  )
}

function QuickActionCard({ icon: Icon, title, description, buttonLabel }: any) {
  return (
    <Card className="hover:shadow-lg transition-shadow cursor-pointer group">
      <CardHeader>
        <div className="w-12 h-12 rounded-xl bg-indigo-100 flex items-center justify-center mb-4 group-hover:bg-indigo-600 transition-colors">
          <Icon className="w-6 h-6 text-indigo-600 group-hover:text-white transition-colors" />
        </div>
        <CardTitle className="text-lg">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <Button className="w-full" variant="outline">{buttonLabel}</Button>
      </CardContent>
    </Card>
  )
}

function MetricRow({ label, value, change }: any) {
  const isPositive = change.startsWith('+')
  return (
    <div className="flex items-center justify-between py-2 border-b border-slate-200 last:border-0">
      <span className="text-slate-600">{label}</span>
      <div className="flex items-center gap-3">
        <span className="font-semibold">{value}</span>
        <span className={`text-sm ${isPositive ? 'text-emerald-600' : 'text-rose-600'}`}>{change}</span>
      </div>
    </div>
  )
}

export default App
