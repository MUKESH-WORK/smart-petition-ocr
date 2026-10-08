import React, { useMemo, useState, useEffect } from 'react';
import { fetchUserPetitionStats } from '../../services/apiService';

export default function UserPetitionChart({ users = [], petitions = [], loading = false }) {
  const [hoveredPoint, setHoveredPoint] = useState(null);
  const [dbUserStats, setDbUserStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);

  // Fetch authoritative user-petition statistics from the database
  useEffect(() => {
    let active = true;
    fetchUserPetitionStats()
      .then(data => {
        if (active && Array.isArray(data)) {
          setDbUserStats(data);
        }
      })
      .catch(err => {
        console.warn('Could not load authoritative user petition stats:', err);
      })
      .finally(() => {
        if (active) setStatsLoading(false);
      });

    return () => { active = false; };
  }, []);

  const chartData = useMemo(() => {
    // Priority 1: Authoritative DB aggregation from /api/v1/admin/user-petition-stats
    if (dbUserStats && Array.isArray(dbUserStats) && dbUserStats.length > 0) {
      return dbUserStats.map(item => {
        const rawName = item.fullName || item.name || 'Officer';
        const shortName = rawName.length > 18 ? `${rawName.slice(0, 16)}…` : rawName;
        return {
          id: item.id || '',
          name: shortName,
          fullName: rawName,
          role: item.role || 'Officer',
          department: item.department || 'Administration',
          count: Number(item.count) || 0,
          completedCount: Number(item.completedCount) || 0,
          failedCount: Number(item.failedCount) || 0
        };
      });
    }

    // Priority 2: Fallback to computing from actual petitions passed to component
    if (Array.isArray(petitions) && petitions.length > 0) {
      // Filter out test records
      const realPetitions = petitions.filter(p => {
        const fileName = (p.file_name || p.fileName || '').toLowerCase();
        return !fileName.startsWith('test_') && p.status !== 'rejected';
      });

      // Group by officer_id
      const countsByOfficer = {};
      for (const p of realPetitions) {
        const officerId = p.officer_id || p.officerId || p.assigned_officer || 'Unassigned';
        countsByOfficer[officerId] = (countsByOfficer[officerId] || 0) + 1;
      }

      // Map only real uploaders
      return Object.entries(countsByOfficer).map(([officerId, count]) => {
        const matchedUser = Array.isArray(users) ? users.find(u => u.id === officerId) : null;
        const rawName = matchedUser?.name || officerId;
        const shortName = rawName.length > 18 ? `${rawName.slice(0, 16)}…` : rawName;
        return {
          id: officerId,
          name: shortName,
          fullName: rawName,
          role: matchedUser?.role || 'District Administrator',
          department: matchedUser?.department || 'District Administration / Collectorate',
          count: count
        };
      }).sort((a, b) => b.count - a.count);
    }

    return [];
  }, [dbUserStats, petitions, users]);

  const isLoading = (loading || statsLoading) && chartData.length === 0;
  const maxVal = Math.max(...chartData.map(d => d.count), 6);
  const chartHeight = 220;
  const chartWidth = Math.max(560, (chartData.length || 1) * 90);
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
      <h2>Petitions Uploaded by User</h2>
      <p className="admin-note">Real-time intake volume grouped by authenticated user account</p>
      
      <div className="admin-chart-body">
        {isLoading ? (
          <div className="admin-chart-empty">Loading verified petition upload data…</div>
        ) : chartData.length === 0 ? (
          <div className="admin-chart-empty">No petition upload records found in database.</div>
        ) : (
          <div className="admin-chart-scroll">
            <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} role="img" aria-label="Petitions uploaded by user chart">
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

              {/* Single User Pillar/Bar visualization for prominent presentation */}
              {points.length === 1 && (
                <g>
                  {/* Subtle bar background */}
                  <rect
                    x={points[0].x - 28}
                    y={points[0].y}
                    width={56}
                    height={paddingTop + innerHeight - points[0].y}
                    rx={6}
                    fill="var(--primary-brand, #102C57)"
                    opacity="0.12"
                  />
                  <line
                    x1={points[0].x}
                    y1={points[0].y}
                    x2={points[0].x}
                    y2={paddingTop + innerHeight}
                    stroke="var(--primary-brand, #102C57)"
                    strokeWidth="2"
                    strokeDasharray="3 3"
                    opacity="0.5"
                  />
                </g>
              )}

              {/* Multi-User Area & Line */}
              {areaD && <path d={areaD} fill="url(#chartGradient)" />}
              {pathD && <path d={pathD} className="admin-chart-line" strokeWidth="2.5" />}

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
                    {/* Wide hit area */}
                    <rect
                      x={p.x - 30}
                      y={paddingTop}
                      width={60}
                      height={innerHeight + paddingBottom}
                      fill="transparent"
                      style={{ cursor: 'pointer' }}
                    />

                    {/* Guideline on hover */}
                    {isHovered && (
                      <line
                        x1={p.x}
                        y1={paddingTop}
                        x2={p.x}
                        y2={paddingTop + innerHeight}
                        stroke="var(--primary-brand, #102C57)"
                        strokeDasharray="2 2"
                        strokeOpacity="0.5"
                        style={{ pointerEvents: 'none' }}
                      />
                    )}

                    {/* Data Point Dot */}
                    <circle
                      cx={p.x}
                      cy={p.y}
                      r={points.length === 1 ? 7.5 : 5.5}
                      className={`admin-chart-point ${isHovered ? 'active' : ''}`}
                      tabIndex={0}
                      onFocus={() => setHoveredPoint(p)}
                      onBlur={() => setHoveredPoint(null)}
                      style={{ pointerEvents: 'none', fill: 'var(--primary-brand, #102C57)' }}
                    />

                    {/* Data Value Tag */}
                    <text
                      x={p.x}
                      y={p.y - 12}
                      textAnchor="middle"
                      className={`admin-chart-val-label ${isHovered ? 'active' : ''}`}
                      style={{ pointerEvents: 'none', fontWeight: 700, fontSize: '0.85rem' }}
                    >
                      {p.count}
                    </text>

                    {/* Rotated X-axis label */}
                    <g transform={`translate(${p.x}, ${chartHeight - 48})`} style={{ pointerEvents: 'none' }}>
                      <text
                        transform={points.length > 1 ? "rotate(-30)" : "rotate(0)"}
                        textAnchor={points.length > 1 ? "end" : "middle"}
                        className={`admin-chart-label admin-chart-x-label ${isHovered ? 'active' : ''}`}
                        style={{ fontWeight: 600 }}
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
            <strong>{hoveredPoint.fullName}</strong> ({hoveredPoint.role} · {hoveredPoint.department}): <strong>{hoveredPoint.count}</strong> petitions uploaded
          </span>
        ) : chartData.length === 1 ? (
          <span className="caption-active">
            <strong>{chartData[0].fullName}</strong> ({chartData[0].role} · {chartData[0].department}): <strong>{chartData[0].count}</strong> petitions uploaded (100% of district intake)
          </span>
        ) : (
          <span className="caption-idle">Hover on data points to view user intake metrics and account details</span>
        )}
      </div>
    </div>
  );
}
