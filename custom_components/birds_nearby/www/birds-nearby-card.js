/*! birds-nearby-card 1.3.0 | MIT License */
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __decorateClass = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc(target, key) : target;
  for (var i5 = decorators.length - 1, decorator; i5 >= 0; i5--)
    if (decorator = decorators[i5])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp(target, key, result);
  return result;
};

// node_modules/@lit/reactive-element/css-tag.js
var t = globalThis;
var e = t.ShadowRoot && (void 0 === t.ShadyCSS || t.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype;
var s = /* @__PURE__ */ Symbol();
var o = /* @__PURE__ */ new WeakMap();
var n = class {
  constructor(t3, e5, o6) {
    if (this._$cssResult$ = true, o6 !== s) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = t3, this.t = e5;
  }
  get styleSheet() {
    let t3 = this.o;
    const s4 = this.t;
    if (e && void 0 === t3) {
      const e5 = void 0 !== s4 && 1 === s4.length;
      e5 && (t3 = o.get(s4)), void 0 === t3 && ((this.o = t3 = new CSSStyleSheet()).replaceSync(this.cssText), e5 && o.set(s4, t3));
    }
    return t3;
  }
  toString() {
    return this.cssText;
  }
};
var r = (t3) => new n("string" == typeof t3 ? t3 : t3 + "", void 0, s);
var i = (t3, ...e5) => {
  const o6 = 1 === t3.length ? t3[0] : e5.reduce((e6, s4, o7) => e6 + ((t4) => {
    if (true === t4._$cssResult$) return t4.cssText;
    if ("number" == typeof t4) return t4;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + t4 + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(s4) + t3[o7 + 1], t3[0]);
  return new n(o6, t3, s);
};
var S = (s4, o6) => {
  if (e) s4.adoptedStyleSheets = o6.map((t3) => t3 instanceof CSSStyleSheet ? t3 : t3.styleSheet);
  else for (const e5 of o6) {
    const o7 = document.createElement("style"), n5 = t.litNonce;
    void 0 !== n5 && o7.setAttribute("nonce", n5), o7.textContent = e5.cssText, s4.appendChild(o7);
  }
};
var c = e ? (t3) => t3 : (t3) => t3 instanceof CSSStyleSheet ? ((t4) => {
  let e5 = "";
  for (const s4 of t4.cssRules) e5 += s4.cssText;
  return r(e5);
})(t3) : t3;

// node_modules/@lit/reactive-element/reactive-element.js
var { is: i2, defineProperty: e2, getOwnPropertyDescriptor: h, getOwnPropertyNames: r2, getOwnPropertySymbols: o2, getPrototypeOf: n2 } = Object;
var a = globalThis;
var c2 = a.trustedTypes;
var l = c2 ? c2.emptyScript : "";
var p = a.reactiveElementPolyfillSupport;
var d = (t3, s4) => t3;
var u = { toAttribute(t3, s4) {
  switch (s4) {
    case Boolean:
      t3 = t3 ? l : null;
      break;
    case Object:
    case Array:
      t3 = null == t3 ? t3 : JSON.stringify(t3);
  }
  return t3;
}, fromAttribute(t3, s4) {
  let i5 = t3;
  switch (s4) {
    case Boolean:
      i5 = null !== t3;
      break;
    case Number:
      i5 = null === t3 ? null : Number(t3);
      break;
    case Object:
    case Array:
      try {
        i5 = JSON.parse(t3);
      } catch (t4) {
        i5 = null;
      }
  }
  return i5;
} };
var f = (t3, s4) => !i2(t3, s4);
var b = { attribute: true, type: String, converter: u, reflect: false, useDefault: false, hasChanged: f };
Symbol.metadata ?? (Symbol.metadata = /* @__PURE__ */ Symbol("metadata")), a.litPropertyMetadata ?? (a.litPropertyMetadata = /* @__PURE__ */ new WeakMap());
var y = class extends HTMLElement {
  static addInitializer(t3) {
    this._$Ei(), (this.l ?? (this.l = [])).push(t3);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(t3, s4 = b) {
    if (s4.state && (s4.attribute = false), this._$Ei(), this.prototype.hasOwnProperty(t3) && ((s4 = Object.create(s4)).wrapped = true), this.elementProperties.set(t3, s4), !s4.noAccessor) {
      const i5 = /* @__PURE__ */ Symbol(), h3 = this.getPropertyDescriptor(t3, i5, s4);
      void 0 !== h3 && e2(this.prototype, t3, h3);
    }
  }
  static getPropertyDescriptor(t3, s4, i5) {
    const { get: e5, set: r6 } = h(this.prototype, t3) ?? { get() {
      return this[s4];
    }, set(t4) {
      this[s4] = t4;
    } };
    return { get: e5, set(s5) {
      const h3 = e5?.call(this);
      r6?.call(this, s5), this.requestUpdate(t3, h3, i5);
    }, configurable: true, enumerable: true };
  }
  static getPropertyOptions(t3) {
    return this.elementProperties.get(t3) ?? b;
  }
  static _$Ei() {
    if (this.hasOwnProperty(d("elementProperties"))) return;
    const t3 = n2(this);
    t3.finalize(), void 0 !== t3.l && (this.l = [...t3.l]), this.elementProperties = new Map(t3.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(d("finalized"))) return;
    if (this.finalized = true, this._$Ei(), this.hasOwnProperty(d("properties"))) {
      const t4 = this.properties, s4 = [...r2(t4), ...o2(t4)];
      for (const i5 of s4) this.createProperty(i5, t4[i5]);
    }
    const t3 = this[Symbol.metadata];
    if (null !== t3) {
      const s4 = litPropertyMetadata.get(t3);
      if (void 0 !== s4) for (const [t4, i5] of s4) this.elementProperties.set(t4, i5);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [t4, s4] of this.elementProperties) {
      const i5 = this._$Eu(t4, s4);
      void 0 !== i5 && this._$Eh.set(i5, t4);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(s4) {
    const i5 = [];
    if (Array.isArray(s4)) {
      const e5 = new Set(s4.flat(1 / 0).reverse());
      for (const s5 of e5) i5.unshift(c(s5));
    } else void 0 !== s4 && i5.push(c(s4));
    return i5;
  }
  static _$Eu(t3, s4) {
    const i5 = s4.attribute;
    return false === i5 ? void 0 : "string" == typeof i5 ? i5 : "string" == typeof t3 ? t3.toLowerCase() : void 0;
  }
  constructor() {
    super(), this._$Ep = void 0, this.isUpdatePending = false, this.hasUpdated = false, this._$Em = null, this._$Ev();
  }
  _$Ev() {
    this._$ES = new Promise((t3) => this.enableUpdating = t3), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), this.constructor.l?.forEach((t3) => t3(this));
  }
  addController(t3) {
    (this._$EO ?? (this._$EO = /* @__PURE__ */ new Set())).add(t3), void 0 !== this.renderRoot && this.isConnected && t3.hostConnected?.();
  }
  removeController(t3) {
    this._$EO?.delete(t3);
  }
  _$E_() {
    const t3 = /* @__PURE__ */ new Map(), s4 = this.constructor.elementProperties;
    for (const i5 of s4.keys()) this.hasOwnProperty(i5) && (t3.set(i5, this[i5]), delete this[i5]);
    t3.size > 0 && (this._$Ep = t3);
  }
  createRenderRoot() {
    const t3 = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return S(t3, this.constructor.elementStyles), t3;
  }
  connectedCallback() {
    this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this.enableUpdating(true), this._$EO?.forEach((t3) => t3.hostConnected?.());
  }
  enableUpdating(t3) {
  }
  disconnectedCallback() {
    this._$EO?.forEach((t3) => t3.hostDisconnected?.());
  }
  attributeChangedCallback(t3, s4, i5) {
    this._$AK(t3, i5);
  }
  _$ET(t3, s4) {
    const i5 = this.constructor.elementProperties.get(t3), e5 = this.constructor._$Eu(t3, i5);
    if (void 0 !== e5 && true === i5.reflect) {
      const h3 = (void 0 !== i5.converter?.toAttribute ? i5.converter : u).toAttribute(s4, i5.type);
      this._$Em = t3, null == h3 ? this.removeAttribute(e5) : this.setAttribute(e5, h3), this._$Em = null;
    }
  }
  _$AK(t3, s4) {
    const i5 = this.constructor, e5 = i5._$Eh.get(t3);
    if (void 0 !== e5 && this._$Em !== e5) {
      const t4 = i5.getPropertyOptions(e5), h3 = "function" == typeof t4.converter ? { fromAttribute: t4.converter } : void 0 !== t4.converter?.fromAttribute ? t4.converter : u;
      this._$Em = e5;
      const r6 = h3.fromAttribute(s4, t4.type);
      this[e5] = r6 ?? this._$Ej?.get(e5) ?? r6, this._$Em = null;
    }
  }
  requestUpdate(t3, s4, i5, e5 = false, h3) {
    if (void 0 !== t3) {
      const r6 = this.constructor;
      if (false === e5 && (h3 = this[t3]), i5 ?? (i5 = r6.getPropertyOptions(t3)), !((i5.hasChanged ?? f)(h3, s4) || i5.useDefault && i5.reflect && h3 === this._$Ej?.get(t3) && !this.hasAttribute(r6._$Eu(t3, i5)))) return;
      this.C(t3, s4, i5);
    }
    false === this.isUpdatePending && (this._$ES = this._$EP());
  }
  C(t3, s4, { useDefault: i5, reflect: e5, wrapped: h3 }, r6) {
    i5 && !(this._$Ej ?? (this._$Ej = /* @__PURE__ */ new Map())).has(t3) && (this._$Ej.set(t3, r6 ?? s4 ?? this[t3]), true !== h3 || void 0 !== r6) || (this._$AL.has(t3) || (this.hasUpdated || i5 || (s4 = void 0), this._$AL.set(t3, s4)), true === e5 && this._$Em !== t3 && (this._$Eq ?? (this._$Eq = /* @__PURE__ */ new Set())).add(t3));
  }
  async _$EP() {
    this.isUpdatePending = true;
    try {
      await this._$ES;
    } catch (t4) {
      Promise.reject(t4);
    }
    const t3 = this.scheduleUpdate();
    return null != t3 && await t3, !this.isUpdatePending;
  }
  scheduleUpdate() {
    return this.performUpdate();
  }
  performUpdate() {
    if (!this.isUpdatePending) return;
    if (!this.hasUpdated) {
      if (this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this._$Ep) {
        for (const [t5, s5] of this._$Ep) this[t5] = s5;
        this._$Ep = void 0;
      }
      const t4 = this.constructor.elementProperties;
      if (t4.size > 0) for (const [s5, i5] of t4) {
        const { wrapped: t5 } = i5, e5 = this[s5];
        true !== t5 || this._$AL.has(s5) || void 0 === e5 || this.C(s5, void 0, i5, e5);
      }
    }
    let t3 = false;
    const s4 = this._$AL;
    try {
      t3 = this.shouldUpdate(s4), t3 ? (this.willUpdate(s4), this._$EO?.forEach((t4) => t4.hostUpdate?.()), this.update(s4)) : this._$EM();
    } catch (s5) {
      throw t3 = false, this._$EM(), s5;
    }
    t3 && this._$AE(s4);
  }
  willUpdate(t3) {
  }
  _$AE(t3) {
    this._$EO?.forEach((t4) => t4.hostUpdated?.()), this.hasUpdated || (this.hasUpdated = true, this.firstUpdated(t3)), this.updated(t3);
  }
  _$EM() {
    this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = false;
  }
  get updateComplete() {
    return this.getUpdateComplete();
  }
  getUpdateComplete() {
    return this._$ES;
  }
  shouldUpdate(t3) {
    return true;
  }
  update(t3) {
    this._$Eq && (this._$Eq = this._$Eq.forEach((t4) => this._$ET(t4, this[t4]))), this._$EM();
  }
  updated(t3) {
  }
  firstUpdated(t3) {
  }
};
y.elementStyles = [], y.shadowRootOptions = { mode: "open" }, y[d("elementProperties")] = /* @__PURE__ */ new Map(), y[d("finalized")] = /* @__PURE__ */ new Map(), p?.({ ReactiveElement: y }), (a.reactiveElementVersions ?? (a.reactiveElementVersions = [])).push("2.1.2");

// node_modules/lit-html/lit-html.js
var t2 = globalThis;
var i3 = (t3) => t3;
var s2 = t2.trustedTypes;
var e3 = s2 ? s2.createPolicy("lit-html", { createHTML: (t3) => t3 }) : void 0;
var h2 = "$lit$";
var o3 = `lit$${Math.random().toFixed(9).slice(2)}$`;
var n3 = "?" + o3;
var r3 = `<${n3}>`;
var l2 = document;
var c3 = () => l2.createComment("");
var a2 = (t3) => null === t3 || "object" != typeof t3 && "function" != typeof t3;
var u2 = Array.isArray;
var d2 = (t3) => u2(t3) || "function" == typeof t3?.[Symbol.iterator];
var f2 = "[ 	\n\f\r]";
var v = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g;
var _ = /-->/g;
var m = />/g;
var p2 = RegExp(`>|${f2}(?:([^\\s"'>=/]+)(${f2}*=${f2}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g");
var g = /'/g;
var $ = /"/g;
var y2 = /^(?:script|style|textarea|title)$/i;
var x = (t3) => (i5, ...s4) => ({ _$litType$: t3, strings: i5, values: s4 });
var b2 = x(1);
var w = x(2);
var T = x(3);
var E = /* @__PURE__ */ Symbol.for("lit-noChange");
var A = /* @__PURE__ */ Symbol.for("lit-nothing");
var C = /* @__PURE__ */ new WeakMap();
var P = l2.createTreeWalker(l2, 129);
function V(t3, i5) {
  if (!u2(t3) || !t3.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return void 0 !== e3 ? e3.createHTML(i5) : i5;
}
var N = (t3, i5) => {
  const s4 = t3.length - 1, e5 = [];
  let n5, l3 = 2 === i5 ? "<svg>" : 3 === i5 ? "<math>" : "", c4 = v;
  for (let i6 = 0; i6 < s4; i6++) {
    const s5 = t3[i6];
    let a3, u3, d3 = -1, f3 = 0;
    for (; f3 < s5.length && (c4.lastIndex = f3, u3 = c4.exec(s5), null !== u3); ) f3 = c4.lastIndex, c4 === v ? "!--" === u3[1] ? c4 = _ : void 0 !== u3[1] ? c4 = m : void 0 !== u3[2] ? (y2.test(u3[2]) && (n5 = RegExp("</" + u3[2], "g")), c4 = p2) : void 0 !== u3[3] && (c4 = p2) : c4 === p2 ? ">" === u3[0] ? (c4 = n5 ?? v, d3 = -1) : void 0 === u3[1] ? d3 = -2 : (d3 = c4.lastIndex - u3[2].length, a3 = u3[1], c4 = void 0 === u3[3] ? p2 : '"' === u3[3] ? $ : g) : c4 === $ || c4 === g ? c4 = p2 : c4 === _ || c4 === m ? c4 = v : (c4 = p2, n5 = void 0);
    const x2 = c4 === p2 && t3[i6 + 1].startsWith("/>") ? " " : "";
    l3 += c4 === v ? s5 + r3 : d3 >= 0 ? (e5.push(a3), s5.slice(0, d3) + h2 + s5.slice(d3) + o3 + x2) : s5 + o3 + (-2 === d3 ? i6 : x2);
  }
  return [V(t3, l3 + (t3[s4] || "<?>") + (2 === i5 ? "</svg>" : 3 === i5 ? "</math>" : "")), e5];
};
var S2 = class _S {
  constructor({ strings: t3, _$litType$: i5 }, e5) {
    let r6;
    this.parts = [];
    let l3 = 0, a3 = 0;
    const u3 = t3.length - 1, d3 = this.parts, [f3, v2] = N(t3, i5);
    if (this.el = _S.createElement(f3, e5), P.currentNode = this.el.content, 2 === i5 || 3 === i5) {
      const t4 = this.el.content.firstChild;
      t4.replaceWith(...t4.childNodes);
    }
    for (; null !== (r6 = P.nextNode()) && d3.length < u3; ) {
      if (1 === r6.nodeType) {
        if (r6.hasAttributes()) for (const t4 of r6.getAttributeNames()) if (t4.endsWith(h2)) {
          const i6 = v2[a3++], s4 = r6.getAttribute(t4).split(o3), e6 = /([.?@])?(.*)/.exec(i6);
          d3.push({ type: 1, index: l3, name: e6[2], strings: s4, ctor: "." === e6[1] ? I : "?" === e6[1] ? L : "@" === e6[1] ? z : H }), r6.removeAttribute(t4);
        } else t4.startsWith(o3) && (d3.push({ type: 6, index: l3 }), r6.removeAttribute(t4));
        if (y2.test(r6.tagName)) {
          const t4 = r6.textContent.split(o3), i6 = t4.length - 1;
          if (i6 > 0) {
            r6.textContent = s2 ? s2.emptyScript : "";
            for (let s4 = 0; s4 < i6; s4++) r6.append(t4[s4], c3()), P.nextNode(), d3.push({ type: 2, index: ++l3 });
            r6.append(t4[i6], c3());
          }
        }
      } else if (8 === r6.nodeType) if (r6.data === n3) d3.push({ type: 2, index: l3 });
      else {
        let t4 = -1;
        for (; -1 !== (t4 = r6.data.indexOf(o3, t4 + 1)); ) d3.push({ type: 7, index: l3 }), t4 += o3.length - 1;
      }
      l3++;
    }
  }
  static createElement(t3, i5) {
    const s4 = l2.createElement("template");
    return s4.innerHTML = t3, s4;
  }
};
function M(t3, i5, s4 = t3, e5) {
  if (i5 === E) return i5;
  let h3 = void 0 !== e5 ? s4._$Co?.[e5] : s4._$Cl;
  const o6 = a2(i5) ? void 0 : i5._$litDirective$;
  return h3?.constructor !== o6 && (h3?._$AO?.(false), void 0 === o6 ? h3 = void 0 : (h3 = new o6(t3), h3._$AT(t3, s4, e5)), void 0 !== e5 ? (s4._$Co ?? (s4._$Co = []))[e5] = h3 : s4._$Cl = h3), void 0 !== h3 && (i5 = M(t3, h3._$AS(t3, i5.values), h3, e5)), i5;
}
var R = class {
  constructor(t3, i5) {
    this._$AV = [], this._$AN = void 0, this._$AD = t3, this._$AM = i5;
  }
  get parentNode() {
    return this._$AM.parentNode;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  u(t3) {
    const { el: { content: i5 }, parts: s4 } = this._$AD, e5 = (t3?.creationScope ?? l2).importNode(i5, true);
    P.currentNode = e5;
    let h3 = P.nextNode(), o6 = 0, n5 = 0, r6 = s4[0];
    for (; void 0 !== r6; ) {
      if (o6 === r6.index) {
        let i6;
        2 === r6.type ? i6 = new k(h3, h3.nextSibling, this, t3) : 1 === r6.type ? i6 = new r6.ctor(h3, r6.name, r6.strings, this, t3) : 6 === r6.type && (i6 = new Z(h3, this, t3)), this._$AV.push(i6), r6 = s4[++n5];
      }
      o6 !== r6?.index && (h3 = P.nextNode(), o6++);
    }
    return P.currentNode = l2, e5;
  }
  p(t3) {
    let i5 = 0;
    for (const s4 of this._$AV) void 0 !== s4 && (void 0 !== s4.strings ? (s4._$AI(t3, s4, i5), i5 += s4.strings.length - 2) : s4._$AI(t3[i5])), i5++;
  }
};
var k = class _k {
  get _$AU() {
    return this._$AM?._$AU ?? this._$Cv;
  }
  constructor(t3, i5, s4, e5) {
    this.type = 2, this._$AH = A, this._$AN = void 0, this._$AA = t3, this._$AB = i5, this._$AM = s4, this.options = e5, this._$Cv = e5?.isConnected ?? true;
  }
  get parentNode() {
    let t3 = this._$AA.parentNode;
    const i5 = this._$AM;
    return void 0 !== i5 && 11 === t3?.nodeType && (t3 = i5.parentNode), t3;
  }
  get startNode() {
    return this._$AA;
  }
  get endNode() {
    return this._$AB;
  }
  _$AI(t3, i5 = this) {
    t3 = M(this, t3, i5), a2(t3) ? t3 === A || null == t3 || "" === t3 ? (this._$AH !== A && this._$AR(), this._$AH = A) : t3 !== this._$AH && t3 !== E && this._(t3) : void 0 !== t3._$litType$ ? this.$(t3) : void 0 !== t3.nodeType ? this.T(t3) : d2(t3) ? this.k(t3) : this._(t3);
  }
  O(t3) {
    return this._$AA.parentNode.insertBefore(t3, this._$AB);
  }
  T(t3) {
    this._$AH !== t3 && (this._$AR(), this._$AH = this.O(t3));
  }
  _(t3) {
    this._$AH !== A && a2(this._$AH) ? this._$AA.nextSibling.data = t3 : this.T(l2.createTextNode(t3)), this._$AH = t3;
  }
  $(t3) {
    const { values: i5, _$litType$: s4 } = t3, e5 = "number" == typeof s4 ? this._$AC(t3) : (void 0 === s4.el && (s4.el = S2.createElement(V(s4.h, s4.h[0]), this.options)), s4);
    if (this._$AH?._$AD === e5) this._$AH.p(i5);
    else {
      const t4 = new R(e5, this), s5 = t4.u(this.options);
      t4.p(i5), this.T(s5), this._$AH = t4;
    }
  }
  _$AC(t3) {
    let i5 = C.get(t3.strings);
    return void 0 === i5 && C.set(t3.strings, i5 = new S2(t3)), i5;
  }
  k(t3) {
    u2(this._$AH) || (this._$AH = [], this._$AR());
    const i5 = this._$AH;
    let s4, e5 = 0;
    for (const h3 of t3) e5 === i5.length ? i5.push(s4 = new _k(this.O(c3()), this.O(c3()), this, this.options)) : s4 = i5[e5], s4._$AI(h3), e5++;
    e5 < i5.length && (this._$AR(s4 && s4._$AB.nextSibling, e5), i5.length = e5);
  }
  _$AR(t3 = this._$AA.nextSibling, s4) {
    for (this._$AP?.(false, true, s4); t3 !== this._$AB; ) {
      const s5 = i3(t3).nextSibling;
      i3(t3).remove(), t3 = s5;
    }
  }
  setConnected(t3) {
    void 0 === this._$AM && (this._$Cv = t3, this._$AP?.(t3));
  }
};
var H = class {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(t3, i5, s4, e5, h3) {
    this.type = 1, this._$AH = A, this._$AN = void 0, this.element = t3, this.name = i5, this._$AM = e5, this.options = h3, s4.length > 2 || "" !== s4[0] || "" !== s4[1] ? (this._$AH = Array(s4.length - 1).fill(new String()), this.strings = s4) : this._$AH = A;
  }
  _$AI(t3, i5 = this, s4, e5) {
    const h3 = this.strings;
    let o6 = false;
    if (void 0 === h3) t3 = M(this, t3, i5, 0), o6 = !a2(t3) || t3 !== this._$AH && t3 !== E, o6 && (this._$AH = t3);
    else {
      const e6 = t3;
      let n5, r6;
      for (t3 = h3[0], n5 = 0; n5 < h3.length - 1; n5++) r6 = M(this, e6[s4 + n5], i5, n5), r6 === E && (r6 = this._$AH[n5]), o6 || (o6 = !a2(r6) || r6 !== this._$AH[n5]), r6 === A ? t3 = A : t3 !== A && (t3 += (r6 ?? "") + h3[n5 + 1]), this._$AH[n5] = r6;
    }
    o6 && !e5 && this.j(t3);
  }
  j(t3) {
    t3 === A ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, t3 ?? "");
  }
};
var I = class extends H {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(t3) {
    this.element[this.name] = t3 === A ? void 0 : t3;
  }
};
var L = class extends H {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(t3) {
    this.element.toggleAttribute(this.name, !!t3 && t3 !== A);
  }
};
var z = class extends H {
  constructor(t3, i5, s4, e5, h3) {
    super(t3, i5, s4, e5, h3), this.type = 5;
  }
  _$AI(t3, i5 = this) {
    if ((t3 = M(this, t3, i5, 0) ?? A) === E) return;
    const s4 = this._$AH, e5 = t3 === A && s4 !== A || t3.capture !== s4.capture || t3.once !== s4.once || t3.passive !== s4.passive, h3 = t3 !== A && (s4 === A || e5);
    e5 && this.element.removeEventListener(this.name, this, s4), h3 && this.element.addEventListener(this.name, this, t3), this._$AH = t3;
  }
  handleEvent(t3) {
    "function" == typeof this._$AH ? this._$AH.call(this.options?.host ?? this.element, t3) : this._$AH.handleEvent(t3);
  }
};
var Z = class {
  constructor(t3, i5, s4) {
    this.element = t3, this.type = 6, this._$AN = void 0, this._$AM = i5, this.options = s4;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(t3) {
    M(this, t3);
  }
};
var B = t2.litHtmlPolyfillSupport;
B?.(S2, k), (t2.litHtmlVersions ?? (t2.litHtmlVersions = [])).push("3.3.3");
var D = (t3, i5, s4) => {
  const e5 = s4?.renderBefore ?? i5;
  let h3 = e5._$litPart$;
  if (void 0 === h3) {
    const t4 = s4?.renderBefore ?? null;
    e5._$litPart$ = h3 = new k(i5.insertBefore(c3(), t4), t4, void 0, s4 ?? {});
  }
  return h3._$AI(t3), h3;
};

// node_modules/lit-element/lit-element.js
var s3 = globalThis;
var i4 = class extends y {
  constructor() {
    super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
  }
  createRenderRoot() {
    var _a;
    const t3 = super.createRenderRoot();
    return (_a = this.renderOptions).renderBefore ?? (_a.renderBefore = t3.firstChild), t3;
  }
  update(t3) {
    const r6 = this.render();
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(t3), this._$Do = D(r6, this.renderRoot, this.renderOptions);
  }
  connectedCallback() {
    super.connectedCallback(), this._$Do?.setConnected(true);
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this._$Do?.setConnected(false);
  }
  render() {
    return E;
  }
};
i4._$litElement$ = true, i4["finalized"] = true, s3.litElementHydrateSupport?.({ LitElement: i4 });
var o4 = s3.litElementPolyfillSupport;
o4?.({ LitElement: i4 });
(s3.litElementVersions ?? (s3.litElementVersions = [])).push("4.2.2");

// node_modules/@lit/reactive-element/decorators/property.js
var o5 = { attribute: true, type: String, converter: u, reflect: false, hasChanged: f };
var r4 = (t3 = o5, e5, r6) => {
  const { kind: n5, metadata: i5 } = r6;
  let s4 = globalThis.litPropertyMetadata.get(i5);
  if (void 0 === s4 && globalThis.litPropertyMetadata.set(i5, s4 = /* @__PURE__ */ new Map()), "setter" === n5 && ((t3 = Object.create(t3)).wrapped = true), s4.set(r6.name, t3), "accessor" === n5) {
    const { name: o6 } = r6;
    return { set(r7) {
      const n6 = e5.get.call(this);
      e5.set.call(this, r7), this.requestUpdate(o6, n6, t3, true, r7);
    }, init(e6) {
      return void 0 !== e6 && this.C(o6, void 0, t3, e6), e6;
    } };
  }
  if ("setter" === n5) {
    const { name: o6 } = r6;
    return function(r7) {
      const n6 = this[o6];
      e5.call(this, r7), this.requestUpdate(o6, n6, t3, true, r7);
    };
  }
  throw Error("Unsupported decorator location: " + n5);
};
function n4(t3) {
  return (e5, o6) => "object" == typeof o6 ? r4(t3, e5, o6) : ((t4, e6, o7) => {
    const r6 = e6.hasOwnProperty(o7);
    return e6.constructor.createProperty(o7, t4), r6 ? Object.getOwnPropertyDescriptor(e6, o7) : void 0;
  })(t3, e5, o6);
}

// node_modules/@lit/reactive-element/decorators/state.js
function r5(r6) {
  return n4({ ...r6, state: true, attribute: false });
}

// src/const.ts
var CARD_VERSION = "1.3.0";
var PLATFORM = "birds_nearby";
var SENSORS = ["notable", "recent", "year_list"];
var THREATENED = ["VU", "EN", "CR", "EW", "EX"];
var STUB_MAX_HEIGHT = 500;

// src/localize/languages/en.json
var en_default = {
  common: {
    name: "Birds Nearby",
    description: "An area's notable sightings, recent species and year list from the Birds Nearby integration",
    title: "Birds nearby",
    invalid_configuration: "Choose an area from the Birds Nearby integration",
    invalid_height: "The height must be a positive number of pixels",
    invalid_row_step: "Invalid rounding. row_step must be full or half.",
    no_area: "The area isn't found. It may have been removed or disabled in the Birds Nearby integration.",
    not_found: "The sensor isn't found. It may be disabled.",
    unavailable: "No data from eBird right now"
  },
  tabs: {
    notable: "Notable",
    recent: "Recent",
    year_list: "Year list"
  },
  empty: {
    notable: "No notable sightings in the last 30 days",
    recent: "No sightings in the last {days} days",
    year_list: "No species on this year's list yet"
  },
  row: {
    present: "present",
    count_one: "{count} bird",
    count_other: "{count} birds",
    notable: "notable",
    unreviewed: "not reviewed",
    reports_one: "{count} checklist in 30 days",
    reports_other: "{count} checklists in 30 days",
    ebird: "The species on eBird",
    no_picture: "No picture found"
  },
  year: {
    before_installation: "Before installation",
    last_year: "Last year {date}",
    species_one: "{count} species",
    species_other: "{count} species"
  },
  editor: {
    device: "Area",
    title: "Title",
    row_step: "Rounding in a sections view",
    row_step_helper: "With automatic row height, the card's height is rounded up to whole rows, or to half rows to save space.",
    row_step_full: "Whole rows",
    row_step_half: "Half rows"
  }
};

// src/localize/languages/fi.json
var fi_default = {
  common: {
    name: "Lintuhavainnot",
    description: "Alueen huomionarvoiset havainnot, viimeaikaiset lajit ja vuosilista Birds Nearby -integraatiosta",
    title: "Lintuhavainnot",
    invalid_configuration: "Valitse alue Birds Nearby -integraatiosta",
    invalid_height: "Korkeuden pit\xE4\xE4 olla positiivinen m\xE4\xE4r\xE4 pikseleit\xE4",
    invalid_row_step: "Virheellinen py\xF6ristys. Py\xF6ristyksen (row_step) on oltava full tai half.",
    no_area: "Aluetta ei l\xF6ydy. Se on ehk\xE4 poistettu tai poistettu k\xE4yt\xF6st\xE4 Birds Nearby -integraatiossa.",
    not_found: "Anturia ei l\xF6ydy. Se on ehk\xE4 poistettu k\xE4yt\xF6st\xE4.",
    unavailable: "eBirdist\xE4 ei saada nyt tietoja"
  },
  tabs: {
    notable: "Huomionarvoiset",
    recent: "Viimeaikaiset",
    year_list: "Vuosilista"
  },
  empty: {
    notable: "Ei huomionarvoisia havaintoja 30 p\xE4iv\xE4\xE4n",
    recent: "Ei havaintoja {days} p\xE4iv\xE4\xE4n",
    year_list: "T\xE4m\xE4n vuoden listalla ei ole viel\xE4 lajeja"
  },
  row: {
    present: "l\xE4sn\xE4",
    count_one: "{count} yks.",
    count_other: "{count} yks.",
    notable: "huomionarvoinen",
    unreviewed: "tarkastamaton",
    reports_one: "{count} havaintoer\xE4 30 p\xE4iv\xE4ss\xE4",
    reports_other: "{count} havaintoer\xE4\xE4 30 p\xE4iv\xE4ss\xE4",
    ebird: "Laji eBirdiss\xE4",
    no_picture: "Kuvaa ei l\xF6ytynyt"
  },
  year: {
    before_installation: "Ennen asennusta",
    last_year: "Viime vuonna {date}",
    species_one: "{count} laji",
    species_other: "{count} lajia"
  },
  editor: {
    device: "Alue",
    title: "Otsikko",
    row_step: "Py\xF6ristys osioihin jaetussa n\xE4kym\xE4ss\xE4",
    row_step_helper: "Automaattisella rivikorkeudella kortin korkeus py\xF6ristet\xE4\xE4n yl\xF6sp\xE4in kokonaisiin riveihin, tai tilan s\xE4\xE4st\xE4miseksi puolikkaisiin riveihin.",
    row_step_full: "Kokonaisiin riveihin",
    row_step_half: "Puolikkaisiin riveihin"
  }
};

// src/localize/localize.ts
var FILES = { "./languages/en.json": en_default, "./languages/fi.json": fi_default };
var LANGUAGES = Object.fromEntries(
  Object.entries(FILES).map(([path, table]) => [path.replace(/^.*\/|\.json$/g, "").toLowerCase(), table])
);
var LANGUAGE_CODES = Object.keys(LANGUAGES).sort();
function translate(language, key) {
  const code = (language ?? "en").split(/[-_]/)[0].toLowerCase();
  return read(LANGUAGES[code], key) ?? read(LANGUAGES.en, key) ?? key;
}
function read(table, key) {
  let value = table;
  for (const part of key.split(".")) {
    if (value === null || typeof value !== "object") {
      return void 0;
    }
    value = value[part];
  }
  return typeof value === "string" ? value : void 0;
}
function browserLanguage() {
  return document.documentElement.lang || navigator.language || "en";
}

// src/height.ts
var HEIGHT_MODES = ["auto", "fixed", "max"];
var pixels = (value) => value == null || typeof value === "number" && Number.isFinite(value) && value > 0;
function validHeight(config) {
  return (config.height_mode == null || HEIGHT_MODES.includes(config.height_mode)) && pixels(config.height) && pixels(config.max_height);
}
function heightMode(config) {
  return config.height_mode ?? (config.height ? "fixed" : config.max_height ? "max" : "auto");
}
var ROW_HEIGHT = 56;
var ROW_GAP = 8;
function heightStyle(config, layout, minimum = 0) {
  const rows = config.grid_options ? config.grid_options.rows : config.layout_options?.grid_rows;
  if (layout === "grid" && typeof rows === "number") {
    return "height: 100%";
  }
  const mode = heightMode(config);
  if (mode === "fixed" && config.height) {
    return `height: ${Math.max(config.height, minimum)}px`;
  }
  return mode === "max" && config.max_height ? `max-height: ${Math.max(config.max_height, minimum)}px` : "";
}
function gridMinRows(minimum) {
  return Math.max(1, Math.ceil((minimum + ROW_GAP) / (ROW_HEIGHT + ROW_GAP)));
}
function heightCardSize(config, content, minimum = 0) {
  const mode = heightMode(config);
  if (mode === "fixed" && config.height) {
    return Math.max(1, Math.round(Math.max(config.height, minimum) / 50));
  }
  return mode === "max" && config.max_height ? Math.max(1, Math.min(content, Math.round(Math.max(config.max_height, minimum) / 50))) : content;
}

// src/rows.ts
var ROW_STEPS = ["full", "half"];
var ROW_PX = 64;
var ROW_GAP_PX = 8;
function validRowStep(config) {
  return config.row_step === void 0 || config.row_step === null || ROW_STEPS.includes(config.row_step);
}
var step = (config) => config.row_step === "half" ? ROW_PX / 2 : ROW_PX;
function filledHeight(content, config, limit = Infinity) {
  return Math.min(Math.max(1, Math.ceil((content + ROW_GAP_PX) / step(config))) * step(config) - ROW_GAP_PX, limit);
}
function fillLimit(config, layout, minimum = 0) {
  const rows = config.grid_options ? config.grid_options.rows : config.layout_options?.grid_rows;
  if (layout !== "grid" || typeof rows === "number") {
    return 0;
  }
  const mode = heightMode(config);
  if (mode === "fixed" && config.height) {
    return 0;
  }
  if (mode !== "max" || !config.max_height) {
    return Infinity;
  }
  const down = Math.floor((config.max_height + ROW_GAP_PX) / step(config)) * step(config) - ROW_GAP_PX;
  return Math.max(down, filledHeight(minimum, config));
}
function filledStyle(config, layout, minimum, filled) {
  const limit = fillLimit(config, layout, minimum);
  if (!limit) {
    return heightStyle(config, layout, minimum);
  }
  return [limit < Infinity && `max-height: ${limit}px`, filled && `min-height: ${filled}px`].filter(Boolean).join("; ");
}
function rowStepSchema(config, text) {
  if (heightMode(config) === "fixed" && config.height) {
    return [];
  }
  return [
    {
      name: "row_step",
      selector: {
        select: { mode: "dropdown", options: ROW_STEPS.map((value) => ({ value, label: text(`editor.row_step_${value}`) })) }
      }
    }
  ];
}
function rowStepData(config) {
  return { ...config, row_step: config.row_step ?? "full" };
}
function tidyRowStep(config) {
  const tidied = { ...config };
  if (tidied.row_step !== "half" || heightMode(tidied) === "fixed" && tidied.height) {
    delete tidied.row_step;
  }
  return tidied;
}

// src/editor.ts
function schema(config, text) {
  return [
    { name: "device", required: true, selector: { device: { filter: { integration: PLATFORM } } } },
    { name: "title", selector: { text: {} } },
    ...rowStepSchema(config, text)
  ];
}
var BirdsNearbyCardEditor = class extends i4 {
  setConfig(config) {
    this.config = config;
  }
  render() {
    if (!this.hass || !this.config) {
      return A;
    }
    return b2`
            <ha-form
                .hass=${this.hass}
                .data=${rowStepData(this.config)}
                .schema=${schema(this.config, (key) => this.text(key))}
                .computeLabel=${(entry) => this.text(`editor.${entry.name}`)}
                .computeHelper=${(entry) => this.helper(entry.name)}
                @value-changed=${this.valueChanged}
            ></ha-form>
        `;
  }
  valueChanged(event) {
    const config = tidyRowStep(event.detail.value);
    if (!config.title) {
      delete config.title;
    }
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }));
  }
  text(key) {
    return translate(this.language(), key);
  }
  helper(name) {
    const key = `editor.${name}_helper`;
    const helper = translate(this.language(), key);
    return helper === key ? void 0 : helper;
  }
  language() {
    return this.hass?.locale?.language ?? this.hass?.language ?? browserLanguage();
  }
};
__decorateClass([
  n4({ attribute: false })
], BirdsNearbyCardEditor.prototype, "hass", 2);
__decorateClass([
  r5()
], BirdsNearbyCardEditor.prototype, "config", 2);
if (!customElements.get("birds-nearby-card-editor")) {
  customElements.define("birds-nearby-card-editor", BirdsNearbyCardEditor);
}

// src/fade.ts
var fadeStyles = i`
    .fades {
        --fade-length: min(24px, 25%);
        scroll-padding-block: calc(var(--fade-top-offset, 0px) + var(--fade-length, 24px)) var(--fade-length, 24px);
    }

    .fade-top {
        mask-image: linear-gradient(
            to bottom,
            #000 var(--fade-top-offset, 0px),
            transparent var(--fade-top-offset, 0px),
            #000 calc(var(--fade-top-offset, 0px) + var(--fade-length, 24px))
        );
    }

    .fade-bottom {
        mask-image: linear-gradient(to top, transparent, #000 var(--fade-length, 24px));
    }

    .fade-top.fade-bottom {
        mask-image: linear-gradient(
            to bottom,
            #000 var(--fade-top-offset, 0px),
            transparent var(--fade-top-offset, 0px),
            #000 calc(var(--fade-top-offset, 0px) + var(--fade-length, 24px)),
            #000 calc(100% - var(--fade-length, 24px)),
            transparent
        );
    }
`;
function markFade(part) {
  const hidden = part.scrollHeight - part.clientHeight;
  part.classList.toggle("fade-top", hidden > 1 && part.scrollTop > 1);
  part.classList.toggle("fade-bottom", hidden > 1 && hidden - part.scrollTop > 1);
}
var onScroll = (event) => markFade(event.currentTarget);
var ScrollFade = class {
  constructor(host, parts) {
    this.host = host;
    this.parts = parts;
    /** Each followed part with the children whose size it watches. */
    this.followed = /* @__PURE__ */ new Map();
    this.resized = typeof ResizeObserver === "undefined" ? void 0 : new ResizeObserver((entries) => {
      for (const { target } of entries) {
        const part = this.followed.has(target) ? target : target.parentElement;
        if (part && this.followed.has(part)) {
          markFade(part);
        }
      }
    });
    host.addController(this);
  }
  hostConnected() {
    if (this.host.hasUpdated) {
      this.follow();
    }
  }
  hostUpdated() {
    if (this.host.isConnected) {
      this.follow();
    }
  }
  hostDisconnected() {
    for (const part of [...this.followed.keys()]) {
      this.forget(part);
    }
  }
  follow() {
    const now = new Set(this.parts());
    for (const part of [...this.followed.keys()]) {
      if (!now.has(part)) {
        this.forget(part);
      }
    }
    for (const part of now) {
      if (!this.followed.has(part)) {
        part.addEventListener("scroll", onScroll, { passive: true });
        this.resized?.observe(part);
      }
      part.classList.add("fades");
      const before = this.followed.get(part) ?? [];
      const children = [...part.children];
      before.filter((child) => !children.includes(child)).forEach((child) => this.resized?.unobserve(child));
      children.filter((child) => !before.includes(child)).forEach((child) => this.resized?.observe(child));
      this.followed.set(part, children);
      markFade(part);
    }
  }
  forget(part) {
    this.followed.get(part)?.forEach((child) => this.resized?.unobserve(child));
    this.followed.delete(part);
    part.removeEventListener("scroll", onScroll);
    this.resized?.unobserve(part);
    part.classList.remove("fades", "fade-top", "fade-bottom");
  }
};

// src/sightings.ts
function areaDevices(hass) {
  const devices = Object.values(hass.entities ?? {}).filter((entry) => entry?.platform === PLATFORM && entry.translation_key === "notable" && entry.device_id).map((entry) => entry?.device_id);
  return [...new Set(devices)];
}
function areaSensors(hass, device) {
  const found = {};
  for (const entry of Object.values(hass.entities ?? {})) {
    const key = entry?.translation_key;
    if (entry && entry.device_id === device && entry.platform === PLATFORM && key && SENSORS.includes(key)) {
      found[key] = entry.entity_id;
    }
  }
  return found;
}
function listOf(hass, entityId, attribute) {
  const entity = entityId ? hass.states[entityId] : void 0;
  if (!entity || entity.state === "unavailable" || entity.state === "unknown") {
    return void 0;
  }
  const value = entity.attributes[attribute];
  return Array.isArray(value) ? value : [];
}
function countOf(hass, entityId) {
  const value = Number.parseInt(entityId ? hass.states[entityId]?.state ?? "" : "", 10);
  return Number.isFinite(value) ? value : null;
}
function threatened(sighting) {
  return !!sighting.iucn_status && THREATENED.includes(sighting.iucn_status);
}
function yearDays(species) {
  const days = /* @__PURE__ */ new Map();
  for (const item of species) {
    const day = item.first_seen || null;
    days.set(day, [...days.get(day) ?? [], item]);
  }
  return [...days.entries()].map(([day, items]) => ({ day, species: items })).sort((a3, b3) => a3.day === null ? 1 : b3.day === null ? -1 : b3.day.localeCompare(a3.day));
}
function numberLocale(format) {
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
      return void 0;
    default:
      return format.language;
  }
}
function formatNumber(value, format, fractions = 0) {
  return new Intl.NumberFormat(numberLocale(format), {
    maximumFractionDigits: fractions,
    ...format.number_format === "none" ? { useGrouping: false } : {}
  }).format(value);
}
function placeOf(sighting, format) {
  const distance = `${formatNumber(sighting.distance_km, format, 1)} km${sighting.direction ? ` ${sighting.direction}` : ""}`;
  return sighting.location ? `${sighting.location}, ${distance}` : distance;
}
function formatDay(value, language, today) {
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  const sameYear = value.slice(0, 4) === today.slice(0, 4);
  return new Intl.DateTimeFormat(language, {
    day: "numeric",
    month: "numeric",
    ...sameYear ? {} : { year: "numeric" },
    timeZone: "UTC"
  }).format(date);
}
function formatClock(value, language) {
  const time = value.slice(11, 16);
  if (!time || time === "00:00") {
    return null;
  }
  const [hours, minutes] = time.split(":").map(Number);
  return new Intl.DateTimeFormat(language, { hour: "numeric", minute: "2-digit", timeZone: "UTC" }).format(
    new Date(Date.UTC(2e3, 0, 1, hours, minutes))
  );
}
function localToday(now = /* @__PURE__ */ new Date()) {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

// src/birds-nearby-card.ts
var PADDING = 24;
var STEP = 32;
var TABS_SIDES = 2 * 16 + 2 * 8;
var TAB_PADDING = 2 * 4;
var ROW_SIDES = 2 * 16 + 48 + 2 * 12;
var SLACK_PX = 0.01;
function tabsFit(width, needs) {
  const room = (width - TABS_SIDES) / 3 - TAB_PADDING;
  return needs.every((need) => need <= room + SLACK_PX);
}
function sideFits(width, texts, side) {
  return ROW_SIDES + texts + side <= width + SLACK_PX;
}
function textWidth(element) {
  if (!element) {
    return 0;
  }
  const range = document.createRange();
  range.selectNodeContents(element);
  return range.getBoundingClientRect().width;
}
function drawnScale(card) {
  const layout = px(getComputedStyle(card).width);
  const drawn = card.getBoundingClientRect().width;
  return layout > 0 && drawn > 0 ? drawn / layout : 1;
}
function px(value) {
  return Number.parseFloat(value) || 0;
}
var BirdsNearbyCard = class extends i4 {
  constructor() {
    super();
    this.tabsSplit = false;
    this.splitRows = /* @__PURE__ */ new Set();
    this.filled = 0;
    this.spare = 0;
    this.resizes = typeof ResizeObserver === "undefined" ? void 0 : new ResizeObserver(() => this.measureSoon());
    new ScrollFade(this, () => this.heightStyle() ? this.renderRoot.querySelectorAll("ha-card > .scroll") : []);
  }
  connectedCallback() {
    super.connectedCallback();
    if (this.hasUpdated) {
      this.requestUpdate();
    }
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this.resizes?.disconnect();
    cancelAnimationFrame(this.frame ?? 0);
  }
  static getConfigElement() {
    return document.createElement("birds-nearby-card-editor");
  }
  /** Offers the first area there is when the card is added from the picker, held to a height so a busy area's list scrolls. */
  static getStubConfig(hass) {
    return { device: hass ? areaDevices(hass)[0] ?? "" : "", max_height: STUB_MAX_HEIGHT };
  }
  setConfig(config) {
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
      this.open = void 0;
    }
    this.config = config;
  }
  getCardSize() {
    return heightCardSize(this.config ?? {}, 10, this.minimumHeight());
  }
  /**
   * In a sections view the card takes a whole section by default and is never narrower than three quarters of one, as
   * on a phone's half a section a species' name would have room for a syllable or two beside its picture.
   */
  getGridOptions() {
    return { columns: 12, min_columns: 9, rows: "auto", min_rows: gridMinRows(this.minimumHeight()) };
  }
  shouldUpdate(changed) {
    const previous = changed.get("hass");
    if (!this.config || !this.hass || changed.size > 1 || !changed.has("hass") || !previous || this.drawnOn !== localToday()) {
      return true;
    }
    if (previous.entities !== this.hass.entities || previous.devices !== this.hass.devices || previous.locale !== this.hass.locale || previous.language !== this.hass.language) {
      return true;
    }
    const sensors = Object.values(areaSensors(this.hass, this.config.device));
    return sensors.some((id) => previous.states[id] !== this.hass?.states[id]);
  }
  render() {
    if (!this.hass || !this.config) {
      return A;
    }
    this.drawnOn = localToday();
    const sensors = areaSensors(this.hass, this.config.device);
    if (!this.hass.devices?.[this.config.device] || !Object.keys(sensors).length) {
      return b2`<ha-card class=${this.heightStyle() ? "held" : ""} style=${this.cardStyle()} lang=${this.textLanguage()}>
                <div class="message">${this.text("common.no_area")}</div>
            </ha-card>`;
    }
    const notable = listOf(this.hass, sensors.notable, "sightings");
    const recent = listOf(this.hass, sensors.recent, "species");
    const tab = this.tab ?? ((countOf(this.hass, sensors.notable) ?? 0) > 0 ? "notable" : "recent");
    const title = this.config.title || this.text("common.title");
    const area = this.areaName();
    return b2`
            <ha-card class=${this.heightStyle() ? "held" : ""} style=${this.cardStyle()} lang=${this.textLanguage()}>
                <div class="header">
                    <span class="title" title=${title}>${title}</span>
                    <span class="area" title=${area}>${area}</span>
                </div>
                <div class="tabs ${this.tabsSplit ? "split" : ""}" role="tablist">
                    ${SENSORS.map((key) => this.tabButton(this.hass, key, sensors[key], tab))}
                </div>
                <div class="scroll" role="tabpanel">${this.list(this.hass, tab, sensors, notable, recent)}</div>
            </ha-card>
        `;
  }
  updated() {
    const card = this.renderRoot.querySelector("ha-card");
    if (card && this.isConnected) {
      this.resizes?.observe(card);
      this.measureSoon();
    }
  }
  tabButton(hass, key, entityId, chosen) {
    const count = countOf(hass, entityId);
    return b2`
            <button
                class="tab ${key} ${key === chosen ? "on" : ""}"
                role="tab"
                aria-selected=${key === chosen ? "true" : "false"}
                @click=${() => this.choose(key)}
            >
                <span class="count">${count === null ? "\u2013" : formatNumber(count, this.numberFormat())}</span>
                <span class="label" title=${this.text(`tabs.${key}`)}>${this.text(`tabs.${key}`)}</span>
            </button>
        `;
  }
  choose(key) {
    this.tab = key;
    this.open = void 0;
    this.renderRoot.querySelector(".scroll")?.scrollTo({ top: 0 });
  }
  list(hass, tab, sensors, notable, recent) {
    if (!sensors[tab]) {
      return this.empty(this.text("common.not_found"));
    }
    if (tab === "year_list") {
      const species = listOf(hass, sensors.year_list, "species");
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
    return b2`${sightings.map((sighting) => this.row(tab, sighting, tab === "recent" && notableSpecies.has(sighting.species_code)))}`;
  }
  empty(message) {
    return b2`<div class="empty">${message}</div>`;
  }
  row(tab, sighting, notable) {
    const key = `${tab}:${sighting.species_code}`;
    const opened = this.open === key;
    const place = placeOf(sighting, this.numberFormat());
    const amount = this.amount(sighting.count);
    const when = this.when(sighting.observed);
    return b2`
            <div class="sighting ${opened ? "opened" : ""}">
                <button
                    class="row ${this.splitRows.has(key) ? "split" : ""}"
                    data-key=${key}
                    aria-expanded=${opened ? "true" : "false"}
                    @click=${() => this.open = opened ? void 0 : key}
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
                ${opened ? this.detail(sighting) : A}
            </div>
        `;
  }
  thumbnail(picture) {
    return picture ? b2`<img class="thumbnail" src=${picture} alt="" loading="lazy" />` : b2`<span class="thumbnail none"><ha-icon icon="mdi:bird"></ha-icon></span>`;
  }
  /** Each after a space, so a screen reader doesn't read a badge into the name. */
  badges(sighting, notable) {
    const badges = [
      notable ? b2`<span class="badge notable">${this.text("row.notable")}</span>` : void 0,
      sighting.reviewed === false ? b2`<span class="badge unreviewed">${this.text("row.unreviewed")}</span>` : void 0,
      threatened(sighting) ? b2`<span class="badge threatened">${sighting.iucn_status}</span>` : void 0
    ];
    return b2`${badges.filter(Boolean).map((badge) => b2` ${badge}`)}`;
  }
  amount(count) {
    if (count === null) {
      return this.text("row.present");
    }
    return this.text(count === 1 ? "row.count_one" : "row.count_other").replace("{count}", formatNumber(count, this.numberFormat()));
  }
  /**
   * The day and the time. eBird's times are the area's own and the card knows no zone for the area, so it never says
   * today or yesterday, which would be the viewer's.
   */
  when(observed) {
    const language = this.language();
    return [formatDay(observed, language, localToday()), formatClock(observed, language)].filter(Boolean).join(" ");
  }
  detail(sighting) {
    const reports = sighting.reports;
    return b2`
            <div class="detail">
                ${sighting.picture ? b2`<img class="picture" src=${sighting.picture} alt=${sighting.name} />
                              ${sighting.picture_credit ? b2`<div class="credit">${sighting.picture_credit}</div>` : A}` : b2`<div class="credit">${this.text("row.no_picture")}</div>`}
                <div class="links">
                    ${reports ? b2`<span
                                  >${this.text(reports === 1 ? "row.reports_one" : "row.reports_other").replace(
      "{count}",
      formatNumber(reports, this.numberFormat())
    )}</span
                              >` : A}
                    <a href=${sighting.url} target="_blank" rel="noopener noreferrer">${this.text("row.ebird")}</a>
                </div>
            </div>
        `;
  }
  yearList(species) {
    const language = this.language();
    const today = localToday();
    return b2`${yearDays(species).map((day) => {
      const date = day.day ? formatDay(day.day, language, today) : this.text("year.before_installation");
      const count = this.text(day.species.length === 1 ? "year.species_one" : "year.species_other").replace(
        "{count}",
        formatNumber(day.species.length, this.numberFormat())
      );
      return b2`
                <div class="day">
                    <span class="day-date" title=${date}>${date}</span>
                    <span class="day-count" title=${count}>${count}</span>
                </div>
                ${day.species.map((item) => {
        const lastYear = item.last_year ? this.text("year.last_year").replace("{date}", formatDay(item.last_year, language, today)) : "";
        return b2`
                        <div class="row year">
                            ${this.thumbnail(item.picture)}
                            <span class="main">
                                <span class="name" title=${item.name}>${item.name}</span>
                                ${lastYear ? b2`<span class="place" title=${lastYear}>${lastYear}</span>` : A}
                            </span>
                        </div>
                    `;
      })}
            `;
    })}`;
  }
  areaName() {
    const device = this.hass?.devices?.[this.config?.device ?? ""];
    return device?.name_by_user || device?.name || "";
  }
  heightStyle() {
    return heightStyle(this.config ?? {}, this.layout, this.minimumHeight());
  }
  /**
   * The lowest the card is held to, in pixels: its header, the tabs one to a row and a sighting with its count and time
   * under its texts, as on the narrowest card either may be split. Four rows.
   */
  minimumHeight() {
    return PADDING + STEP + 3 * STEP + 3 * STEP;
  }
  /** The card's inline style: the height it is held to, or the rows it fills up to any limit, with their spare room. */
  cardStyle() {
    const style = filledStyle(this.config ?? {}, this.layout, this.minimumHeight(), this.filled);
    return this.filled ? `${style}; --spare: ${this.spare}px` : style;
  }
  measureSoon() {
    cancelAnimationFrame(this.frame ?? 0);
    this.frame = requestAnimationFrame(() => this.measure());
  }
  measure() {
    const card = this.renderRoot.querySelector("ha-card");
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
  measureSplits(card, scale) {
    const width = (element) => textWidth(element) / scale;
    const tabs = card.querySelector(".tabs");
    if (tabs) {
      const needs = [...tabs.querySelectorAll(".tab")].map(
        (tab) => Math.max(width(tab.querySelector(".count")), width(tab.querySelector(".label")))
      );
      const split2 = !tabsFit(tabs.getBoundingClientRect().width / scale, needs);
      if (split2 !== this.tabsSplit) {
        this.tabsSplit = split2;
      }
    }
    const rows = [...card.querySelectorAll("button.row")];
    const heights = rows.map((row) => getComputedStyle(row).height);
    rows.forEach((row, index) => row.style.height = heights[index]);
    card.classList.add("measuring");
    const split = /* @__PURE__ */ new Set();
    for (const row of rows) {
      const texts = Math.max(0, ...[...row.querySelectorAll(".main > *")].map(width));
      const side = Math.max(0, ...[...row.querySelectorAll(".side > *")].map(width));
      if (!sideFits(row.getBoundingClientRect().width / scale, texts, side) && row.dataset.key) {
        split.add(row.dataset.key);
      }
    }
    card.classList.remove("measuring");
    rows.forEach((row) => row.style.height = "");
    const drawn = new Set(rows.map((row) => row.dataset.key));
    const kept = [...this.splitRows].filter((key) => !drawn.has(key));
    const next = /* @__PURE__ */ new Set([...kept, ...split]);
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
  fillRows(card, scale) {
    const limit = fillLimit(this.config ?? {}, this.layout, this.minimumHeight());
    if (!limit) {
      this.filled = 0;
      this.spare = 0;
      return;
    }
    const parts = card.querySelectorAll(":scope > .header, :scope > .tabs, :scope > .scroll > *, :scope > .message");
    const last = parts[parts.length - 1];
    if (!last) {
      return;
    }
    const style = getComputedStyle(card);
    const drawn = (last.getBoundingClientRect().bottom - card.getBoundingClientRect().top) / scale;
    let content = drawn + px(style.paddingBottom) + px(style.borderBottomWidth);
    const header = card.querySelector(":scope > .header");
    const message = card.querySelector(":scope > .message");
    if (header) {
      content -= px(getComputedStyle(header).paddingBottom);
    } else if (message) {
      content -= px(getComputedStyle(message).paddingTop);
    }
    const filled = filledHeight(Math.ceil(content - SLACK_PX), this.config ?? {}, limit);
    const spare = Math.max(0, Math.floor(filled - content + SLACK_PX));
    if (filled !== this.filled || spare !== this.spare) {
      this.filled = filled;
      this.spare = spare;
    }
  }
  numberFormat() {
    return { language: this.language(), number_format: this.hass?.locale?.number_format };
  }
  text(key) {
    return translate(this.language(), key);
  }
  language() {
    return this.hass?.locale?.language ?? this.hass?.language ?? browserLanguage();
  }
  /** The language the card's texts are in: the viewer's when the card has it, otherwise English, which it falls back to. */
  textLanguage() {
    const code = this.language().split(/[-_]/)[0].toLowerCase();
    return LANGUAGE_CODES.includes(code) ? code : "en";
  }
  static get styles() {
    return [
      i`
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

                /* Held, the list keeps the scrollbar's room whether it scrolls or not, as room that came with the scrolling
                would put a sighting's count and time under its texts, and keep the card scrolling. */
                ha-card.held > .scroll {
                    flex: 1 1 auto;
                    min-height: 0;
                    overflow-y: auto;
                    scrollbar-width: thin;
                    scrollbar-gutter: stable;
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

                /* A line between the rows that takes no room of its own, so each row stays on the step. */
                .row {
                    box-sizing: border-box;
                    display: grid;
                    grid-template-columns: auto minmax(0, 1fr) auto;
                    align-items: center;
                    gap: 0 12px;
                    width: 100%;
                    min-height: 64px;
                    padding: 6px 16px;
                    box-shadow: inset 0 -1px 0 var(--divider-color);
                }

                button.row:hover {
                    background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.08);
                }

                .opened > .row {
                    box-shadow: none;
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
                ha-card.held .day > * {
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }

                /* While measuring, each text is laid out on one line, whole, as it would be with room enough. */
                ha-card.measuring button.row .main > *,
                ha-card.measuring button.row .side > * {
                    white-space: nowrap;
                }

                /* At the top of the name's line, 16 px in its 20, so a badge never makes the line, and the row, taller. */
                .badge {
                    display: inline-block;
                    margin-top: 2px;
                    margin-left: 2px;
                    padding: 0 6px;
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

                /* The year list's day and each of its species are half a row, and a line that wraps adds half a row. */
                .day {
                    display: flex;
                    justify-content: space-between;
                    gap: 12px;
                    padding: 0 16px;
                    line-height: 32px;
                    color: var(--secondary-text-color);
                    font-size: var(--ha-font-size-s, 12px);
                    font-weight: var(--ha-font-weight-medium, 500);
                }

                .day > * {
                    min-width: 0;
                }

                .row.year {
                    grid-template-columns: auto minmax(0, 1fr);
                    gap: 0 8px;
                    min-height: 32px;
                    padding: 0 16px;
                }

                .row.year .thumbnail {
                    align-self: start;
                    margin-top: 4px;
                    width: 24px;
                    height: 24px;
                }

                .row.year .thumbnail ha-icon {
                    --mdc-icon-size: 18px;
                }

                /* The name and the date of last year on one line, the date going to a line of its own when it doesn't fit. */
                .row.year .main {
                    flex-direction: row;
                    flex-wrap: wrap;
                    justify-content: space-between;
                    column-gap: 12px;
                }

                .row.year .name,
                .row.year .place {
                    line-height: 32px;
                }

                ha-card.held .row.year .main {
                    flex-wrap: nowrap;
                }

                .empty {
                    padding: 0 16px;
                    line-height: 32px;
                    color: var(--secondary-text-color);
                }
            `,
      fadeStyles
    ];
  }
};
__decorateClass([
  n4({ attribute: false })
], BirdsNearbyCard.prototype, "hass", 2);
__decorateClass([
  n4({ attribute: false })
], BirdsNearbyCard.prototype, "layout", 2);
__decorateClass([
  r5()
], BirdsNearbyCard.prototype, "config", 2);
__decorateClass([
  r5()
], BirdsNearbyCard.prototype, "tab", 2);
__decorateClass([
  r5()
], BirdsNearbyCard.prototype, "open", 2);
__decorateClass([
  r5()
], BirdsNearbyCard.prototype, "tabsSplit", 2);
__decorateClass([
  r5()
], BirdsNearbyCard.prototype, "splitRows", 2);
__decorateClass([
  r5()
], BirdsNearbyCard.prototype, "filled", 2);
__decorateClass([
  r5()
], BirdsNearbyCard.prototype, "spare", 2);
if (!customElements.get("birds-nearby-card")) {
  console.info(
    `%c  BIRDS-NEARBY-CARD 
%c  ${CARD_VERSION}    `,
    "color: orange; font-weight: bold; background: black",
    "color: white; font-weight: bold; background: dimgray"
  );
  const registry = window;
  registry.customCards = registry.customCards ?? [];
  registry.customCards.push({
    type: "birds-nearby-card",
    name: translate(browserLanguage(), "common.name"),
    description: translate(browserLanguage(), "common.description"),
    documentationURL: "https://github.com/jesmak/birds_nearby#birds-nearby-card",
    preview: true
  });
  customElements.define("birds-nearby-card", BirdsNearbyCard);
}
export {
  BirdsNearbyCard,
  sideFits,
  tabsFit
};
