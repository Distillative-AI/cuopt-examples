## Scenario

We have just received notice of a one-time spot-buy shipment: **500 units of a
new material RM4** arriving in **week 2**. RM4 is chemically compatible with RM1
and can substitute for it in any process where RM1 is consumed, using the same
input quantities. However, RM4 should only be used when RM1 inventory is
insufficient to cover demand in a given period.

## Request

Make the necessary data and model changes to support this:

1. **Data** — Add RM4 as a new procured item (assign it to an appropriate
   family). Create a supply entry for 500 units in period 2 only.

2. **Model** — Introduce substitution logic so that any process consuming RM1
   can alternatively consume RM4 at the same rate. The solver should prefer
   using RM1 first and fall back to RM4 only when RM1 is not available in
   sufficient quantity.

   *Hint: one approach is to add a small penalty to RM4 usage in the objective
   so the solver naturally prefers RM1 while still allowing substitution.*

3. **Run** — Solve the updated model with the sample dataset (10 periods).

Analyse the results:

1. In which periods is RM4 actually consumed, and by which processes?
2. How does the additional material improve the objective value?
3. Does RM4 inventory carry across multiple periods, or is it consumed quickly?
4. What would happen if the shipment were moved to week 5 instead of week 2?