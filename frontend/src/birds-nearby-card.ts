/**
 * A dashboard card for an area of the Birds Nearby integration: the counts of its notable sightings, recent species and
 * year list as tabs, and under them the chosen list with the species' pictures. A sighting opens to its picture at full
 * width, and the year list is grouped by the day each species was first seen.
 */
import { LitElement, css, html, nothing } from "lit";
import type { CSSResultGroup, PropertyValues, TemplateResult } from "lit";
import { property, state } from "lit/decorators.js";

import { CARD_VERSION, SENSORS, STUB_MAX_HEIGHT } from "./const";
import type { SensorKey } from "./const";
import "./editor";
import { ScrollFade, fadeStyles } from "./fade";
import type { HomeAssistant } from "./hass";
import { gridMinRows, heightCardSize, heightStyle, validHeight } from "./height";
import { LANGUAGE_CODES, browserLanguage, translate } from "./localize/localize";
import {
    areaDevices,
    areaSensors,
    countOf,
    formatClock,
    formatDay,
    formatNumber,
    listOf,
    localToday,
    picturesOf,
    placeOf,
    threatened,
    yearDays,
} from "./sightings";
import type { NumberFormat } from "./sightings";
import type { BirdsNearbyCardConfig, Sighting, YearSpecies } from "./types";

interface CardRegistration {
    type: string;
    name: string;
    description: string;
    documentationURL?: string;
    preview?: boolean;
}

/**
 * The heights the minimum is made of, in pixels, as measured at the narrowest card a sections view allows (6 columns):
 * the header on two lines, the tabs as rows and a row whose place wraps, with the list's top border. A full section's
 * width needs less, but a card held to its minimum then still shows a row at every width.
 */
const HEADER_HEIGHT = 49;
const TABS_HEIGHT = 117;
const ROW_HEIGHT = 109;

export class BirdsNearbyCard extends LitElement {
    @property({ attribute: false }) public hass?: HomeAssistant;
    /** "grid" in a sections view, as Home Assistant sets it. */
    @property({ attribute: false }) public layout?: string;
    @state() private config?: BirdsNearbyCardConfig;
    /** The tab chosen by hand. Until then the card opens on the notable sightings when there are any. */
    @state() private tab?: SensorKey;
    /** The opened sighting, as its tab and species. */
    @state() private open?: string;
    /** The viewer's day at the last redraw: a date of an earlier year is written with its year from New Year on. */
    private drawnOn?: string;

    constructor() {
        super();
        // Fades the list's edges while the card is held to a height, through the card's own lifecycle.
        new ScrollFade(this, () => (this.heightStyle() ? this.renderRoot.querySelectorAll<HTMLElement>("ha-card > .scroll") : []));
    }

    public static getConfigElement(): HTMLElement {
        return document.createElement("birds-nearby-card-editor");
    }

    /** Offers the first area there is when the card is added from the picker, held to a height so a busy area's list scrolls. */
    public static getStubConfig(hass?: HomeAssistant): Record<string, unknown> {
        return { device: hass ? (areaDevices(hass)[0] ?? "") : "", max_height: STUB_MAX_HEIGHT };
    }

    public setConfig(config: BirdsNearbyCardConfig): void {
        if (!config || typeof config.device !== "string" || !config.device) {
            throw new Error(translate(browserLanguage(), "common.invalid_configuration"));
        }
        if (!validHeight(config)) {
            throw new Error(translate(browserLanguage(), "common.invalid_height"));
        }
        if (this.config && this.config.device !== config.device) {
            // Another area's opened sighting is none of this one's.
            this.open = undefined;
        }
        this.config = config;
    }

    public getCardSize(): number {
        return heightCardSize(this.config ?? {}, 10, this.minimumHeight());
    }

    /** In a sections view the card takes a whole section by default and is never narrower than half of one. */
    public getGridOptions(): Record<string, unknown> {
        return { columns: 12, min_columns: 6, rows: "auto", min_rows: gridMinRows(this.minimumHeight()) };
    }

    protected shouldUpdate(changed: PropertyValues): boolean {
        const previous = changed.get("hass") as HomeAssistant | undefined;
        if (!this.config || !this.hass || changed.size > 1 || !changed.has("hass") || !previous || this.drawnOn !== localToday()) {
            return true;
        }
        if (
            previous.entities !== this.hass.entities ||
            previous.devices !== this.hass.devices ||
            previous.locale !== this.hass.locale ||
            previous.language !== this.hass.language
        ) {
            return true;
        }
        // Home Assistant hands the card every state change in the house; only the area's sensors matter.
        const sensors = Object.values(areaSensors(this.hass, this.config.device));
        return sensors.some((id) => previous.states[id] !== this.hass?.states[id]);
    }

    protected render(): TemplateResult | typeof nothing {
        if (!this.hass || !this.config) {
            return nothing;
        }
        this.drawnOn = localToday();
        const sensors = areaSensors(this.hass, this.config.device);
        if (!this.hass.devices?.[this.config.device] || !Object.keys(sensors).length) {
            return html`<ha-card class="message" style=${this.heightStyle()} lang=${this.textLanguage()}
                >${this.text("common.no_area")}</ha-card
            >`;
        }
        const notable = listOf<Sighting>(this.hass, sensors.notable, "sightings");
        const recent = listOf<Sighting>(this.hass, sensors.recent, "species");
        const tab = this.tab ?? ((countOf(this.hass, sensors.notable) ?? 0) > 0 ? "notable" : "recent");
        const height = this.heightStyle();
        return html`
            <ha-card class=${height ? "held" : ""} style=${height} lang=${this.textLanguage()}>
                <div class="header">
                    <span class="title">${this.config.title || this.text("common.title")}</span>
                    <span class="area">${this.areaName()}</span>
                </div>
                <div class="tabs" role="tablist">${SENSORS.map((key) => this.tabButton(this.hass!, key, sensors[key], tab))}</div>
                <div class="scroll" role="tabpanel">${this.list(this.hass, tab, sensors, notable, recent)}</div>
            </ha-card>
        `;
    }

    private tabButton(hass: HomeAssistant, key: SensorKey, entityId: string | undefined, chosen: SensorKey): TemplateResult {
        const count = countOf(hass, entityId);
        return html`
            <button
                class="tab ${key} ${key === chosen ? "on" : ""}"
                role="tab"
                aria-selected=${key === chosen ? "true" : "false"}
                @click=${() => this.choose(key)}
            >
                <span class="count">${count === null ? "–" : formatNumber(count, this.numberFormat())}</span>
                <span class="label">${this.text(`tabs.${key}`)}</span>
            </button>
        `;
    }

    private choose(key: SensorKey): void {
        this.tab = key;
        this.open = undefined;
        this.renderRoot.querySelector(".scroll")?.scrollTo({ top: 0 });
    }

    private list(
        hass: HomeAssistant,
        tab: SensorKey,
        sensors: Partial<Record<SensorKey, string>>,
        notable: Sighting[] | undefined,
        recent: Sighting[] | undefined,
    ): TemplateResult {
        // A disabled sensor isn't in the frontend's registry at all, which is no fault of eBird's.
        if (!sensors[tab]) {
            return this.empty(this.text("common.not_found"));
        }
        if (tab === "year_list") {
            const species = listOf<YearSpecies>(hass, sensors.year_list, "species");
            if (!species) {
                return this.empty(this.text("common.unavailable"));
            }
            return species.length ? this.yearList(species, picturesOf(recent, notable)) : this.empty(this.text("empty.year_list"));
        }
        const sightings = tab === "notable" ? notable : recent;
        if (!sightings) {
            return this.empty(this.text("common.unavailable"));
        }
        if (!sightings.length) {
            const days = hass.states[sensors.recent ?? ""]?.attributes.days;
            return this.empty(this.text(`empty.${tab}`).replace("{days}", String(days ?? 7)));
        }
        const notableSpecies = new Set((notable ?? []).map((sighting) => sighting.species_code));
        return html`${sightings.map((sighting) => this.row(tab, sighting, tab === "recent" && notableSpecies.has(sighting.species_code)))}`;
    }

    private empty(message: string): TemplateResult {
        return html`<div class="empty">${message}</div>`;
    }

    private row(tab: SensorKey, sighting: Sighting, notable: boolean): TemplateResult {
        const key = `${tab}:${sighting.species_code}`;
        const opened = this.open === key;
        return html`
            <div class="sighting ${opened ? "opened" : ""}">
                <button class="row" aria-expanded=${opened ? "true" : "false"} @click=${() => (this.open = opened ? undefined : key)}>
                    ${this.thumbnail(sighting.picture)}
                    <span class="main">
                        <span class="name">${sighting.name}${this.badges(sighting, notable)}</span>
                        <span class="scientific">${sighting.scientific_name}</span>
                        <span class="place">${placeOf(sighting, this.numberFormat())}</span>
                    </span>
                    <span class="side">
                        <span class="amount">${this.amount(sighting.count)}</span>
                        <span class="when">${this.when(sighting.observed)}</span>
                    </span>
                </button>
                ${opened ? this.detail(sighting) : nothing}
            </div>
        `;
    }

    private thumbnail(picture: string | undefined): TemplateResult {
        return picture
            ? html`<img class="thumbnail" src=${picture} alt="" loading="lazy" />`
            : html`<span class="thumbnail none"><ha-icon icon="mdi:bird"></ha-icon></span>`;
    }

    /** Each after a space, so a screen reader doesn't read a badge into the name. */
    private badges(sighting: Sighting, notable: boolean): TemplateResult {
        const badges = [
            notable ? html`<span class="badge notable">${this.text("row.notable")}</span>` : undefined,
            sighting.reviewed === false ? html`<span class="badge unreviewed">${this.text("row.unreviewed")}</span>` : undefined,
            threatened(sighting) ? html`<span class="badge threatened">${sighting.iucn_status}</span>` : undefined,
        ];
        return html`${badges.filter(Boolean).map((badge) => html` ${badge}`)}`;
    }

    private amount(count: number | null): string {
        if (count === null) {
            return this.text("row.present");
        }
        return this.text(count === 1 ? "row.count_one" : "row.count_other").replace("{count}", formatNumber(count, this.numberFormat()));
    }

    /**
     * The day and the time. eBird's times are the area's own and the card knows no zone for the area, so it never says
     * today or yesterday, which would be the viewer's.
     */
    private when(observed: string): string {
        const language = this.language();
        return [formatDay(observed, language, localToday()), formatClock(observed, language)].filter(Boolean).join(" ");
    }

    private detail(sighting: Sighting): TemplateResult {
        const reports = sighting.reports;
        return html`
            <div class="detail">
                ${
                    sighting.picture
                        ? html`<img class="picture" src=${sighting.picture} alt=${sighting.name} />
                              ${sighting.picture_credit ? html`<div class="credit">${sighting.picture_credit}</div>` : nothing}`
                        : html`<div class="credit">${this.text("row.no_picture")}</div>`
                }
                <div class="links">
                    ${
                        reports
                            ? html`<span
                                  >${this.text(reports === 1 ? "row.reports_one" : "row.reports_other").replace(
                                      "{count}",
                                      formatNumber(reports, this.numberFormat()),
                                  )}</span
                              >`
                            : nothing
                    }
                    <a href=${sighting.url} target="_blank" rel="noopener noreferrer">${this.text("row.ebird")}</a>
                </div>
            </div>
        `;
    }

    private yearList(species: YearSpecies[], pictures: Map<string, Sighting>): TemplateResult {
        const language = this.language();
        const today = localToday();
        return html`${yearDays(species).map(
            (day) => html`
                <div class="day">
                    <span>${day.day ? formatDay(day.day, language, today) : this.text("year.before_installation")}</span>
                    <span class="day-count"
                        >${this.text(day.species.length === 1 ? "year.species_one" : "year.species_other").replace(
                            "{count}",
                            formatNumber(day.species.length, this.numberFormat()),
                        )}</span
                    >
                </div>
                ${day.species.map(
                    (item) => html`
                        <div class="row year">
                            ${this.thumbnail(pictures.get(item.species_code)?.picture)}
                            <span class="main">
                                <span class="name">${item.name}</span>
                                ${
                                    item.last_year
                                        ? html`<span class="place"
                                              >${this.text("year.last_year").replace("{date}", formatDay(item.last_year, language, today))}</span
                                          >`
                                        : nothing
                                }
                            </span>
                        </div>
                    `,
                )}
            `,
        )}`;
    }

    private areaName(): string {
        const device = this.hass?.devices?.[this.config?.device ?? ""];
        return device?.name_by_user || device?.name || "";
    }

    private heightStyle(): string {
        return heightStyle(this.config ?? {}, this.layout, this.minimumHeight());
    }

    /** The lowest the card is held to, in pixels: its header, the tabs and one row of the list. */
    private minimumHeight(): number {
        return HEADER_HEIGHT + TABS_HEIGHT + ROW_HEIGHT;
    }

    private numberFormat(): NumberFormat {
        return { language: this.language(), number_format: this.hass?.locale?.number_format };
    }

    private text(key: string): string {
        return translate(this.language(), key);
    }

    private language(): string {
        return this.hass?.locale?.language ?? this.hass?.language ?? browserLanguage();
    }

    /** The language the card's texts are in: the viewer's when the card has it, otherwise English, which it falls back to. */
    private textLanguage(): string {
        const code = this.language().split(/[-_]/)[0].toLowerCase();
        return LANGUAGE_CODES.includes(code) ? code : "en";
    }

    static get styles(): CSSResultGroup {
        return [
            css`
                ha-card {
                    container-type: inline-size;
                    overflow: hidden;
                    font-variant-numeric: tabular-nums;
                }

                ha-card.held {
                    display: flex;
                    flex-direction: column;
                }

                ha-card.held > * {
                    flex: none;
                }

                ha-card.held > .scroll {
                    flex: 1 1 auto;
                    min-height: 0;
                    overflow-y: auto;
                    overscroll-behavior: contain;
                    scrollbar-width: thin;
                }

                ha-card.message {
                    padding: 16px;
                    color: var(--secondary-text-color);
                }

                button {
                    padding: 0;
                    border: none;
                    background: none;
                    color: inherit;
                    font: inherit;
                    text-align: inherit;
                    cursor: pointer;
                }

                .header {
                    display: flex;
                    flex-wrap: wrap;
                    align-items: baseline;
                    justify-content: space-between;
                    gap: 0 12px;
                    padding: 12px 16px 4px;
                }

                .title {
                    font-size: var(--ha-font-size-l, 18px);
                    overflow-wrap: anywhere;
                }

                .area {
                    color: var(--secondary-text-color);
                    font-size: var(--ha-font-size-s, 12px);
                    overflow-wrap: anywhere;
                }

                .tabs {
                    display: grid;
                    grid-template-columns: repeat(3, minmax(0, 1fr));
                    gap: 8px;
                    padding: 8px 16px 12px;
                }

                .tab {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 2px;
                    padding: 8px 4px;
                    border-radius: var(--ha-card-border-radius, 12px);
                    background: rgba(var(--rgb-primary-text-color, 33, 33, 33), 0.06);
                    text-align: center;
                }

                /* The chosen tab is shaded, so the focus ring below stays a ring of its own. */
                .tab.on {
                    background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.2);
                    box-shadow: inset 0 -2px 0 var(--primary-color);
                }

                /* Inside the edges, as the list scrolls and the card clips: an outer ring would lose its sides. */
                button:focus-visible {
                    outline: 2px solid var(--primary-color);
                    outline-offset: -2px;
                }

                .tab .count {
                    font-size: 24px;
                    line-height: 1.2;
                }

                .tab.notable .count {
                    color: var(--warning-color, #ffa600);
                }

                /* A word is hyphenated where the browser can, and broken only when nothing else fits. */
                .tab .label {
                    color: var(--secondary-text-color);
                    font-size: var(--ha-font-size-s, 12px);
                    hyphens: auto;
                    overflow-wrap: break-word;
                    max-width: 100%;
                }

                /* Narrower, the tabs are rows of their own, as "Huomionarvoiset" would no longer fit a third of the width. */
                @container (max-width: 359px) {
                    .tabs {
                        grid-template-columns: minmax(0, 1fr);
                        gap: 4px;
                    }

                    .tab {
                        flex-direction: row;
                        align-items: baseline;
                        gap: 8px;
                        padding: 4px 12px;
                        text-align: left;
                    }

                    .tab .count {
                        min-width: 2.5em;
                        font-size: 18px;
                    }
                }

                .scroll {
                    border-top: 1px solid var(--divider-color);
                }

                .row {
                    box-sizing: border-box;
                    display: grid;
                    grid-template-columns: auto minmax(0, 1fr) auto;
                    align-items: center;
                    gap: 0 12px;
                    width: 100%;
                    padding: 8px 16px;
                    border-bottom: 1px solid var(--divider-color);
                }

                button.row:hover {
                    background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.08);
                }

                .opened > .row {
                    border-bottom: none;
                }

                .thumbnail {
                    flex: none;
                    width: 48px;
                    height: 48px;
                    border-radius: 4px;
                    object-fit: cover;
                    background: rgba(var(--rgb-primary-text-color, 33, 33, 33), 0.08);
                }

                .thumbnail.none {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: var(--state-icon-color);
                }

                .main {
                    display: flex;
                    flex-direction: column;
                    min-width: 0;
                }

                .name {
                    font-weight: var(--ha-font-weight-medium, 500);
                    overflow-wrap: anywhere;
                }

                .name::first-letter {
                    text-transform: uppercase;
                }

                .scientific {
                    color: var(--secondary-text-color);
                    font-size: var(--ha-font-size-s, 12px);
                    font-style: italic;
                    overflow-wrap: anywhere;
                }

                .place {
                    color: var(--secondary-text-color);
                    font-size: var(--ha-font-size-s, 12px);
                    overflow-wrap: anywhere;
                }

                .side {
                    display: flex;
                    flex-direction: column;
                    align-items: flex-end;
                    max-width: 9em;
                    text-align: right;
                    color: var(--secondary-text-color);
                    font-size: var(--ha-font-size-s, 12px);
                }

                .amount {
                    color: var(--primary-text-color);
                    font-size: var(--ha-font-size-m, 14px);
                }

                .badge {
                    display: inline-block;
                    margin-left: 2px;
                    padding: 0 6px;
                    border-radius: 8px;
                    font-size: 11px;
                    font-weight: var(--ha-font-weight-normal, 400);
                    vertical-align: 1px;
                }

                .badge.notable {
                    background: var(--warning-color, #ffa600);
                    color: var(--primary-background-color, #fff);
                }

                .badge.unreviewed {
                    border: 1px solid var(--secondary-text-color);
                    color: var(--secondary-text-color);
                }

                .badge.threatened {
                    background: var(--error-color, #db4437);
                    color: var(--primary-background-color, #fff);
                }

                .detail {
                    padding: 0 16px 12px;
                    border-bottom: 1px solid var(--divider-color);
                }

                .picture {
                    display: block;
                    width: 100%;
                    max-height: 260px;
                    object-fit: cover;
                    border-radius: 4px;
                }

                .credit {
                    margin-top: 4px;
                    color: var(--secondary-text-color);
                    font-size: 11px;
                    overflow-wrap: anywhere;
                }

                .links {
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: space-between;
                    gap: 4px 12px;
                    margin-top: 6px;
                    color: var(--secondary-text-color);
                    font-size: var(--ha-font-size-s, 12px);
                }

                .links a {
                    color: var(--primary-color);
                }

                .day {
                    display: flex;
                    justify-content: space-between;
                    gap: 12px;
                    padding: 10px 16px 4px;
                    color: var(--secondary-text-color);
                    font-size: var(--ha-font-size-s, 12px);
                    font-weight: var(--ha-font-weight-medium, 500);
                }

                .row.year {
                    padding-top: 6px;
                    padding-bottom: 6px;
                }

                .row.year .thumbnail {
                    width: 36px;
                    height: 36px;
                }

                .empty {
                    padding: 16px;
                    color: var(--secondary-text-color);
                }

                /* On a narrow card the count and time go under the place, so the name keeps its room. */
                @container (max-width: 299px) {
                    .row {
                        grid-template-columns: auto minmax(0, 1fr);
                        align-items: start;
                    }

                    .side {
                        grid-column: 2;
                        flex-direction: row;
                        flex-wrap: wrap;
                        gap: 0 8px;
                        align-items: baseline;
                        max-width: none;
                        text-align: left;
                    }
                }
            `,
            fadeStyles,
        ];
    }
}

// The card registers itself once, also if a copy installed some other way is loaded too.
if (!customElements.get("birds-nearby-card")) {
    console.info(
        `%c  BIRDS-NEARBY-CARD \n%c  ${CARD_VERSION}    `,
        "color: orange; font-weight: bold; background: black",
        "color: white; font-weight: bold; background: dimgray",
    );

    const registry = window as unknown as { customCards?: CardRegistration[] };
    registry.customCards = registry.customCards ?? [];
    registry.customCards.push({
        type: "birds-nearby-card",
        name: translate(browserLanguage(), "common.name"),
        description: translate(browserLanguage(), "common.description"),
        documentationURL: "https://github.com/jesmak/birds_nearby#birds-nearby-card",
        preview: true,
    });
    customElements.define("birds-nearby-card", BirdsNearbyCard);
}

declare global {
    interface HTMLElementTagNameMap {
        "birds-nearby-card": BirdsNearbyCard;
    }
}
