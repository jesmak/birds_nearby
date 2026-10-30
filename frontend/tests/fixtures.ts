import type { EntityRegistryEntry, HassEntity, HomeAssistant } from "../src/hass";
import type { Sighting, YearSpecies } from "../src/types";

// A made-up area, shaped like what Birds Nearby 1.3.0 registers. The sightings are invented, not eBird's.
export const AREA = "area0001";
export const OTHER_AREA = "area0002";

export const SENSOR_IDS = {
    notable: "sensor.lintuhavainnot_huomionarvoiset",
    recent: "sensor.lintuhavainnot_viimeaikaiset",
    year_list: "sensor.lintuhavainnot_vuosilista",
    map: "sensor.lintuhavainnot_havaintopaikat",
} as const;

export function sighting(fields: Partial<Sighting> = {}): Sighting {
    return {
        species_code: "eurbla",
        name: "mustarastas",
        scientific_name: "Turdus merula",
        count: 2,
        observed: "2026-10-30T08:15",
        location: "Esimerkkilahti",
        distance_km: 3.2,
        direction: "koilliseen",
        iucn_status: "LC",
        url: "https://ebird.org/species/eurbla",
        picture: "https://upload.wikimedia.org/eurbla.jpg",
        picture_credit: "A. Kuvaaja, CC BY 4.0",
        ...fields,
    };
}

export const NOTABLE: Sighting[] = [
    sighting({
        species_code: "palhar1",
        name: "arosuohaukka",
        scientific_name: "Circus macrourus",
        count: 1,
        observed: "2026-10-29T14:05",
        iucn_status: "NT",
        url: "https://ebird.org/species/palhar1",
        picture: "https://upload.wikimedia.org/palhar1.jpg",
        reports: 3,
        reviewed: false,
    }),
];

export const RECENT: Sighting[] = [
    sighting(),
    sighting({
        species_code: "palhar1",
        name: "arosuohaukka",
        scientific_name: "Circus macrourus",
        count: 1,
        observed: "2026-10-29T14:05",
        iucn_status: "NT",
        url: "https://ebird.org/species/palhar1",
        picture: "https://upload.wikimedia.org/palhar1.jpg",
    }),
    sighting({
        species_code: "comeid",
        name: "haahka",
        scientific_name: "Somateria mollissima",
        count: null,
        observed: "2026-10-20T00:00",
        location: null,
        distance_km: 12.5,
        direction: "etelään",
        iucn_status: "EN",
        url: "https://ebird.org/species/comeid",
        picture: undefined,
        picture_credit: undefined,
    }),
];

export const YEAR: YearSpecies[] = [
    { species_code: "palhar1", name: "arosuohaukka", first_seen: "2026-10-29", last_year: null },
    { species_code: "comeid", name: "haahka", first_seen: "2026-10-20", last_year: "2025-04-12" },
    { species_code: "eurbla", name: "mustarastas", first_seen: null, last_year: null },
    { species_code: "hoocro1", name: "varis", first_seen: "2026-10-29", last_year: null },
];

function entity(entity_id: string, state: string, attributes: Record<string, unknown> = {}): HassEntity {
    return { entity_id, state, last_changed: "2026-10-30T07:40:00+00:00", attributes };
}

export interface Lists {
    notable?: Sighting[] | "unavailable";
    recent?: Sighting[] | "unavailable";
    year?: YearSpecies[] | "unavailable";
}

export function hass(lists: Lists = {}): HomeAssistant {
    const notable = lists.notable ?? NOTABLE;
    const recent = lists.recent ?? RECENT;
    const year = lists.year ?? YEAR;
    const state = (list: unknown[] | "unavailable") => (list === "unavailable" ? "unavailable" : String(list.length));
    const states: Record<string, HassEntity> = {
        [SENSOR_IDS.notable]: entity(SENSOR_IDS.notable, state(notable), notable === "unavailable" ? {} : { sightings: notable }),
        [SENSOR_IDS.recent]: entity(SENSOR_IDS.recent, state(recent), recent === "unavailable" ? {} : { days: 7, species: recent }),
        [SENSOR_IDS.year_list]: entity(SENSOR_IDS.year_list, state(year), year === "unavailable" ? {} : { year: 2026, species: year }),
        [SENSOR_IDS.map]: entity(SENSOR_IDS.map, "4"),
    };
    const entities: Record<string, EntityRegistryEntry> = {};
    for (const [key, id] of Object.entries(SENSOR_IDS)) {
        entities[id] = { entity_id: id, device_id: AREA, platform: "birds_nearby", translation_key: key };
    }
    // Another integration's sensor with the same translation key on another device.
    states["sensor.other_notable"] = entity("sensor.other_notable", "9");
    entities["sensor.other_notable"] = {
        entity_id: "sensor.other_notable",
        device_id: OTHER_AREA,
        platform: "other",
        translation_key: "notable",
    };
    return {
        locale: { language: "fi" },
        states,
        entities,
        devices: { [AREA]: { id: AREA, name: "Esimerkkilä", manufacturer: "eBird" }, [OTHER_AREA]: { id: OTHER_AREA, name: "Muu" } },
    };
}
