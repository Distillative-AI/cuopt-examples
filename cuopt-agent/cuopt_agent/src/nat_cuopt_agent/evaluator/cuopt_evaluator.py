# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""NAT custom evaluator for cuOpt optimization workflow outputs.

Matches evaluation logic from evaluation/evaluate.py: extracts objective value
from \\boxed{...} in workflow output, compares to ground truth with relative
tolerance, returns binary score.
"""

import re
from typing import override

from nat.builder.builder import EvalBuilder
from nat.builder.evaluator import EvaluatorInfo
from nat.cli.register_workflow import register_evaluator
from nat.data_models.evaluator import EvaluatorBaseConfig
from nat.plugins.eval.evaluator.base_evaluator import BaseEvaluator
from nat.plugins.eval.evaluator.evaluator_model import EvalInputItem, EvalOutputItem
from pydantic import Field

DEFAULT_BOXED_PATTERN = r"\\boxed\{([^}]+)\}"
DEFAULT_TOLERANCE = 1e-6


class CuoptEvaluatorConfig(EvaluatorBaseConfig, name="cuopt_objective"):
    """Configuration for cuOpt objective value evaluator."""

    tolerance: float = Field(
        default=DEFAULT_TOLERANCE,
        description="Relative tolerance for comparing predicted vs expected objective value",
    )
    boxed_pattern: str = Field(
        default=DEFAULT_BOXED_PATTERN,
        description="Regex with one capture group to extract the predicted value from workflow output",
    )


def _extract_predicted_answer(output_obj: str | None, pattern: re.Pattern[str]) -> str | None:
    """Extract value from workflow output using the given regex pattern."""
    if output_obj is None:
        return None
    match = pattern.search(str(output_obj))
    return match.group(1).strip() if match else None


def _score(expected: float, predicted: str | None, tolerance: float) -> int:
    """Return 1 if relative error < tolerance, else 0."""
    if predicted is None:
        return 0
    try:
        pred_float = float(predicted)
        rel_error = abs(float(expected) - pred_float) / abs(float(expected))
        return int(rel_error < tolerance)
    except (TypeError, ValueError):
        return 0


class CuoptEvaluator(BaseEvaluator):
    """Evaluator that scores cuOpt workflow outputs by comparing objective values."""

    def __init__(
        self,
        tolerance: float = DEFAULT_TOLERANCE,
        boxed_pattern: str = DEFAULT_BOXED_PATTERN,
        max_concurrency: int = 4,
    ):
        super().__init__(
            max_concurrency,
            tqdm_desc="Evaluating cuOpt objective",
        )
        self.tolerance = tolerance
        self._boxed_re = re.compile(boxed_pattern)

    @override
    async def evaluate_item(self, item: EvalInputItem) -> EvalOutputItem:
        expected = item.expected_output_obj
        output_obj = item.output_obj
        predicted = _extract_predicted_answer(output_obj, self._boxed_re)
        score_val = _score(expected, predicted, self.tolerance)

        try:
            expected_float = float(expected)
            pred_float = float(predicted) if predicted else None
            rel_error = abs(expected_float - pred_float) / abs(expected_float) if pred_float is not None else None
        except (TypeError, ValueError):
            rel_error = None

        reasoning = {
            "expected": expected,
            "predicted": predicted,
            "relative_error": rel_error,
            "tolerance": self.tolerance,
        }
        return EvalOutputItem(id=item.id, score=score_val, reasoning=reasoning)


@register_evaluator(config_type=CuoptEvaluatorConfig)
async def register_cuopt_evaluator(config: CuoptEvaluatorConfig, builder: EvalBuilder):
    """Register cuOpt objective evaluator with NAT."""
    evaluator = CuoptEvaluator(
        tolerance=config.tolerance,
        boxed_pattern=config.boxed_pattern,
        max_concurrency=builder.get_max_concurrency(),
    )
    yield EvaluatorInfo(
        config=config,
        evaluate_fn=evaluator.evaluate,
        description="CuOpt objective value evaluator (\\boxed{...} vs ground truth)",
    )
