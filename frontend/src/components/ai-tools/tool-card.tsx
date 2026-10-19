import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import type { Tool } from "@/content/ai-tools/tools";

interface ToolCardProps {
  tool: Tool;
}

/**
 * Directory card for one AI tool. Thin facade over the shared ui/card and
 * ui/badge primitives, linking to the tool's full review page.
 */
export function ToolCard({ tool }: ToolCardProps) {
  const href = `/ai-tools/${tool.category}/${tool.slug}`;

  return (
    <Card className="flex h-full flex-col">
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-xl">
            <Link href={href} className="hover:underline">
              {tool.name}
            </Link>
          </CardTitle>
          {tool.featured ? <Badge>Our pick</Badge> : null}
        </div>
        <CardDescription>{tool.tagline}</CardDescription>
      </CardHeader>
      <CardContent className="flex-1">
        <p className="text-sm font-semibold text-foreground">{tool.pricing}</p>
        <p className="mt-2 text-sm text-muted-foreground">
          <span className="font-medium text-foreground">Best for: </span>
          {tool.bestFor}
        </p>
      </CardContent>
      <CardFooter>
        <Link
          href={href}
          className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
        >
          Read the review <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Link>
      </CardFooter>
    </Card>
  );
}
