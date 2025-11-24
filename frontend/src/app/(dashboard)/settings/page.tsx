'use client';

import React from 'react';
import { useTheme } from '@/contexts/theme-context';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { 
  Settings as SettingsIcon, 
  Palette
} from 'lucide-react';

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="p-6">
      {/* Page Header */}
      <div className="mb-6">
        <div className="flex items-center space-x-4">
          <div className="bg-primary/10 p-3 rounded-lg">
            <SettingsIcon className="h-8 w-8 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-foreground">Settings</h1>
            <p className="text-muted-foreground">Manage your account and application preferences</p>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Palette className="h-5 w-5" />
              <span>Appearance</span>
            </CardTitle>
            <CardDescription>
              Customize how the application looks and feels
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium mb-3">Theme</h4>
                <div className="grid grid-cols-3 gap-3 mb-4">
                  <div 
                    className={`border rounded-lg p-3 cursor-pointer transition-all ${
                      theme === 'light' 
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-950' 
                        : 'border-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 dark:border-gray-700'
                    }`}
                    onClick={() => setTheme('light')}
                  >
                    <div className="w-full h-20 bg-white border rounded mb-2 shadow-sm"></div>
                    <p className="text-xs text-center font-medium">Light</p>
                    {theme === 'light' && (
                      <div className="flex justify-center mt-1">
                        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                      </div>
                    )}
                  </div>
                  <div 
                    className={`border rounded-lg p-3 cursor-pointer transition-all ${
                      theme === 'dark' 
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-950' 
                        : 'border-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 dark:border-gray-700'
                    }`}
                    onClick={() => setTheme('dark')}
                  >
                    <div className="w-full h-20 bg-gray-900 border rounded mb-2 shadow-sm"></div>
                    <p className="text-xs text-center font-medium">Dark</p>
                    {theme === 'dark' && (
                      <div className="flex justify-center mt-1">
                        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                      </div>
                    )}
                  </div>
                  <div 
                    className={`border rounded-lg p-3 cursor-pointer transition-all ${
                      theme === 'system' 
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-950' 
                        : 'border-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 dark:border-gray-700'
                    }`}
                    onClick={() => setTheme('system')}
                  >
                    <div className="w-full h-20 bg-gradient-to-r from-white to-gray-900 border rounded mb-2 shadow-sm"></div>
                    <p className="text-xs text-center font-medium">System</p>
                    {theme === 'system' && (
                      <div className="flex justify-center mt-1">
                        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                      </div>
                    )}
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  {theme === 'system' 
                    ? 'Automatically matches your system preference' 
                    : `Currently using ${theme} theme`
                  }
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}