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
import { fillLimit, filledHeight, filledStyle, validRowStep } from "./rows";
import {
    areaDevices,
    areaSensors,
    countOf,
    formatClock,
    formatDay,
    formatNumber,
    listOf,
    localToday,
    placeOf,
    threatened,
    yearSpecies,
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

/** The card's padding and border, top and bottom, so that its parts, each on the half-row step of 32 px, end on the rows. */
const PADDING = 24;
/** Half a row of a sections view: the header, a tab one to a row, a day and a species of the year list. */
const STEP = 32;

/** A tab's room for its count and label: the tabs' side padding and the gaps between three of them, then a tab's own padding. */
const TABS_SIDES = 2 * 16 + 2 * 8;
const TAB_PADDING = 2 * 4;
/** A row's room beside its texts: its side padding, the picture and the gaps on either side of the texts. */
const ROW_SIDES = 2 * 8 + 48 + 2 * 12;
/**
 * Room for a measure read in fractions of a pixel, so a text exactly as wide as its room still fits, and a content
 * unscaled with floating-point noise counts as the whole pixels it is. Smaller than the 1/64 px a browser lays out in.
 */
const SLACK_PX = 0.01;

/** Whether the tabs fit side by side, each count and label whole on one line: `needs` are their widths, `width` the tabs'. */
export function tabsFit(width: number, needs: number[]): boolean {
    const room = (width - TABS_SIDES) / 3 - TAB_PADDING;
    return needs.every((need) => need <= room + SLACK_PX);
}

/** Whether a sighting's count and time fit beside its name, scientific name and place, each whole on one line. */
export function sideFits(width: number, texts: number, side: number): boolean {
    return ROW_SIDES + texts + side <= width + SLACK_PX;
}

/** The width of an element's text laid out as it is, whole however narrow its box, as a range measures its glyphs. */
function textWidth(element: Element | null): number {
    if (!element) {
        return 0;
    }
    const range = document.createRange();
    range.selectNodeContents(element);
    return range.getBoundingClientRect().width;
}

/**
 * How much the card is drawn scaled, 1 unless something scales it, such as a dialog's opening animation (0.8 to 1).
 * Drawn widths and a range's are scaled while the card's padding and the constants above are not, so drawn measures
 * are divided by it. A scale doesn't resize the card, so no ResizeObserver would correct a measure made mid-scale.
 */
function drawnScale(card: HTMLElement): number {
    const layout = px(getComputedStyle(card).width);
    const drawn = card.getBoundingClientRect().width;
    return layout > 0 && drawn > 0 ? drawn / layout : 1;
}

function px(value: string): number {
    return Number.parseFloat(value) || 0;
}

export class BirdsNearbyCard extends LitElement {
    @property({ attribute: false }) public hass?: HomeAssistant;
    /** "grid" in a sections view, as Home Assistant sets it. */
    @property({ attribute: false }) public layout?: string;
    @state() private config?: BirdsNearbyCardConfig;
    /** The tab chosen by hand. Until then the card opens on the notable sightings when there are any. */
    @state() private tab?: SensorKey;
    /** The opened sighting, as its tab and species. */
    @state() private open?: string;
    /** As last measured: whether the tabs are one to a row, and the sightings whose count and time are under their texts. */
    @state() private tabsSplit = false;
    @state() private splitRows: ReadonlySet<string> = new Set();
    /** The height that fills the card's rows on automatic rows, and the room in it the content leaves over. */
    @state() private filled = 0;
    @state() private spare = 0;
    /** The viewer's day at the last redraw: a date of an earlier year is written with its year from New Year on. */
    private drawnOn?: string;
    private frame?: number;
    private readonly resizes = typeof ResizeObserver === "undefined" ? undefined : new ResizeObserver(() => this.measureSoon());

    constructor() {
        super();
        // Fades the list's edges while the card is held to a height, through the card's own lifecycle.
        new ScrollFade(this, () => (this.heightStyle() ? this.renderRoot.querySelectorAll<HTMLElement>("ha-card > .scroll") : []));
    }

    public connectedCallback(): void {
        super.connectedCallback();
        // Back on the page, the card is observed and measured again, as it was let go when it left.
        if (this.hasUpdated) {
            this.requestUpdate();
        }
    }

    public disconnectedCallback(): void {
        super.disconnectedCallback();
        this.resizes?.disconnect();
        cancelAnimationFrame(this.frame ?? 0);
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
        if (!validRowStep(config)) {
            throw new Error(translate(browserLanguage(), "common.invalid_row_step"));
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

    /**
     * In a sections view the card takes a whole section by default and is never narrower than three quarters of one, as
     * on a phone's half a section a species' name would have room for a syllable or two beside its picture.
     */
    public getGridOptions(): Record<string, unknown> {
        return { columns: 12, min_columns: 9, rows: "auto", min_rows: gridMinRows(this.minimumHeight()) };
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
            // A part of its own, so the card fills whole rows with it too, the room left over above it.
            return html`<ha-card class=${this.heightStyle() ? "held" : ""} style=${this.cardStyle()} lang=${this.textLanguage()}>
                <div class="message">${this.text("common.no_area")}</div>
            </ha-card>`;
        }
        const notable = listOf<Sighting>(this.hass, sensors.notable, "sightings");
        const recent = listOf<Sighting>(this.hass, sensors.recent, "species");
        const tab = this.tab ?? ((countOf(this.hass, sensors.notable) ?? 0) > 0 ? "notable" : "recent");
        const title = this.config.title || this.text("common.title");
        const area = this.areaName();
        return html`
            <ha-card class=${this.heightStyle() ? "held" : ""} style=${this.cardStyle()} lang=${this.textLanguage()}>
                <div class="header">
                    <span class="title" title=${title}>${title}</span>
                    <span class="area" title=${area}>${area}</span>
                </div>
                <div class="tabs ${this.tabsSplit ? "split" : ""}" role="tablist">
                    ${SENSORS.map((key) => this.tabButton(this.hass!, key, sensors[key], tab))}
                </div>
                <div class="scroll" role="tabpanel">${this.list(this.hass, tab, sensors, notable, recent)}</div>
            </ha-card>
        `;
    }

    protected updated(): void {
        const card = this.renderRoot.querySelector<HTMLElement>("ha-card");
        if (card && this.isConnected) {
            this.resizes?.observe(card);
            this.measureSoon();
        }
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
                <span class="label" title=${this.text(`tabs.${key}`)}>${this.text(`tabs.${key}`)}</span>
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
            return species.length ? this.yearList(species) : this.empty(this.text("empty.year_list"));
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
        const place = placeOf(sighting, this.numberFormat());
        const amount = this.amount(sighting.count);
        const when = this.when(sighting.observed);
        return html`
            <div class="sighting ${opened ? "opened" : ""}">
                <button
                    class="row ${this.splitRows.has(key) ? "split" : ""}"
                    data-key=${key}
                    aria-expanded=${opened ? "true" : "false"}
                    @click=${() => (this.open = opened ? undefined : key)}
                >
                    ${this.thumbnail(sighting.picture)}
                    <span class="main">
                        <span class="name" title=${sighting.name}>${sighting.name}${this.badges(sighting, notable)}</span>
                        <span class="scientific" title=${sighting.scientific_name}>${sighting.scientific_name}</span>
                        <span class="place" title=${place}>${place}</span>
                    </span>
                    <span class="side">
                        <span class="amount" title=${amount}>${amount}</span>
                        <span class="when" title=${when}>${when}</span>
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

    /** A species' picture at full width with its credit, and its page on eBird, for a sighting or a species of the year list. */
    private detail(sighting: Pick<Sighting, "name" | "url" | "picture" | "picture_credit" | "reports">): TemplateResult {
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

    /** The species as the sightings are, the day each was first seen beside it, and those seen before installation apart. */
    private yearList(species: YearSpecies[]): TemplateResult {
        const { dated, before } = yearSpecies(species);
        const count = this.text(before.length === 1 ? "year.species_one" : "year.species_other").replace(
            "{count}",
            formatNumber(before.length, this.numberFormat()),
        );
        const heading = `${this.text("year.before_installation")} · ${count}`;
        return html`
            ${dated.map((item) => this.yearRow(item))}
            ${before.length ? html`<div class="before" title=${heading}>${heading}</div>` : nothing}
            ${before.map((item) => this.yearRow(item))}
        `;
    }

    private yearRow(item: YearSpecies): TemplateResult {
        const language = this.language();
        const today = localToday();
        const key = `year_list:${item.species_code}`;
        const lastYear = item.last_year ? this.text("year.last_year").replace("{date}", formatDay(item.last_year, language, today)) : "";
        const first = item.first_seen ? formatDay(item.first_seen, language, today) : "";
        const opened = this.open === key;
        return html`
            <div class="sighting ${opened ? "opened" : ""}">
                <button
                    class="row year ${this.splitRows.has(key) ? "split" : ""}"
                    data-key=${key}
                    aria-expanded=${opened ? "true" : "false"}
                    @click=${() => (this.open = opened ? undefined : key)}
                >
                    ${this.thumbnail(item.picture)}
                    <span class="main">
                        <span class="name" title=${item.name}>${item.name}</span>
                        ${item.scientific_name ? html`<span class="scientific" title=${item.scientific_name}>${item.scientific_name}</span>` : nothing}
                        ${lastYear ? html`<span class="place" title=${lastYear}>${lastYear}</span>` : nothing}
                    </span>
                    ${
                        first
                            ? html`<span class="side">
                                  <span class="amount" title=${first}>${first}</span>
                                  <span class="when" title=${this.text("year.first")}>${this.text("year.first")}</span>
                              </span>`
                            : nothing
                    }
                </button>
                ${opened ? this.detail({ ...item, url: `https://ebird.org/species/${item.species_code}` }) : nothing}
            </div>
        `;
    }

    private areaName(): string {
        const device = this.hass?.devices?.[this.config?.device ?? ""];
        return device?.name_by_user || device?.name || "";
    }

    private heightStyle(): string {
        return heightStyle(this.config ?? {}, this.layout, this.minimumHeight());
    }

    /**
     * The lowest the card is held to, in pixels: its header, the tabs one to a row and a sighting with its count and time
     * under its texts, as on the narrowest card either may be split. Four rows.
     */
    private minimumHeight(): number {
        return PADDING + STEP + 3 * STEP + 3 * STEP;
    }

    /** The card's inline style: the height it is held to, or the rows it fills up to any limit, with their spare room. */
    private cardStyle(): string {
        const style = filledStyle(this.config ?? {}, this.layout, this.minimumHeight(), this.filled);
        return this.filled ? `${style}; --spare: ${this.spare}px` : style;
    }

    private measureSoon(): void {
        cancelAnimationFrame(this.frame ?? 0);
        this.frame = requestAnimationFrame(() => this.measure());
    }

    private measure(): void {
        const card = this.renderRoot.querySelector<HTMLElement>("ha-card");
        if (!card || !card.clientWidth) {
            return;
        }
        const scale = drawnScale(card);
        this.measureSplits(card, scale);
        this.fillRows(card, scale);
    }

    /**
     * Splits only what doesn't fit: the tabs go one to a row when a count or a label wouldn't fit its third whole, and a
     * sighting's count and time go under its texts when they wouldn't fit beside them, each text whole on one line.
     * Wrapped texts are measured on one line, each row held to its drawn height meanwhile, so nothing moves. The room is
     * each part's drawn width in fractions of a pixel, as clientWidth's whole pixels can promise more room than there is,
     * and every drawn width is unscaled to compare with the layout's pixels.
     */
    private measureSplits(card: HTMLElement, scale: number): void {
        const width = (element: Element | null) => textWidth(element) / scale;
        const tabs = card.querySelector<HTMLElement>(".tabs");
        if (tabs) {
            const needs = [...tabs.querySelectorAll(".tab")].map((tab) =>
                Math.max(width(tab.querySelector(".count")), width(tab.querySelector(".label"))),
            );
            const split = !tabsFit(tabs.getBoundingClientRect().width / scale, needs);
            if (split !== this.tabsSplit) {
                this.tabsSplit = split;
            }
        }
        const rows = [...card.querySelectorAll<HTMLElement>(".row[data-key]")];
        const heights = rows.map((row) => getComputedStyle(row).height);
        rows.forEach((row, index) => (row.style.height = heights[index]));
        card.classList.add("measuring");
        const split = new Set<string>();
        for (const row of rows) {
            const texts = Math.max(0, ...[...row.querySelectorAll(".main > *")].map(width));
            const side = Math.max(0, ...[...row.querySelectorAll(".side > *")].map(width));
            if (!sideFits(row.getBoundingClientRect().width / scale, texts, side) && row.dataset.key) {
                split.add(row.dataset.key);
            }
        }
        card.classList.remove("measuring");
        rows.forEach((row) => (row.style.height = ""));
        // Only the rows drawn now are measured: a row of another tab keeps its last split until it is drawn again.
        const drawn = new Set(rows.map((row) => row.dataset.key));
        const kept = [...this.splitRows].filter((key) => !drawn.has(key));
        const next = new Set([...kept, ...split]);
        if (next.size !== this.splitRows.size || [...next].some((key) => !this.splitRows.has(key))) {
            this.splitRows = next;
        }
    }

    /**
     * In a sections view whose rows are left automatic, the card takes the whole rows its content needs, or the half rows
     * with `row_step: half`, so the cards under it stay on the rows, up to the limit of a card that grows up to one. The
     * room left over goes under the header, or above
     * the message when the area isn't found.
     */
    private fillRows(card: HTMLElement, scale: number): void {
        const limit = fillLimit(this.config ?? {}, this.layout, this.minimumHeight());
        if (!limit) {
            this.filled = 0;
            this.spare = 0;
            return;
        }
        // From the card's top to the end of its own last part, never its own height, which is the min-height set here, and
        // never an element a theme adds to it.
        const parts = card.querySelectorAll<HTMLElement>(":scope > .header, :scope > .tabs, :scope > .scroll > *, :scope > .message");
        const last = parts[parts.length - 1];
        if (!last) {
            return;
        }
        const style = getComputedStyle(card);
        // The drawn distance unscaled, as the padding and border added to it are the layout's.
        const drawn = (last.getBoundingClientRect().bottom - card.getBoundingClientRect().top) / scale;
        let content = drawn + px(style.paddingBottom) + px(style.borderBottomWidth);
        // The spare room as drawn now: under the header, or above the message.
        const header = card.querySelector<HTMLElement>(":scope > .header");
        const message = card.querySelector<HTMLElement>(":scope > .message");
        if (header) {
            content -= px(getComputedStyle(header).paddingBottom);
        } else if (message) {
            content -= px(getComputedStyle(message).paddingTop);
        }
        // Up to the whole pixel, so a content a fraction over, such as 120.4, still ends inside the rows. The slack keeps
        // noise from unscaling mid-scale (48 drawn at 0.8 unscales to 48.00000000000001) from costing a pixel either way.
        const filled = filledHeight(Math.ceil(content - SLACK_PX), this.config ?? {}, limit);
        const spare = Math.max(0, Math.floor(filled - content + SLACK_PX));
        if (filled !== this.filled || spare !== this.spare) {
            this.filled = filled;
            this.spare = spare;
        }
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
                /* 11 px of padding and the border, top and bottom, make 24 px, so the parts on the 32 px step end on the rows. */
                ha-card {
                    container-type: inline-size;
                    box-sizing: border-box;
                    overflow: hidden;
                    padding: 11px 0;
                    font-variant-numeric: tabular-nums;
                }

                ha-card.held {
                    display: flex;
                    flex-direction: column;
                }

                ha-card.held > * {
                    flex: none;
                }

                /* The list is inset from the card's edges, its rows rounded, so a scrollbar has a margin of its own. */
                .scroll {
                    margin: 0 8px;
                }

                /* Held, the list keeps the scrollbar's room whether it scrolls or not, as room that came with the scrolling
                would put a sighting's count and time under its texts, and keep the card scrolling. The same room on the
                left keeps the rows in the middle, and the scrollbar is 4 px from the card's edge. */
                ha-card.held > .scroll {
                    flex: 1 1 auto;
                    min-height: 0;
                    margin: 0 4px;
                    overflow-y: auto;
                    scrollbar-width: thin;
                    scrollbar-gutter: stable both-edges;
                }

                /* Each line half a row, and the room a whole row leaves over above it. */
                .message {
                    padding: var(--spare, 0px) 16px 0;
                    line-height: 32px;
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

                /* Each line of the header is half a row, and the room a whole row leaves over goes under it. Padding, not a
                margin, which would collapse into a neighbour's. */
                .header {
                    display: flex;
                    flex-wrap: wrap;
                    align-items: flex-start;
                    justify-content: space-between;
                    column-gap: 12px;
                    padding: 0 16px var(--spare, 0px);
                    line-height: 32px;
                }

                .title {
                    min-width: 0;
                    font-size: var(--ha-font-size-l, 18px);
                    overflow-wrap: anywhere;
                }

                /* On the title's baseline, moved there rather than aligned by it: two sizes on one baseline would make the
                header a pixel taller than its half row. */
                .area {
                    position: relative;
                    top: 2px;
                    min-width: 0;
                    color: var(--secondary-text-color);
                    font-size: var(--ha-font-size-s, 12px);
                    overflow-wrap: anywhere;
                }

                /* Held to a height, the header keeps to one line, its texts cut short with their whole text as a tooltip. */
                ha-card.held .header {
                    flex-wrap: nowrap;
                }

                ha-card.held .title,
                ha-card.held .area {
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }

                /* Side by side the tabs are a row: a 56 px tile, 7 px and the line under them. One to a row, each is half a row. */
                .tabs {
                    display: grid;
                    grid-template-columns: repeat(3, minmax(0, 1fr));
                    gap: 8px;
                    padding: 0 16px 7px;
                    border-bottom: 1px solid var(--divider-color);
                }

                .tab {
                    box-sizing: border-box;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 56px;
                    padding: 0 4px;
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

                /* The count is the same size side by side and one to a row, so it measures the same either way. */
                .tab .count {
                    font-size: 22px;
                    line-height: 28px;
                }

                .tab.notable .count {
                    color: var(--warning-color, #ffa600);
                }

                /* Whole on one line: the tabs go one to a row before a label is cut, and only a card narrower than its least is. */
                .tab .label {
                    max-width: 100%;
                    color: var(--secondary-text-color);
                    font-size: var(--ha-font-size-s, 12px);
                    line-height: 16px;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }

                /* One to a row when a count or a label wouldn't fit its third, as measured: 24 px each and 8 px under it. */
                .tabs.split {
                    grid-template-columns: minmax(0, 1fr);
                }

                .tabs.split .tab {
                    flex-direction: row;
                    align-items: baseline;
                    justify-content: flex-start;
                    gap: 8px;
                    height: 24px;
                    padding: 0 12px;
                    text-align: start;
                }

                .tabs.split .tab .count {
                    min-width: 2.5em;
                    line-height: 24px;
                }

                .tabs.split .tab .label {
                    line-height: 24px;
                }

                /* A line between the rows that takes no room of its own, so each row stays on the step, inset to the texts. */
                .row,
                .detail {
                    background: linear-gradient(var(--divider-color), var(--divider-color)) center bottom / calc(100% - 16px) 1px no-repeat;
                }

                .row {
                    box-sizing: border-box;
                    display: grid;
                    grid-template-columns: auto minmax(0, 1fr) auto;
                    align-items: center;
                    gap: 0 12px;
                    width: 100%;
                    min-height: 64px;
                    padding: 6px 8px;
                    border-radius: 8px;
                }

                button.row:hover {
                    background-color: rgba(var(--rgb-primary-color, 3, 169, 244), 0.08);
                }

                .opened > .row {
                    background-image: none;
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

                /* A sighting's three lines and its padding make a row. */
                .name {
                    font-weight: var(--ha-font-weight-medium, 500);
                    line-height: 20px;
                    overflow-wrap: anywhere;
                }

                .name::first-letter {
                    text-transform: uppercase;
                }

                .scientific {
                    color: var(--secondary-text-color);
                    font-size: var(--ha-font-size-s, 12px);
                    font-style: italic;
                    line-height: 16px;
                    overflow-wrap: anywhere;
                }

                .place {
                    color: var(--secondary-text-color);
                    font-size: var(--ha-font-size-s, 12px);
                    line-height: 16px;
                    overflow-wrap: anywhere;
                }

                /* Beside the texts only while it fits whole, as measured, so it never wraps there. */
                .side {
                    display: flex;
                    flex-direction: column;
                    align-items: flex-end;
                    text-align: end;
                    white-space: nowrap;
                    color: var(--secondary-text-color);
                    font-size: var(--ha-font-size-s, 12px);
                    line-height: 16px;
                }

                .amount {
                    color: var(--primary-text-color);
                    font-size: var(--ha-font-size-m, 14px);
                    line-height: 20px;
                }

                /* Under the texts when it wouldn't fit beside them, as measured: three half rows, unless a text wraps unheld. */
                .row.split {
                    grid-template-columns: auto minmax(0, 1fr);
                    align-items: start;
                    min-height: 96px;
                }

                .row.split .side {
                    grid-column: 2;
                    flex-direction: row;
                    flex-wrap: wrap;
                    align-items: baseline;
                    gap: 0 8px;
                    text-align: start;
                    white-space: normal;
                }

                /* Held, the count and time under the texts share one line too, so a split row is always its three half rows. */
                ha-card.held .row.split .side {
                    flex-wrap: nowrap;
                    min-width: 0;
                }

                ha-card.held .row.split .side > * {
                    min-width: 0;
                }

                /* Held to a height, a sighting's texts keep to one line, cut short with their whole text as a tooltip. */
                ha-card.held .row .main > *,
                ha-card.held .row .side > *,
                ha-card.held .before {
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }

                /* While measuring, each text is laid out on one line, whole, as it would be with room enough. */
                ha-card.measuring .row .main > *,
                ha-card.measuring .row .side > * {
                    white-space: nowrap;
                }

                /* At the top of the name's line, 16 px in its 20, so a badge never makes the line, and the row, taller. */
                /* The capitals centred in the badge, their baseline on a whole pixel, 12 px down its 16. */
                .badge {
                    display: inline-block;
                    box-sizing: border-box;
                    height: 16px;
                    margin-top: 2px;
                    margin-left: 2px;
                    padding: calc(12px - 1cap) 6px 0;
                    text-box: trim-both cap alphabetic;
                    border-radius: 8px;
                    font-size: 11px;
                    font-weight: var(--ha-font-weight-normal, 400);
                    line-height: 16px;
                    vertical-align: top;
                }

                .badge.notable {
                    background: var(--warning-color, #ffa600);
                    color: var(--primary-background-color, #fff);
                }

                /* Its border takes a pixel of the padding, so the baseline stays at 12. */
                .badge.unreviewed {
                    padding-top: calc(11px - 1cap);
                    border: 1px solid var(--secondary-text-color);
                    color: var(--secondary-text-color);
                }

                .badge.threatened {
                    background: var(--error-color, #db4437);
                    color: var(--primary-background-color, #fff);
                }

                .detail {
                    padding: 0 8px 12px;
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

                /* Half a row over the species seen before the installation, and a line that wraps adds half a row. */
                .before {
                    padding: 0 8px;
                    line-height: 32px;
                    color: var(--secondary-text-color);
                    font-size: var(--ha-font-size-s, 12px);
                    font-weight: var(--ha-font-weight-medium, 500);
                }

                .empty {
                    padding: 0 8px;
                    line-height: 32px;
                    color: var(--secondary-text-color);
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
