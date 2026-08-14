import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-12 w-full rounded-lg border border-line bg-canvas/65 px-4 font-mono text-base text-ink outline-none transition placeholder:text-muted/60 hover:border-muted/60 focus:border-mint focus:ring-1 focus:ring-mint",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";
