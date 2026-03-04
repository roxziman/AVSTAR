"use client";

import Table, { type DataTableColumn } from "./table";

const TABLE_COLUMNS: DataTableColumn[] = [
    {
        id: "bibtexKey",
        label: "BibTex Key",
        group: "Studies",
        dataKey: "BibTex Key",
        minWidth: 120,
        initialWidth: 200,
        filterType: "text",
    },
    {
        id: "interactivity",
        label: "Interactivity",
        group: "Features",
        dataKey: "Interactivity",
        minWidth: 42,
        initialWidth: 52,
        filterType: "feature",
        color: "#1976d2",
    },
    {
        id: "animation",
        label: "Animation",
        group: "Features",
        dataKey: "Animation",
        minWidth: 42,
        initialWidth: 52,
        filterType: "feature",
        color: "#2e7d32",
    },
];

const TABLE_DATA_URL = "/corpus260130_interactivity_animation.json";
const TABLE_TITLE = "Corpus 260130";

export default function TableTestPage() {
    return <Table columns={TABLE_COLUMNS} dataUrl={TABLE_DATA_URL} title={TABLE_TITLE} />;
}
