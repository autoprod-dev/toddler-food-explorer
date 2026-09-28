# Toddler Food Explorer

A private, on-device food exposure and food chaining tracker for your little one. Log each food offered (ate / touched / refused), see which foods are accepted or still being worked on, and get gentle food chaining suggestions based on foods your child already eats.

Single self-contained file: index.html (open in any browser; data stays on the device in localStorage key `toddlerFoodExplorer.v1`; data from an older `*FoodExplorer.v1` key is migrated automatically and the old key is kept). Export/Import backups use JSON files named `toddler-food-log-YYYY-MM-DD.json`.

This is a tracker, not medical advice. Talk to your GP, child health nurse or a paediatric dietitian about feeding concerns. Some foods are choking hazards for children under 3 (whole nuts, whole grapes, popcorn, hard raw vegetables): cut, grate, squash or cook foods to a safe size and texture, and always supervise.

Tests: `python3 tests/e2e_playwright.py` (Playwright + Chromium). Date-dependent checks assume the run date is 2026-09-29.
