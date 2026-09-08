import { cleanup } from '@testing-library/react';
import { afterEach, beforeEach, vi } from 'vitest';

// jsdom does not perform layout. Browser QA remains responsible for responsive
// geometry; these shims only let components use the absent DOM methods safely.
class TestResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

Object.defineProperty(globalThis, 'ResizeObserver', {
  configurable: true,
  writable: true,
  value: TestResizeObserver,
});

for (const method of [
  'scrollIntoView',
  'setPointerCapture',
  'releasePointerCapture',
] as const) {
  if (!HTMLElement.prototype[method]) {
    Object.defineProperty(HTMLElement.prototype, method, {
      configurable: true,
      value() {},
    });
  }
}
if (!HTMLElement.prototype.hasPointerCapture) {
  Object.defineProperty(HTMLElement.prototype, 'hasPointerCapture', {
    configurable: true,
    value: () => false,
  });
}

beforeEach(() => {
  // No test can accidentally use the user's local database or a remote API.
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async () => {
      throw new Error(
        'La prueba debe simular explícitamente su respuesta HTTP.',
      );
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});
