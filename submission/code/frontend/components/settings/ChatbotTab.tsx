"use client";

import { useEffect, useMemo, useState } from "react";
import { useT } from "@/components/LanguageProvider";
import { fetchAdminSettings, updateAdminSettings, type AdminSettings } from "@/lib/admin-api";
import { AuthApiError } from "@/lib/auth";
import type { AuthProfileController } from "@/lib/use-auth-profile";

type RawChat = {
  model: string | null;
  fallbackModels: string[] | null;
  temperature: number | null;
  topP: number | null;
  maxTokens: number | null;
  systemPromptExtra: string | null;
};
type ChatField = keyof RawChat;
type FieldErrors = Partial<Record<ChatField, string>>;

const EMPTY_RAW: RawChat = {
  model: null,
  fallbackModels: null,
  temperature: null,
  topP: null,
  maxTokens: null,
  systemPromptExtra: null,
};

function rawFromSettings(settings: AdminSettings): RawChat {
  return {
    model: settings.chat.overrides.model,
    fallbackModels: settings.chat.overrides.fallbackModels,
    temperature: settings.chat.overrides.temperature,
    topP: settings.chat.overrides.topP,
    maxTokens: settings.chat.overrides.maxTokens,
    systemPromptExtra: settings.chat.overrides.systemPromptExtra,
  };
}

function validateRaw(raw: RawChat): FieldErrors {
  const errors: FieldErrors = {};
  if (raw.model !== null && (!raw.model.trim() || raw.model.length > 200 || /\s|[\u0000-\u001f\u007f]/u.test(raw.model))) {
    errors.model = "Enter a model identifier without whitespace or controls.";
  }
  if (raw.fallbackModels !== null) {
    if (raw.fallbackModels.length > 8) errors.fallbackModels = "Choose at most 8 fallback models.";
    if (raw.model && raw.fallbackModels.includes(raw.model)) errors.fallbackModels = "Fallbacks must not repeat the primary model.";
  }
  if (raw.temperature !== null && (!Number.isFinite(raw.temperature) || raw.temperature < 0 || raw.temperature > 2)) {
    errors.temperature = "Temperature must be between 0 and 2.";
  }
  if (raw.topP !== null && (!Number.isFinite(raw.topP) || raw.topP < 0 || raw.topP > 1)) {
    errors.topP = "Top-p must be between 0 and 1.";
  }
  if (raw.maxTokens !== null && (!Number.isInteger(raw.maxTokens) || raw.maxTokens < 1 || raw.maxTokens > 32768)) {
    errors.maxTokens = "Max tokens must be an integer from 1 to 32768.";
  }
  if (raw.systemPromptExtra !== null && (raw.systemPromptExtra.length > 4000 || Array.from(raw.systemPromptExtra).some((char) => /\p{Cc}/u.test(char) && char !== "\n" && char !== "\t"))) {
    errors.systemPromptExtra = "Prompt suffix must be at most 4,000 characters without controls.";
  }
  return errors;
}

function displayValue(value: unknown, field: ChatField, t: (key: string) => string): string {
  if (value === null) return t("settings.useEnvironment");
  if (field === "fallbackModels") {
    if (Array.isArray(value) && value.length === 0) return t("settings.chatNoFallbacks");
    return Array.isArray(value) ? value.join(", ") : t("settings.emptyValue");
  }
  if (value === "") return t("settings.emptyValue");
  return String(value);
}

export default function ChatbotTab({ auth }: { auth: AuthProfileController }) {
  const t = useT();
  const [settings, setSettings] = useState<AdminSettings | null>(null);
  const [raw, setRaw] = useState<RawChat>(EMPTY_RAW);
  const [initialRaw, setInitialRaw] = useState<RawChat | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [success, setSuccess] = useState(false);
  const [conflict, setConflict] = useState(false);

  const hydrate = (next: AdminSettings) => {
    const nextRaw = rawFromSettings(next);
    setSettings(next);
    setRaw(nextRaw);
    setInitialRaw(nextRaw);
    setFieldErrors({});
  };

  useEffect(() => {
    if (!auth.token || auth.profile?.role !== "admin") return;
    const controller = new AbortController();
    void fetchAdminSettings(auth.token, { signal: controller.signal })
      .then(hydrate)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : t("settings.loadError"));
      });
    return () => controller.abort();
  }, [auth.profile?.role, auth.token, t]);

  const reload = async () => {
    if (!auth.token) return;
    setConflict(false);
    setError(null);
    try {
      hydrate(await fetchAdminSettings(auth.token));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : t("settings.loadError"));
    }
  };

  const clientErrors = useMemo(() => validateRaw(raw), [raw]);
  const errors = { ...fieldErrors, ...clientErrors };
  const dirty = Boolean(settings && initialRaw && JSON.stringify(raw) !== JSON.stringify(initialRaw));
  const save = async () => {
    if (!auth.token || !settings || busy || !dirty) return;
    if (Object.keys(clientErrors).length) {
      setFieldErrors(clientErrors);
      return;
    }
    setBusy(true); setError(null); setSuccess(false); setConflict(false); setFieldErrors({});
    try {
      const next = await updateAdminSettings(auth.token, settings.version, { chat: raw });
      hydrate(next);
      setSuccess(true);
    } catch (reason: unknown) {
      const isConflict = reason instanceof AuthApiError && reason.status === 409;
      setConflict(isConflict);
      setError(isConflict ? t("settings.chatConflict") : reason instanceof AuthApiError ? t("settings.saveError") : reason instanceof Error ? reason.message : t("settings.saveError"));
    } finally {
      setBusy(false);
    }
  };

  if (auth.profile?.role !== "admin") {
    return <p role="alert" className="text-sm text-red-300">{t("settings.adminOnly")}</p>;
  }
  if (!settings && !error) return <div aria-busy="true" className="h-48 animate-pulse rounded-lg bg-gray-800" />;

  const availableModels = settings?.chat.availableModels ?? [];
  const modelOptions = raw.model && !availableModels.includes(raw.model) ? [raw.model, ...availableModels] : availableModels;
  const columns: Array<[ChatField, string, unknown, unknown, unknown]> = settings ? [
    ["model", t("settings.chatModel"), raw.model, settings.chat.defaults.model, settings.chat.effective.model],
    ["fallbackModels", t("settings.chatFallbacks"), raw.fallbackModels, settings.chat.defaults.fallbackModels, settings.chat.effective.fallbackModels],
    ["temperature", t("settings.chatTemperature"), raw.temperature, settings.chat.defaults.temperature, settings.chat.effective.temperature],
    ["topP", t("settings.chatTopP"), raw.topP, settings.chat.defaults.topP, settings.chat.effective.topP],
    ["maxTokens", t("settings.chatMaxTokens"), raw.maxTokens, settings.chat.defaults.maxTokens, settings.chat.effective.maxTokens],
    ["systemPromptExtra", t("settings.chatPromptSuffix"), raw.systemPromptExtra, settings.chat.defaults.systemPromptExtra, settings.chat.effective.systemPromptExtra],
  ] : [];
  const fieldId = (field: ChatField) => `chat-${field}`;
  const errorId = (field: ChatField) => `${fieldId(field)}-error`;
  const update = <K extends ChatField>(field: K, value: RawChat[K]) => {
    setRaw((current) => ({ ...current, [field]: value }));
    setFieldErrors((current) => ({ ...current, [field]: undefined }));
    setError(null);
  };

  return (
    <div className="space-y-5" aria-busy={busy}>
      <p className="text-xs text-gray-500">{t("settings.chatbotHint")}</p>
      <p className="rounded border border-amber-700/60 bg-amber-950/30 p-3 text-xs text-amber-200">{t("settings.chatProviderWarning")}</p>
      <div><label htmlFor={fieldId("model")} className="mb-1 block text-sm text-gray-200">{t("settings.chatModel")}</label><select id={fieldId("model")} value={raw.model ?? ""} onChange={(event) => update("model", event.target.value || null)} aria-invalid={Boolean(errors.model)} aria-describedby={errors.model ? errorId("model") : undefined} className="w-full rounded-md border border-gray-600 bg-gray-900 px-3 py-2 text-gray-100"><option value="">{t("settings.useEnvironment")}</option>{modelOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select>{errors.model ? <p id={errorId("model")} role="alert" className="mt-1 text-xs text-red-300">{errors.model}</p> : null}</div>
      <div><label htmlFor={fieldId("fallbackModels")} className="mb-1 block text-sm text-gray-200">{t("settings.chatFallbacks")}</label><select id={fieldId("fallbackModels")} multiple value={raw.fallbackModels ?? []} onChange={(event) => update("fallbackModels", Array.from(event.target.selectedOptions, (option) => option.value))} aria-invalid={Boolean(errors.fallbackModels)} aria-describedby={errors.fallbackModels ? errorId("fallbackModels") : undefined} className="min-h-24 w-full rounded-md border border-gray-600 bg-gray-900 px-3 py-2 text-gray-100">{availableModels.map((item) => <option key={item} value={item}>{item}</option>)}</select><div className="mt-2 flex flex-wrap gap-2"><button type="button" onClick={() => update("fallbackModels", null)} className={`rounded border px-2 py-1 text-xs ${raw.fallbackModels === null ? "border-teal-400 text-teal-200" : "border-gray-600 text-gray-400"}`}>{t("settings.chatUseEnvironmentFallbacks")}</button><button type="button" onClick={() => update("fallbackModels", [])} className={`rounded border px-2 py-1 text-xs ${Array.isArray(raw.fallbackModels) && raw.fallbackModels.length === 0 ? "border-teal-400 text-teal-200" : "border-gray-600 text-gray-400"}`}>{t("settings.chatNoFallbacks")}</button></div>{errors.fallbackModels ? <p id={errorId("fallbackModels")} role="alert" className="mt-1 text-xs text-red-300">{errors.fallbackModels}</p> : null}</div>
      {(["temperature", "topP", "maxTokens"] as const).map((field) => { const label = field === "temperature" ? t("settings.chatTemperature") : field === "topP" ? t("settings.chatTopP") : t("settings.chatMaxTokens"); const value = raw[field]; const min = field === "temperature" ? 0 : field === "topP" ? 0 : 1; const max = field === "temperature" ? 2 : field === "topP" ? 1 : 32768; return <div key={field}><label htmlFor={fieldId(field)} className="mb-1 block text-sm text-gray-200">{label}</label><input id={fieldId(field)} type="number" min={min} max={max} step={field === "maxTokens" ? 1 : field === "temperature" ? 0.1 : 0.05} value={value ?? ""} onChange={(event) => update(field, event.target.value === "" ? null : Number(event.target.value))} aria-invalid={Boolean(errors[field])} aria-describedby={errors[field] ? errorId(field) : undefined} className="w-full rounded-md border border-gray-600 bg-gray-900 px-2 py-2" />{errors[field] ? <p id={errorId(field)} role="alert" className="mt-1 text-xs text-red-300">{errors[field]}</p> : null}</div>; })}
      <div><label htmlFor={fieldId("systemPromptExtra")} className="mb-1 block text-sm text-gray-200">{t("settings.chatPromptSuffix")}</label><textarea id={fieldId("systemPromptExtra")} maxLength={4000} value={raw.systemPromptExtra ?? ""} onChange={(event) => update("systemPromptExtra", event.target.value || null)} aria-invalid={Boolean(errors.systemPromptExtra)} aria-describedby={errors.systemPromptExtra ? errorId("systemPromptExtra") : undefined} className="min-h-28 w-full rounded-md border border-gray-600 bg-gray-900 px-3 py-2 text-gray-100" />{errors.systemPromptExtra ? <p id={errorId("systemPromptExtra")} role="alert" className="mt-1 text-xs text-red-300">{errors.systemPromptExtra}</p> : null}</div>
      <div className="grid gap-3 rounded-lg border border-gray-700 bg-gray-900/50 p-3 text-xs text-gray-400 sm:grid-cols-3"><div><p className="font-medium text-gray-300">{t("settings.chatRaw")}</p><dl>{columns.map(([field, label, value]) => <div key={`raw-${field}`}><dt className="inline">{label}: </dt><dd className="inline">{displayValue(value, field, t)}</dd></div>)}</dl></div><div><p className="font-medium text-gray-300">{t("settings.chatDefaults")}</p><dl>{columns.map(([field, label, , value]) => <div key={`default-${field}`}><dt className="inline">{label}: </dt><dd className="inline">{displayValue(value, field, t)}</dd></div>)}</dl></div><div><p className="font-medium text-gray-300">{t("settings.chatEffective")}</p><dl>{columns.map(([field, label, , , value]) => <div key={`effective-${field}`}><dt className="inline">{label}: </dt><dd className="inline">{displayValue(value, field, t)}</dd></div>)}</dl></div></div>
      {error ? <p role="alert" className="text-sm text-red-300">{error}</p> : null}{conflict ? <button type="button" onClick={() => void reload()} className="text-sm text-amber-300 underline">{t("settings.chatReload")}</button> : null}{success ? <p role="status" className="text-sm text-teal-300">{t("settings.saved")}</p> : null}
      <button type="button" disabled={!settings || !dirty || busy || Object.values(errors).some(Boolean)} onClick={() => void save()} className="rounded-md bg-teal-400 px-4 py-2 text-sm font-medium text-teal-950 disabled:opacity-50">{busy ? t("settings.saving") : t("settings.save")}</button>
    </div>
  );
}
