## Scenario
A manufacturing plant produces one finished good — **Finished Good Alpha (FG1)** — from raw materials through a multi-level bill of materials (BOM). The plant operates over a **10-period planning horizon** and must determine production schedules, procurement quantities, and resource allocation to **maximise the inventory of FG1 at the end of the horizon**.

The plant tracks five items across three tiers:

| Item | Name | Family |
|------|------|--------|
| FG1 | Finished Good Alpha | Finished Goods |
| SA1 | Subassembly X | Subassemblies |
| SA2 | Subassembly Y | Subassemblies |
| RM1 | Raw Material 1 | Raw Materials Group 1 |
| RM2 | Raw Material 2 | Raw Materials Group 2 |

Each item belongs to a product family. Families are classified as either **constrained** or **unconstrained**, which affects procurement limits and resource capacity enforcement:

| Family | Constrained? |
|--------|:------------:|
| Finished Goods | Yes |
| Subassemblies | Yes |
| Raw Materials Group 1 | Yes |
| Raw Materials Group 2 | No |

The rules are:
- Procured items in **constrained** families have procurement capped by a per-period supply schedule. Items not listed in the supply schedule have zero available supply.
- Procured items in **unconstrained** families have unlimited supply (no upper bound on procurement).
- Processes whose outputs all belong to **unconstrained** families do not consume resource capacity.
- Processes with at least one output in a **constrained** family are subject to resource capacity limits.

Three manufacturing processes transform inputs into outputs. Each process has a lead time (in periods) and consumes resource-hours per unit of execution:

| Process | Name | Lead Time (periods) | Hours per Unit |
|---------|------|:-------------------:|:--------------:|
| PROC1 | Make Subassembly X | 1 | 0.5 |
| PROC2 | Make Subassembly Y (co-production) | 1 | 0.3 |
| PROC3 | Assemble Finished Good Alpha | 2 | 1.0 |

The bill of materials defines inputs consumed and outputs produced per unit of process execution. All yield losses are already baked into these coefficients:

**Process Inputs (consumed per unit of process execution):**

| Process | Item | Quantity |
|---------|------|:--------:|
| PROC1 | RM1 | 2.2 |
| PROC2 | RM2 | 3.0 |
| PROC3 | SA1 | 2.0 |
| PROC3 | SA2 | 3.0 |

**Process Outputs (produced per unit of process execution):**

| Process | Item | Quantity |
|---------|------|:--------:|
| PROC1 | SA1 | 1.0 |
| PROC2 | SA2 | 1.8 |
| PROC2 | SA1 | 0.5 |
| PROC3 | FG1 | 1.0 |

Note that PROC2 is a **co-production** process: it simultaneously produces both SA2 (primary output) and SA1 (co-product). Production output may be fractional; only the **integer floor** of fractional production is usable. The fractional surplus is lost. For example, if a process produces 7.9 units, only 7 are usable.

Two machine lines provide capacity. Each unit of a process requires exactly one resource to complete, but a process may be eligible to run on more than one resource. The solver decides how many units to assign to each eligible resource in each period, and each resource's allocated units consume that resource's capacity independently. The eligible resource assignments are:

| Process | Resource |
|---------|----------|
| PROC1 | RES1 |
| PROC2 | RES1 |
| PROC2 | RES2 |
| PROC3 | RES2 |

Available resource hours per period:

| Period | RES1 (Machine Line A) | RES2 (Machine Line B) |
|:------:|:---------------------:|:---------------------:|
| 1 | 40 | 60 |
| 2 | 40 | 60 |
| 3 | 40 | 60 |
| 4 | 40 | 60 |
| 5 | 40 | 30 |
| 6 | 40 | 60 |
| 7 | 40 | 60 |
| 8 | 40 | 60 |
| 9 | 40 | 60 |
| 10 | 40 | 60 |

Note that RES2 has reduced capacity in period 5 (30 hours instead of 60).

Procurement of raw materials in constrained families is limited by the following supply schedule:

| Period | RM1 |
|:------:|:---:|
| 1 | 100 |
| 2 | 120 |
| 3 | 100 |
| 4 | 80 |
| 5 | 100 |
| 6 | 100 |
| 7 | 120 |
| 8 | 100 |
| 9 | 80 |
| 10 | 100 |

RM2 belongs to the unconstrained family Raw Materials Group 2, so it has unlimited supply.

The objective is to **maximise FG1 inventory at the end of period 10**.

**Timing rules:**
- A process started in period $t$ consumes its input materials immediately (in period $t$) and delivers output in period $t + \text{lead\_time}$.
- Processes cannot start before period 1.
- All items begin with **zero inventory** at the start of the horizon.

**Constraints summary:**
1. **Initial inventory** — all items start at zero.
2. **Production definition** — total production of an item in period $t$ equals the sum over all processes that produce it, accounting for lead time and yields.
3. **Floor truncation** — usable production is the integer floor of fractional production.
4. **Material balance** — for every item and period: ending inventory = beginning inventory + inflows (procurement or usable production) − consumption by processes starting in that period.
5. **Supply limits** — procurement of constrained-family items is bounded by the supply schedule.
6. **Resource capacity** — total resource-hours used by constrained processes on each resource per period cannot exceed available hours.

Formulate this as a Mixed-Integer Linear Program and determine the production and procurement plan that maximises FG1 final inventory.
