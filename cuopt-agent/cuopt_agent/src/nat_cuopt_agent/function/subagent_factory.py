# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
# ß
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

from nat.builder.builder import Builder
from nat.builder.framework_enum import LLMFrameworkEnum
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.component_ref import FunctionRef, LLMRef
from nat.data_models.function import FunctionBaseConfig
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ToolCallLimit(BaseModel):
    tool_name: str
    call_limit: int


class SubAgentFactory(FunctionBaseConfig, name="subagent_factory"):
    """Configuration for a DeepAgents subagent, registered as a NAT function.

    Each instance resolves its own LLM and tools via the Builder at startup,
    then yields a callable that returns the subagent dict expected by
    ``create_deep_agent(subagents=[...])``.
    """

    agent_name: str = Field(
        description="Unique subagent name (used by the orchestrator's task() tool for delegation).",
    )
    description: str = Field(
        description="Description of what this subagent does. The orchestrator reads this to decide when to delegate.",
    )
    system_prompt: str = Field(
        default="",
        description="Behavioral instructions for this subagent. Empty = no system prompt.",
    )
    tools: list[FunctionRef] = Field(
        default_factory=list,
        description="Tool function references available to this subagent. Resolved via Builder at startup.",
    )
    model: LLMRef = Field(
        description="LLM reference for this subagent (resolved via Builder).",
    )
    skills: list[str] = Field(
        default_factory=list,
        description="Skill paths (relative to sandbox) available to this subagent.",
    )
    memory: list[str] = Field(
        default_factory=list,
        description="Memory file paths (relative to sandbox) available to this subagent.",
    )
    tool_call_limits: list[ToolCallLimit] = Field(
        default_factory=lambda: [
            ToolCallLimit(tool_name="edit_file", call_limit=5),
            ToolCallLimit(tool_name="read_file", call_limit=30),
            ToolCallLimit(tool_name="write_file", call_limit=5),
            ToolCallLimit(tool_name="execute", call_limit=5),
        ],
        description="Tool call limits for this subagent. Default is no limits.",
    )


@register_function(config_type=SubAgentFactory, framework_wrappers=[LLMFrameworkEnum.LANGCHAIN])
async def subagent_factory(config: SubAgentFactory, builder: Builder):

    llm = await builder.get_llm(config.model, wrapper_type=LLMFrameworkEnum.LANGCHAIN)

    tools = await builder.get_tools(config.tools, wrapper_type=LLMFrameworkEnum.LANGCHAIN)

    sub_agent_dict: dict = {
        "name": config.agent_name,
        "description": config.description,
        "tools": tools,
        "model": llm,
        "memory": config.memory,
        "middleware": [],
    }
    if config.system_prompt:
        sub_agent_dict["system_prompt"] = config.system_prompt
    if config.skills:
        sub_agent_dict["skills"] = config.skills

    async def _inner(unused: str | None = None) -> dict:
        """Subagent factory function that returns a dictionary of subagent configuration.
        Args:
            unused: Unused parameter.
        Returns:
            A dictionary of subagent configuration.
        """
        return {**sub_agent_dict, "middleware": list(sub_agent_dict["middleware"])}

    yield FunctionInfo.from_fn(_inner, description=config.description)
