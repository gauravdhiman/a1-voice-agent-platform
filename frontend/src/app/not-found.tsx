import Link from "next/link";
import { ArrowLeft, Phone, PhoneCall } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SITE_NAME } from "@/lib/site-config";

/**
 * Branded catch-all for unknown routes.
 *
 * Every dead end offers a way forward: home for orientation, demo
 * request for intent. No blank framework default pages ship to visitors.
 */
export default function NotFound() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans">
      <header className="w-full border-b border-border/40">
        <div className="container flex h-16 items-center max-w-3xl mx-auto px-4">
          <Link href="/" className="flex items-center gap-3">
            <div className="bg-gradient-to-br from-blue-600 to-cyan-600 w-10 h-10 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Phone className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold tracking-tight">
              {SITE_NAME}
            </span>
          </Link>
        </div>
      </header>
      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md space-y-6 text-center">
          <div className="mx-auto w-14 h-14 rounded-2xl bg-blue-100 dark:bg-blue-950/50 flex items-center justify-center">
            <PhoneCall className="w-7 h-7 text-blue-600" />
          </div>
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-blue-600">
              Lost call
            </p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight">
              This page didn&apos;t pick up
            </h1>
            <p className="text-muted-foreground mt-2">
              The link is wrong or the page moved. Unlike this page, your AI
              front desk answers everything.
            </p>
          </div>
          <div className="flex flex-col gap-3">
            <Button asChild className="bg-blue-600 hover:bg-blue-700 h-12">
              <Link href="/">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to home
              </Link>
            </Button>
            <Button asChild variant="outline" className="h-12">
              <Link href="/request-demo">Request a demo</Link>
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
