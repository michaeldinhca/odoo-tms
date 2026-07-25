/** Joins conditional class names, skipping falsy values. No dependency —
 * this is the only "utility" this project pulls in for styling. */
export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}
