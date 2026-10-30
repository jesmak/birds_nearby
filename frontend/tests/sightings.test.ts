import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { areaDevices, areaSensors, formatClock, formatDay, localToday, picturesOf, placeOf, threatened, yearDays } from "../src/sightings";
import { AREA, NOTABLE, RECENT, SENSOR_IDS, YEAR, hass, sighting } from "./fixtures";

const FI = { language: "fi" };

describe("an area's sensors", () => {
    it("are found on its device by their translation keys, not by their names", () => {
        expect(areaSensors(hass(), AREA)).toEqual({
            notable: SENSOR_IDS.notable,
            recent: SENSOR_IDS.recent,
            year_list: SENSOR_IDS.year_list,
        });
    });

    it("are offered only from the integration's devices", () => {
        expect(areaDevices(hass())).toEqual([AREA]);
    });
});

describe("a sighting's place", () => {
    it.each([
        ["a hotspot by its name", sighting(), "Esimerkkilahti, 3,2 km koilliseen"],
        [
            "a personal location by its distance only",
            sighting({ location: null, distance_km: 12.5, direction: "etelään" }),
            "12,5 km etelään",
        ],
        ["the centre without a direction", sighting({ location: null, distance_km: 0.1, direction: null }), "0,1 km"],
    ])("%s", (_name, item, expected) => {
        expect(placeOf(item, FI)).toBe(expected);
    });

    it("follows Home Assistant's number format setting", () => {
        expect(placeOf(sighting(), { language: "fi", number_format: "comma_decimal" })).toBe("Esimerkkilahti, 3.2 km koilliseen");
    });
});

describe("dates and times of the observation's own", () => {
    // Far from UTC, so that reading the text as a time in the viewer's zone, or today in UTC, would show.
    let zone: string | undefined;
    beforeEach(() => {
        zone = process.env.TZ;
        process.env.TZ = "Pacific/Kiritimati";
    });
    afterEach(() => {
        process.env.TZ = zone;
    });

    it.each([
        ["2026-10-29T14:05", "fi", "14.05"],
        ["2026-10-29T14:05", "en", "2:05 PM"],
        // eBird sends a record without a time as midnight, as the map does too.
        ["2026-10-29T00:00", "fi", null],
        ["2026-10-29T00:00", "en", null],
        ["2026-10-29", "fi", null],
        ["2026-10-29", "en", null],
        // Only exactly midnight means no time.
        ["2026-10-29T00:30", "fi", "0.30"],
        ["2026-10-29T09:05", "fi", "9.05"],
        ["2026-10-29T00:30", "en", "12:30 AM"],
        ["2026-10-29T09:05", "en", "9:05 AM"],
    ])("%s in %s is %s", (value, language, expected) => {
        expect(formatClock(value, language)).toBe(expected);
    });

    it("are read as text, whatever the viewer's zone", () => {
        expect(formatDay("2026-10-29T23:30", "fi", "2026-10-30")).toBe("29.10.");
        expect(formatClock("2026-10-29T23:30", "fi")).toBe("23.30");
    });

    it("name the year only when it isn't this year's", () => {
        expect(formatDay("2025-04-12", "fi", "2026-10-30")).toBe("12.4.2025");
    });

    it("count today in the viewer's own zone", () => {
        expect(localToday(new Date(2026, 9, 30, 0, 5))).toBe("2026-10-30");
    });
});

describe("the year list", () => {
    it("is grouped by the day each species was first seen, the newest first and those from before installation last", () => {
        const days = yearDays(YEAR);
        expect(days.map((day) => day.day)).toEqual(["2026-10-29", "2026-10-20", null]);
        expect(days[0].species.map((item) => item.species_code)).toEqual(["palhar1", "hoocro1"]);
    });

    it("takes its pictures from the sightings, as its own sensor has none", () => {
        const pictures = picturesOf(RECENT, NOTABLE);
        expect(pictures.get("palhar1")?.picture).toBe("https://upload.wikimedia.org/palhar1.jpg");
        expect(pictures.has("comeid")).toBe(false);
    });
});

describe("a threatened species", () => {
    it.each([
        ["LC", false],
        ["NT", false],
        ["VU", true],
        ["EN", true],
        ["CR", true],
        [null, false],
    ])("%s is %s", (status, expected) => {
        expect(threatened(sighting({ iucn_status: status }))).toBe(expected);
    });
});
