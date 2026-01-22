import React, { useState } from 'react'
import { 
  LayoutDashboard, 
  Settings, 
  Users, 
  Building2,
  ChevronRight,
  Plus,
  Search,
  MoreVertical,
  Bot,
  Clock,
  Phone
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

const mockAgents = [
  {
    id: '1',
    name: 'Customer Support Bot',
    description: 'Handles customer inquiries, troubleshooting, and support tickets',
    status: 'active',
    type: 'Support',
    callsToday: 247,
    avgDuration: '4:32',
    satisfaction: 4.7,
    lastActive: '2 min ago'
  },
  {
    id: '2',
    name: 'Sales Qualifier',
    description: 'Qualifies inbound leads, collects requirements, schedules demos',
    status: 'active',
    type: 'Sales',
    callsToday: 89,
    avgDuration: '6:15',
    satisfaction: 4.5,
    lastActive: '15 min ago'
  },
  {
    id: '3',
    name: 'Appointment Scheduler',
    description: 'Books and manages appointments with automated follow-ups',
    status: 'inactive',
    type: 'Operations',
    callsToday: 0,
    avgDuration: '3:45',
    satisfaction: 4.8,
    lastActive: '2 days ago'
  },
  {
    id: '4',
    name: 'Tech Support Assistant',
    description: 'Technical troubleshooting and product guidance',
    status: 'active',
    type: 'Support',
    callsToday: 156,
    avgDuration: '8:20',
    satisfaction: 4.6,
    lastActive: '5 min ago'
  },
  {
    id: '5',
    name: 'Lead Generator',
    description: 'Outbound calling to qualify and generate new leads',
    status: 'paused',
    type: 'Sales',
    callsToday: 0,
    avgDuration: '5:10',
    satisfaction: 4.3,
    lastActive: '1 week ago'
  },
  {
    id: '6',
    name: 'Billing Inquiries',
    description: 'Handles billing questions, invoices, and payment processing',
    status: 'active',
    type: 'Support',
    callsToday: 42,
    avgDuration: '3:18',
    satisfaction: 4.8,
    lastActive: '1 min ago'
  }
]

function App() {
  const [agents] = useState(mockAgents)
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateDialog, setShowCreateDialog] = useState(false)

  const filteredAgents = agents.filter(agent =>
    agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    agent.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const getStatusColor = (status: string) => {
    switch(status) {
      case 'active': return 'bg-emerald-500/10 text-emerald-700 border-emerald-500/20'
      case 'inactive': return 'bg-slate-100 text-slate-600 border-slate-200'
      case 'paused': return 'bg-amber-500/10 text-amber-700 border-amber-500/20'
      default: return 'bg-slate-100 text-slate-600'
    }
  }

  const getTypeColor = (type: string) => {
    switch(type) {
      case 'Support': return 'bg-blue-500/10 text-blue-700 border-blue-500/20'
      case 'Sales': return 'bg-purple-500/10 text-purple-700 border-purple-500/20'
      case 'Operations': return 'bg-teal-500/10 text-teal-700 border-teal-500/20'
      default: return 'bg-slate-100 text-slate-600'
    }
  }

  const AgentCard = ({ agent }: { agent: typeof mockAgents[0] }) => (
    <Card className="group hover:shadow-lg transition-all duration-200 cursor-pointer border-2 hover:border-indigo-500/20">
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div className="flex-1">
              <CardTitle className="text-lg font-semibold group-hover:text-indigo-600 transition-colors">
                {agent.name}
              </CardTitle>
              <div className="flex items-center gap-2 mt-1">
                <Badge className={`text-xs font-medium ${getTypeColor(agent.type)}`}>
                  {agent.type}
                </Badge>
                <Badge className={`text-xs font-medium ${getStatusColor(agent.status)}`}>
                  {agent.status}
                </Badge>
              </div>
            </div>
          </div>
          <button className="p-2 hover:bg-slate-100 rounded-lg transition-colors">
            <MoreVertical className="w-4 h-4 text-slate-500" />
          </button>
        </div>
        <CardDescription className="mt-3 line-clamp-2">
          {agent.description}
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-slate-200">
          <div>
            <div className="text-2xl font-bold text-slate-900">{agent.callsToday}</div>
            <div className="text-xs text-slate-500">Calls Today</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900">{agent.avgDuration}</div>
            <div className="text-xs text-slate-500">Avg Duration</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900">{agent.satisfaction}</div>
            <div className="text-xs text-slate-500">Satisfaction</div>
          </div>
        </div>
        <div className="flex items-center gap-2 mt-4 text-xs text-slate-500">
          <Clock className="w-3 h-3" />
          Last active: {agent.lastActive}
        </div>
      </CardContent>
    </Card>
  )

  const CreateAgentDialog = () => (
    <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl">Create New Agent</DialogTitle>
          <DialogDescription>
            Configure your voice AI agent with custom settings, voice, and behavior
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-6 mt-4">
          <div className="space-y-4">
            <div>
              <Label className="text-base font-semibold">Agent Name</Label>
              <Input placeholder="Customer Support Bot" className="mt-2" />
            </div>
            
            <div>
              <Label className="text-base font-semibold">Description</Label>
              <Textarea 
                placeholder="Describe what this agent does, its purpose, and key functions..."
                className="mt-2 resize-none" 
                rows={3}
              />
            </div>
          </div>

          <Separator />

          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Configuration</h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Agent Type</Label>
                <Select>
                  <SelectTrigger className="mt-2">
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="support">Support</SelectItem>
                    <SelectItem value="sales">Sales</SelectItem>
                    <SelectItem value="operations">Operations</SelectItem>
                    <SelectItem value="custom">Custom</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div>
                <Label>Voice</Label>
                <Select>
                  <SelectTrigger className="mt-2">
                    <SelectValue placeholder="Select voice" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="female1">Sarah (Female)</SelectItem>
                    <SelectItem value="male1">John (Male)</SelectItem>
                    <SelectItem value="female2">Emma (Female)</SelectItem>
                    <SelectItem value="male2">David (Male)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <Label>System Prompt</Label>
              <Textarea 
                placeholder="You are a helpful customer service assistant..."
                className="mt-2 resize-none" 
                rows={4}
              />
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className="text-base">Enable Recording</Label>
                  <div className="text-xs text-slate-500">Record all calls for quality assurance</div>
                </div>
                <Switch />
              </div>
              
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className="text-base">Transcribe Calls</Label>
                  <div className="text-xs text-slate-500">Generate call transcripts automatically</div>
                </div>
                <Switch defaultChecked />
              </div>
              
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className="text-base">Auto-Pause</Label>
                  <div className="text-xs text-slate-500">Pause agent after long calls</div>
                </div>
                <Switch />
              </div>
            </div>
          </div>

          <Separator />

          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Advanced Settings</h3>
            
            <Tabs defaultValue="general">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="general">General</TabsTrigger>
                <TabsTrigger value="voice">Voice</TabsTrigger>
                <TabsTrigger value="behavior">Behavior</TabsTrigger>
              </TabsList>
              
              <TabsContent value="general" className="space-y-4 mt-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Max Call Duration</Label>
                    <Input placeholder="10" className="mt-2" />
                    <div className="text-xs text-slate-500 mt-1">minutes</div>
                  </div>
                  <div>
                    <Label>Retry Attempts</Label>
                    <Input placeholder="3" className="mt-2" />
                  </div>
                </div>
              </TabsContent>
              
              <TabsContent value="voice" className="space-y-4 mt-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Speech Rate</Label>
                    <Select>
                      <SelectTrigger className="mt-2">
                        <SelectValue placeholder="Normal" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="slow">Slow</SelectItem>
                        <SelectItem value="normal">Normal</SelectItem>
                        <SelectItem value="fast">Fast</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Pitch</Label>
                    <Select>
                      <SelectTrigger className="mt-2">
                        <SelectValue placeholder="Normal" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="low">Low</SelectItem>
                        <SelectItem value="normal">Normal</SelectItem>
                        <SelectItem value="high">High</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </TabsContent>
              
              <TabsContent value="behavior" className="space-y-4 mt-4">
                <div>
                  <Label>Greeting Message</Label>
                  <Textarea 
                    placeholder="Hello! How can I help you today?"
                    className="mt-2 resize-none" 
                    rows={2}
                  />
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </div>

        <DialogFooter className="mt-6">
          <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
            Cancel
          </Button>
          <Button className="min-w-[120px]">
            Create Agent
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Sidebar Navigation */}
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

        <nav className="flex-1 p-4 space-y-1">
          <NavItem icon={LayoutDashboard} label="Dashboard" />
          <NavItem icon={Bot} label="Agents" active />
          <NavItem icon={Building2} label="Organization" />
          <NavItem icon={Users} label="Team" />
          <NavItem icon={Settings} label="Settings" />
        </nav>

        <div className="p-4 border-t border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center text-white text-sm font-semibold">
              JD
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium text-slate-900">John Doe</div>
              <div className="text-xs text-slate-500">Admin</div>
            </div>
            <ChevronRight className="w-4 h-4 text-slate-400" />
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-white border-b border-slate-200 px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Agents</h1>
              <p className="text-sm text-slate-500 mt-1">
                Manage your voice AI agents and their configurations
              </p>
            </div>
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Search agents..."
                  className="w-64 pl-10"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
                <DialogTrigger asChild>
                  <Button className="gap-2">
                    <Plus className="w-4 h-4" />
                    Create Agent
                  </Button>
                </DialogTrigger>
              </Dialog>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-8">
          {filteredAgents.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <Bot className="w-16 h-16 text-slate-300 mb-4" />
              <h3 className="text-lg font-semibold text-slate-900 mb-2">No agents found</h3>
              <p className="text-slate-500 mb-4">
                {searchQuery ? 'Try a different search term' : 'Get started by creating your first agent'}
              </p>
              {!searchQuery && (
                <Button onClick={() => setShowCreateDialog(true)} className="gap-2">
                  <Plus className="w-4 h-4" />
                  Create Your First Agent
                </Button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredAgents.map(agent => (
                <AgentCard key={agent.id} agent={agent} />
              ))}
            </div>
          )}
        </div>
      </main>

      <CreateAgentDialog />
    </div>
  )
}

function NavItem({ icon: Icon, label, active = false }: { icon: any, label: string, active?: boolean }) {
  return (
    <button className={`
      w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200
      ${active 
        ? 'bg-indigo-50 text-indigo-700' 
        : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
      }
    `}>
      <Icon className={`w-5 h-5 ${active ? 'text-indigo-600' : 'text-slate-400'}`} />
      {label}
      {active && <ChevronRight className="w-4 h-4 ml-auto" />}
    </button>
  )
}

export default App
