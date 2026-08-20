"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { writeAuthToken } from "@/lib/auth";
import { beginHostedUiLogin, isCognitoConfigured } from "@/lib/cognito";

export default function AuthGate({
  title,
  description,
  error,
  nextPath,
  onTokenSaved,
}: {
  title: string;
  description: string;
  error?: string | null;
  nextPath?: string;
  onTokenSaved: () => void;
}) {
  const [tokenInput, setTokenInput] = useState("");
  const [loginError, setLoginError] = useState<string | null>(null);
  const cognito = isCognitoConfigured();

  const startCognitoLogin = () => {
    setLoginError(null);
    void beginHostedUiLogin({ next: nextPath }).catch((err: unknown) => {
      setLoginError(err instanceof Error ? err.message : "Unable to start sign-in.");
    });
  };

  if (cognito) {
    return (
      <div className="mx-auto max-w-lg rounded-xl border border-gray-600 bg-gray-800/60 p-6">
        <h1 className="text-xl font-semibold text-gray-100">{title}</h1>
        <p className="mt-2 text-sm text-gray-400">Sign in to continue. Token paste is disabled while Cognito is configured.</p>
        <Button
          type="button"
          className="mt-4"
          onClick={startCognitoLogin}
        >
          Sign in
        </Button>
        {loginError || error ? <p className="mt-3 text-sm text-red-400">{loginError || error}</p> : null}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg rounded-xl border border-gray-600 bg-gray-800/60 p-6">
      <h1 className="text-xl font-semibold text-gray-100">{title}</h1>
      <p className="mt-2 text-sm text-gray-400">{description}</p>
      <input
        value={tokenInput}
        onChange={(e) => setTokenInput(e.target.value)}
        placeholder="Bearer token or fake:userId"
        className="mt-4 h-10 w-full rounded-md border border-gray-600 bg-gray-900 px-3 text-sm text-gray-200 outline-none focus:border-teal-500"
      />
      <div className="mt-3 flex gap-2">
        <Button
          type="button"
          onClick={() => {
            writeAuthToken(tokenInput);
            setTokenInput("");
            onTokenSaved();
          }}
          disabled={!tokenInput.trim()}
        >
          Continue with token
        </Button>
      </div>
      {error ? <p className="mt-3 text-sm text-red-400">{error}</p> : null}
    </div>
  );
}
