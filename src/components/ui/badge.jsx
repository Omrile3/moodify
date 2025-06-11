import * as React from "react"

const badgeVariants = {
  default: "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
  secondary: "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
  outline: "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none text-foreground"
}

function Badge({ className = "", variant = "default", children, ...props }) {
  const classes = `${badgeVariants[variant] || badgeVariants.default} ${className}`;
  
  return (
    <div className={classes} {...props}>
      {children}
    </div>
  )
}

export { Badge }