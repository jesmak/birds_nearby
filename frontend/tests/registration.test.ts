import { expect, test, vi } from "vitest";

// Another copy of the card, loaded from some other resource, may be loaded first.
test("a copy of the card loaded earlier stays the card and its editor, and the picker lists it once", async () => {
    class Earlier extends HTMLElement {}
    class EarlierEditor extends HTMLElement {}
    customElements.define("birds-nearby-card", Earlier);
    customElements.define("birds-nearby-card-editor", EarlierEditor);
    const registry = window as unknown as { customCards?: unknown[] };
    registry.customCards = [{ type: "birds-nearby-card" }];
    const info = vi.spyOn(console, "info").mockImplementation(() => undefined);

    await import("../src/birds-nearby-card");

    expect(customElements.get("birds-nearby-card")).toBe(Earlier);
    expect(customElements.get("birds-nearby-card-editor")).toBe(EarlierEditor);
    expect(registry.customCards).toHaveLength(1);
    expect(info).not.toHaveBeenCalled();
});
