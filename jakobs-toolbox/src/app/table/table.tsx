"use client";

import { ArrowDownIcon, ArrowUpIcon } from "@heroicons/react/16/solid";
import { useEffect, useMemo, useState } from "react";

type CorpusRow = {
    "BibTex Key": string | null;
    Interactivity: string | null;
    Animation: string | null;
};

type SortColumn = "bibtexKey" | "interactivity" | "animation";
type SortDirection = "asc" | "desc";
type ColumnId = SortColumn;
type ColumnWidths = Record<ColumnId, number>;
type FeatureFilter = "all" | "yes" | "low" | "empty";
type ResizeState = {
    column: ColumnId;
    startX: number;
    startWidth: number;
};

const MIN_COLUMN_WIDTH: Record<ColumnId, number> = {
    bibtexKey: 120,
    interactivity: 42,
    animation: 42,
};

function hasYes(value: string | null): boolean {
    return typeof value === "string" && value.trim().toLowerCase() === "yes";
}

function hasLow(value: string | null): boolean {
    return typeof value === "string" && value.trim().toLowerCase() === "low";
}
function matchesFeatureFilter(value: string | null, filter: FeatureFilter): boolean {
    const normalized = (value ?? "").trim().toLowerCase();
    if (filter === "all") {
        return true;
    }
    if (filter === "empty") {
        return normalized === "";
    }
    return normalized === filter;
}

function getCellText(row: CorpusRow, column: ColumnId): string {
    if (column === "bibtexKey") {
        return row["BibTex Key"] ?? "";
    }
    if (column === "interactivity") {
        return row.Interactivity ?? "";
    }
    return row.Animation ?? "";
}

function getColumnLabel(column: ColumnId): string {
    if (column === "bibtexKey") {
        return "BibTex Key";
    }
    if (column === "interactivity") {
        return "Interactivity";
    }
    return "Animation";
}
function getColumnGroup(column: ColumnId): "Studies" | "Features" {
    if (column === "bibtexKey") {
        return "Studies";
    }
    return "Features";
}

export default function Table() {
    const [rows, setRows] = useState<CorpusRow[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [hoveredColumn, setHoveredColumn] = useState<ColumnId | null>(null);
    const [sortColumn, setSortColumn] = useState<SortColumn>("bibtexKey");
    const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
    const [columnOrder, setColumnOrder] = useState<ColumnId[]>([
        "bibtexKey",
        "interactivity",
        "animation",
    ]);
    const [draggedColumn, setDraggedColumn] = useState<ColumnId | null>(null);
    const [columnWidths, setColumnWidths] = useState<ColumnWidths>({
        bibtexKey: 200,
        interactivity: 52,
        animation: 52,
    });
    const [resizeState, setResizeState] = useState<ResizeState | null>(null);
    const [filters, setFilters] = useState<{
        bibtexKey: string;
        interactivity: FeatureFilter;
        animation: FeatureFilter;
    }>({
        bibtexKey: "",
        interactivity: "all",
        animation: "all",
    });
    const [hoveredRow, setHoveredRow] = useState<number | null>(null);

    useEffect(() => {
        let isActive = true;

        async function loadData() {
            try {
                const res = await fetch("/corpus260130_interactivity_animation.json", { cache: "no-store" });
                if (!res.ok) {
                    throw new Error(`Request failed with status ${res.status}`);
                }
                const data = (await res.json()) as CorpusRow[];
                if (isActive) {
                    setRows(Array.isArray(data) ? data : []);
                }
            } catch (e) {
                if (isActive) {
                    const message =
                        e instanceof Error ? e.message : "Unknown error while loading table data.";
                    setError(message);
                }
            } finally {
                if (isActive) {
                    setLoading(false);
                }
            }
        }

        loadData();
        return () => {
            isActive = false;
        };
    }, []);

    useEffect(() => {
        if (!resizeState) {
            return;
        }

        const handleMouseMove = (event: MouseEvent) => {
            const delta = event.clientX - resizeState.startX;
            const nextWidth = Math.max(
                MIN_COLUMN_WIDTH[resizeState.column],
                resizeState.startWidth + delta
            );
            setColumnWidths((prev) => ({
                ...prev,
                [resizeState.column]: nextWidth,
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
    }, [resizeState]);

    const rowCount = useMemo(() => rows.length, [rows]);
    const filteredRows = useMemo(() => {
        const bibQuery = filters.bibtexKey.trim().toLowerCase();
        return rows.filter((row) => {
            const bibtexValue = (row["BibTex Key"] ?? "").toLowerCase();
            if (bibQuery && !bibtexValue.includes(bibQuery)) {
                return false;
            }
            if (!matchesFeatureFilter(row.Interactivity, filters.interactivity)) {
                return false;
            }
            if (!matchesFeatureFilter(row.Animation, filters.animation)) {
                return false;
            }
            return true;
        });
    }, [rows, filters]);

    const sortedRows = useMemo(() => {
        const toSortable = (value: string) => value.trim().toLowerCase();
        const sorted = [...filteredRows].sort((a, b) => {
            const aValue = toSortable(getCellText(a, sortColumn));
            const bValue = toSortable(getCellText(b, sortColumn));
            return aValue.localeCompare(bValue);
        });

        if (sortDirection === "desc") {
            sorted.reverse();
        }
        return sorted;
    }, [filteredRows, sortColumn, sortDirection]);
    const groupedHeaderSegments = useMemo(() => {
        const segments: { label: string; span: number }[] = [];
        for (const column of columnOrder) {
            const label = getColumnGroup(column);
            const last = segments[segments.length - 1];
            if (last && last.label === label) {
                last.span += 1;
            } else {
                segments.push({ label, span: 1 });
            }
        }
        return segments;
    }, [columnOrder]);

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

        if (hoveredColumn === "interactivity") {
            return hasYes(row.Interactivity) || hasLow(row.Interactivity);
        }

        if (hoveredColumn === "animation") {
            return hasYes(row.Animation) || hasLow(row.Animation);
        }

        return false;
    };
    const hasActiveHighlight =
        hoveredRow !== null || hoveredColumn === "interactivity" || hoveredColumn === "animation";

    const handleSort = (column: SortColumn) => {
        if (sortColumn === column) {
            setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
            return;
        }
        setSortColumn(column);
        setSortDirection("asc");
    };

    const moveColumn = (from: ColumnId, to: ColumnId) => {
        if (from === to) {
            return;
        }

        setColumnOrder((prev) => {
            const next = [...prev];
            const fromIndex = next.indexOf(from);
            const toIndex = next.indexOf(to);
            if (fromIndex < 0 || toIndex < 0) {
                return prev;
            }

            const [moved] = next.splice(fromIndex, 1);
            next.splice(toIndex, 0, moved);
            return next;
        });
    };

    return (
        <div className="page">
            <div className="container">
                <h1 className="title">Corpus 260130</h1>
                <p className="subtitle">
                    Showing {sortedRows.length} of {rowCount} entries from corpus260130_interactivity_animation.json
                </p>

                {loading && <div className="status">Loading data...</div>}

                {!loading && error && <div className="error">{error}</div>}

                {!loading && !error && (
                    <div className="table-wrap">
                        <table className="dense-table">
                            <colgroup>
                                {columnOrder.map((column) => (
                                    <col key={column} style={{ width: `${columnWidths[column]}px` }} />
                                ))}
                            </colgroup>
                            <thead>
                                <tr className="group-row">
                                    {groupedHeaderSegments.map((segment, index) => (
                                        <th
                                            key={`${segment.label}-${segment.span}-${index}`}
                                            colSpan={segment.span}
                                            className="group-th"
                                        >
                                            <span className="group-label">{segment.label}</span>
                                        </th>
                                    ))}
                                </tr>
                                <tr>
                                    {columnOrder.map((column) => (
                                        <th
                                            key={column}
                                            draggable
                                            className={`w-full col col-${column} ${draggedColumn === column ? "column-dragging" : ""
                                                }`}
                                            onMouseEnter={() => setHoveredColumn(column)}
                                            onMouseLeave={() => setHoveredColumn(null)}
                                            onClick={() => handleSort(column)}
                                            onDragStart={(event) => {
                                                event.dataTransfer.effectAllowed = "move";
                                                setDraggedColumn(column);
                                            }}
                                            onDragOver={(event) => {
                                                event.preventDefault();
                                                event.dataTransfer.dropEffect = "move";
                                            }}
                                            onDrop={() => {
                                                if (draggedColumn) {
                                                    moveColumn(draggedColumn, column);
                                                }
                                                setDraggedColumn(null);
                                            }}
                                            onDragEnd={() => setDraggedColumn(null)}
                                        >
                                            <div
                                                className="resize-handle"
                                                onMouseDown={(event) => {
                                                    event.preventDefault();
                                                    event.stopPropagation();
                                                    setResizeState({
                                                        column,
                                                        startX: event.clientX,
                                                        startWidth: columnWidths[column],
                                                    });
                                                }}
                                            />
                                            <div className="flex flex-col gap-2 justify-center items-center p-2">
                                                {sortColumn === column && (sortDirection === "asc" ? <ArrowUpIcon className="size-3" /> : <ArrowDownIcon className="size-3" />)}
                                                <span className="vertical-label">{getColumnLabel(column)}</span>
                                            </div>
                                        </th>
                                    ))}
                                </tr>
                                <tr className="filter-row">
                                    {columnOrder.map((column) => (
                                        <th key={`filter-${column}`} className={`col col-${column}`}>
                                            {column === "bibtexKey" ? (
                                                <input
                                                    className="filter-input"
                                                    type="text"
                                                    value={filters.bibtexKey}
                                                    onChange={(event) =>
                                                        setFilters((prev) => ({
                                                            ...prev,
                                                            bibtexKey: event.target.value,
                                                        }))
                                                    }
                                                    onClick={(event) => event.stopPropagation()}
                                                    placeholder="Filter"
                                                />
                                            ) : (
                                                <select
                                                    className="filter-select"
                                                    value={filters[column]}
                                                    onChange={(event) =>
                                                        setFilters((prev) => ({
                                                            ...prev,
                                                            [column]: event.target.value as FeatureFilter,
                                                        }))
                                                    }
                                                    onClick={(event) => event.stopPropagation()}
                                                >
                                                    <option value="all">All</option>
                                                    <option value="yes">Yes</option>
                                                    <option value="low">Low</option>
                                                    <option value="empty">Empty</option>
                                                </select>
                                            )}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className={hasActiveHighlight ? "highlight-mode" : ""}>
                                {sortedRows.map((row, index) => (
                                    <tr
                                        key={`${row["BibTex Key"] ?? "row"}-${index}`}
                                        className={`${hoveredRow === index ? "row-highlighted-mouse" : ""} ${isRowHighlighted(row, index) ? "row-highlighted" : ""}`}
                                        onMouseEnter={() => setHoveredRow(index)}
                                        onMouseLeave={() => setHoveredRow(null)}
                                    >
                                        {columnOrder.map((column) => (
                                            <td
                                                key={`${column}-${index}`}
                                                className={`col col-${column}`}
                                            >
                                                {column === "bibtexKey"
                                                    ? getCellText(row, column)
                                                    : column === "interactivity"
                                                        ? renderLevelBox(row.Interactivity, "#1976d2")
                                                        : renderLevelBox(row.Animation, "#2e7d32")}
                                            </td>
                                        ))}
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
                .row-highlighted-mouse {
                    background: rgba(25, 118, 210, 0.14);
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
