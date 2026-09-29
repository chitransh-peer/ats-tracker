import { useEffect, useState } from "react";

/** `value`, but only once it has stopped changing for `delayMs`. For search
 * boxes that query the server, so each keystroke is not its own request. */
export function useDebouncedValue<T>(value: T, delayMs = 250): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
