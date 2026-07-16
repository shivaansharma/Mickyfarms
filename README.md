Micky Farms Management System
An advanced, enterprise-grade Agricultural Resource Planning (ERP) platform built on the Frappe Framework. Micky Farms unifies precise livestock genetic lineage tracking with multi-sector operational frameworks covering dairy logistics, crop rotation cycles, deep inventory management, and data-driven business intelligence reports.

🏗️ Core Operational Modules
The codebase is organized into four major functional domains:

1. Advanced Livestock & Breeding Registry
Hierarchical Family Trees (animal): Implements Frappe's native is_tree nested-set database architecture to track recursive genetic lineages (Dam/Sire linkages) without recursive query overhead.

Dynamic Lactation State Engine (animal.js): Client-side hooks automatically upgrade animal taxonomy and states (e.g., auto-transitioning a Heifer to a Cow upon entry of a breading_date, and switching states dynamically between Pregnant, Milking, and Dry based on logging gaps).

Breed Standardization Profile (breed): Normalizes breed variations to track lineage production characteristics across the herd.

Auditable Breeding Sub-Grid (animal_pregnancy_log): Child table system tracking infinite individual life cycles over historical parameters.

Clinical Intervention Audits (doctor_log): Tracks veterinarian actions, medical treatments, vaccines, and localized health protocols per animal block.

2. Commercial Dairy Operations & Yield Logistics
High-Volume Yield Auditing (bulk_milking_log & _item): Collects shift-wide milking metrics across sessions, linking yields back to targeted farm sections.

Milk Production Report: Compiles raw milk yield volumes across shifts to track seasonal performance trends, herd productivity, and peak lactation windows.

Milk Payment Summary Report: Audits financial data from commercial milk sales, tracking revenues against delivery volumes.

3. Crop Lifecycle & Plot-Based Inventory Control
Acreage Asset Mapping (plot & crop_plot): Defines geometric parameters for farm sectors, assigning target fields cleanly to either crop growth zones or cattle grazing pastures.

Rotation Schedule Management (crop_cycle): Audits soil utility timelines, fertilization routines, crop growth milestones, and projected harvest windows.

Granular Asset Auditing (plot_material_log): Provides a continuous ledger tracking physical item usage across land sectors.

Material Allocation (material_issue_by_plot & _non_plot): Tracks localized feed, seed, and fertilizer deployment to individual plots, separating general farm consumption from direct cultivation inputs.

4. Supply Chain, Workforce, & Financial Analytics
Internal Logistics Routing (internal_purchase_request & _item): Manages internal material requisitions before generating official purchase orders.

Internal Purchase Request Tracking Report: A real-time audit grid monitoring open vs. fulfilled supply requisitions across farm sectors.

Contractual Labor Allocation (employee_contract & _plot): Binds staff tasks to concrete land zones or specific livestock operations for transparent efficiency analytics.

Weekly Financial Settlements (weekly_wage, weekly_wage_payment, & _line_item): Calculates structural payroll calculations, attendance matrices, field labor payouts, and raw material vendor accounts.

Doctor Expense Report: Tracks clinical overhead, medicine costs, and professional veterinarian fees to isolate total livestock health expenditure.

Supplier Account Statement: Generates deep, auditable accounting ledgers tracking pending vendor balances, settlements, and historical transactions.
