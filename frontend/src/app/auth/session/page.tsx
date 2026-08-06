import { Suspense } from "react";
import OAuthSessionClient from "./page.client";

export default function SessionPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto flex min-h-[50vh] w-full max-w-md items-center justify-center p-6 text-muted-foreground">
          Completing sign-in...
        </div>
      }
    >
      <OAuthSessionClient />
    </Suspense>
  );
}
