"use client";

import Table, { type DataTableGroup } from "./table";

const TABLE_GROUPS: DataTableGroup[] = [
    {
        name: "Studies",
        color: "#dbeafe",
        columns: [
            {
                dataKey: "BibTex Key",
                minWidth: 120,
                initialWidth: 200,
                filterType: "text",
            },
        ],
    },
    {
        name: "Features",
        color: "#FF2222",
        columns: [
            {
                dataKey: "Interactivity",
                filterType: "feature",
            },
            {
                dataKey: "Animation",
                filterType: "feature",
            },
        ],
    },
];

const TABLE_DATA_URL = "/corpus260130_interactivity_animation.json";
const TABLE_TITLE = "Corpus 260130";

export default function TableTestPage() {
    return <Table groups={TABLE_GROUPS} dataUrl={TABLE_DATA_URL} title={TABLE_TITLE} />;
}
