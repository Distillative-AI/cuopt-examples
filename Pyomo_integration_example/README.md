# Pyomo Integration Example

This folder contains a Jupyter Notebook demonstrating how to integrate NVIDIA cuOpt as a solver backend for optimization problems modeled with Pyomo.

## About Pyomo

[Pyomo](https://www.pyomo.org/) is a Python-based open-source software package that supports a diverse set of optimization capabilities for formulating, solving, and analyzing optimization models.

## Using cuOpt with Pyomo

Pyomo supports cuOpt as a backend solver, allowing you to leverage GPU-accelerated optimization while using Pyomo's intuitive modeling syntax. This integration provides:

- **Familiar API**: Use Pyomo's pythonic syntax for modeling
- **GPU Acceleration**: Benefit from cuOpt's high-performance GPU-based solving
- **Easy Solver Switching**: Compare different solvers by simply changing the solver parameter

## Example Notebook

### `p_median_problem.ipynb`

This notebook demonstrates the classic p-median problem:
- **Problem**: Choosing facility locations to minimize the weighted distance while meeting assignment constraints.
- **Approach**: Model the problem using Pyomo and solve with cuOpt
- **Features**:
  - Setting up decision variables and constraints with Pyomo
  - Solving with setting `solver = pyo.SolverFactory("cuopt")` parameter
  - Analyzing and visualizing results