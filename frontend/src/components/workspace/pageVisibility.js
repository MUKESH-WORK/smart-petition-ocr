/**
 * Return the 1-based page with the largest visible area in a scroll viewport.
 * Using overlap (with center-distance tie breaking) is stable for fast scrolls
 * and for pages taller than the viewport.
 */
export function getMostVisiblePage(pageRects, viewportRect) {
  if (!pageRects?.length || !viewportRect) return 1;

  const viewportCenter = (viewportRect.top + viewportRect.bottom) / 2;
  let bestIndex = 0;
  let bestOverlap = -1;
  let bestCenterDistance = Number.POSITIVE_INFINITY;

  pageRects.forEach((rect, index) => {
    if (!rect) return;
    const overlap = Math.max(0, Math.min(rect.bottom, viewportRect.bottom) - Math.max(rect.top, viewportRect.top));
    const centerDistance = Math.abs((rect.top + rect.bottom) / 2 - viewportCenter);
    if (overlap > bestOverlap || (overlap === bestOverlap && centerDistance < bestCenterDistance)) {
      bestIndex = index;
      bestOverlap = overlap;
      bestCenterDistance = centerDistance;
    }
  });

  return bestIndex + 1;
}
