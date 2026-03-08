# Skill: CSS Diagnosis

## When to activate
Any time a visual issue is reported â alignment, spacing, overflow, rendering, "looks weird", "something's off."

## Reasoning pattern
1. **VIEWPORT FIRST:** Identify the viewport. Is this mobile (375px), tablet (768px), or desktop (1440px)? If David sent a screenshot, determine which viewport from the dimensions. If unclear, ask.
2. **DOM TREE:** Think about the DOM structure. What's the parent container? What display mode (flex, grid, block)? What's the containing element?
3. **PARENT BEFORE CHILD:** 80% of alignment issues are parent container problems, not child element problems. Check `align-items`, `justify-content`, `flex-direction`, `gap` on the parent FIRST.
4. **MEDIA QUERIES:** Check if CSS changes at this breakpoint. Is there a competing rule? Does `styles.css` have a global rule that conflicts with a page-specific `<style>` block?
5. **CHECK STYLES.CSS FIRST:** Global styles are in `styles.css`. Page-specific styles are in `<style>` blocks at the top of each HTML file. Check global before local.
6. **VERIFY 3 VIEWPORTS:** After fixing, ALWAYS mentally verify the fix works on mobile (375px), tablet (768px), and desktop (1440px). If the fix uses pixel values, it probably breaks on other viewports.

## What NOT to do
- Don't just add `!important` â that's a band-aid, not a fix. Find the actual conflicting rule.
- Don't change one sibling element without checking the others in the same container.
- Don't assume the fix works on mobile just because it works on desktop.
- Don't use pixel values for spacing if the layout needs to be responsive â use rem, em, or percentages.

## Key knowledge
- Brand background: `#0a0f1a` (near-black)
- Brand cyan: `#00d4ff`
- Sidebar collapses at <=1100px on methodology pages
- `.prominent` class on sidebar headers = bigger, glowing white (12px, text-shadow glow)
- `.lab-divider` = thin 1px line between top 6 labs and rest

## Source
Seeded from brain.md COMMON FIX PATTERNS + DESIGN RULES. Version 1.0.
