import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import "../src/birds-nearby-card";
import type { BirdsNearbyCard } from "../src/birds-nearby-card";
import { BirdsNearbyCardEditor } from "../src/editor";
import type { HomeAssistant } from "../src/hass";
import type { BirdsNearbyCardConfig } from "../src/types";
import { AREA, RECENT, SENSOR_IDS, hass, sighting } from "./fixtures";

// The viewer's clock: the morning after the newest sighting but one.
const NOW = new Date(2026, 9, 30, 9, 0);

async function card(state: HomeAssistant, config: Partial<BirdsNearbyCardConfig> = {}): Promise<BirdsNearbyCard> {
    const element = document.createElement("birds-nearby-card");
    element.setConfig({ type: "custom:birds-nearby-card", device: AREA, ...config } as BirdsNearbyCardConfig);
    element.hass = state;
    document.body.append(element);
    await element.updateComplete;
    return element;
}

function text(element: Element | null | undefined): string {
    return (element?.textContent ?? "").replace(/\s+/g, " ").trim();
}

function rows(element: BirdsNearbyCard): string[] {
    return [...element.shadowRoot!.querySelectorAll(".row")].map((row) => text(row.querySelector(".name")));
}

async function click(element: BirdsNearbyCard, selector: string, index = 0): Promise<void> {
    (element.shadowRoot!.querySelectorAll<HTMLElement>(selector)[index] as HTMLElement).click();
    await element.updateComplete;
}

describe("birds-nearby-card", () => {
    beforeEach(() => {
        vi.useFakeTimers({ now: NOW, toFake: ["Date"] });
    });

    afterEach(() => {
        vi.useRealTimers();
        document.body.innerHTML = "";
    });

    it("shows the title, the area and the three counts as tabs", async () => {
        const root = (await card(hass())).shadowRoot!;
        expect(text(root.querySelector(".title"))).toBe("Lintuhavainnot");
        expect(text(root.querySelector(".area"))).toBe("Esimerkkilä");
        expect([...root.querySelectorAll(".tab")].map(text)).toEqual(["1 Huomionarvoiset", "3 Viimeaikaiset", "4 Vuosilista"]);
    });

    it("opens on the notable sightings when there are any, otherwise on the recent ones", async () => {
        expect((await card(hass())).shadowRoot!.querySelector(".tab.on")?.classList.contains("notable")).toBe(true);
        document.body.innerHTML = "";
        expect((await card(hass({ notable: [] }))).shadowRoot!.querySelector(".tab.on")?.classList.contains("recent")).toBe(true);
    });

    it("writes a notable sighting with its badges, count and time", async () => {
        const root = (await card(hass())).shadowRoot!;
        const row = root.querySelector(".row")!;
        expect(text(row.querySelector(".name"))).toBe("arosuohaukka tarkastamaton");
        expect(text(row.querySelector(".scientific"))).toBe("Circus macrourus");
        expect(text(row.querySelector(".place"))).toBe("Esimerkkilahti, 3,2 km koilliseen");
        expect(text(row.querySelector(".side"))).toBe("1 yks. 29.10. 14.05");
    });

    it("marks a recent species that is also notable, and a threatened one", async () => {
        const element = await card(hass());
        await click(element, ".tab.recent");
        const names = [...element.shadowRoot!.querySelectorAll(".row .name")].map(text);
        expect(names).toEqual(["mustarastas", "arosuohaukka huomionarvoinen", "haahka EN"]);
    });

    it("shows a count left empty as present, a personal location by its distance, and the bird for a missing picture", async () => {
        const element = await card(hass());
        await click(element, ".tab.recent");
        const row = element.shadowRoot!.querySelectorAll(".row")[2];
        expect(text(row.querySelector(".place"))).toBe("12,5 km etelään");
        expect(text(row.querySelector(".side"))).toBe("läsnä 20.10.");
        expect(row.querySelector(".thumbnail.none ha-icon")?.getAttribute("icon")).toBe("mdi:bird");
    });

    // eBird's times are the area's own, and the card knows no zone for the area, so it never says today or yesterday.
    it("shows a sighting's day with its time, today's too, and the day alone without a time", async () => {
        const element = await card(hass());
        await click(element, ".tab.recent");
        expect([...element.shadowRoot!.querySelectorAll(".row .when")].map(text)).toEqual(["30.10. 8.15", "29.10. 14.05", "20.10."]);
    });

    it("writes the year on a date of an earlier year from the moment it is one", async () => {
        vi.setSystemTime(new Date(2026, 11, 31, 23, 50));
        const state = hass({ notable: [], recent: [sighting({ observed: "2026-12-31T21:00" })] });
        const element = await card(state);
        expect(text(element.shadowRoot!.querySelector(".row .when"))).toBe("31.12. 21.00");
        vi.setSystemTime(new Date(2027, 0, 1, 0, 10));
        // Something else in the house changes after midnight, which hands the card a new hass.
        element.hass = { ...state, states: { ...state.states } };
        await element.updateComplete;
        expect(text(element.shadowRoot!.querySelector(".row .when"))).toBe("31.12.2026 21.00");
    });

    it("opens a sighting to its picture, credit, reports and eBird page, and shuts it again", async () => {
        const element = await card(hass());
        await click(element, ".row");
        const detail = element.shadowRoot!.querySelector(".detail")!;
        expect(detail.querySelector("img.picture")?.getAttribute("src")).toBe("https://upload.wikimedia.org/palhar1.jpg");
        expect(text(detail.querySelector(".credit"))).toBe("A. Kuvaaja, CC BY 4.0");
        expect(text(detail.querySelector(".links"))).toBe("3 havaintoerää 30 päivässä Laji eBirdissä");
        expect(detail.querySelector("a")?.getAttribute("href")).toBe("https://ebird.org/species/palhar1");
        expect(element.shadowRoot!.querySelector(".row")?.getAttribute("aria-expanded")).toBe("true");
        await click(element, ".row");
        expect(element.shadowRoot!.querySelector(".detail")).toBeNull();
    });

    it("says so when an opened sighting has no picture", async () => {
        const element = await card(hass());
        await click(element, ".tab.recent");
        await click(element, ".row", 2);
        expect(text(element.shadowRoot!.querySelector(".detail .credit"))).toBe("Kuvaa ei löytynyt");
    });

    it("shuts an opened sighting when another tab is chosen", async () => {
        const element = await card(hass());
        await click(element, ".row");
        await click(element, ".tab.recent");
        expect(element.shadowRoot!.querySelector(".detail")).toBeNull();
    });

    it("groups the year list by day, those from before installation last, with pictures from the sightings", async () => {
        const element = await card(hass());
        await click(element, ".tab.year_list");
        const root = element.shadowRoot!;
        expect([...root.querySelectorAll(".day")].map(text)).toEqual(["29.10. 2 lajia", "20.10. 1 laji", "Ennen asennusta 1 laji"]);
        expect(rows(element)).toEqual(["arosuohaukka", "varis", "haahka", "mustarastas"]);
        expect(text(root.querySelectorAll(".row")[2].querySelector(".place"))).toBe("Viime vuonna 12.4.2025");
        expect(root.querySelectorAll(".row")[0].querySelector("img")?.getAttribute("src")).toBe("https://upload.wikimedia.org/palhar1.jpg");
        expect(root.querySelector(".row.year button, button.row.year")).toBeNull();
    });

    it.each([
        ["notable", { notable: [] }, "Ei huomionarvoisia havaintoja 30 päivään"],
        ["recent", { recent: [] }, "Ei havaintoja 7 päivään"],
        ["year_list", { year: [] }, "Tämän vuoden listalla ei ole vielä lajeja"],
        ["notable", { notable: "unavailable" as const }, "eBirdistä ei saada nyt tietoja"],
        ["year_list", { year: "unavailable" as const }, "eBirdistä ei saada nyt tietoja"],
    ])("says why the %s list is empty", async (tab, lists, message) => {
        const element = await card(hass(lists));
        await click(element, `.tab.${tab}`);
        expect(text(element.shadowRoot!.querySelector(".empty"))).toBe(message);
    });

    it("shows a dash for a count it can't read", async () => {
        const root = (await card(hass({ notable: "unavailable" }))).shadowRoot!;
        expect(text(root.querySelector(".tab.notable .count"))).toBe("–");
    });

    it("says so when the area isn't there", async () => {
        const element = await card(hass(), { device: "gone0001" });
        expect(text(element.shadowRoot!.querySelector("ha-card.message"))).toBe(
            "Aluetta ei löydy. Se on ehkä poistettu tai poistettu käytöstä Birds Nearby -integraatiossa.",
        );
    });

    it("takes its title from the configuration", async () => {
        expect(text((await card(hass(), { title: "Linnut" })).shadowRoot!.querySelector(".title"))).toBe("Linnut");
    });

    it("holds the list to the height asked for, never lower than its minimum, and scrolls it", async () => {
        const root = (await card(hass(), { max_height: 100 })).shadowRoot!;
        const haCard = root.querySelector("ha-card")!;
        expect(haCard.classList.contains("held")).toBe(true);
        expect(haCard.getAttribute("style")).toBe("max-height: 275px");
        expect(root.querySelector("ha-card > .scroll")).not.toBeNull();
    });

    it("grows with its content without a height", async () => {
        const haCard = (await card(hass())).shadowRoot!.querySelector("ha-card")!;
        expect(haCard.classList.contains("held")).toBe(false);
        expect(haCard.getAttribute("style")).toBe("");
    });

    it("refuses a configuration without an area or with a broken height", () => {
        const element = document.createElement("birds-nearby-card");
        expect(() => element.setConfig({ type: "custom:birds-nearby-card" } as BirdsNearbyCardConfig)).toThrow(
            "Choose an area from the Birds Nearby integration",
        );
        expect(() => element.setConfig({ type: "custom:birds-nearby-card", device: AREA, max_height: -5 })).toThrow();
    });

    it("is added from the picker with the first area, held to a height so a busy area's list scrolls", () => {
        const Card = customElements.get("birds-nearby-card") as unknown as { getStubConfig(hass?: HomeAssistant): Record<string, unknown> };
        expect(Card.getStubConfig(hass())).toEqual({ device: AREA, max_height: 500 });
        expect(Card.getStubConfig()).toEqual({ device: "", max_height: 500 });
    });

    it("redraws only for its own sensors", async () => {
        const state = hass();
        const element = await card(state);
        const render = vi.spyOn(element as unknown as { render(): unknown }, "render");
        const light = { entity_id: "light.kitchen", state: "on", last_changed: "", attributes: {} };
        element.hass = { ...state, states: { ...state.states, "light.kitchen": light } };
        await element.updateComplete;
        expect(render).not.toHaveBeenCalled();
        const recent = state.states[SENSOR_IDS.recent]!;
        const more = {
            ...recent,
            state: "4",
            attributes: { ...recent.attributes, species: [...RECENT, sighting({ species_code: "gretit1" })] },
        };
        element.hass = { ...state, states: { ...state.states, [SENSOR_IDS.recent]: more } };
        await element.updateComplete;
        expect(render).toHaveBeenCalled();
    });

    it("says so when a sensor isn't found, as a disabled one isn't, rather than blaming eBird", async () => {
        const state = hass();
        const entities = { ...state.entities };
        delete entities[SENSOR_IDS.year_list];
        const element = await card({ ...state, entities });
        expect(text(element.shadowRoot!.querySelector(".tab.year_list .count"))).toBe("–");
        await click(element, ".tab.year_list");
        expect(text(element.shadowRoot!.querySelector(".empty"))).toBe("Anturia ei löydy. Se on ehkä poistettu käytöstä.");
    });

    it.each([
        ["fi", "the card", "fi"],
        ["fi-FI", "the card", "fi"],
        ["FI-fi", "the card", "fi"],
        ["en", "the card", "en"],
        ["sv", "the card", "en"],
        ["fi", "the message of a missing area", "fi"],
        ["fi-FI", "the message of a missing area", "fi"],
        ["sv", "the message of a missing area", "en"],
    ])("marks its texts in %s on %s as %s for hyphenation", async (language, shown, expected) => {
        const element = await card({ ...hass(), locale: { language } }, shown === "the card" ? {} : { device: "gone0001" });
        expect(element.shadowRoot!.querySelector("ha-card")?.getAttribute("lang")).toBe(expected);
    });

    it("takes its language from Home Assistant's own when the profile has none", async () => {
        const element = await card({ ...hass(), locale: undefined, language: "fi" });
        expect(element.shadowRoot!.querySelector("ha-card")?.getAttribute("lang")).toBe("fi");
        expect(text(element.shadowRoot!.querySelector(".title"))).toBe("Lintuhavainnot");
    });
});

describe("birds-nearby-card-editor", () => {
    it("leaves an empty title and a height mode the heights give out of the configuration", () => {
        const editor = new BirdsNearbyCardEditor();
        const changed = vi.fn();
        editor.addEventListener("config-changed", (event) => changed((event as CustomEvent).detail.config));
        (editor as unknown as { valueChanged(event: CustomEvent): void }).valueChanged(
            new CustomEvent("value-changed", {
                detail: { value: { type: "custom:birds-nearby-card", device: AREA, title: "", height_mode: "max", max_height: 500 } },
            }),
        );
        expect(changed).toHaveBeenCalledWith({ type: "custom:birds-nearby-card", device: AREA, max_height: 500 });
    });
});
