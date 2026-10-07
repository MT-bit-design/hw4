# Usability improvements (Problem 9)

Four small improvements, all live in the running app and tested in the browser.

## 1. Sort by price + "In stock only" (Products page)

**What:** next to the search box and garment filter, a **Sort** menu (featured, price low → high, price high → low) and an **In stock only** checkbox. Both work together with search and the type filter. Sorting is stable, so items with the same price keep their A–Z order.

**Why it helps:**
- **Shoppers** on a budget see the $32 tees first; gift buyers can start from the $98 jackets. "In stock only" stops them falling for something they can't buy.
- **The business:** fewer dead-end clicks and an easier path to a sale.

**Tested:**
- **Sorting:** low → high runs $32 → $98 and high → low runs $98 → $32, in order across all 102 items. It also works with a type filter (18 pullover hoodies).
- **In stock only today:** every product has at least one size in stock, as the database confirms (0 of 102 fully sold out), so the checkbox hides nothing and shows 102 items.
- **In stock only, simulated:** with 3 items marked sold out in the browser only, it went from 102 to 99 and removed all 3 "Sold out" badges.

## 2. Quick-reply buttons (chat panel)

**What:** three tappable starters: "What hoodies do you have?", "Gifts under $40", and "Is my size in stock?". Tapping one sends it as a message. They disappear as soon as the shopper types or sends anything. They come back after Clear chat.

**Why it helps:**
- **Shoppers:** many don't know what a shop chatbot can do; the buttons show it in one tap, which matters most on a phone.
- **The business:** more shoppers start a conversation that leads to products.

**Tested:**
- **Visibility:** the buttons showed on open, hid while typing, and came back when the input was erased.
- **Sending:** tapping "Gifts under $40" sent it, and the reply put 25 gift options on the page.
- **After a reply:** the buttons were gone.

## 3. Search by size (new agent tool)

**What:** a `search_by_size` tool. "Hoodies in medium under $60" returns only products that **have that size in stock right now**, checked in the `inventory` table. It also gives the exact quantity in that size. Results go to the page like any search.

**Why it helps:**
- **Shoppers:** they stop finding a hoodie they love, only to see their size is sold out. The single most common follow-up question is answered up front.
- **The business:** fewer abandoned visits, and no promises the shop can't keep.

**Tested (browser + database):**
- **"hoodies in medium under $60":** 2 cards, both $45.00, with M stock 8 and 25. These are exactly the 2 matches in the database.
- **"What crewnecks do you have in XS?":** "showing 12 of 19". The database has 19 crewnecks with XS in stock, and every card's XS quantity is above 0. The **10 crewnecks with XS sold out were correctly left out**.

## 4. Price check on every reply

**What:** before a reply goes out, the server finds every dollar amount in it. Each one must match a price a tool returned in that conversation, or an amount the shopper typed (like their budget). If one doesn't, the agent is asked once to rewrite. If the rewrite still has an unverified amount, a safe fallback reply is sent. The product cards stay, because their prices come straight from the database.

**Why it helps:**
- **Shoppers:** they can trust every price they see.
- **The business:** a made-up price, total, discount, or shipping fee is a customer-service problem and a possible legal one. This is a hard, code-level guarantee on top of the prompt's "never guess" rule.

**Tested:**
- **Live:** "I have exactly $100… how much change would I get?" made the agent draft a computed amount. The server log shows "price check: 1 unverified amount(s); asking the agent to rewrite" → "rewrite passed". The shopper saw only "The Boola Boola T-Shirt is $32.00 each."
- **Unit tests:** `$96.00 total` and `today only $25` were flagged, while real prices and the shopper's own "$40" budget passed. A failed or erroring rewrite fell back to the safe message.
- **Trade-off:** harmless arithmetic (like a total for 3 shirts) is blocked too. The bot gives the unit price instead.
