# StyleSense — `PUBLIC DRESSING ROOM`

## The creative decision

StyleSense should feel like a **fashion desk, not a fashion app**: opinionated, social, tactile, and slightly confrontational. The product is useful because it helps people get dressed; the interface should therefore put clothes, context, and choice first—not “intelligence”, glowing magic, or a chatbot persona.

The visual reference is a city style paper crossed with a backstage fitting room:

- large editorial type beside very small utility type;
- blunt black rules, tape-label metadata, and image-led layouts;
- a warm paper background, carbon ink, one vivid signal colour;
- deliberately asymmetric grids and full-bleed product photography;
- words as controls wherever possible.

The working campaign line is **“GET DRESSED. GO SOMEWHERE.”** StyleSense is a tool, not a virtual stylist with a personality.

## Non-negotiables

1. No gradients, glassy cards, floating blobs, shimmer, or “magic” visual effects. Glass is reserved for the global masthead, temporary filter sheets, and modal/side-panel overlays—never for the product grid or page background.
2. No sparkle, robot, brain, wand, shopping-bag, or stock Lucide icons as primary navigation. Use clear words, counts, and typographic marks (`+`, `×`, `→`, `01`) instead.
3. No emoji in product UI. Use photography, swatches, or text labels.
4. No pills except compact status tags and selected filters. Cards are square, bordered panels—not soft floating containers.
5. Never lead with “AI”. The system can power a suggestion, but the UI calls it “a suggestion”, “a match”, or “a second opinion”. Explain the mechanism only in Privacy / About.
6. Do not use purple/blue/pink SaaS colours, centered marketing copy, fake metrics, or tech-stack copy on customer pages.
7. Every page gets one clear job. If a control does not move the user toward that job, remove it.

## Brand language

| Use | Avoid |
| --- | --- |
| Closet, rack, look, edit, pull, save, wear, match, second opinion | AI Stylist, Style DNA, intelligence, powered by, next-gen, optimize |
| “What are we dressing for?” | “What’s your vibe?” |
| “3 looks, built from your closet” | “Your personalized AI recommendations” |
| “Add a piece” | “Upload garment with AI” |
| “Why this works” | “AI rationale” |

Keep copy specific and a little dry. Example microcopy: `You own the shirt. We found the outfit.` Never add hype, exclamation marks, or product promises the system cannot prove.

## Design tokens

### Colour

The palette deliberately uses no gradient. The signal colour is rare: it directs action and selected state, not decoration.

| Token | Value | Use |
| --- | --- | --- |
| `--paper` | `#F4F0E8` | main canvas |
| `--paper-strong` | `#E7E1D5` | sections, selected filter field |
| `--ink` | `#181716` | headings, borders, primary buttons |
| `--ink-soft` | `#5E5A54` | supporting copy |
| `--line` | `#C9C2B6` | 1px rules |
| `--acid` | `#DFFF00` | one active action / active state |
| `--cobalt` | `#234BFF` | link and information state only |
| `--signal` | `#E33B1E` | destructive / urgent state |
| `--white` | `#FFFFFF` | reversed text, image overlays only |

Dark mode is not a first-release requirement. If added, it is `--paper: #181716`, `--ink: #F4F0E8`, `--line: #48433D`; preserve acid and signal unchanged.

### Type

Use system-installed typefaces so the product has no remote font dependency. Keep the high contrast between a bookish display serif, clean interface sans, and compact mono metadata.

| Role | Family | Style |
| --- | --- | --- |
| Display / campaign | Baskerville → Palatino Linotype → Book Antiqua → Georgia | regular, sentence case; tight but not cramped |
| Interface / headings | Helvetica Neue → Arial | 500–700; mostly sentence case |
| Metadata / controls | SF Mono → Consolas | 400–500; uppercase only for short labels |

Type scale: `12 / 14 / 16 / 20 / 28 / 40 / clamp(54, 8vw, 128)`. Use `letter-spacing: .08em` only for mono metadata. Use a 1.0–1.08 line-height for display and 1.35–1.5 for body. Avoid huge all-caps headlines.

### Geometry and motion

- Page max width: `1440px`; horizontal gutter: `20px` mobile, `32px` tablet, `48px` desktop.
- Base spacing unit: `4px`; normal rhythm: 8, 12, 16, 24, 32, 48, 72, 112.
- Radius: `0` everywhere. A `2px` radius is permitted for text inputs only.
- Border: `1px solid var(--line)`; use `2px solid var(--ink)` for a selected/sticky key action.
- Shadows: none. Depth comes from overlap, crops, rules, contrast, and the limited glass layers below.
- Motion: 120ms press/hover, 220ms panel reveal. Images may scale to `1.015`; do not bounce, float, shimmer, or animate continuously. Respect `prefers-reduced-motion`.

### Editorial glass (the exception)

Glass is an atmospheric layer, not the product’s personality. Apply it only where an element sits **above** live image or scrolling content:

```css
--glass-paper: rgb(244 240 232 / 76%);
--glass-ink: rgb(24 23 22 / 84%);
--glass-line: rgb(244 240 232 / 32%);

.glass-paper {
  background: var(--glass-paper);
  border: 1px solid rgb(255 255 255 / 34%);
  backdrop-filter: blur(18px) saturate(110%);
  -webkit-backdrop-filter: blur(18px) saturate(110%);
}

.glass-ink {
  background: var(--glass-ink);
  border: 1px solid var(--glass-line);
  backdrop-filter: blur(18px) saturate(105%);
  -webkit-backdrop-filter: blur(18px) saturate(105%);
}
```

The masthead is `glass-ink`; mobile menu, gallery counter, floating product action bar, and modal scrim panels are `glass-paper` or `glass-ink` depending on contrast. Keep blur at 18px or lower, use no coloured tint, no gradient, and provide an opaque `--paper` fallback when `backdrop-filter` is unsupported or reduced-transparency preferences are enabled.

## Layout primitives

### Global shell

Replace the existing long centered navigation with a 56px **masthead** using `glass-ink`:

`STYLESENSE / ISSUE 01` on the left, primary sections in the centre, `BAG [02]` and `ACCOUNT` on the right. It uses an ink background with paper text, a 1px paper rule, and no logo icon. On mobile, show the masthead plus `MENU`; open a full-height paper index with large numbered links.

Use a footer as a compact newspaper colophon: newsletter / support / privacy / Instagram-style social link / copyright. Do not repeat the primary nav or fill it with feature copy.

### Page grid

Desktop uses 12 columns with 24px gutters. Mobile uses 4 columns with 12px gutters. The three reusable compositions are:

1. **Editorial split:** 7-column image and 5-column copy/tool panel.
2. **Archive grid:** 4 / 3 / 5 columns, with varied image ratios (`3:4`, `4:5`, `1:1`) but an aligned metadata baseline.
3. **Workbench:** 3-column control rail and 9-column live result. On mobile the control rail becomes a bottom sheet or an open first section—not an icon drawer.

## Component system

### Buttons and links

Primary: square ink block, paper text, 48px height, `→` at the end. Example: `BUILD LOOK →`.

Secondary: transparent with a bottom rule, not an outlined rounded button. Example: `VIEW THE RACK →`.

Quiet / destructive actions are text links. Use the full word `REMOVE`, never a lone trash icon. An icon-only button is allowed only for `× Close` and must have an accessible label.

### Fields, filters, selection

Inputs are paper or white with an ink bottom border and a 16px value. Labels are 12px mono. On focus, add a 2px ink outline—not a glowing ring.

Filters are a left-aligned text list or a rectangular “tape” selection strip. Selected values are acid with ink text. Include a visible `CLEAR [N]` control. Do not hide essential filtering behind a funnel icon.

Swatches are 20px square with a 1px ink outline; selection adds a 2px offset outline. Always pair a swatch with an accessible colour name.

### Product tile

The product image is the tile. Below it: category / name / price on one coherent caption. Hover reveals a hard bottom action bar: `VIEW` and `ADD`. Ratings, fake review counts, hearts, and “quick view” eye icons are removed until their data is real and useful. Badges become flat mono labels: `NEW`, `LAST PIECE`, `PRICE DROP`.

### Look tile

Use a “contact sheet” composition: a large primary garment image with two smaller item crops attached to its edge. Caption gives occasion, source (`YOUR CLOSET` / `SHOP`), and `WHY IT WORKS`. Feedback is text: `KEEP`, `NOT FOR ME`, `WORE IT`—never thumb icons.

### Panels, modals, feedback

Panels use a paper/ink rule, not cards. Modals occupy the right third on desktop and full height on mobile, with a 2px ink left edge and a restrained glass surface only when they overlay imagery. Confirm destructive actions in an explicit two-step panel with human consequences.

Loading states use a static layout with `LOADING THE RACK…`; error states say what happened and offer a direct recovery action. No spinners as decorative centrepieces.

### Charts and data

Use a printed-data aesthetic: direct labels, thin grid rules, one acid bar/marker, and an adjacent text summary. No floating tooltips as the only way to read data; no rainbow charts.

## Screen-by-screen redesign

| Current route | New page title / job | New composition |
| --- | --- | --- |
| `/` | **Get dressed. Go somewhere.** | Full-bleed moving/image fashion story on the left; oversized campaign line and two text CTAs on the right. Below: a horizontal “Today’s pull” rail, then three editorial stories. Delete trust-icon row, fabricated metrics, generic category cards, and chatbot launcher. |
| `/shop` | **The rack** | Dense archive grid with a 3-column sticky filter rail. Search is a visible type field; selected filters form a top tape line. Results show real count and sorting as words. |
| `/shop/:id` and `/product/:id` | **Piece dossier** | Consolidate both duplicated product details into one route. Left: image strip; right: sticky product dossier with price, sizes, colour, delivery facts, and an unapologetic `ADD TO BAG →`. “Wear it with” is an editorial strip, not a recommendation card. |
| `/cart` | **Bag / [count]** | Editorial checkout ledger: line items on the left, total and delivery on a right ink panel. Quantity uses `− 01 +`; remove item is text. |
| `/login` | **Sign in to your rack** | Quiet two-column page: campaign crop and minimal auth form. OAuth is a named button, never a provider-logo pile. |
| `/style-onboarding` | **Set the brief** | Five numbered pages, no emojis and no “vibe”. Questions become `01 What do you reach for?`, `02 Colours you return to`, `03 Where are you going?`, `04 Your price range`, `05 Fit notes (optional)`. A left rail makes progress and privacy explicit. |
| `/wardrobe` | **Your rack** | 12-column closet archive. The first tile is a bold `+ ADD A PIECE` tile; filters are words. “Needs review” becomes `CHECK DETAILS`. Upload is a side panel that shows the photo large and fields in a deliberate vertical sequence. |
| `/outfits` | **The fitting room** | A workbench, not “AI Outfit Studio”: persistent brief rail on the left, generated look contact sheets on the right. Tabs become `BUILD / SAVED / GAPS`. Button reads `PULL LOOKS →`. Explainability stays in `WHY THIS WORKS`. |
| `/style-dna` | **Your pattern** | Rename the concept in UI. Show a personal “style receipt”: what you save, wear, and skip, as direct labelled bars. Reset becomes `START OVER` in a sober confirmation panel. |
| `/ai` | **Second opinion** | Conversational feature becomes a focused editorial prompt page. Large text input: `Describe the plan.` Suggested prompts are text examples, not sparkle chips. System responses are attributed as `STYLESENSE NOTES`; no bot avatar, no “AI is typing”. |
| `/settings` | **Account / terms** | Split list page: profile, closet data, permissions, export, account deletion. Privacy copy remains exact and calm. Do not use danger-zone red card theatrics. |
| `/about` | **The point of StyleSense** | A short editorial manifesto and factual methodology. Mention deterministic styling and optional external processing here, not in conversion surfaces. |
| `/admin` | **Stock room** | Separate functional staff shell with the same tokens, a denser mono table, visible state tags, and text actions. |
| `/admin/analytics` | **Store notes** | Same staff shell. Direct-label charts, date range as a field, no consumer storefront footer. |

## Mobile rules

- Preserve the masthead; do not compress every action into mystery icons.
- Make buy/build actions sticky at the bottom only on product and fitting-room pages.
- Product tiles become two columns; the image keeps a `3:4` crop.
- The closet upload and filters open as full-height sheets with a visible `× CLOSE` word control.
- Keep tap targets at least 44px. Never rely on hover to reveal add-to-bag.

## Accessibility and content quality

- Ink on paper meets WCAG AA; acid is never the only indicator of selection.
- The interface remains fully useful with images unavailable: meaningful image alt text, labels, and textual state.
- Use semantic headings, native labels, keyboard-visible focus, and logical source order even where desktop layout overlaps.
- User photo consent is separate, explicit, revocable, and written in plain language.
- Show real data only. Remove the homepage’s invented `1,200+`, `99.8%`, and technology marketing.

## Implementation map

1. Remove the duplicate root Next storefront from deployment scope or formally archive it. The documented production application is `frontend/`; leaving both live guarantees visual drift.
2. Replace `frontend/src/index.css` with the token layer above; delete gradient, float, shimmer, purple/pink variables, and generic card utility assumptions.
3. Rebuild `navigation.tsx`, `footer.tsx`, `button.tsx`, `product-card.tsx`, and the existing chat launcher first. These are the old UI’s most repeated visual fingerprints.
4. Consolidate `ProductDetailPage.tsx` and `ShopProductDetailPage.tsx` into a single product route before styling product detail.
5. Rebuild public commerce routes, then signed-in closet/fitting-room flows, then staff routes. Do not attempt a CSS skin over the current 204 gradient/icon/rounding/emoji references; the markup and content model need to change together.
6. Add visual regression screenshots at 390px, 768px, and 1440px for: home, shop, product, closet, fitting room, bag, onboarding, and settings.

## Acceptance checklist

- A first-time visitor can identify StyleSense as a fashion product before reading any technology claim.
- No sparkle, gradient, rounded-SaaS card, emoji, or generic dashboard icon remains in customer UI; frosted glass appears only on the three defined overlay roles.
- “AI” appears only where transparency requires it; never in the global nav, hero, or primary CTA.
- Every shopping, closet, and outfit action is readable as text without an icon.
- The same type, rule, spacing, and selected-state system appears in all 16 routes.
