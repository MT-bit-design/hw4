/** "smooth" normally, "auto" (instant) for shoppers who turned on reduced motion. */
export function scrollBehavior(): ScrollBehavior {
  return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
}
