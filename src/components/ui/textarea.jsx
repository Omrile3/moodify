import * as React from "react"

const Textarea = React.forwardRef(({ className = "", ...props }, ref) => {
  const classes = `flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50 ${className}`;
  
  return (
    <textarea
      className={classes}
      ref={ref}
      {...props}
    />
  )
})
Textarea.displayName = "Textarea"

export { Textarea }