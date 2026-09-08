'use client';
import { useCallback, useEffect, useRef, useState } from 'react';

export const sections = [
  'portfolio',
  'lab',
  'agent',
  'data',
  'settings',
] as const;
export type Section = (typeof sections)[number];
type Navigation = { tab: Section; dataset: string; experiment: string };
const initial: Navigation = { tab: 'portfolio', dataset: '', experiment: '' };
const identifier = (value: string | null) =>
  value && /^[a-zA-Z0-9_-]{1,128}$/.test(value) ? value : '';
export function readNavigation(search: string): Navigation {
  const params = new URLSearchParams(search);
  const tab = params.get('tab');
  return {
    tab: sections.includes(tab as Section) ? (tab as Section) : 'portfolio',
    dataset: identifier(params.get('dataset')),
    experiment: identifier(params.get('experiment')),
  };
}

/** URL stores navigation only. Drafts live in mounted panels; authorization,
 * CSV, hypotheses and provider configuration are never persisted here. */
export function useNavigation() {
  const [navigation, setNavigation] = useState(initial);
  const current = useRef(initial);
  useEffect(() => {
    const read = () => {
      current.current = readNavigation(window.location.search);
      setNavigation(current.current);
    };
    read();
    window.addEventListener('popstate', read);
    return () => window.removeEventListener('popstate', read);
  }, []);
  const navigate = useCallback((patch: Partial<Navigation>) => {
    const next = { ...current.current, ...patch };
    const params = new URLSearchParams();
    if (next.tab !== 'portfolio') params.set('tab', next.tab);
    if (next.dataset) params.set('dataset', next.dataset);
    if (next.experiment) params.set('experiment', next.experiment);
    const query = params.toString();
    const url =
      window.location.pathname +
      (query ? '?' + query : '') +
      window.location.hash;
    if (
      url !==
      window.location.pathname + window.location.search + window.location.hash
    )
      window.history.pushState(null, '', url);
    current.current = next;
    setNavigation(next);
  }, []);
  return { navigation, navigate };
}
