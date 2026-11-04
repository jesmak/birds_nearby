/** The little of Home Assistant a card needs, so the unmaintained custom-card-helpers isn't a dependency. */

export interface HassEntity {
    entity_id: string;
    state: string;
    last_changed: string;
    attributes: Record<string, unknown>;
}

/** An entity's registry entry as the frontend has it: enough to find a device's sensors by what they are. */
export interface EntityRegistryEntry {
    entity_id: string;
    device_id?: string | null;
    platform?: string;
    translation_key?: string | null;
}

interface DeviceRegistryEntry {
    id: string;
    name?: string | null;
    name_by_user?: string | null;
}

export interface HomeAssistant {
    states: Record<string, HassEntity | undefined>;
    entities?: Record<string, EntityRegistryEntry | undefined>;
    devices?: Record<string, DeviceRegistryEntry | undefined>;
    language?: string;
    /** `number_format` is "language", "system", "comma_decimal", "decimal_comma", "space_comma", "quote_decimal" or "none". */
    locale?: { language?: string; number_format?: string };
}

export interface LovelaceCardConfig {
    type: string;
    [key: string]: unknown;
}
