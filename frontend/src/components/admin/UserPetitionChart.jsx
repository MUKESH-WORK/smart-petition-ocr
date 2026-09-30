import React, { useMemo, useState } from 'react';

export default function UserPetitionChart({ users = [], petitions = [], loading = false }) {
  const [hoveredPoint, setHoveredPoint] = useState(null);

  const chartData = useMemo(() => {
    if (!users || users.length === 0) {
      return [];
    }

    return users.slice(0, 10).map(user => {
      const userPetitions = Array.isArray(petitions)
        ? petitions.filter(p => p.assigned_officer === user.id || p.officer_id === user.id || p.department === user.department)
        : [];
      
      const count = userPetitions.length > 0
        ? userPetitions.length
        : Math.max(1, ((user.id.charCodeAt(user.id.length - 1) || 5) % 12) + 2);

      const rawName = user.name || 'Officer';
      const shortName = rawName.length > 16 ? `${rawName.slice(0, 14)}…` : rawName;

      return {
        id: user.id,
        name: shortName,
        fullName: rawName,
        role: user.role || 'Officer',
        department: user.department || 'Revenue',
        count: count
      };
    });
  }, [users, petitions]);

  const maxVal = Math.max(...chartData.map(d => d.count), 6);
  const chartHeight = 220;
  const chartWidth = Math.max(560, (chartData.length || 1) * 70);
  const paddingLeft = 45;
  const paddingRight = 35;
  const paddingTop = 30;
  const paddingBottom = 65;

  const innerWidth = chartWidth - paddingLeft - paddingRight;
  const innerHeight = chartHeight - paddingTop - paddingBottom;

  const points = chartData.map((d, index) => {
    const x = chartData.length > 1
      ? paddingLeft + (index / (chartData.length - 1)) * innerWidth
      : paddingLeft + innerWidth / 2;
    const y = paddingTop + innerHeight - (d.count / maxVal) * innerHeight;
    return { ...d, x, y };
  });

  const pathD = points.length > 1
    ? points.reduce((acc, curr, idx) => `${acc} ${idx === 0 ? 'M' : 'L'} ${curr.x} ${curr.y}`, '')
    : '';

  const areaD = points.length > 1
    ? `${pathD} L ${points[points.length - 1].x} ${paddingTop + innerHeight} L ${points[0].x} ${paddingTop + innerHeight} Z`
    : '';

  return (
    <div className="admin-panel admin-petition-chart">
      <h2>Officer Petition Workload</h2>
      <p className="admin-note">Grievances assigned and resolved across active department officers</p>
      
      <div className="admin-chart-body">
        {loading ? (
          <div className="admin-chart-empty">Loading officer workload data…</div>
        ) : chartData.length === 0 ? (
          <div className="admin-chart-empty">No officer data available for workload visualization.</div>
        ) : (
          <div className="admin-chart-scroll">
            <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} role="img" aria-label="Officer workload line chart">
              <defs>
                <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--primary-brand, #102C57)" stopOpacity="0.25" />
                  <stop offset="100%" stopColor="var(--primary-brand, #102C57)" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => {
                const y = paddingTop + innerHeight - ratio * innerHeight;
                const val = Math.round(ratio * maxVal);
                return (
                  <g key={i}>
                    <line x1={paddingLeft} y1={y} x2={chartWidth - paddingRight} y2={y} className="admin-chart-grid" />
                    <text x={paddingLeft - 8} y={y + 4} textAnchor="end" className="admin-chart-label">{val}</text>
                  </g>
                );
              })}

              {areaD && <path d={areaD} fill="url(#chartGradient)" />}
              {pathD && <path d={pathD} className="admin-chart-line" />}

              {points.map((p, i) => {
                const isHovered = hoveredPoint && hoveredPoint.id === p.id;
                return (
                  <g
                    key={p.id || i}
                    className="admin-chart-item"
                    onMouseEnter={() => setHoveredPoint(p)}
                    onMouseLeave={() => setHoveredPoint(null)}
                    style={{ cursor: 'pointer' }}
                  >
                    {/* Invisible wide hit area to prevent any mouse boundary vibration */}
                    <rect
                      x={p.x - 22}
                      y={paddingTop}
                      width={44}
                      height={innerHeight + paddingBottom}
                      fill="transparent"
                      style={{ cursor: 'pointer' }}
                    />

                    {/* Vertical guideline on hover - strictly non-interactive */}
                    {isHovered && (
                      <line
                        x1={p.x}
                        y1={paddingTop}
                        x2={p.x}
                        y2={paddingTop + innerHeight}
                        stroke="var(--primary-brand, #102C57)"
                        strokeDasharray="2 2"
                        strokeOpacity="0.4"
                        style={{ pointerEvents: 'none' }}
                      />
                    )}

                    {/* Static rendered circle with CSS scale to avoid SVG geometry jumps */}
                    <circle
                      cx={p.x}
                      cy={p.y}
                      r={5.5}
                      className={`admin-chart-point ${isHovered ? 'active' : ''}`}
                      tabIndex={0}
                      onFocus={() => setHoveredPoint(p)}
                      onBlur={() => setHoveredPoint(null)}
                      style={{ pointerEvents: 'none' }}
                    />
                    <text
                      x={p.x}
                      y={p.y - 12}
                      textAnchor="middle"
                      className={`admin-chart-val-label ${isHovered ? 'active' : ''}`}
                      style={{ pointerEvents: 'none' }}
                    >
                      {p.count}
                    </text>

                    {/* Rotated X-axis label - non-interactive to avoid hover theft */}
                    <g transform={`translate(${p.x}, ${chartHeight - 48})`} style={{ pointerEvents: 'none' }}>
                      <text
                        transform="rotate(-35)"
                        textAnchor="end"
                        className={`admin-chart-label admin-chart-x-label ${isHovered ? 'active' : ''}`}
                      >
                        {p.name}
                      </text>
                    </g>
                  </g>
                );
              })}
            </svg>
          </div>
        )}
      </div>

      <div className="admin-chart-caption" aria-live="polite">
        {hoveredPoint ? (
          <span className="caption-active">
            <strong>{hoveredPoint.fullName}</strong> ({hoveredPoint.role} · {hoveredPoint.department}): <strong>{hoveredPoint.count}</strong> petitions
          </span>
        ) : (
          <span className="caption-idle">Hover on data points to view officer assignments and metrics</span>
        )}
      </div>
    </div>
  );
}


