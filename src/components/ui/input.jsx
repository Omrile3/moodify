import * as React from "react"

const Input = React.forwardRef(({ className = "", type = "text", ...props }, ref) => {
  const classes = `flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50 ${className}`;
  
  return (
    <input
      type={type}
      className={classes}
      ref={ref}
      {...props}
    />
  )
})
Input.displayName = "Input"

export { Input }