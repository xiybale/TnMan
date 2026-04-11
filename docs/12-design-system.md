# Design System

## Target Feel

The UI should feel like a premium sports analytics product, not a CRUD dashboard and not a generic Tailwind starter.

## Visual Direction

- strong scoreboard hierarchy
- compact data density
- editorial player cards
- high-contrast stat comparison components
- restrained motion used for reveal and emphasis

## Color Direction

- primary background: deep graphite or dark green-black
- secondary surfaces: muted slate panels with subtle transparency
- accent family: tennis-ball yellow, clay orange, and cool grass green used intentionally
- critical outcomes: red for double faults and collapses, blue or green for control and edge

## Typography

- use a display face for score headers and match cards
- use a highly legible sans family for dense stats tables
- keep numerals aligned for scoreboards and stat matrices

## Component Inventory

- app shell
- top nav
- roster table
- player card
- skill bar group
- compare delta row
- scoreboard header
- set stat table
- game accordion
- point row
- shot sequence drawer
- batch metric tiles
- distribution chart panels

## Interaction Rules

- surfaces should be selectable from a persistent control group
- recent simulations should be one click away
- compare and simulate actions should be available from the player browser
- point rows should expand to show shot-level detail
- mobile layouts should collapse dense tables into stacked stat cards without losing score context

## Motion

- use staged page reveals for main sections
- animate score and stat deltas, not every UI element
- use quick expand and collapse for games and point details

## Accessibility

- keyboard access for every interactive panel
- clear focus styles
- sufficient contrast on dense stat panels
- no information conveyed by color alone
