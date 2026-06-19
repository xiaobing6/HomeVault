# Phase 2 Known Limitations

- Residence names are currently enforced as globally unique by the Phase 2
  database migration and service layer. The product rule is active-only
  uniqueness, so a later management-enhancement migration should relax the
  database constraint before inactive residence names can be reused safely.
