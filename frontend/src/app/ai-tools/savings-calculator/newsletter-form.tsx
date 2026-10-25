"use client";

import { useEffect, useRef } from "react";

const FORM_ID = "76696728-99f0-49cf-9472-faba9d9e13ff";

/**
 * Beehiiv subscribe form, loaded after mount.
 *
 * The embed script must be injected on the client: a script tag rendered
 * into server HTML gets its loader-inserted form wiped when React hydrates
 * the page, which is why the form rendered as an empty box. Injecting the
 * script in useEffect runs the loader after hydration, so the form stays.
 */
export function NewsletterForm() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || container.querySelector("script")) return;
    const script = document.createElement("script");
    script.async = true;
    script.src = "https://subscribe-forms.beehiiv.com/v3/loader.js";
    script.setAttribute("data-beehiiv-form", FORM_ID);
    container.appendChild(script);
    return () => {
      container.innerHTML = "";
    };
  }, []);

  return <div ref={containerRef} />;
}
