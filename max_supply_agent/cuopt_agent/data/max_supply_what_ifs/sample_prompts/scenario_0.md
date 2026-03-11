## Scenario

The our max supply model currently assumes zero on-hand inventory at the start of the planning
horizon. In practice, our warehouse already holds stock from previous cycles.

## Request

We have the following opening balances at `t = 0`:

| Item | On-hand quantity |
|------|-----------------|
| SA1  | 40              |
| RM1  | 250             |
| RM3  | 180             |

Update the model so that these items start with the given inventory levels
instead of zero. All other items should remain at zero.

Re-run the optimisation with the sample dataset (10 periods) and
compare the results against the baseline:

1. How does the objective value change?
2. Which buy orders are reduced or eliminated in early periods?
3. Does the final-product mix shift (more FG1, more FG2, or both)?

Summarise the before/after in a concise table.