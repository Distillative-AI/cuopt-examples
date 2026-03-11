## Scenario

The current max supply model treats constrained supply as an **upper bound** — the solver
may procure *up to* the quantity in `supply.csv` each period. In reality, these
quantities represent confirmed purchase orders: the material **will** arrive
regardless of whether we need it. Unused arrivals accumulate as inventory.

## Request

Change the supply constraint so that, for every procured item in a constrained
family, the buy quantity **equals** the supply schedule rather than being bounded
by it:

```
buy[i, t] = S[i, t]    (instead of buy[i, t] <= S[i, t])
```

Re-run the optimisation with the sample dataset (10 periods) and
analyse the impact:

1. How does the objective value change compared to the baseline?
2. Which raw materials accumulate excess inventory, and in which periods?
3. Does forcing full procurement create any downstream bottleneck shifts
   (e.g., resource capacity becoming the binding constraint instead of supply)?

Highlight any periods where the solver was previously choosing to buy less
than the available supply, and explain why.