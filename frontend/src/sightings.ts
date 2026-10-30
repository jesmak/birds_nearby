/** What the card reads from an area: its sensors, found through the device, and how a sighting is written out. */
import { PLATFORM, SENSORS, THREATENED } from "./const";
import type { SensorKey } from "./const";
import type { HomeAssistant } from "./hass";
import type { Sighting, YearSpecies } from "./types";

/** The areas there are, for the card's first configuration. */
export function areaDevices(hass: HomeAssistant): string[] {
    const devices = Object.values(hass.entities ?? {})
        .filter((entry) => entry?.platform === PLATFORM && entry.translation_key === "notable" && entry.device_id)
        .map((entry) => entry?.device_id as string);
    return [...new Set(devices)];
}

/** The area's sensors by what they are. A sensor the area doesn't have is left out. */
export function areaSensors(hass: HomeAssistant, device: string): Partial<Record<SensorKey, string>> {
    const found: Partial<Record<SensorKey, string>> = {};
    for (const entry of Object.values(hass.entities ?? {})) {
        const key = entry?.translation_key as SensorKey | undefined;
        if (entry && entry.device_id === device && entry.platform === PLATFORM && key && SENSORS.includes(key)) {
            found[key] = entry.entity_id;
        }
    }
    return found;
}

/** A list attribute of a sensor, or none while the sensor has no state worth reading. */
export function listOf<T>(hass: HomeAssistant, entityId: string | undefined, attribute: string): T[] | undefined {
    const entity = entityId ? hass.states[entityId] : undefined;
    if (!entity || entity.state === "unavailable" || entity.state === "unknown") {
        return undefined;
    }
    const value = entity.attributes[attribute];
    return Array.isArray(value) ? (value as T[]) : [];
}

/** A sensor's count, the number on its tab. */
export function countOf(hass: HomeAssistant, entityId: string | undefined): number | null {
    const value = Number.parseInt(entityId ? (hass.states[entityId]?.state ?? "") : "", 10);
    return Number.isFinite(value) ? value : null;
}

export function threatened(sighting: Sighting): boolean {
    return !!sighting.iucn_status && THREATENED.includes(sighting.iucn_status);
}

/** The species' pictures from the sightings, for the year list, whose sensor has none. */
export function picturesOf(...lists: (Sighting[] | undefined)[]): Map<string, Sighting> {
    const found = new Map<string, Sighting>();
    for (const sighting of lists.flatMap((list) => list ?? [])) {
        if (sighting.picture && !found.has(sighting.species_code)) {
            found.set(sighting.species_code, sighting);
        }
    }
    return found;
}

/** A day of the year list: the species first seen that day, or with `day` null, those seen before the installation. */
export interface YearDay {
    day: string | null;
    species: YearSpecies[];
}

/** The year list by the day each species was first seen, the newest day first and those without a day last. */
export function yearDays(species: YearSpecies[]): YearDay[] {
    const days = new Map<string | null, YearSpecies[]>();
    for (const item of species) {
        const day = item.first_seen || null;
        days.set(day, [...(days.get(day) ?? []), item]);
    }
    return [...days.entries()]
        .map(([day, items]) => ({ day, species: items }))
        .sort((a, b) => (a.day === null ? 1 : b.day === null ? -1 : b.day.localeCompare(a.day)));
}

/** The viewer's language and Home Assistant's number format setting, from the user's profile. */
export interface NumberFormat {
    language: string;
    /** "language", "system", "comma_decimal", "decimal_comma", "space_comma", "quote_decimal" or "none". */
    number_format?: string;
}

/**
 * The locales the number format setting asks for, as Home Assistant's own frontend reads it: `numberFormatToLocale`, except
 * none, which `formatNumberToParts` writes in en-US without grouping.
 */
function numberLocale(format: NumberFormat): string | string[] | undefined {
    switch (format.number_format) {
        case "comma_decimal":
            return ["en-US", "en"];
        case "decimal_comma":
            return ["de", "es", "it"];
        case "space_comma":
            return ["fr", "sv", "cs"];
        case "quote_decimal":
            return ["de-CH"];
        case "none":
            return "en-US";
        case "system":
            return undefined;
        default:
            return format.language;
    }
}

export function formatNumber(value: number, format: NumberFormat, fractions = 0): string {
    return new Intl.NumberFormat(numberLocale(format), {
        maximumFractionDigits: fractions,
        ...(format.number_format === "none" ? { useGrouping: false } : {}),
    }).format(value);
}

/** Where it was: a hotspot's name, then the distance and direction from the area's centre. A personal location shows only the latter. */
export function placeOf(sighting: Sighting, format: NumberFormat): string {
    const distance = `${formatNumber(sighting.distance_km, format, 1)} km${sighting.direction ? ` ${sighting.direction}` : ""}`;
    return sighting.location ? `${sighting.location}, ${distance}` : distance;
}

/**
 * A date of the observation's own, "2026-10-29" or the date part of "2026-10-29T08:06", as a short day and month in the
 * viewer's language. Read as text, as eBird's times are the observation's local time without a zone.
 */
export function formatDay(value: string, language: string, today: string): string {
    const [year, month, day] = value.slice(0, 10).split("-").map(Number);
    const date = new Date(Date.UTC(year, month - 1, day));
    const sameYear = value.slice(0, 4) === today.slice(0, 4);
    return new Intl.DateTimeFormat(language, {
        day: "numeric",
        month: "numeric",
        ...(sameYear ? {} : { year: "numeric" }),
        timeZone: "UTC",
    }).format(date);
}

/** The observation's clock time, or null when the observer gave none (eBird's date-only records arrive as midnight). */
export function formatClock(value: string, language: string): string | null {
    const time = value.slice(11, 16);
    if (!time || time === "00:00") {
        return null;
    }
    const [hours, minutes] = time.split(":").map(Number);
    return new Intl.DateTimeFormat(language, { hour: "numeric", minute: "2-digit", timeZone: "UTC" }).format(
        new Date(Date.UTC(2000, 0, 1, hours, minutes)),
    );
}

/** Today in the viewer's own zone, "2026-10-30": whether a date needs its year, and when the day has changed. */
export function localToday(now: Date = new Date()): string {
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}
