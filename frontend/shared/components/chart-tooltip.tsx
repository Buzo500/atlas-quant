'use client';

import {
  useEffect,
  useContext,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { createPortal } from 'react-dom';
import { ChartPortalContext } from './chart-workspace';
import './chart-tooltip.css';

/** Coordinates in CSS viewport pixels, independently of the SVG viewBox. */
export type ChartTooltipAnchor = { x: number; y: number };

export function ChartTooltip({
  anchor,
  children,
  onDismiss,
  id,
}: {
  anchor: ChartTooltipAnchor | null;
  children: ReactNode;
  onDismiss?: () => void;
  id?: string;
}) {
  const element = useRef<HTMLDivElement>(null);
  const workspace = useContext(ChartPortalContext);
  const [position, setPosition] = useState({ left: 0, top: 0 });
  const visible = anchor !== null;

  useLayoutEffect(() => {
    if (!anchor || !element.current) return;
    const update = () => {
      if (!element.current) return;
      const rect = element.current.getBoundingClientRect();
      const viewport = window.visualViewport;
      const originX = viewport?.offsetLeft ?? 0;
      const originY = viewport?.offsetTop ?? 0;
      const width = viewport?.width ?? window.innerWidth;
      const height = viewport?.height ?? window.innerHeight;
      const margin = 8;
      const gap = 16;
      // Prefer below and to the right. Flip before clamping near an edge.
      const left =
        anchor.x + gap + rect.width <= originX + width - margin
          ? anchor.x + gap
          : anchor.x - gap - rect.width;
      const top =
        anchor.y + gap + rect.height <= originY + height - margin
          ? anchor.y + gap
          : anchor.y - gap - rect.height;
      const next = {
        left: Math.max(
          originX + margin,
          Math.min(left, originX + width - rect.width - margin),
        ),
        top: Math.max(
          originY + margin,
          Math.min(top, originY + height - rect.height - margin),
        ),
      };
      setPosition((previous) =>
        previous.left === next.left && previous.top === next.top
          ? previous
          : next,
      );
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(element.current);
    return () => observer.disconnect();
  }, [anchor, children]);

  useEffect(() => {
    if (!visible || !onDismiss) return;
    const dismiss = () => onDismiss();
    const key = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onDismiss();
    };
    // A fixed tooltip must not linger at an old screen position after scrolling.
    window.addEventListener('scroll', dismiss, true);
    window.addEventListener('resize', dismiss);
    window.addEventListener('blur', dismiss);
    window.addEventListener('keydown', key);
    window.visualViewport?.addEventListener('resize', dismiss);
    return () => {
      window.removeEventListener('scroll', dismiss, true);
      window.removeEventListener('resize', dismiss);
      window.removeEventListener('blur', dismiss);
      window.removeEventListener('keydown', key);
      window.visualViewport?.removeEventListener('resize', dismiss);
    };
  }, [visible, onDismiss]);

  if (!visible || typeof document === 'undefined') return null;
  return createPortal(
    <div
      ref={element}
      id={id}
      role="tooltip"
      className="chart-tooltip"
      style={position}
    >
      {children}
    </div>,
    (workspace?.expanded ? workspace.root.current : null) ??
      document.fullscreenElement ??
      document.body,
  );
}
