'use client';

import {
  useEffect,
  useLayoutEffect,
  useRef,
  type PointerEvent,
  type RefObject,
} from 'react';

type WindowRange = { start: number; count: number };
type ChartGestureOptions = WindowRange & {
  svgRef: RefObject<SVGSVGElement | null>;
  enabled: boolean;
  total: number;
  maxCount?: number;
  onNavigate: (start: number, count: number) => void;
  onGesture: () => void;
  plotLeft: number;
  plotWidth: number;
};

/** Clamp navigation to observations that exist; never fabricate samples. */
export function clampChartWindow(
  start: number,
  count: number,
  total: number,
  maxCount = total,
): WindowRange {
  const available = Number.isFinite(total) ? Math.max(0, Math.floor(total)) : 0;
  const limit = Number.isFinite(maxCount)
    ? Math.max(0, Math.floor(maxCount))
    : available;
  const boundedCount = Math.min(
    available,
    limit,
    Math.max(0, Number.isFinite(count) ? Math.round(count) : 0),
  );
  return {
    start: Math.max(
      0,
      Math.min(
        available - boundedCount,
        Number.isFinite(start) ? Math.round(start) : 0,
      ),
    ),
    count: boundedCount,
  };
}

export function zoomChartWindow(
  start: number,
  count: number,
  total: number,
  factor: number,
  anchor = 0.5,
  maxCount = total,
): WindowRange {
  if (count <= 0 || total <= 0)
    return clampChartWindow(start, count, total, maxCount);
  const scaledCount = Math.round(count * factor);
  // Fractional wheel steps must still cross 1 ↔ 2; rounding alone can get stuck.
  const requestedCount =
    factor < 1
      ? Math.min(count - 1, scaledCount)
      : factor > 1
        ? Math.max(count + 1, scaledCount)
        : count;
  const nextCount = Math.min(total, maxCount, Math.max(1, requestedCount));
  const fraction = Math.max(0, Math.min(1, anchor));
  return clampChartWindow(
    start + (count - nextCount) * fraction,
    nextCount,
    total,
    maxCount,
  );
}

function localX(
  svg: SVGSVGElement,
  clientX: number,
  clientY: number,
): number | null {
  const matrix = svg.getScreenCTM?.();
  if (matrix) {
    try {
      const inverse = matrix.inverse();
      const result = inverse.a * clientX + inverse.c * clientY + inverse.e;
      return Number.isFinite(result) ? result : null;
    } catch {
      return null;
    }
  }
  const bounds = svg.getBoundingClientRect();
  const viewBox = svg.viewBox?.baseVal;
  if (bounds.width <= 0 || bounds.height <= 0) return null;
  const width = viewBox?.width || bounds.width;
  const height = viewBox?.height || bounds.height;
  // SVG's default xMidYMid meet centers the drawing when its box has another ratio.
  const scale = Math.min(bounds.width / width, bounds.height / height);
  if (!Number.isFinite(scale) || scale <= 0) return null;
  return (
    (clientX - bounds.left - (bounds.width - width * scale) / 2) / scale +
    (viewBox?.x || 0)
  );
}

/** Mouse gestures are opt-in for expanded charts; regular wheel keeps page scroll. */
export function useChartGestures(options: ChartGestureOptions) {
  const latest = useRef(options);
  const drag = useRef<{
    pointerId: number;
    clientX: number;
    localX: number;
    start: number;
    count: number;
    plotWidth: number;
    active: boolean;
    element: SVGSVGElement;
  } | null>(null);
  const suppressClick = useRef(false);
  useLayoutEffect(() => {
    latest.current = options;
  });

  const stopDrag = () => {
    const previous = drag.current;
    drag.current = null;
    if (!previous) return false;
    delete previous.element.dataset.chartDragging;
    if (previous.element.hasPointerCapture?.(previous.pointerId)) {
      previous.element.releasePointerCapture(previous.pointerId);
    }
    return previous.active;
  };

  useEffect(() => {
    if (!options.enabled) stopDrag();
    const svg = options.svgRef.current;
    if (!svg || !options.enabled) return;
    const wheel = (event: WheelEvent) => {
      const current = latest.current;
      // Preserve browser zoom and modified gestures. Do not hijack ordinary scroll outside fullscreen.
      if (
        !current.enabled ||
        event.ctrlKey ||
        event.metaKey ||
        event.altKey ||
        current.count <= 0 ||
        !Number.isFinite(event.deltaY) ||
        event.deltaY === 0
      )
        return;
      const x = localX(svg, event.clientX, event.clientY);
      if (
        x === null ||
        !Number.isFinite(current.plotWidth) ||
        current.plotWidth <= 0 ||
        x < current.plotLeft ||
        x > current.plotLeft + current.plotWidth
      )
        return;
      event.preventDefault();
      stopDrag();
      current.onGesture();
      const next = zoomChartWindow(
        current.start,
        current.count,
        current.total,
        event.deltaY < 0 ? 0.8 : 1.25,
        (x - current.plotLeft) / current.plotWidth,
        current.maxCount,
      );
      if (next.start !== current.start || next.count !== current.count) {
        latest.current = { ...current, ...next };
        current.onNavigate(next.start, next.count);
      }
    };
    svg.addEventListener('wheel', wheel, { passive: false });
    return () => {
      svg.removeEventListener('wheel', wheel);
      stopDrag();
    };
  }, [options.enabled, options.svgRef]);

  return {
    onPointerDown(event: PointerEvent<SVGSVGElement>) {
      const current = latest.current;
      suppressClick.current = false;
      if (
        !current.enabled ||
        event.button !== 0 ||
        (event.pointerType && event.pointerType !== 'mouse') ||
        current.count <= 0 ||
        current.plotWidth <= 0
      )
        return false;
      const x = localX(event.currentTarget, event.clientX, event.clientY);
      if (
        x === null ||
        x < current.plotLeft ||
        x > current.plotLeft + current.plotWidth
      )
        return false;
      drag.current = {
        pointerId: event.pointerId,
        clientX: event.clientX,
        localX: x,
        start: current.start,
        count: current.count,
        plotWidth: current.plotWidth,
        active: false,
        element: event.currentTarget,
      };
      event.currentTarget.setPointerCapture?.(event.pointerId);
      return false; // A click can still inspect the observation; dragging starts after the threshold.
    },
    onPointerMove(event: PointerEvent<SVGSVGElement>) {
      const current = latest.current;
      const previous = drag.current;
      if (
        !current.enabled ||
        !previous ||
        previous.pointerId !== event.pointerId
      )
        return false;
      if (!previous.active && Math.abs(event.clientX - previous.clientX) < 3)
        return false;
      const x = localX(event.currentTarget, event.clientX, event.clientY);
      if (x === null) return previous.active;
      if (!previous.active) {
        previous.active = true;
        previous.element.dataset.chartDragging = 'true';
        suppressClick.current = true;
        current.onGesture();
      }
      event.preventDefault();
      const shift = Math.round(
        ((x - previous.localX) / previous.plotWidth) *
          Math.max(1, previous.count - 1),
      );
      const next = clampChartWindow(
        previous.start - shift,
        previous.count,
        current.total,
        current.maxCount,
      );
      if (next.start !== current.start || next.count !== current.count) {
        latest.current = { ...current, ...next };
        current.onNavigate(next.start, next.count);
      }
      return true;
    },
    onPointerUp(event: PointerEvent<SVGSVGElement>) {
      if (drag.current?.pointerId !== event.pointerId) return false;
      return stopDrag();
    },
    onPointerCancel(event: PointerEvent<SVGSVGElement>) {
      if (drag.current?.pointerId !== event.pointerId) return false;
      return stopDrag();
    },
    onLostPointerCapture(event: PointerEvent<SVGSVGElement>) {
      if (drag.current?.pointerId !== event.pointerId) return false;
      return stopDrag();
    },
    onClick() {
      const consumed = suppressClick.current;
      suppressClick.current = false;
      return consumed;
    },
  };
}
