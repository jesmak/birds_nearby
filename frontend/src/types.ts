import type { LovelaceCardConfig } from "./hass";
import type { HeightConfig } from "./height";

export interface BirdsNearbyCardConfig extends LovelaceCardConfig, HeightConfig {
    /** The area's device, from the Birds Nearby integration. */
    device: string;
    /** Replaces the card's title. */
    title?: string;
}

/** A sighting as the integration's notable and recent sensors give it. */
export interface Sighting {
    species_code: string;
    name: string;
    scientific_name: string;
    /** Null when the observer only noted the species as present. */
    count: number | null;
    /** The observation's own local time, without a zone: "2026-10-29T08:06", or midnight when it had no time. */
    observed: string;
    /** Null for a personal location, whose name is never shown. */
    location: string | null;
    distance_km: number;
    /** Null at the area's centre. */
    direction: string | null;
    iucn_status: string | null;
    url: string;
    picture?: string;
    picture_credit?: string;
    /** Only a notable sighting: how many checklists reported the species in 30 days, and whether eBird has reviewed it. */
    reports?: number;
    reviewed?: boolean;
}

/** A species on the year list. `first_seen` is null for a species already seen when the integration was set up. */
export interface YearSpecies {
    species_code: string;
    name: string;
    first_seen: string | null;
    last_year: string | null;
}
