import { defineConfig } from "vitest/config";

export default defineConfig({
    // The build replaces this with the integration's version from manifest.json; the tests don't care which.
    define: { __CARD_VERSION__: '"0.0.0-test"' },
    // The card is a custom element, so the tests need a DOM to render into. UTC, as in CI, so that a test leaning on the
    // machine's own zone, Finnish on a Finnish desktop, fails here too. In processes, not threads: a worker thread keeps
    // the machine's zone whatever TZ says, and a test can then set a zone of its own.
    test: { environment: "happy-dom", env: { TZ: "UTC" }, pool: "forks" },
});
