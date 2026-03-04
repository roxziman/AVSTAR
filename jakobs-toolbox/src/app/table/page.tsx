"use client";

import Table, { type DataTableGroup } from "./table";

const TABLE_GROUPS: DataTableGroup[] = [
    {
        name: "Publications",
        color: "#8da0cb",
        columns: [
            {
                dataKey: "AuthorYear",
                minWidth: 120,
                initialWidth: 200,
                filterType: "text",
            },
        ],
    },
    {
        name: "Domain Application",
        color: "#fc8d62",
        columns: [
            {
                dataKey: "Agnostic",
                filterType: "feature",
            },
            {
                dataKey: "Medicine",
                filterType: "feature",
            },
            {
                dataKey: "Public Health",
                filterType: "feature",
            },
            {
                dataKey: "Social/Civic",
                filterType: "feature",
            },
            {
                dataKey: "Business/Industry",
                filterType: "feature",
            },
            {
                dataKey: "Climate",
                filterType: "feature",
            },
            {
                dataKey: "Science Education",
                filterType: "feature",
            },
            {
                dataKey: "Journalism",
                filterType: "feature",
            },
            {
                dataKey: "Culture/Humanities",
                filterType: "feature",
            },
            {
                dataKey: "Various",
                filterType: "feature",
            },
        ],
    },
    {
        name: "Features",
        color: "#66c2a5",
        columns: [
            {
                dataKey: "chart",
                filterType: "feature",
            },
            {
                dataKey: "graph",
                filterType: "feature",
            },
            {
                dataKey: "Tree",
                filterType: "feature",
            },
            {
                dataKey: "Set",
                filterType: "feature",
            },
            {
                dataKey: "Map",
                filterType: "feature",
            },
            {
                dataKey: "Pictograph",
                filterType: "feature",
            },
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

const TABLE_DATA_URL = "/classtable.json";
const TABLE_TITLE = "AV STAR Classification";

export default function TableTestPage() {
    return <Table groups={TABLE_GROUPS} dataUrl={TABLE_DATA_URL} title={TABLE_TITLE} />;
}
