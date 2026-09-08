/** Pure presentation helpers. Bounds are inclusive indices of original observations. */
export type CurveWindow = { start: number; end: number };

export function dateWindow(
  data: readonly { date: string }[],
  from: string,
  to: string,
): CurveWindow {
  const boundary = (date: string, after: boolean) => {
    let low = 0;
    let high = data.length;
    while (low < high) {
      const mid = Math.floor((low + high) / 2);
      if (data[mid].date < date || (after && data[mid].date === date))
        low = mid + 1;
      else high = mid;
    }
    return low;
  };
  return {
    start: from ? boundary(from, false) : 0,
    end: to ? boundary(to, true) - 1 : data.length - 1,
  };
}

export function nearestObservation(
  fraction: number,
  window: CurveWindow,
): number {
  // Ties select the later observation. The x axis represents observations, not elapsed days.
  const bounded = Math.max(
    0,
    Math.min(1, Number.isFinite(fraction) ? fraction : 0),
  );
  return (
    window.start + Math.round(bounded * Math.max(0, window.end - window.start))
  );
}

export function zoomWindow(
  window: CurveWindow,
  length: number,
  factor: number,
  anchor: number,
): CurveWindow {
  if (length === 0 || window.end < window.start) return window;
  const current = window.end - window.start + 1;
  const count = Math.min(
    length,
    Math.max(
      1,
      factor > 1 ? Math.ceil(current * factor) : Math.floor(current * factor),
    ),
  );
  const focus = Math.min(window.end, Math.max(window.start, anchor));
  const fraction = current > 1 ? (focus - window.start) / (current - 1) : 0.5;
  const start = Math.min(
    length - count,
    Math.max(0, Math.round(focus - fraction * (count - 1))),
  );
  return { start, end: start + count - 1 };
}

export function panWindow(
  window: CurveWindow,
  length: number,
  direction: -1 | 1,
): CurveWindow {
  if (length === 0 || window.end < window.start) return window;
  const count = window.end - window.start + 1;
  const start = Math.min(
    length - count,
    Math.max(0, window.start + direction * Math.max(1, Math.floor(count / 2))),
  );
  return { start, end: start + count - 1 };
}
