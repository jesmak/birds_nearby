/** Replaced at build time with the integration's version in manifest.json. */
declare const __CARD_VERSION__: string;

export const CARD_VERSION = __CARD_VERSION__;

/** The integration whose areas the card shows. */
export const PLATFORM = "birds_nearby";

/** An area's sensors the card reads, by their translation key in the integration. They are also the card's tabs. */
export const SENSORS = ["notable", "recent", "year_list"] as const;
export type SensorKey = (typeof SENSORS)[number];

/** The IUCN Red List categories above Near Threatened, which get a badge. */
export const THREATENED = ["VU", "EN", "CR", "EW", "EX"];

/** The height a card added from the picker is held to, which leaves its list about 400 px. */
export const STUB_MAX_HEIGHT = 500;
