interface BlogTableProps {
  headers: string[];
  rows: string[][];
  caption?: string;
}

/**
 * Reusable styled table for blog posts (and anywhere on the marketing site).
 * Markdown tables are NOT supported by the MDX setup, so use this component
 * for all tabular data in posts.
 *
 * Usage in MDX:
 *   import { BlogTable } from "@/components/blog/blog-table";
 *   <BlogTable
 *     headers={["Feature", "Option A", "Option B"]}
 *     rows={[
 *       ["Cost", "$100/mo", "$50/mo"],
 *       ["Support", "Email", "24/7 phone"],
 *     ]}
 *   />
 */
export function BlogTable({ headers, rows, caption }: BlogTableProps) {
  return (
    <div className="not-prose my-8 overflow-x-auto rounded-xl border border-border">
      <table className="w-full border-collapse text-left text-sm">
        {caption ? (
          <caption className="px-4 py-3 text-left font-medium text-muted-foreground">
            {caption}
          </caption>
        ) : null}
        <thead>
          <tr className="bg-muted/60">
            {headers.map((h, i) => (
              <th
                key={i}
                className="border-b border-border px-4 py-3 font-semibold text-foreground"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              className={i % 2 === 1 ? "bg-muted/25" : "bg-transparent"}
            >
              {row.map((cell, j) => (
                <td
                  key={j}
                  className="border-b border-border/50 px-4 py-3 align-top text-muted-foreground last:border-b-0"
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
