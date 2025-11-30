# Capacitated Facility Location Optimization

A Mixed Integer Linear Program (MILP) example for optimizing distribution center (DC) placement and customer assignment to minimize total logistics cost.

## Problem Overview

A logistics company needs to determine:
- Which distribution centers (DCs) to open from a set of candidate locations
- How to assign customers to open DCs
- How to balance fixed operating costs with transportation costs

**Goal**: Minimize total annualized logistics cost while meeting demand and respecting capacity constraints

## Model Assumptions

**Important**: This model uses the following assumptions:

1. **Single assignment**: Each customer is assigned to exactly one DC
2. **Capacity limits**: Each DC has a maximum pallet-handling capacity
3. **Fixed costs**: Opening a DC incurs a fixed annual operating cost
4. **Known demand**: Customer demand is deterministic and known
5. **Euclidean distances**: Transportation costs are proportional to straight-line distance

This formulation works well for:
- Distribution network design
- Warehouse location planning
- Supply chain optimization
- Retail store placement

**Note**: Extensions include multi-period capacity expansion and fractional (LP relaxed) assignments.

## Notebook Contents

### Setup & Data
- 5 candidate distribution centers
- 20 customers with varying demand
- Synthetic 2D coordinates for visualization
- Transportation cost proportional to distance ($0.05/pallet-km)
- Fixed DC operating costs (~$80,000-$120,000)

### Optimization
- **Decision Variables**: 
  - DC open/close binaries (y_i)
  - Customer assignment binaries (x_ij)
- **Objective**: Minimize fixed costs + transportation costs
- **Constraints**: 
  - Assignment: Each customer assigned to exactly one DC
  - Capacity: DC load cannot exceed capacity
  - Linking: Customers can only be assigned to open DCs

### Results & Analysis
- Optimal DC selection and network design
- Customer-to-DC assignment matrix
- DC utilization rates
- Cost breakdown (fixed vs. transportation)
- Network visualization with assignment arcs

### Extensions
- **LP Relaxation**: Fractional assignments for lower bound analysis
- **Multi-Period Expansion**: Time-phased DC opening decisions with discounting

## Installation

**Requirements**: 
- NVIDIA GPU with CUDA 12 or 13 support
- Python 3.9+

**Install cuOpt** (choose one based on your CUDA version):

```bash
# For CUDA 12
pip install --upgrade --extra-index-url=https://pypi.nvidia.com cuopt-cu12

# For CUDA 13  
pip install --upgrade --extra-index-url=https://pypi.nvidia.com cuopt-cu13
```

**Install visualization dependencies**:

```bash
pip install matplotlib seaborn
```

## Quick Start

```bash
jupyter notebook cflp_cuopt_milp.ipynb
```

The notebook includes GPU detection and will guide you through any missing dependencies.

## Possible Extensions

**Multi-Period Planning** (included in notebook):
- Open DCs over multiple time periods
- Time-discounted costs
- Time-varying demand with growth rates
- Capacity expansion decisions

**Additional**:
- Multiple DC capacity tiers
- Product-specific assignment
- Stochastic demand scenarios
- Service level constraints (max distance)
- Multi-echelon supply chain
- Inventory considerations

