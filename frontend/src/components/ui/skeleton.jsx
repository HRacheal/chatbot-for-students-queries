import { cn } from "@/lib/utils"
import PropTypes from "prop-types"

function Skeleton({
  className,
  ...props
}) {
  return (
    (<div
      className={cn("animate-pulse rounded-md bg-gray-800", className)}
      {...props} />)
  );
}

Skeleton.propTypes = {
  className: PropTypes.string,
}

export { Skeleton }
