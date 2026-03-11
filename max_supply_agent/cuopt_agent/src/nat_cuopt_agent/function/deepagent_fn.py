# SPDX-FileCopyrightText: Copyright (c) 2024-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

import logging
import os
import re
from pathlib import Path
from tempfile import TemporaryDirectory

from nat.builder.builder import Builder
from nat.builder.framework_enum import LLMFrameworkEnum
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.api_server import ChatRequest, ChatRequestOrMessage, ChatResponse, Usage
from nat.data_models.component_ref import FunctionRef, LLMRef
from nat.data_models.function import FunctionBaseConfig
from nat.utils.type_converter import GlobalTypeConverter
from pydantic import Field

logger = logging.getLogger(__name__)


class OrchestratorAgentConfig(FunctionBaseConfig, name="deepagent_fn"):
    """Langchain DeepAgents agent that delegates to subagents via create_deep_agent.

    Subagents are defined as separate NAT functions (``subagent_factory``)
    in the YAML ``functions:`` section and referenced here by name.
    """

    llm_name: LLMRef = Field(
        description="The name of the configured LLM to use for the orchestrator.",
    )
    description: str = Field(
        default="Orchestrator agent",
        description="Function description.",
    )
    skills_dir: list[Path] | Path | None = Field(
        default=None,
        description=(
            "Directory or list of directories (relative to cwd or absolute) whose "
            "skill sub-folders are merged into .skills/ in the sandbox."
        ),
    )
    agents_md_path: Path | None = Field(
        default=None,
        description="Path to AGENTS.md (relative to cwd or absolute) copied into the sandbox.",
    )
    skills: list[str] | None = Field(
        default=None,
        description=(
            "Skill paths passed to create_deep_agent (relative to sandbox). "
            "None = auto ([SANDBOX_SKILLS_DIR] if skills_dir resolved, else []). "
            "Explicit [] = no skills even if skills_dir exists."
        ),
    )
    memory: list[str] | None = Field(
        default=None,
        description=(
            "Memory file paths passed to create_deep_agent (relative to sandbox). "
            "None = auto ([SANDBOX_AGENTS_MD] if agents_md resolved, else []). "
            "Explicit [] = no memory even if AGENTS.md exists."
        ),
    )
    tools: list[str] = Field(
        default_factory=list,
        description="Additional tool names passed to create_deep_agent. Default [] = built-in backend tools only.",
    )
    subagents: list[FunctionRef] = Field(
        default_factory=list,
        description=(
            "References to sub_agent_factory functions defined in the YAML functions: section. "
            "Each is resolved via builder.get_function() at startup and yields a subagent dict "
            "passed to create_deep_agent(subagents=[...])."
        ),
    )
    workspace_dirs: list[Path] = Field(
        default_factory=list,
        description=(
            "Directories whose files are copied into the sandbox root at invocation time. "
            "Use for data files (CSVs, scripts) the agent should have access to."
        ),
    )
    system_prompt: str = Field(
        default="",
        description=(
            "System prompt for the orchestrator agent. "
            "Use for coordination instructions, delegation guidance, or output formatting. "
            "Empty string = no system prompt."
        ),
    )
    venv_path: Path | None = Field(
        default=None,
        description="Path to venv for sandbox (None = inherit_env only, e.g. in container).",
    )
    max_retries: int = Field(
        default=2,
        description="Max retry attempts for transient LLM failures (429, 5xx, timeouts).",
    )
    retry_backoff_factor: float = Field(
        default=2.0,
        description="Exponential backoff multiplier between retries.",
    )
    retry_initial_delay: float = Field(
        default=1.0,
        description="Initial delay in seconds before first retry.",
    )
    retry_max_delay: float = Field(
        default=60.0,
        description="Maximum delay cap in seconds between retries.",
    )
    strip_reasoning_pattern: str = Field(
        default=r"<think>.*?</think>\s*|<think>.*",
        description=(
            "Regex pattern (re.DOTALL) to strip from the final response. "
            "Matches are removed before returning to the caller. "
            "Set to empty string to disable stripping."
        ),
    )


@register_function(config_type=OrchestratorAgentConfig, framework_wrappers=[LLMFrameworkEnum.LANGCHAIN])
async def orchestrator_agent(config: OrchestratorAgentConfig, builder: Builder):
    import psutil
    from deepagents import create_deep_agent
    from deepagents.backends.local_shell import LocalShellBackend
    from deepagents.middleware.memory import MemoryMiddleware
    from langchain.agents.middleware.model_retry import ModelRetryMiddleware

    from .utils import (
        SANDBOX_AGENTS_MD,
        SANDBOX_SKILLS_DIR,
        FixToolNamesMiddleware,
        kill_orphaned_children,
        populate_sandbox,
        resolve_skills_dirs,
        strip_pattern,
    )

    # resolve skills directories
    skills_src_dirs = resolve_skills_dirs(config.skills_dir)

    # resolve agents_md_path
    agents_md_src: Path | None = None
    if config.agents_md_path:
        candidate = Path(config.agents_md_path)
        if candidate.is_file():
            agents_md_src = candidate
        else:
            logger.warning("agents_md_path not found (cwd=%s): %s", Path.cwd(), candidate)

    logger.info("Resolved skills dirs: %s", skills_src_dirs or "(none)")
    logger.info("Resolved AGENTS.md: %s", agents_md_src or "(none)")

    # Instantiate LLM with NAT builder
    llm = await builder.get_llm(config.llm_name, wrapper_type=LLMFrameworkEnum.LANGCHAIN)

    # Resolve venv path if provided for use in sandbox
    env: dict[str, str] = {}
    if config.venv_path is not None:
        venv = Path(config.venv_path)
        env = {
            "PATH": f"{venv / 'bin'}:{os.environ.get('PATH', '')}",
            "VIRTUAL_ENV": str(venv),
        }

    # Resolve effective skills and memory paths used in agent configuration
    effective_skills = config.skills if config.skills is not None else ([SANDBOX_SKILLS_DIR] if skills_src_dirs else [])
    effective_memory = config.memory if config.memory is not None else ([SANDBOX_AGENTS_MD] if agents_md_src else [])

    # Workaround to strip reasoning patterns from the final response with minimax model
    strip_re = re.compile(config.strip_reasoning_pattern, re.DOTALL) if config.strip_reasoning_pattern else None

    # Inner function that handles the agent invocation and response processing
    async def _inner(chat_request_or_message: ChatRequestOrMessage) -> ChatResponse | str:
        """Inner function that handles the agent invocation and response processing.
        Args:
            chat_request_or_message: The chat request or message to process.
        Returns:
            A chat response or string.
        """
        chat_request = GlobalTypeConverter.get().convert(chat_request_or_message, to_type=ChatRequest)
        messages = [m.model_dump() for m in chat_request.messages]

        # Create a temporary sandbox directory for the agent
        # Note execute tool will create files on host, a more robust sandbox should be used for production.
        with TemporaryDirectory() as sandbox_dir:
            sandbox = Path(sandbox_dir)

            populate_sandbox(sandbox, skills_src_dirs, agents_md_src, config.workspace_dirs)

            # Create a local shell backend for the agent
            backend = LocalShellBackend(
                root_dir=sandbox,
                virtual_mode=True,
                inherit_env=True,
                env=env,
            )

            # create subagent dictionaries
            sub_agent_dicts: list[dict] = []
            for ref in config.subagents:
                fn = await builder.get_function(ref)
                sa_dict = await fn.ainvoke(None)
                memory = sa_dict.pop("memory")
                sa_dict["middleware"].append(MemoryMiddleware(backend=backend, sources=memory))
                sub_agent_dicts.append(sa_dict)

            logger.info(
                "Resolved %d subagent(s): %s", len(sub_agent_dicts), [sa.get("name", "?") for sa in sub_agent_dicts]
            )

            # Create a middleware chain for the agent to improve reliability and performance
            middleware = [
                FixToolNamesMiddleware(),
                ModelRetryMiddleware(
                    max_retries=config.max_retries,
                    backoff_factor=config.retry_backoff_factor,
                    initial_delay=config.retry_initial_delay,
                    max_delay=config.retry_max_delay,
                    jitter=True,
                    on_failure="continue",
                ),
            ]

            # Create a dictionary of agent configuration arguments, including subagents if configured
            agent_kwargs: dict = dict(
                tools=config.tools,
                model=llm,
                backend=backend,
                middleware=middleware,
                subagents=sub_agent_dicts,
            )
            if config.system_prompt:
                agent_kwargs["system_prompt"] = config.system_prompt
            if effective_skills:
                agent_kwargs["skills"] = effective_skills
            if effective_memory:
                agent_kwargs["memory"] = effective_memory

            agent = create_deep_agent(**agent_kwargs)

            # Ensure child/orphaned processes are cleaned up
            pre_children = {c.pid for c in psutil.Process().children(recursive=True)}
            try:
                agent_result = await agent.ainvoke({"messages": messages})

                result_messages = agent_result["messages"]
                content = result_messages[-1].content if result_messages else ""
                content = strip_pattern(content, strip_re)
            finally:
                kill_orphaned_children(pre_children)

        # Calculate usage metrics
        prompt_tokens = sum(len(str(m.content).split()) for m in chat_request.messages)
        completion_tokens = len(content.split()) if content else 0
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
        response = ChatResponse.from_string(content, usage=usage)
        if chat_request_or_message.is_string:
            return GlobalTypeConverter.get().convert(response, to_type=str)
        return response

    yield FunctionInfo.from_fn(_inner, description=config.description)
