import { webcrypto } from "node:crypto";
import "@testing-library/jest-dom/vitest";

if (typeof globalThis.crypto === "undefined") {
  Object.defineProperty(globalThis, "crypto", { value: webcrypto, configurable: true });
} else {
  if (!globalThis.crypto.subtle) {
    Object.defineProperty(globalThis.crypto, "subtle", { value: webcrypto.subtle, configurable: true });
  }
  if (!globalThis.crypto.getRandomValues) {
    Object.defineProperty(globalThis.crypto, "getRandomValues", {
      value: webcrypto.getRandomValues.bind(webcrypto),
      configurable: true,
    });
  }
}
