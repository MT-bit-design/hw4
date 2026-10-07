# Design (Problem 10): the fall storefront

Goal: make Campus Customs feel like a real, trustworthy shop, so people stay, find something, and buy. Only the look changed. The one data addition is a read-only `low_stock` flag on the products API so cards can show "Low stock".

## What changed, and why it helps

| Change | Details | Why it helps customers stay and buy |
|---|---|---|
| **Minimal white layout** | White background everywhere, thin gray dividers, generous white space, one spacing scale (0.5 / 1 / 1.5 / 2.5 / 4 / 6 rem) used on every page. | Products are the color on the page; nothing competes with them. Calm pages feel premium and are easier to scan. |
| **One type family** | `"Segoe UI", Carlito, Calibri, sans-serif` everywhere, including buttons and inputs. Big, bold headings (800 weight) and a muted gray for body copy. | Consistent and readable on Windows, Mac (Calibri/Carlito fallbacks), and phones. A clear hierarchy tells shoppers what to read first. |
| **Yale navy first, fall accents sparingly** | Navy for the brand, headings, prices, and buttons. Burnt orange `#c8571b`, deep red `#9b2226`, and gold `#c99a2e` only for leaves, small eyebrows, the active-link underline, and stock tags. | Instantly "Yale"; the fall accents add seasonal warmth without looking like a costume. Accents used rarely draw the eye to what matters (tags, the CTA area). |
| **Bold Home hero, one action** | "Bleed blue. Wear it proud." at up to 74 px, a short lede, and one button: **Shop fall favorites**. Simple SVG leaves drift slowly behind it. | One obvious next step; no choice paralysis. The motion is subtle and seasonal, so the page feels alive without distracting. |
| **Leaf details** | Small inline-SVG leaves (no image downloads) in section dividers, the footer, the "Picked for you" label, the perks, the chat header, and empty states ("Nothing matches that yet", 404, item not found). | Ties the whole site to the season. Empty states feel friendly and on-brand instead of broken, so shoppers try again instead of leaving. |
| **Cleaner product cards** | White cards with a thin border, a garment-type label, the name, a two-line description, and a bold navy price. Soft lift and shadow on hover, gentle 5% image zoom. | The price is easy to find. Hover feedback makes cards feel clickable, which leads to more product-page visits. |
| **"Sold out" / "Low stock" tags** | Small pill tags on the card image and next to the price on the single-item page. Low stock = 1–20 units left across all sizes (4 products today). Sizes with 1–3 left show "Only N left" in orange; sold-out sizes are crossed out in red. | Honest urgency ("Low stock") nudges a decision; clear "Sold out" avoids frustration at checkout. |
| **Single-item page polish** | Large image in a bordered frame (gentle zoom on hover; sticky beside the text on wide screens), a big price with its tag, a quiet "SIZES" label, and size tiles with clear available / low / sold-out states. | Everything needed to decide is visible in one glance: image, price, stock in your size. |
| **Gentle motion** | Pages fade up over 0.45 s; buttons, cards, and size tiles get smooth hovers; the chat panel slides in. | Feels polished and responsive. Durations are short, so the site never feels slow. |
| **Reduced motion respected** | With `prefers-reduced-motion: reduce`, all animations and transitions are turned off, the drifting leaves are hidden, and JS scrolling is instant (`motion.ts`). | Comfortable for shoppers who get motion sickness or find movement distracting. Required for accessibility. |
| **Chat panel** | Rounded 18 px bubbles (navy for the shopper, light gray for the assistant), a navy header with a small gold leaf, and an animated three-dot typing indicator (screen readers hear "The assistant is typing"). | The assistant feels like a friendly person at the counter. The typing dots show the bot is working, so shoppers wait instead of re-sending. |
| **Phones** | Below 820 px, the nav becomes a menu and the item page stacks. Below 560 px, there are 2 product columns, a full-width CTA, filters on their own rows, and a full-width chat panel. No sideways scrolling anywhere. | Most campus shoppers browse on their phones; everything stays readable and tappable. |

## Tested in the real browser

- **Wide (1200 px):**
  - **Home:** one CTA, 7 drifting leaves.
  - **Products:** 4 columns; 4 "Low stock" tags, the same 4 products the database has with 20 or fewer units.
  - **Single-item page:** two columns; for the Football tee, "Low stock", "Only 2 left" for S and L, and XS, M, and XL sold out, all matching the database.
  - **Chat:** typing dots appeared and went away; the reply was correct.
  - **About and Log in:** checked.
- **Narrow (375 px, phone):**
  - **Home:** full-width CTA, no sideways scroll.
  - **Menu:** shows all 5 links.
  - **Products:** 2 columns.
  - **Single-item page:** stacked.
  - **Chat:** panel spans the screen, with quick replies and typing dots.
  - **"Picked for you":** 12 of 27 hoodies.
  - **About, Log in, Create account, and 404:** checked.
- **Reduced motion:** applying the stylesheet's reduced-motion rules took running animations from 9 to 0, hid the leaves, and left all content fully visible.
- **Nothing broke:** login and logout, sorting, "In stock only", chat search to the page, page context ("5 in XXL" on the product page), and the size tiles all still work.
- **Two layout bugs found on the phone and fixed:**
  - The search-box styles were also hitting the "In stock only" checkbox, which blew it up to a huge pill with clipped text.
  - The chat header title and "Clear chat" wrapped onto two lines; they now stay on one line, and the title is shortened with "…".
