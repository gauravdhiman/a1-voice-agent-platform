"use client";

import React from "react";
import { useTheme } from "@/contexts/theme-context";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Settings as SettingsIcon, Palette } from "lucide-react";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex min-w-0 items-center gap-3 sm:gap-4">
        <div className="shrink-0 rounded-lg bg-primary/10 p-2">
          <SettingsIcon className="h-6 w-6 text-primary" />
        </div>
        <div className="min-w-0">
          <h1 className="text-xl font-bold text-foreground sm:text-2xl">Settings</h1>
          <p className="text-sm text-muted-foreground">
            Manage your account and application preferences
          </p>
        </div>
      </div>

      <div className="space-y-6">
        <Card>
          <CardHeader className="p-5 pb-3">
            <CardTitle className="flex items-center space-x-2 text-lg">
              <Palette className="h-5 w-5" />
              <span>Appearance</span>
            </CardTitle>
            <CardDescription>
              Customize how the application looks and feels
            </CardDescription>
          </CardHeader>
          <CardContent className="p-5 pt-0 space-y-6">
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium mb-3">Theme</h4>
                <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div
                    className={`border rounded-lg p-3 cursor-pointer transition-all ${
                      theme === "light"
                        ? "border-primary bg-primary/5"
                        : "border-border hover:bg-accent"
                    }`}
                    onClick={() => setTheme("light")}
                  >
                    <div className="w-full h-20 bg-background border rounded mb-2 shadow-sm flex items-center justify-center">
                      <div className="w-1/2 h-1/2 bg-foreground/10 rounded-md"></div>
                    </div>
                    <p className="text-xs text-center font-medium">Light</p>
                    {theme === "light" && (
                      <div className="flex justify-center mt-1">
                        <div className="w-1.5 h-1.5 bg-primary rounded-full"></div>
                      </div>
                    )}
                  </div>
                  <div
                    className={`border rounded-lg p-3 cursor-pointer transition-all ${
                      theme === "dark"
                        ? "border-primary bg-primary/5"
                        : "border-border hover:bg-accent"
                    }`}
                    onClick={() => setTheme("dark")}
                  >
                    <div className="w-full h-20 bg-foreground border rounded mb-2 shadow-sm flex items-center justify-center">
                      <div className="w-1/2 h-1/2 bg-background/10 rounded-md"></div>
                    </div>
                    <p className="text-xs text-center font-medium">Dark</p>
                    {theme === "dark" && (
                      <div className="flex justify-center mt-1">
                        <div className="w-1.5 h-1.5 bg-primary rounded-full"></div>
                      </div>
                    )}
                  </div>
                  <div
                    className={`border rounded-lg p-3 cursor-pointer transition-all ${
                      theme === "system"
                        ? "border-primary bg-primary/5"
                        : "border-border hover:bg-accent"
                    }`}
                    onClick={() => setTheme("system")}
                  >
                    <div className="w-full h-20 bg-gradient-to-r from-background to-foreground border rounded mb-2 shadow-sm opacity-50"></div>
                    <p className="text-xs text-center font-medium">System</p>
                    {theme === "system" && (
                      <div className="flex justify-center mt-1">
                        <div className="w-1.5 h-1.5 bg-primary rounded-full"></div>
                      </div>
                    )}
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  {theme === "system"
                    ? "Automatically matches your system preference"
                    : `Currently using ${theme} theme`}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

      </div>
    </div>
  );
}
