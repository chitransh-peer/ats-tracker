"use client";

import { useEffect } from "react";

const EVENT = "quick-create";

/**
 * Opens a page's "new" dialog when Quick Create sends the user there with
 * `?new=1`, or asks again while they are already on the page.
 */
export function useQuickCreate(open: () => void) {
  useEffect(() => {
    const url = new URL(window.location.href);
    if (url.searchParams.has("new")) {
      url.searchParams.delete("new");
      window.history.replaceState(null, "", url.toString());
      open();
    }
    window.addEventListener(EVENT, open);
    return () => window.removeEventListener(EVENT, open);
  }, [open]);
}

/** Tells the page already on screen to open its "new" dialog. */
export function requestQuickCreate() {
  window.dispatchEvent(new Event(EVENT));
}
