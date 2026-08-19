"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { beginHostedUiLogin, completeHostedUiCallback, isCognitoConfigured } from "@/lib/cognito";

export default function AuthCallbackPage() {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    void completeHostedUiCallback({ search: params }).then((result) => {
      if (result.ok) {
        window.location.replace(result.next);
        return;
      }
      setError(result.error);
    });
  }, []);

  if (error) {
    return (
      <div className="mx-auto max-w-lg rounded-xl border border-gray-600 bg-gray-800/60 p-6">
        <h1 className="text-xl font-semibold text-gray-100">Sign-in failed</h1>
        <p className="mt-2 text-sm text-red-400">{error}</p>
        {isCognitoConfigured() ? (
          <Button className="mt-4" type="button" onClick={() => void beginHostedUiLogin()}>
            Retry Sign in
          </Button>
        ) : null}
      </div>
    );
  }

  return <div className="py-16 text-center text-sm text-gray-500">Signing you in…</div>;
}
