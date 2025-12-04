'use client'

import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

const tabs = [
  {
    name: 'Overview',
    value: 'overview',
    content: (
      <div className="p-4">
        <p className="text-muted-foreground">
          Discover <span className="text-foreground font-semibold">fresh insights</span>, trending topics, and hidden gems
          curated just for you. Start exploring and let your curiosity lead the way!
        </p>
      </div>
    )
  },
  {
    name: 'Analytics',
    value: 'analytics',
    content: (
      <div className="p-4">
        <p className="text-muted-foreground">
          All your <span className="text-foreground font-semibold">analytics</span> are tracked here. Revisit performance metrics,
          growth insights, and data-driven moments that help you understand your progress.
        </p>
      </div>
    )
  },
  {
    name: 'Reports',
    value: 'reports',
    content: (
      <div className="p-4">
        <p className="text-muted-foreground">
          <span className="text-foreground font-semibold">Detailed reports</span> await! Generate comprehensive insights, 
          export data, and create actionable recommendations for your business growth.
        </p>
      </div>
    )
  }
]

export const TabsDemo = () => {
  const [activeTab, setActiveTab] = useState('overview')

  return (
    <div className="w-full max-w-2xl mx-auto p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-foreground mb-2">Modern Animated Tabs</h2>
        <p className="text-muted-foreground">
          Experience our sleek, modern tabs with smooth animated underlines.
        </p>
      </div>
      
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="w-full">
          {tabs.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value}>
              {tab.name}
            </TabsTrigger>
          ))}
        </TabsList>

        {tabs.map((tab) => (
          <TabsContent key={tab.value} value={tab.value}>
            <div className="bg-card border rounded-lg p-6 shadow-sm">
              {tab.content}
            </div>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}

export default TabsDemo