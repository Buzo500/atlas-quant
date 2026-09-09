'use client';

import {
  createContext,
  useEffect,
  useId,
  useRef,
  type CSSProperties,
  type ReactNode,
  type RefObject,
} from 'react';
import { Maximize2, Minimize2, RotateCcw, ZoomIn, ZoomOut } from 'lucide-react';
import { clampChartWindow, zoomChartWindow } from './chart-gestures';
import './chart-workspace.css';

export const ChartPortalContext = createContext<{
  root: RefObject<HTMLDivElement | null>;
  expanded: boolean;
} | null>(null);

export type ChartWorkspaceProps = {
  title: string;
  noun: 'curva' | 'precios';
  expanded: boolean;
  onExpandedChange: (expanded: boolean) => void;
  start: number;
  count: number;
  total: number;
  maxCount?: number;
  /** Fraction of the current window to retain when using the zoom buttons. */
  zoomAnchor?: number;
  onNavigate: (start: number, count: number) => void;
  onReset: () => void;
  children: ReactNode;
};

export function ChartWorkspace({
  title,
  noun,
  expanded,
  onExpandedChange,
  start,
  count,
  total,
  maxCount = total,
  zoomAnchor = 0.5,
  onNavigate,
  onReset,
  children,
}: ChartWorkspaceProps) {
  const root = useRef<HTMLDivElement>(null);
  const expandButton = useRef<HTMLButtonElement>(null);
  const restoreFocus = useRef<HTMLElement | null>(null);
  const desired = useRef(expanded);
  const wasNative = useRef(false);
  const mounted = useRef(true);
  const callback = useRef(onExpandedChange);
  const labelId = useId();
  const hintId = useId();
  const window = clampChartWindow(start, count, total, maxCount);
  const maxStart = Math.max(0, total - window.count);
  useEffect(() => {
    callback.current = onExpandedChange;
  }, [onExpandedChange]);
  useEffect(() => {
    desired.current = expanded;
  }, [expanded]);

  const close = () => {
    desired.current = false;
    if (
      document.fullscreenElement === root.current &&
      document.exitFullscreen
    ) {
      void document
        .exitFullscreen()
        .then(() => {
          if (mounted.current && !desired.current) callback.current(false);
        })
        .catch(() => {
          // Keep the exit control visible if the browser declined to leave fullscreen.
          if (mounted.current) desired.current = true;
        });
    } else callback.current(false);
  };

  useEffect(() => {
    mounted.current = true;
    const fullscreen = () => {
      if (document.fullscreenElement === root.current) wasNative.current = true;
      else if (wasNative.current) {
        wasNative.current = false;
        desired.current = false;
        callback.current(false);
      }
    };
    document.addEventListener('fullscreenchange', fullscreen);
    const element = root.current;
    return () => {
      mounted.current = false;
      desired.current = false;
      document.removeEventListener('fullscreenchange', fullscreen);
      if (document.fullscreenElement === element)
        void document.exitFullscreen?.().catch(() => {});
    };
  }, []);

  useEffect(() => {
    if (!expanded || !root.current) return;
    const element = root.current;
    const priorOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const priorFocus =
      restoreFocus.current ??
      (document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null);
    const inertSiblings: Array<{ element: Element; prior: string | null }> = [];
    // Keep unrelated controls out of both keyboard and assistive-technology navigation.
    let branch: Element = element;
    while (branch.parentElement && branch !== document.body) {
      for (const sibling of branch.parentElement.children) {
        if (
          sibling === branch ||
          sibling.tagName === 'SCRIPT' ||
          sibling.tagName === 'STYLE'
        )
          continue;
        inertSiblings.push({
          element: sibling,
          prior: sibling.getAttribute('inert'),
        });
        sibling.setAttribute('inert', '');
      }
      branch = branch.parentElement;
    }
    const focusable = () =>
      Array.from(
        element.querySelectorAll<HTMLElement>(
          'button:not(:disabled),input:not(:disabled),select:not(:disabled),a[href],[tabindex="0"]',
        ),
      )
        .filter((node) => !node.closest('[hidden],[inert]'))
        // Preserve document order across HTML and SVG namespaces as well.
        .sort((first, second) =>
          first.compareDocumentPosition(second) &
          Node.DOCUMENT_POSITION_FOLLOWING
            ? -1
            : 1,
        );
    expandButton.current?.focus();
    const key = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        event.stopPropagation();
        close();
        return;
      }
      if (event.key !== 'Tab') return;
      const controls = focusable();
      const first = controls[0] ?? element;
      const last = controls[controls.length - 1] ?? element;
      if (
        event.shiftKey &&
        (document.activeElement === first ||
          !element.contains(document.activeElement))
      ) {
        event.preventDefault();
        last.focus();
      } else if (
        !event.shiftKey &&
        (document.activeElement === last ||
          !element.contains(document.activeElement))
      ) {
        event.preventDefault();
        first.focus();
      }
    };
    const focus = (event: FocusEvent) => {
      if (event.target instanceof Node && !element.contains(event.target))
        expandButton.current?.focus();
    };
    document.addEventListener('keydown', key, true);
    document.addEventListener('focusin', focus);
    return () => {
      document.removeEventListener('keydown', key, true);
      document.removeEventListener('focusin', focus);
      document.body.style.overflow = priorOverflow;
      for (const item of inertSiblings) {
        if (item.prior === null) item.element.removeAttribute('inert');
        else item.element.setAttribute('inert', item.prior);
      }
      if (priorFocus?.isConnected) priorFocus.focus();
      restoreFocus.current = null;
    };
  }, [expanded]);

  const toggle = () => {
    if (expanded) {
      close();
      return;
    }
    restoreFocus.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    desired.current = true;
    onExpandedChange(true);
    const element = root.current;
    if (!element?.requestFullscreen) return;
    // The same DOM remains mounted; denied/unavailable fullscreen falls back to a viewport dialog.
    try {
      void element
        .requestFullscreen()
        .then(() => {
          if (
            (!mounted.current || !desired.current) &&
            document.fullscreenElement === element
          )
            void document.exitFullscreen?.().catch(() => {});
        })
        .catch(() => {});
    } catch {
      /* Embedded browsers can expose an API that throws synchronously. */
    }
  };
  const zoom = (factor: number) => {
    const next = zoomChartWindow(
      window.start,
      window.count,
      total,
      factor,
      zoomAnchor,
      maxCount,
    );
    onNavigate(next.start, next.count);
  };
  const number = (value: number) => value.toLocaleString('es-ES');
  return (
    <ChartPortalContext.Provider value={{ root, expanded }}>
      <div
        ref={root}
        className={`chart-workspace${expanded ? ' is-expanded' : ''}`}
        role={expanded ? 'dialog' : undefined}
        aria-modal={expanded ? true : undefined}
        aria-labelledby={expanded ? labelId : undefined}
        tabIndex={expanded ? -1 : undefined}
      >
        {(total > 0 || expanded) && (
          <div className="chart-workspace-toolbar">
            <span id={labelId} className="chart-workspace-title">
              {title}
            </span>
            <fieldset
              className="chart-workspace-actions"
              aria-label={`Vista de ${noun}`}
            >
              <button
                type="button"
                aria-label={`Acercar ${noun}`}
                title={`Acercar ${noun}`}
                disabled={window.count <= 1}
                onClick={() => zoom(0.5)}
              >
                <ZoomIn aria-hidden="true" />
              </button>
              <button
                type="button"
                aria-label={`Alejar ${noun}`}
                title={`Alejar ${noun}`}
                disabled={
                  window.count <= 0 || window.count >= Math.min(total, maxCount)
                }
                onClick={() => zoom(2)}
              >
                <ZoomOut aria-hidden="true" />
              </button>
              <button
                type="button"
                aria-label={
                  noun === 'curva' ? 'Restablecer curva' : 'Restablecer vista'
                }
                title={
                  noun === 'curva' ? 'Restablecer curva' : 'Restablecer vista'
                }
                onClick={onReset}
              >
                <RotateCcw aria-hidden="true" />
              </button>
              <span className="chart-workspace-separator" aria-hidden="true" />
              <button
                ref={expandButton}
                type="button"
                aria-label={
                  expanded
                    ? 'Salir de pantalla completa'
                    : `Pantalla completa: ${title}`
                }
                title={
                  expanded
                    ? 'Salir de pantalla completa (Esc)'
                    : `Pantalla completa: ${title}`
                }
                onClick={toggle}
              >
                {expanded ? (
                  <Minimize2 aria-hidden="true" />
                ) : (
                  <Maximize2 aria-hidden="true" />
                )}
              </button>
            </fieldset>
          </div>
        )}
        {expanded && (
          <p className="chart-workspace-hint" id={hintId}>
            Arrastra el gráfico para desplazarte · rueda para ampliar o reducir
            · Esc para salir
          </p>
        )}
        <div className="chart-workspace-canvas">{children}</div>
        {total > 0 && (
          <div className="chart-workspace-navigation">
            <input
              className="chart-workspace-range"
              type="range"
              min={0}
              max={maxStart}
              step={1}
              value={window.start}
              disabled={window.count <= 0 || maxStart === 0}
              aria-label={`Desplazar ${noun}`}
              aria-valuetext={
                window.count
                  ? `Observaciones ${number(window.start + 1)} a ${number(window.start + window.count)} de ${number(total)}`
                  : 'Sin observaciones en la vista'
              }
              aria-describedby={expanded ? hintId : undefined}
              title={`Arrastra para desplazar ${noun}`}
              style={
                {
                  '--chart-window-width': `${(100 * window.count) / total}%`,
                } as CSSProperties
              }
              onChange={(event) =>
                onNavigate(Number(event.currentTarget.value), window.count)
              }
            />
            <span className="chart-workspace-range-caption" aria-hidden="true">
              {window.count
                ? `${number(window.start + 1)}–${number(window.start + window.count)} / ${number(total)}`
                : `0 / ${number(total)}`}
            </span>
          </div>
        )}
      </div>
    </ChartPortalContext.Provider>
  );
}
