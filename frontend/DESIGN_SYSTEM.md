# AI-RMMS Frontend Design System

Inspired by modern product UI practice (clear hierarchy, calm surfaces, strong focus states) and applied in-repo — not dependent on external design SaaS.

## Foundations
- Brand blue (`--color-brand-600`, `--color-brand-700`) for primary actions and selected navigation.
- White cards on a light slate application background.
- Inter/system sans-serif; primary text slate 900, secondary slate 600, muted slate 500.
- Use the 4px-based `--space-*` tokens for consistent spacing.
- Use 10px controls and 16px cards, with subtle elevation and clear borders.
- Keep the department shell responsive below 900px and compact below 640px.

## Interaction and accessibility
- Keyboard focus remains visible on links, buttons and form fields.
- Inputs, selects and buttons have a minimum 44px touch height.
- Form fields require labels, validation messages and clear error states.
- Do not use color alone to convey status; pair badges with text.
- Respect reduced-motion preferences.
- Use semantic HTML and preserve logical heading order.

## Department workspace pattern
1. Department-specific navigation and page title.
2. Overview with live data and loading, empty and error states.
3. Searchable, filterable records with pagination for large datasets.
4. Detail views with history and attachments where relevant.
5. Validated create/edit forms and confirmation for destructive actions.
6. Reports and exports protected by department permissions.

## Completion criteria
A dashboard card is not a complete module. Mark a module complete only when list/detail/create/update flows, API integration, authorization, error/empty/loading states and tests are implemented.
