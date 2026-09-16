import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { LucideIcon, Trash2 } from "lucide-react";
import { ButtonHTMLAttributes } from "react";

export interface DeleteButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: LucideIcon;
  iconPosition?: "left" | "right" | "none";
}

export function DeleteButton({
  children,
  className,
  icon: Icon = Trash2,
  iconPosition = "left",
  ...props
}: DeleteButtonProps) {
  return (
    <Button
      variant="outline"
      className={cn(
        "text-destructive",
        "hover:bg-status-danger hover:text-status-danger-foreground",
        className,
      )}
      {...props}
    >
      {iconPosition !== "right" && Icon && <Icon className="h-4 w-4 mr-2" />}
      {children}
      {iconPosition === "right" && Icon && <Icon className="h-4 w-4 ml-2" />}
    </Button>
  );
}
