import { afterEach, describe, expect, it, vi } from "vitest";

import { sideFits, tabsFit } from "../src/birds-nearby-card";
import type { BirdsNearbyCard } from "../src/birds-nearby-card";
import { BirdsNearbyCardEditor } from "../src/editor";
import type { BirdsNearbyCardConfig } from "../src/types";
import { AREA, hass } from "./fixtures";

async function card(config: Partial<BirdsNearbyCardConfig> = {}, layout?: string): Promise<BirdsNearbyCard> {
    const element = document.createElement("birds-nearby-card");
    element.setConfig({ type: "custom:birds-nearby-card", device: AREA, ...config } as BirdsNearbyCardConfig);
    element.hass = hass();
    element.layout = layout;
    document.body.append(element);
    await element.updateComplete;
    return element;
}

function one(element: BirdsNearbyCard, selector: string): HTMLElement {
    return element.shadowRoot!.querySelector<HTMLElement>(selector)!;
}

function all(element: BirdsNearbyCard, selector: string): HTMLElement[] {
    return [...element.shadowRoot!.querySelectorAll<HTMLElement>(selector)];
}

/**
 * Gives the card the width it has in layout, which a scale leaves alone while its box shrinks with the scale. happy-dom
 * computes no width, so the card's computed style gets one, with its own padding and border kept.
 */
function layoutWidth(haCard: Element, value: number): void {
    const original = window.getComputedStyle.bind(window);
    vi.spyOn(window, "getComputedStyle").mockImplementation((target, pseudo) => {
        const style = original(target, pseudo);
        if (target !== haCard) return style;
        return {
            width: `${value}px`,
            paddingBottom: style.paddingBottom,
            borderBottomWidth: style.borderBottomWidth,
            height: style.height,
        } as CSSStyleDeclaration;
    });
}

/** Gives a part its drawn width, in whole pixels as clientWidth and in fractions as its box. */
function width(target: Element, value: number): void {
    Object.defineProperty(target, "clientWidth", { value: Math.round(value), configurable: true });
    target.getBoundingClientRect = () => ({ top: 0, bottom: 0, height: 0, width: value }) as DOMRect;
}

// happy-dom lays nothing out, so each part is given the box it would have, measured from the card's top.
function box(target: Element, top: number, bottom: number, drawnWidth = 300): void {
    target.getBoundingClientRect = () => ({ top, bottom, height: bottom - top, width: drawnWidth }) as DOMRect;
}

/** Gives every text measured the width `widths` has for it, as a range over it would measure its glyphs. */
function textWidths(widths: (element: Element) => number): void {
    vi.spyOn(document, "createRange").mockImplementation(() => {
        let measured: Element | undefined;
        return {
            selectNodeContents: (node: Element) => (measured = node),
            getBoundingClientRect: () => ({ width: measured ? widths(measured) : 0 }) as DOMRect,
        } as unknown as Range;
    });
}

/** Runs the card's next measuring frame now. */
async function measure(element: BirdsNearbyCard): Promise<void> {
    const frames: FrameRequestCallback[] = [];
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => frames.push(callback));
    (element as unknown as { measureSoon(): void }).measureSoon();
    frames.at(-1)?.(0);
    vi.restoreAllMocks();
    await element.updateComplete;
}

afterEach(() => {
    vi.restoreAllMocks();
    document.body.replaceChildren();
});

describe("the card's size in a sections view", () => {
    it("takes a whole section by default, never less than 9 columns, and at least four rows", async () => {
        expect((await card()).getGridOptions()).toEqual({ columns: 12, min_columns: 9, rows: "auto", min_rows: 4 });
    });

    it("refuses a rounding other than whole or half rows", () => {
        const element = document.createElement("birds-nearby-card");
        expect(() => element.setConfig({ type: "custom:birds-nearby-card", device: AREA, row_step: "third" } as never)).toThrow(
            "row_step must be full or half",
        );
    });
});

describe("whether the tabs fit side by side", () => {
    // The tabs are the card's width less its border, 1 px each side. Less 48 px of padding and gaps they make three
    // thirds, each with 8 px of its own padding: 46.67 px of room on a 214 px card, 71.33 on 288, 136.33 on 483.
    it.each([
        ["a phone's whole section (288 px), the widest just fitting", 286, [71.33, 40, 50], true],
        ["a phone's whole section, a tenth of a pixel over", 286, [71.44, 40, 50], false],
        ["a phone's whole section, over by less than the slack", 286, [71.34, 40, 50], true],
        ["the narrowest card (214 px), short counts and labels", 212, [40, 30, 46.6], true],
        ["the narrowest card, a label of 47 px", 212, [40, 30, 47], false],
        ["a full section in my HA (483 px)", 481, [90, 70, 136], true],
    ])("%s", (_name, tabsWidth, needs, fits) => {
        expect(tabsFit(tabsWidth, needs)).toBe(fits);
    });
});

describe("whether a sighting's count and time fit beside its texts", () => {
    // 32 px of padding, the 48 px picture and 12 px on either side of the texts.
    it.each([
        ["exactly", 288, 120, 64, true],
        ["a fraction of a pixel short", 288.4, 120.4, 64, true],
        ["two hundredths over", 288, 120.02, 64, false],
        ["over by less than the slack", 288, 120.005, 64, true],
        ["a pixel over", 288, 121, 64, false],
        ["a long name on a full section", 483, 300, 70, true],
    ])("%s", (_name, rowWidth, texts, side, fits) => {
        expect(sideFits(rowWidth, texts, side)).toBe(fits);
    });
});

describe("the card's splits, as measured", () => {
    it("puts the tabs one to a row when a label doesn't fit its third, and back when it does", async () => {
        const element = await card();
        width(one(element, "ha-card"), 214);
        width(one(element, ".tabs"), 214);
        textWidths((text) => (text.classList.contains("label") ? 80 : 20));
        await measure(element);
        expect(one(element, ".tabs").classList.contains("split")).toBe(true);

        width(one(element, ".tabs"), 483);
        textWidths((text) => (text.classList.contains("label") ? 80 : 20));
        await measure(element);
        expect(one(element, ".tabs").classList.contains("split")).toBe(false);
    });

    it("puts a sighting's count and time under its texts only when they don't fit beside them", async () => {
        const element = await card();
        // The recent species, of which the fixtures have more than one.
        all(element, ".tab")[1].click();
        await element.updateComplete;
        width(one(element, "ha-card"), 288);
        width(one(element, ".tabs"), 483);
        const [first, second] = all(element, "button.row");
        width(first, 288);
        width(second, 288);
        // The first row's longest text, its name, is too long to have its count beside it, the second's isn't.
        textWidths((text) => {
            const row = text.closest("button.row");
            if (text.classList.contains("name")) {
                return row === first ? 150 : 100;
            }
            return 40;
        });
        await measure(element);
        const [firstAfter, secondAfter] = all(element, "button.row");
        expect(firstAfter.classList.contains("split")).toBe(true);
        expect(secondAfter.classList.contains("split")).toBe(false);
    });

    it("lays the texts out on one line while measuring, and holds each row to its height meanwhile", async () => {
        const element = await card();
        width(one(element, "ha-card"), 288);
        const row = all(element, "button.row")[0];
        const seen: { measuring: boolean; height: string }[] = [];
        textWidths((text) => {
            if (text.classList.contains("name")) {
                seen.push({ measuring: one(element, "ha-card").classList.contains("measuring"), height: row.style.height });
            }
            return 10;
        });
        vi.spyOn(window, "getComputedStyle").mockImplementation(() => ({ height: "64px" }) as CSSStyleDeclaration);
        const frames: FrameRequestCallback[] = [];
        vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => frames.push(callback));
        (element as unknown as { measureSoon(): void }).measureSoon();
        frames.at(-1)?.(0);
        expect(seen[0]).toEqual({ measuring: true, height: "64px" });
        expect(one(element, "ha-card").classList.contains("measuring")).toBe(false);
        expect(row.style.height).toBe("");
    });
});

describe("the splits as the card comes and goes", () => {
    it("keeps a row's split on another tab, until that tab is drawn and measured again", async () => {
        const element = await card();
        all(element, ".tab")[1].click();
        await element.updateComplete;
        width(one(element, "ha-card"), 288);
        width(one(element, ".tabs"), 481);
        all(element, "button.row").forEach((row) => width(row, 288));
        textWidths((text) => (text.classList.contains("name") ? 200 : 40));
        await measure(element);
        const recentKeys = all(element, "button.row.split").map((row) => row.dataset.key);
        expect(recentKeys.length).toBeGreaterThan(0);

        // On the notable tab, none of the recent rows is drawn, so their splits stay as they were.
        all(element, ".tab")[0].click();
        await element.updateComplete;
        width(one(element, "ha-card"), 288);
        width(one(element, ".tabs"), 481);
        all(element, "button.row").forEach((row) => width(row, 288));
        textWidths(() => 10);
        await measure(element);
        all(element, ".tab")[1].click();
        await element.updateComplete;
        expect(all(element, "button.row.split").map((row) => row.dataset.key)).toEqual(recentKeys);
    });

    it("is measured again when it comes back on the page, as it was let go when it left", async () => {
        const element = await card();
        const frames: FrameRequestCallback[] = [];
        element.remove();
        vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => frames.push(callback));
        document.body.append(element);
        await element.updateComplete;
        expect(frames.length).toBeGreaterThan(0);
    });

    it("isn't measured while it is off the page", async () => {
        const element = await card();
        element.remove();
        const frames: FrameRequestCallback[] = [];
        vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => frames.push(callback));
        element.requestUpdate();
        await element.updateComplete;
        expect(frames).toEqual([]);
    });
});

describe("filling the rows on automatic rows", () => {
    it("fills the rows with the message of a missing area too, the room left over above it", async () => {
        const element = await card({ device: "gone0001" }, "grid");
        const haCard = one(element, "ha-card");
        width(haCard, 214);
        // The message on four lines, 128 px, ends 140 px from the card's top: two rows and a half, so three.
        box(haCard, 0, 151);
        box(one(element, "ha-card > .message"), 12, 140);
        await measure(element);
        expect(haCard.getAttribute("style")).toBe("min-height: 184px; --spare: 33px");
    });

    /**
     * Measures the card with its last part ending `bottom` px from the card's top. happy-dom gives the card its 11 px of
     * bottom padding but no border, so the content is `bottom` + 11 here, and a pixel more in a browser.
     */
    async function filled(config: Partial<BirdsNearbyCardConfig>, layout: string | undefined, bottom: number): Promise<BirdsNearbyCard> {
        const element = await card(config, layout);
        const haCard = one(element, "ha-card");
        width(haCard, 300);
        width(one(element, ".tabs"), 483);
        textWidths(() => 10);
        box(haCard, 0, bottom + 11);
        const parts = all(element, "ha-card > .header, ha-card > .tabs, ha-card > .scroll > *");
        box(parts.at(-1)!, bottom - 64, bottom);
        await measure(element);
        return element;
    }

    it.each([
        ["a content of a row, 56 px", {}, 45, "min-height: 56px; --spare: 0px"],
        ["a content a pixel over a row, to two", {}, 46, "min-height: 120px; --spare: 63px"],
        ["a content of a row and a half, to two with the half spare", {}, 77, "min-height: 120px; --spare: 32px"],
        ["a content of a row and a half, kept with half rows", { row_step: "half" as const }, 77, "min-height: 88px; --spare: 0px"],
        // 109.4 + 11 is 120.4, a fraction over two rows: three, so the card never ends past its rows.
        ["a content a fraction over two rows, to three", {}, 109.4, "min-height: 184px; --spare: 63px"],
        [
            "a content a pixel over a row and a half, to two with half rows",
            { row_step: "half" as const },
            78,
            "min-height: 120px; --spare: 31px",
        ],
    ])("%s", async (_name, config, bottom, style) => {
        expect(one(await filled(config, "grid", bottom), "ha-card").getAttribute("style")).toBe(style);
    });

    it("puts the message's spare room above it, as its top padding, each line half a row", async () => {
        const element = await card({ device: "gone0001" }, "grid");
        const haCard = one(element, "ha-card");
        width(haCard, 214);
        box(haCard, 0, 151);
        box(one(element, "ha-card > .message"), 12, 140);
        await measure(element);
        const message = getComputedStyle(one(element, "ha-card > .message"));
        expect([message.paddingTop, message.lineHeight]).toEqual(["33px", "32px"]);

        // Measured again, with the 33 px drawn above it, the message ends 33 px lower and the rows stay as they were.
        box(haCard, 0, 184);
        box(one(element, "ha-card > .message"), 45, 173);
        await measure(element);
        expect(haCard.getAttribute("style")).toBe("min-height: 184px; --spare: 33px");
    });

    it("gives the same rows when measured again with its spare room drawn, as it takes that room out first", async () => {
        const element = await filled({}, "grid", 77);
        expect(one(element, "ha-card").getAttribute("style")).toBe("min-height: 120px; --spare: 32px");
        // Drawn now with the 32 px under the header, the content ends 32 px lower.
        const haCard = one(element, "ha-card");
        box(haCard, 0, 120);
        const parts = all(element, "ha-card > .header, ha-card > .tabs, ha-card > .scroll > *");
        box(parts.at(-1)!, 109 - 64, 109);
        await measure(element);
        expect(one(element, "ha-card").getAttribute("style")).toBe("min-height: 120px; --spare: 32px");
    });

    it("puts the spare room under the header, as its bottom padding", async () => {
        const element = await filled({}, "grid", 77);
        expect(getComputedStyle(one(element, ".header")).paddingBottom).toBe("32px");
    });

    it("leaves a card outside a sections view to its content", async () => {
        expect(one(await filled({}, undefined, 46), "ha-card").getAttribute("style")).toBe("");
    });

    it("leaves a card held to a height to that height", async () => {
        expect(one(await filled({ height_mode: "fixed", height: 400 }, "grid", 46), "ha-card").getAttribute("style")).toBe("height: 400px");
    });
});

describe("measuring in drawn and layout pixels", () => {
    /**
     * Measures the recent tab's rows, each drawn `rowWidth` wide with its texts and side as `texts` and `side`, on a card
     * 300 px wide in layout and drawn at `scale`. happy-dom has no computed width, so a scaled card is given one.
     */
    async function splitRows(rowWidth: number, texts: number, side: number, scale = 1): Promise<number> {
        const element = await card();
        all(element, ".tab")[1].click();
        await element.updateComplete;
        const haCard = one(element, "ha-card");
        width(haCard, 300 * scale);
        width(one(element, ".tabs"), 481 * scale);
        all(element, "button.row").forEach((row) => width(row, rowWidth));
        textWidths((text) => (text.classList.contains("name") ? texts : text.closest(".side") ? side : 10 * scale));
        if (scale !== 1) {
            layoutWidth(haCard, 300);
        }
        await measure(element);
        return all(element, "button.row.split").length;
    }

    it("splits a row over by a pixel in layout while a dialog scales the card", async () => {
        // At 0.8, texts of 121 drawn as 96.8 and a side of 64 as 51.2 are a pixel over a row of 288, drawn as 230.4.
        expect(await splitRows(230.4, 96.8, 51.2, 0.8)).toBeGreaterThan(0);
    });

    it("unscales the tabs' room while a dialog scales the card", async () => {
        // Tabs of 286 in layout, 228.8 drawn at 0.8, leave each tab 71.33 px once its padding is taken off. A label of 71
        // (56.8 drawn) fits, one of 72 (57.6 drawn) doesn't. Taken as drawn, the 48 px of padding and gaps would leave 52.27, too little for either.
        async function tabsSplit(label: number): Promise<boolean> {
            const element = await card();
            const haCard = one(element, "ha-card");
            width(haCard, 240);
            width(one(element, ".tabs"), 228.8);
            textWidths((text) => (text.classList.contains("label") ? label * 0.8 : 8));
            layoutWidth(haCard, 300);
            await measure(element);
            return one(element, ".tabs").classList.contains("split");
        }
        expect(await tabsSplit(71)).toBe(false);
        expect(await tabsSplit(72)).toBe(true);
    });

    /** Measures the card with its last part ending `bottom` px from its top in layout, drawn at 0.8. */
    async function filledAtScale(bottom: number): Promise<string | null> {
        const element = await card({}, "grid");
        const haCard = one(element, "ha-card");
        width(haCard, 240);
        width(one(element, ".tabs"), 384.8);
        textWidths(() => 8);
        box(haCard, 0, (bottom + 11) * 0.8, 240);
        const parts = all(element, "ha-card > .header, ha-card > .tabs, ha-card > .scroll > *");
        box(parts.at(-1)!, 10, bottom * 0.8);
        layoutWidth(haCard, 300);
        await measure(element);
        return haCard.getAttribute("style");
    }

    it.each([
        // 77 drawn as 61.6: a row and a half, so two with the half spare, as at rest.
        ["a row and a half", 77, "min-height: 120px; --spare: 32px"],
        // 48 drawn as 38.400000000000006 unscales to 48.00000000000001: the spare keeps its last pixel, 61 and not 60.
        ["a distance whose unscaling leaves noise above it", 48, "min-height: 120px; --spare: 61px"],
        // 48.3 is a real fraction over 48, not noise: the slack doesn't hide it, and the spare loses that pixel, 60.
        ["a distance a real fraction over a whole pixel", 48.3, "min-height: 120px; --spare: 60px"],
        // 237 drawn as 189.6 unscales to a content of 248.00000000000003: exactly four rows, not five.
        ["a distance whose unscaling leaves noise on a row's edge", 237, "min-height: 248px; --spare: 0px"],
    ])("fills the same rows while a dialog scales the card as at rest, %s", async (_name, bottom, style) => {
        expect(await filledAtScale(bottom)).toBe(style);
    });

    it("takes the room from the drawn width, as clientWidth's whole pixels can promise more", async () => {
        // 104 + 120 + 64 is 288, and a row drawn 287.6 wide, whose clientWidth is 288, is short of it.
        expect(await splitRows(287.6, 120, 64)).toBeGreaterThan(0);
        expect(await splitRows(288, 120, 64)).toBe(0);
    });

    it("unscales what it measures while a dialog scales the card, so a row that fits isn't split", async () => {
        // Drawn at 0.8: a row of 288 px is 230.4 drawn, its texts of 120 are 96 and its side of 64 is 51.2. Unscaled,
        // they fit exactly. Taken as drawn, the 104 px of padding and picture would leave them 25.6 px short.
        expect(await splitRows(230.4, 96, 51.2, 0.8)).toBe(0);
        expect(await splitRows(230.4, 96, 51.2)).toBeGreaterThan(0);
    });
});

describe("the editor's rounding", () => {
    function schemaNames(config: Partial<BirdsNearbyCardConfig>): string[] {
        const editor = new BirdsNearbyCardEditor();
        editor.hass = hass();
        editor.setConfig({ type: "custom:birds-nearby-card", device: AREA, ...config } as BirdsNearbyCardConfig);
        const render = (editor as unknown as { render(): { values: unknown[] } }).render();
        const schema = render.values.find((value) => Array.isArray(value)) as { name: string }[];
        return schema.map((entry) => entry.name);
    }

    it("offers the rounding only while the card fits its content", () => {
        expect(schemaNames({})).toContain("row_step");
        expect(schemaNames({ height_mode: "max", max_height: 400 })).not.toContain("row_step");
    });
});
