/** The card's visual editor: the area, the title and the height. */
import { LitElement, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { property, state } from "lit/decorators.js";

import { PLATFORM } from "./const";
import type { HomeAssistant } from "./hass";
import { heightData, heightSchema, tidyHeight } from "./height";
import { browserLanguage, translate } from "./localize/localize";
import type { BirdsNearbyCardConfig } from "./types";

interface SchemaEntry {
    name: string;
}

function schema(config: BirdsNearbyCardConfig, text: (key: string) => string) {
    return [
        { name: "device", required: true, selector: { device: { filter: { integration: PLATFORM } } } },
        { name: "title", selector: { text: {} } },
        ...heightSchema(config, text),
    ];
}

export class BirdsNearbyCardEditor extends LitElement {
    @property({ attribute: false }) public hass?: HomeAssistant;
    @state() private config?: BirdsNearbyCardConfig;

    public setConfig(config: BirdsNearbyCardConfig): void {
        this.config = config;
    }

    protected render(): TemplateResult | typeof nothing {
        if (!this.hass || !this.config) {
            return nothing;
        }
        return html`
            <ha-form
                .hass=${this.hass}
                .data=${heightData(this.config)}
                .schema=${schema(this.config, (key) => this.text(key))}
                .computeLabel=${(entry: SchemaEntry) => this.text(`editor.${entry.name}`)}
                .computeHelper=${(entry: SchemaEntry) => this.helper(entry.name)}
                @value-changed=${this.valueChanged}
            ></ha-form>
        `;
    }

    private valueChanged(event: CustomEvent<{ value: BirdsNearbyCardConfig }>): void {
        const config: BirdsNearbyCardConfig = tidyHeight(event.detail.value);
        if (!config.title) {
            delete config.title;
        }
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }));
    }

    private text(key: string): string {
        return translate(this.language(), key);
    }

    private helper(name: string): string | undefined {
        const key = `editor.${name}_helper`;
        const helper = translate(this.language(), key);
        return helper === key ? undefined : helper;
    }

    private language(): string {
        return this.hass?.locale?.language ?? this.hass?.language ?? browserLanguage();
    }
}

if (!customElements.get("birds-nearby-card-editor")) {
    customElements.define("birds-nearby-card-editor", BirdsNearbyCardEditor);
}

declare global {
    interface HTMLElementTagNameMap {
        "birds-nearby-card-editor": BirdsNearbyCardEditor;
    }
}
