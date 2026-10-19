import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  TableCaption,
} from "@/components/ui/table";

interface BlogTableProps {
  headers: string[];
  rows: string[][];
  caption?: string;
}

/**
 * Reusable styled table for blog posts (and anywhere on the marketing site).
 * Thin MDX-friendly facade over the shared ui/table primitives.
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
    <div className="not-prose my-8 overflow-hidden rounded-xl border border-border">
      <Table className="table-auto">
        {caption ? <TableCaption>{caption}</TableCaption> : null}
        <TableHeader>
          <TableRow className="bg-muted/60 hover:bg-muted/60">
            {headers.map((h, i) => (
              <TableHead key={i} className="font-semibold text-foreground">
                {h}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row, i) => (
            <TableRow
              key={i}
              className={i % 2 === 1 ? "bg-muted/25" : undefined}
            >
              {row.map((cell, j) => (
                <TableCell
                  key={j}
                  className="whitespace-normal align-top text-muted-foreground"
                >
                  {cell}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
