import React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider font-medium transition-colors",
  {
    variants: {
      variant: {
        default:
          "border-forest bg-forest text-[#FFFCF6]",
        secondary:
          "border-pale-sage bg-pale-sage text-forest",
        destructive:
          "border-blush-clay bg-blush-clay text-clay",
        outline:
          "border-border bg-transparent text-foreground",
        butter:
          "border-border bg-butter-wash text-foreground",
        teal:
          "border-teal-mist bg-teal-mist text-dusty-teal",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}
