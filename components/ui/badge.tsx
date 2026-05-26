import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-terminal-blue focus:ring-offset-2 focus:ring-offset-terminal-bg",
  {
    variants: {
      variant: {
        default:
          "border-terminal-border bg-terminal-card text-white hover:border-terminal-blue/60",
        secondary:
          "border-terminal-border bg-terminal-bg text-zinc-300 hover:border-terminal-green/60",
        positive:
          "border-terminal-green/30 bg-terminal-green/10 text-terminal-green",
        negative: "border-terminal-red/30 bg-terminal-red/10 text-terminal-red",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
