'use client';

import React from 'react';

export default function DashboardPage() {
  return (
    <div className="p-6">
      <div className="bg-card rounded-lg shadow-md p-6">
        <h1 className="text-3xl font-bold text-foreground mb-2">Dashboard</h1>
        <p className="text-muted-foreground mb-6">Welcome to your dashboard!</p>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="bg-primary/5 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-foreground mb-2">Organizations</h2>
            <p className="text-muted-foreground">Manage your organizations</p>
          </div>
          
          <div className="bg-primary/5 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-foreground mb-2">Billing</h2>
            <p className="text-muted-foreground">View your billing information</p>
          </div>
          
          <div className="bg-primary/5 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-foreground mb-2">Settings</h2>
            <p className="text-muted-foreground">Customize your preferences</p>
          </div>
        </div>
      </div>
    </div>
  );
}