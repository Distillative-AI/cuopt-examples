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

import logging
import re
import shutil
from pathlib import Path

from deepagents.graph import AgentMiddleware

logger = logging.getLogger(__name__)

SANDBOX_SKILLS_DIR = "skills"
SANDBOX_AGENTS_MD = "AGENTS.md"


class FixToolNamesMiddleware(AgentMiddleware):
    """Normalise hyphenated tool names emitted by some models.

    Certain LLMs produce tool-call names with hyphens (e.g. ``read-file``)
    instead of the underscored variants expected by LangChain
    (``read_file``).  This middleware rewrites them in-place after every
    model call so downstream tool dispatch succeeds.
    """

    @staticmethod
    def _patch(response):
        """Replace hyphens with underscores in all tool-call names."""
        for msg in response.result:
            for tc in getattr(msg, "tool_calls", []):
                if "-" in tc["name"]:
                    tc["name"] = tc["name"].replace("-", "_")
        return response

    def wrap_model_call(self, request, handler):
        """Synchronous wrapper that patches tool names after the model call.

        Args:
            request: The incoming model request.
            handler: The next handler in the middleware chain.

        Returns:
            The model response with tool names normalised.
        """
        return self._patch(handler(request))

    async def awrap_model_call(self, request, handler):
        """Async wrapper that patches tool names after the model call.

        Args:
            request: The incoming model request.
            handler: The next async handler in the middleware chain.

        Returns:
            The model response with tool names normalised.
        """
        return self._patch(await handler(request))


def strip_pattern(text: str, pattern: re.Pattern[str] | None) -> str:
    """Remove all regex matches from *text*.

    If the stripped result would be empty, the original text is returned
    unchanged so that downstream consumers always receive non-empty output.

    Args:
        text: The source string to process.
        pattern: A compiled regex whose matches are removed, or ``None``
            to skip stripping entirely.

    Returns:
        The text with all matches removed (and whitespace-trimmed), or the
        original text if stripping would produce an empty string.
    """
    if not pattern:
        return text
    return pattern.sub("", text).strip() or text


def kill_orphaned_children(pre_children: set[int]) -> None:
    """Terminate child processes spawned during agent execution.

    ``LocalShellBackend`` has no shutdown API, so processes started by the
    agent (cuOpt solvers, Python scripts) can outlive ``agent.invoke()``.
    This helper diffs the current process tree against a pre-invocation
    snapshot and sends SIGTERM first, falling back to SIGKILL after a
    grace period.

    Args:
        pre_children: Set of PIDs that existed *before* the agent
            invocation.  Any current child whose PID is not in this set
            is considered orphaned and will be terminated.
    """
    import psutil

    for child in psutil.Process().children(recursive=True):
        if child.pid not in pre_children:
            try:
                logger.info(
                    "Terminating orphaned child process %d (%s)",
                    child.pid,
                    child.name(),
                )
                child.terminate()
                try:
                    child.wait(timeout=3)
                except psutil.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=2)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                pass


def populate_sandbox(
    sandbox: Path,
    skills_src_dirs: list[Path],
    agents_md_src: Path | None,
    workspace_dirs: list[Path],
) -> None:
    """Copy skills, AGENTS.md, and workspace data files into the sandbox.

    Skill directories are merged under ``{sandbox}/skills/``.  If two
    source directories contain a skill with the same name, the first one
    wins and a warning is logged for the duplicate.

    Args:
        sandbox: Root directory of the temporary sandbox.
        skills_src_dirs: Resolved skill source directories whose
            children are merged into ``{sandbox}/skills/``.
        agents_md_src: Path to the AGENTS.md file to copy into the
            sandbox root, or ``None`` to skip.
        workspace_dirs: Additional directories whose *files* (not
            sub-directories) are copied into the sandbox root.
    """
    if skills_src_dirs:
        merged = sandbox / SANDBOX_SKILLS_DIR
        merged.mkdir(exist_ok=True)
        for src in skills_src_dirs:
            for child in sorted(src.iterdir()):
                dest = merged / child.name
                if dest.exists():
                    logger.warning(
                        "Skill name collision: %s (from %s) — skipping duplicate",
                        child.name,
                        src,
                    )
                    continue
                if child.is_dir():
                    shutil.copytree(child, dest)
                elif child.is_file():
                    shutil.copy(child, dest)
    if agents_md_src:
        shutil.copy(agents_md_src, sandbox / SANDBOX_AGENTS_MD)
    for ws_dir in workspace_dirs:
        ws_path = Path(ws_dir)
        if ws_path.is_dir():
            for f in sorted(ws_path.iterdir()):
                if f.is_file():
                    shutil.copy(f, sandbox / f.name)
        else:
            logger.warning("workspace_dir not found: %s", ws_path)


def resolve_skills_dirs(raw: list[Path] | Path | None) -> list[Path]:
    """Resolve the ``skills_dir`` config value to a list of existing directories.

    Accepts a single path, a list of paths, or ``None``.  Each path is
    checked for existence; missing directories are logged as warnings and
    omitted from the result.

    Args:
        raw: One or more skill directory paths (relative to cwd or
            absolute), or ``None`` if no skill directories are configured.

    Returns:
        A list of ``Path`` objects for directories that actually exist
        on disk.  May be empty if none of the supplied paths resolve.
    """
    if isinstance(raw, (str, Path)):
        raw = [raw]
    result = []
    for p in raw or []:
        d = Path(p)
        if d.is_dir():
            result.append(d)
        else:
            logger.warning("skills_dir not found (cwd=%s): %s", Path.cwd(), d)
    return result
