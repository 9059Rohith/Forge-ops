import * as React from "react";
import { cn } from "@/lib/utils";

export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "min-h-40 w-full resize-y rounded-lg border border-line bg-canvas/65 px-4 py-3 font-mono text-base leading-7 text-ink outline-none transition placeholder:text-muted/60 hover:border-muted/60 focus:border-mint focus:ring-1 focus:ring-mint",
      className,
    )}
    {...props}
  />
));
Textarea.displayName = "Textarea";
