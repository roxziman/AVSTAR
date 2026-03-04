"use client";

import { ArrowDownIcon, ArrowUpIcon } from "@heroicons/react/16/solid";
import { useCallback, useEffect, useMemo, useState } from "react";

type SortDirection = "asc" | "desc";
type SortRule = { columnId: string; direction: SortDirection };
type FeatureFilter = "all" | "yes" | "low" | "empty";
type CorpusRow = Record<string, string | null>;

type ResizeState = {
  columnId: string;
  startX: number;
  startWidth: number;
};

export type DataTableColumn = {
  dataKey: string;
  minWidth?: number;
  initialWidth?: number;
  filterType: "text" | "feature";
};

export type DataTableGroup = {
  name: string;
  color: string;
  columns: DataTableColumn[];
};

type ResolvedDataTableColumn = DataTableColumn & {
  id: string;
  label: string;
  groupName: string;
  groupColor: string;
  minWidth: number;
  initialWidth: number;
};

type DataTableProps = {
  groups: DataTableGroup[];
  dataUrl: string;
  title: string;
};

function normalizeValue(value: string | null): string {
  return (value ?? "").trim().toLowerCase();
}

function hasYes(value: string | null): boolean {
  return normalizeValue(value) === "yes";
}

function hasLow(value: string | null): boolean {
  return normalizeValue(value) === "low";
}

function matchesFeatureFilter(value: string | null, filter: FeatureFilter): boolean {
  const normalized = normalizeValue(value);
  if (filter === "all") {
    return true;
  }
  if (filter === "empty") {
    return normalized === "";
  }
  return normalized === filter;
}

function toColumnId(dataKey: string): string {
  return dataKey.replace(/\s+/g, "");
}

const DEFAULT_MIN_WIDTH = 42;
const DEFAULT_INITIAL_WIDTH = 52;

export default function Table({ groups, dataUrl, title }: DataTableProps) {
  const normalizedColumns = useMemo(() => {
    const seen = new Set<string>();
    return groups.reduce<ResolvedDataTableColumn[]>((acc, group) => {
      for (const column of group.columns) {
        const id = toColumnId(column.dataKey);
        if (!id || seen.has(id)) {
          continue;
        }
        seen.add(id);
        acc.push({
          ...column,
          id,
          label: column.dataKey,
          groupName: group.name,
          groupColor: group.color,
          minWidth: column.minWidth ?? DEFAULT_MIN_WIDTH,
          initialWidth: column.initialWidth ?? DEFAULT_INITIAL_WIDTH,
        });
      }
      return acc;
    }, []);
  }, [groups]);

  const columnsById = useMemo<Record<string, ResolvedDataTableColumn>>(
    () =>
      normalizedColumns.reduce<Record<string, ResolvedDataTableColumn>>((acc, column) => {
        acc[column.id] = column;
        return acc;
      }, {}),
    [normalizedColumns]
  );

  const guidingColumnId = normalizedColumns[0]?.id ?? "";

  const [rows, setRows] = useState<CorpusRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredColumnId, setHoveredColumnId] = useState<string | null>(null);
  const [hoveredRow, setHoveredRow] = useState<number | null>(null);
  const [sortRules, setSortRules] = useState<SortRule[]>(
    guidingColumnId ? [{ columnId: guidingColumnId, direction: "asc" }] : []
  );
  const [columnOrder, setColumnOrder] = useState<string[]>(normalizedColumns.map((column) => column.id));
  const [draggedColumnId, setDraggedColumnId] = useState<string | null>(null);
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>(() =>
    normalizedColumns.reduce<Record<string, number>>((acc, column) => {
      acc[column.id] = column.initialWidth;
      return acc;
    }, {})
  );
  const [resizeState, setResizeState] = useState<ResizeState | null>(null);
  const [guidingFilter, setGuidingFilter] = useState("");
  const [featureFilters, setFeatureFilters] = useState<Record<string, FeatureFilter>>(() => {
    const initial: Record<string, FeatureFilter> = {};
    for (const column of normalizedColumns) {
      if (column.id !== guidingColumnId && column.filterType === "feature") {
        initial[column.id] = "all";
      }
    }
    return initial;
  });

  const getCellText = useCallback(
    (row: CorpusRow, columnId: string): string => {
      const definition = columnsById[columnId];
      if (!definition) {
        return "";
      }
      return row[definition.dataKey] ?? "";
    },
    [columnsById]
  );

  useEffect(() => {
    setColumnOrder(normalizedColumns.map((column) => column.id));
    setSortRules((prev) => {
      const validColumnIds = new Set(normalizedColumns.map((column) => column.id));
      const next = prev.filter((rule) => validColumnIds.has(rule.columnId));
      if (next.length === 0 && guidingColumnId) {
        return [{ columnId: guidingColumnId, direction: "asc" }];
      }
      return next;
    });
    setColumnWidths((prev) => {
      const next: Record<string, number> = {};
      for (const column of normalizedColumns) {
        next[column.id] = prev[column.id] ?? column.initialWidth;
      }
      return next;
    });
    setFeatureFilters((prev) => {
      const next: Record<string, FeatureFilter> = {};
      for (const column of normalizedColumns) {
        if (column.id !== guidingColumnId && column.filterType === "feature") {
          next[column.id] = prev[column.id] ?? "all";
        }
      }
      return next;
    });
  }, [normalizedColumns, guidingColumnId]);

  useEffect(() => {
    let isActive = true;

    async function loadData() {
      try {
        const res = await fetch(dataUrl, { cache: "no-store" });
        if (!res.ok) {
          throw new Error(`Request failed with status ${res.status}`);
        }
        const data = (await res.json()) as CorpusRow[];
        if (isActive) {
          setRows(Array.isArray(data) ? data : []);
          setError(null);
        }
      } catch (e) {
        if (isActive) {
          const message = e instanceof Error ? e.message : "Unknown error while loading table data.";
          setError(message);
          setRows([]);
        }
      } finally {
        if (isActive) {
          setLoading(false);
        }
      }
    }

    setLoading(true);
    loadData();

    return () => {
      isActive = false;
    };
  }, [dataUrl]);

  useEffect(() => {
    if (!resizeState) {
      return;
    }

    const handleMouseMove = (event: MouseEvent) => {
      const definition = columnsById[resizeState.columnId];
      if (!definition) {
        return;
      }
      const delta = event.clientX - resizeState.startX;
      const nextWidth = Math.max(definition.minWidth, resizeState.startWidth + delta);
      setColumnWidths((prev) => ({
        ...prev,
        [resizeState.columnId]: nextWidth,
      }));
    };

    const handleMouseUp = () => {
      setResizeState(null);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [resizeState, columnsById]);

  const rowCount = useMemo(() => rows.length, [rows]);

  const filteredRows = useMemo(() => {
    const guidingQuery = guidingFilter.trim().toLowerCase();

    return rows.filter((row) => {
      if (guidingColumnId) {
        const guidingValue = getCellText(row, guidingColumnId).toLowerCase();
        if (guidingQuery && !guidingValue.includes(guidingQuery)) {
          return false;
        }
      }

      for (const columnId of columnOrder) {
        const definition = columnsById[columnId];
        if (!definition || columnId === guidingColumnId || definition.filterType !== "feature") {
          continue;
        }
        const filter = featureFilters[columnId] ?? "all";
        if (!matchesFeatureFilter(getCellText(row, columnId), filter)) {
          return false;
        }
      }

      return true;
    });
  }, [rows, guidingFilter, guidingColumnId, columnOrder, columnsById, featureFilters, getCellText]);

  const sortedRows = useMemo(() => {
    if (sortRules.length === 0) {
      return filteredRows;
    }

    const sorted = [...filteredRows].sort((a, b) => {
      for (const rule of sortRules) {
        const aValue = normalizeValue(getCellText(a, rule.columnId));
        const bValue = normalizeValue(getCellText(b, rule.columnId));
        const comparison = aValue.localeCompare(bValue);
        if (comparison !== 0) {
          return rule.direction === "asc" ? comparison : -comparison;
        }
      }
      return 0;
    });

    return sorted;
  }, [filteredRows, sortRules, getCellText]);

  const groupedHeaderSegments = useMemo(() => {
    const segments: { label: string; span: number; color: string }[] = [];
    for (const columnId of columnOrder) {
      const definition = columnsById[columnId];
      if (!definition) {
        continue;
      }
      const last = segments[segments.length - 1];
      if (last && last.label === definition.groupName) {
        last.span += 1;
      } else {
        segments.push({ label: definition.groupName, span: 1, color: definition.groupColor });
      }
    }
    return segments;
  }, [columnOrder, columnsById]);

  const renderLevelBox = (value: string | null, color: string) => {
    if (!hasYes(value) && !hasLow(value)) {
      return null;
    }

    return (
      <div
        className="level-box"
        style={{
          width: 14,
          height: 14,
          borderRadius: 2,
          backgroundColor: color,
          opacity: hasLow(value) ? 0.35 : 1,
          margin: "0 auto",
        }}
      />
    );
  };

  const isRowHighlighted = (row: CorpusRow, rowIndex: number) => {
    if (hoveredRow === rowIndex) {
      return true;
    }

    if (!hoveredColumnId || hoveredColumnId === guidingColumnId) {
      return false;
    }

    const hoveredDefinition = columnsById[hoveredColumnId];
    if (!hoveredDefinition || hoveredDefinition.filterType !== "feature") {
      return false;
    }

    const value = getCellText(row, hoveredColumnId);
    return hasYes(value) || hasLow(value);
  };

  const hasActiveHighlight =
    hoveredRow !== null ||
    (hoveredColumnId !== null &&
      hoveredColumnId !== guidingColumnId &&
      columnsById[hoveredColumnId]?.filterType === "feature");

  const handleSort = (columnId: string, additive: boolean) => {
    setSortRules((prev) => {
      const existingIndex = prev.findIndex((rule) => rule.columnId === columnId);

      if (!additive) {
        if (existingIndex === 0 && prev.length === 1) {
          return [{ columnId, direction: prev[0].direction === "asc" ? "desc" : "asc" }];
        }
        const existingDirection = existingIndex >= 0 ? prev[existingIndex].direction : "asc";
        return [{ columnId, direction: existingDirection === "asc" ? "desc" : "asc" }];
      }

      if (existingIndex < 0) {
        return [...prev, { columnId, direction: "asc" }];
      }

      const existingRule = prev[existingIndex];
      if (existingRule.direction === "asc") {
        const next = [...prev];
        next[existingIndex] = { ...existingRule, direction: "desc" };
        return next;
      }

      const next = prev.filter((rule) => rule.columnId !== columnId);
      if (next.length === 0 && guidingColumnId) {
        return [{ columnId: guidingColumnId, direction: "asc" }];
      }
      return next;
    });
  };

  const moveColumn = (fromId: string, toId: string) => {
    if (fromId === toId) {
      return;
    }

    setColumnOrder((prev) => {
      const next = [...prev];
      const fromIndex = next.indexOf(fromId);
      const toIndex = next.indexOf(toId);
      if (fromIndex < 0 || toIndex < 0) {
        return prev;
      }

      const [moved] = next.splice(fromIndex, 1);
      next.splice(toIndex, 0, moved);
      return next;
    });
  };

  if (normalizedColumns.length === 0) {
    return (
      <div className="page">
        <div className="container">
          <div className="error">No columns configured.</div>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="container">
        <h1 className="title">{title}</h1>
        <p className="subtitle">
          Showing {sortedRows.length} of {rowCount} entries from {dataUrl.replace(/^\//, "")}
        </p>

        {loading && <div className="status">Loading data...</div>}

        {!loading && error && <div className="error">{error}</div>}

        {!loading && !error && (
          <div className="table-wrap">
            <table className="dense-table">
              <colgroup>
                {columnOrder.map((columnId) => (
                  <col key={columnId} style={{ width: `${columnWidths[columnId] ?? 60}px` }} />
                ))}
              </colgroup>
              <thead>
                <tr className="group-row">
                  {groupedHeaderSegments.map((segment, index) => (
                    <th
                      key={`${segment.label}-${segment.span}-${index}`}
                      colSpan={segment.span}
                      className="group-th"
                      style={{ background: segment.color }}
                    >
                      <span className="group-label">{segment.label}</span>
                    </th>
                  ))}
                </tr>
                <tr>
                  {columnOrder.map((columnId) => {
                    const definition = columnsById[columnId];
                    if (!definition) {
                      return null;
                    }

                    return (
                      <th
                        key={columnId}
                        draggable
                        className={`w-full col col-${columnId} ${draggedColumnId === columnId ? "column-dragging" : ""}`}
                        onMouseEnter={() => setHoveredColumnId(columnId)}
                        onMouseLeave={() => setHoveredColumnId(null)}
                        onClick={(event) => handleSort(columnId, event.shiftKey)}
                        onDragStart={(event) => {
                          event.dataTransfer.effectAllowed = "move";
                          setDraggedColumnId(columnId);
                        }}
                        onDragOver={(event) => {
                          event.preventDefault();
                          event.dataTransfer.dropEffect = "move";
                        }}
                        onDrop={() => {
                          if (draggedColumnId) {
                            moveColumn(draggedColumnId, columnId);
                          }
                          setDraggedColumnId(null);
                        }}
                        onDragEnd={() => setDraggedColumnId(null)}
                      >
                        <div
                          className="resize-handle"
                          onMouseDown={(event) => {
                            event.preventDefault();
                            event.stopPropagation();
                            setResizeState({
                              columnId,
                              startX: event.clientX,
                              startWidth: columnWidths[columnId] ?? definition.initialWidth,
                            });
                          }}
                        />
                        <div className="flex flex-col gap-2 justify-center items-center p-2">
                          {(() => {
                            const sortIndex = sortRules.findIndex((rule) => rule.columnId === columnId);
                            if (sortIndex < 0) {
                              return null;
                            }
                            const direction = sortRules[sortIndex].direction;
                            return (
                              <span className="sort-indicator">
                                {direction === "asc" ? (
                                  <ArrowUpIcon className="size-3" />
                                ) : (
                                  <ArrowDownIcon className="size-3" />
                                )}
                                <span className="sort-rank">{sortIndex + 1}</span>
                              </span>
                            );
                          })()}
                          <span className="vertical-label">{definition.label}</span>
                        </div>
                      </th>
                    );
                  })}
                </tr>
                <tr className="filter-row">
                  {columnOrder.map((columnId) => {
                    const definition = columnsById[columnId];
                    if (!definition) {
                      return null;
                    }

                    const isGuidingColumn = columnId === guidingColumnId;

                    return (
                      <th key={`filter-${columnId}`} className={`col col-${columnId}`}>
                        {isGuidingColumn ? (
                          <input
                            className="filter-input"
                            type="text"
                            value={guidingFilter}
                            onChange={(event) => setGuidingFilter(event.target.value)}
                            onClick={(event) => event.stopPropagation()}
                            placeholder="Filter"
                          />
                        ) : definition.filterType === "feature" ? (
                          <select
                            className="filter-select"
                            value={featureFilters[columnId] ?? "all"}
                            onChange={(event) =>
                              setFeatureFilters((prev) => ({
                                ...prev,
                                [columnId]: event.target.value as FeatureFilter,
                              }))
                            }
                            onClick={(event) => event.stopPropagation()}
                          >
                            <option value="all">All</option>
                            <option value="yes">Yes</option>
                            <option value="low">Low</option>
                            <option value="empty">Empty</option>
                          </select>
                        ) : null}
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody className={hasActiveHighlight ? "highlight-mode" : ""}>
                {sortedRows.map((row, index) => (
                  <tr
                    key={`${getCellText(row, guidingColumnId) || "row"}-${index}`}
                    className={isRowHighlighted(row, index) ? "row-highlighted" : ""}
                    onMouseEnter={() => setHoveredRow(index)}
                    onMouseLeave={() => setHoveredRow(null)}
                  >
                    {columnOrder.map((columnId) => {
                      const definition = columnsById[columnId];
                      if (!definition) {
                        return null;
                      }
                      const value = getCellText(row, columnId);

                      return (
                        <td key={`${columnId}-${index}`} className={`col col-${columnId}`}>
                          {columnId === guidingColumnId
                            ? value
                            : definition.filterType === "feature"
                              ? renderLevelBox(value, definition.groupColor)
                              : value}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <style jsx>{`
        .page {
          min-height: 100vh;
          padding: 24px;
          background: #f5f7fa;
        }
        .container {
          max-width: 320px;
          margin: 0 auto;
        }
        .title {
          margin: 0 0 4px;
          font-size: 1.8rem;
          line-height: 1.2;
          font-weight: 700;
          color: #111827;
        }
        .subtitle {
          margin: 0 0 12px;
          color: #4b5563;
          font-size: 0.95rem;
        }
        .status {
          padding: 16px;
          text-align: center;
          color: #334155;
          background: #fff;
          border: 1px solid #e2e8f0;
        }
        .error {
          padding: 10px 12px;
          color: #991b1b;
          background: #fee2e2;
          border: 1px solid #fecaca;
          border-radius: 6px;
        }
        .table-wrap {
          background: #fff;
          overflow: hidden;
        }
        .dense-table {
          width: 100%;
          border-collapse: collapse;
          table-layout: fixed;
        }
        .group-row .group-th {
          height: 24px;
          padding: 2px 4px;
          vertical-align: middle;
          text-align: center;
          background: #eef2ff;
          cursor: default;
        }
        .group-label {
          font-size: 0.72rem;
          font-weight: 700;
          letter-spacing: 0.02em;
          text-transform: uppercase;
          color: #334155;
        }
        .dense-table th {
          padding: 2px;
          vertical-align: bottom;
          text-align: center;
          background: #f8fafc;
          cursor: grab;
          user-select: none;
          position: relative;
        }
        .filter-row th {
          height: auto;
          padding: 4px;
          background: #f9fafb;
          cursor: default;
        }
        .dense-table td {
          height: 20px;
          padding: 1px 4px;
          font-size: 0.8rem;
          line-height: 1.1;
        }
        .col {
          max-width: 350px;
          min-width: 30px;
          text-align: left;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .dense-table tbody tr:last-child td {
          border-bottom: none;
        }
        .vertical-label {
          display: inline-block;
          writing-mode: vertical-rl;
          transform: rotate(180deg);
          white-space: nowrap;
          font-weight: 700;
          line-height: 1.1;
        }
        .sort-indicator {
          display: flex;
          align-items: center;
          gap: 2px;
        }
        .sort-rank {
          font-size: 0.65rem;
          font-weight: 700;
          line-height: 1;
        }
        .highlight-mode tr:not(.row-highlighted) td {
          opacity: 0.4;
        }
        .column-dragging {
          opacity: 0.6;
        }
        .filter-input,
        .filter-select {
          width: 100%;
          height: 22px;
          border: 1px solid #cbd5e1;
          background: #ffffff;
          border-radius: 3px;
          font-size: 0.72rem;
          color: #1f2937;
          padding: 0 6px;
        }
        .filter-input:focus,
        .filter-select:focus {
          outline: 1px solid #3b82f6;
          border-color: #3b82f6;
        }
        .resize-handle {
          position: absolute;
          top: 0;
          right: -4px;
          width: 8px;
          height: 100%;
          cursor: col-resize;
          z-index: 2;
        }
        .resize-handle:hover {
          background: rgba(37, 99, 235, 0.2);
        }
      `}</style>
    </div>
  );
}
