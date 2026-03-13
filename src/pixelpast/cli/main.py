"""Typer-based operational CLI for PixelPast."""

import logging
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from enum import IntEnum
from pathlib import Path
from typing import Annotated

import typer

from pixelpast.analytics.entrypoints import run_derive_job
from pixelpast.ingestion.progress import IngestionProgressSnapshot
from pixelpast.ingestion.entrypoints import run_ingest_source
from pixelpast.shared.logging import configure_logging
from pixelpast.shared.runtime import (
    RuntimeContext,
    create_runtime_context,
    initialize_database,
)

logger = logging.getLogger(__name__)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
UI_WORKSPACE = REPOSITORY_ROOT / "ui"


class ExitCode(IntEnum):
    """Explicit CLI exit codes."""

    SUCCESS = 0
    FAILURE = 1
    INVALID_ARGUMENT = 2


@dataclass(slots=True, frozen=True)
class DevProcessSpec:
    """Describe one child process in the local development stack."""

    name: str
    command: tuple[str, ...]
    cwd: Path
    env: dict[str, str] | None = None


@dataclass(slots=True)
class RunningDevProcess:
    """Track one started development child process."""

    spec: DevProcessSpec
    process: subprocess.Popen[None]


class DevProcessExitedError(RuntimeError):
    """Raised when one dev child process exits unexpectedly."""

    def __init__(self, *, process_name: str, exit_code: int) -> None:
        super().__init__(f"{process_name} exited with code {exit_code}")
        self.process_name = process_name
        self.exit_code = exit_code


class IngestionCliProgressReporter:
    """Render phase-aware ingest progress as robust terminal lines."""

    def __init__(self) -> None:
        self._last_discovered_file_count = -1
        self._last_analyzed_total = -1
        self._last_items_persisted = -1

    def __call__(self, snapshot: IngestionProgressSnapshot) -> None:
        """Print meaningful progress and terminal summary lines."""

        if snapshot.event == "phase_started":
            typer.echo(
                f"[{snapshot.source}] phase={snapshot.phase} status=started"
                f"{_format_total_suffix(snapshot.phase_total)}"
            )
            return

        if snapshot.event == "phase_completed":
            typer.echo(
                f"[{snapshot.source}] phase={snapshot.phase} status=completed"
                f" completed={snapshot.phase_completed}"
                f"{_format_total_suffix(snapshot.phase_total)}"
            )
            return

        if snapshot.event == "metadata_batch_submitted":
            typer.echo(
                f"[{snapshot.source}] phase=metadata extraction"
                f" batch_submitted={snapshot.current_batch_index}/{snapshot.current_batch_total}"
                f" batch_size={snapshot.current_batch_size}"
            )
            return

        if snapshot.event == "metadata_batch_completed":
            typer.echo(
                f"[{snapshot.source}] phase=metadata extraction"
                f" batch_completed={snapshot.current_batch_index}/{snapshot.current_batch_total}"
                f" batch_size={snapshot.current_batch_size}"
            )
            return

        if snapshot.event == "run_finished":
            typer.echo(
                f"[{snapshot.source}] summary"
                f" status={snapshot.status}"
                f" import_run_id={snapshot.import_run_id}"
                f" discovered={snapshot.discovered_file_count}"
                f" analyzed={snapshot.analyzed_file_count}"
                f" analysis_failed={snapshot.analysis_failed_file_count}"
                f" inserted={snapshot.inserted_item_count}"
                f" updated={snapshot.updated_item_count}"
                f" unchanged={snapshot.unchanged_item_count}"
                f" skipped={snapshot.skipped_item_count}"
                f" missing_from_source={snapshot.missing_from_source_count}"
            )
            return

        if snapshot.event == "run_failed":
            typer.echo(
                f"[{snapshot.source}] summary"
                f" status={snapshot.status}"
                f" import_run_id={snapshot.import_run_id}"
                f" phase={snapshot.phase}"
                f" discovered={snapshot.discovered_file_count}"
                f" analyzed={snapshot.analyzed_file_count}"
                f" analysis_failed={snapshot.analysis_failed_file_count}"
                f" persisted={snapshot.items_persisted}"
            )
            return

        if snapshot.phase == "filesystem discovery":
            if snapshot.discovered_file_count != self._last_discovered_file_count:
                self._last_discovered_file_count = snapshot.discovered_file_count
                typer.echo(
                    f"[{snapshot.source}] phase=filesystem discovery"
                    f" discovered={snapshot.discovered_file_count}"
                )
            return

        if snapshot.phase == "metadata extraction":
            analyzed_total = (
                snapshot.analyzed_file_count + snapshot.analysis_failed_file_count
            )
            if analyzed_total != self._last_analyzed_total:
                self._last_analyzed_total = analyzed_total
                typer.echo(
                    f"[{snapshot.source}] phase=metadata extraction"
                    f" completed={analyzed_total}/{snapshot.phase_total or 0}"
                    f" analyzed={snapshot.analyzed_file_count}"
                    f" analysis_failed={snapshot.analysis_failed_file_count}"
                    f" batches={snapshot.metadata_batches_completed}/{snapshot.metadata_batches_submitted}"
                )
            return

        if snapshot.phase == "canonical persistence":
            if snapshot.items_persisted != self._last_items_persisted:
                self._last_items_persisted = snapshot.items_persisted
                typer.echo(
                    f"[{snapshot.source}] phase=canonical persistence"
                    f" completed={snapshot.phase_completed}/{snapshot.phase_total or 0}"
                    f" persisted={snapshot.items_persisted}"
                    f" inserted={snapshot.inserted_item_count}"
                    f" updated={snapshot.updated_item_count}"
                    f" unchanged={snapshot.unchanged_item_count}"
                    f" skipped={snapshot.skipped_item_count}"
                    f" missing_from_source={snapshot.missing_from_source_count}"
                )


app = typer.Typer(
    help="Operational CLI for PixelPast ingestion, API and derived jobs.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)


@app.command("dev")
def dev_command(
    demo: Annotated[
        bool,
        typer.Option(
            "--demo",
            help="Run the Python API with the deterministic demo projection provider.",
        ),
    ] = False,
    api_host: Annotated[
        str,
        typer.Option(
            "--api-host",
            help="Host bound by the Python API process.",
        ),
    ] = "127.0.0.1",
    api_port: Annotated[
        int,
        typer.Option(
            "--api-port",
            min=1,
            max=65535,
            help="Port bound by the Python API process.",
        ),
    ] = 8000,
    ui_host: Annotated[
        str,
        typer.Option(
            "--ui-host",
            help="Host bound by the Vite UI process.",
        ),
    ] = "127.0.0.1",
    ui_port: Annotated[
        int,
        typer.Option(
            "--ui-port",
            min=1,
            max=65535,
            help="Port bound by the Vite UI process.",
        ),
    ] = 5173,
) -> None:
    """Run the FastAPI API and Vite UI together for local development."""

    configure_logging(debug=False)
    try:
        process_specs = _build_dev_process_specs(
            demo=demo,
            api_host=api_host,
            api_port=api_port,
            ui_host=ui_host,
            ui_port=ui_port,
        )

        logger.info(
            "dev stack starting",
            extra={
                "api_host": api_host,
                "api_port": api_port,
                "demo": demo,
                "ui_host": ui_host,
                "ui_port": ui_port,
            },
        )
        for spec in process_specs:
            typer.echo(f"starting {spec.name}: {' '.join(spec.command)}")

        _run_dev_processes(process_specs)
    except ValueError as error:
        logger.error("dev stack failed", extra={"reason": str(error)})
        raise typer.Exit(code=ExitCode.INVALID_ARGUMENT) from error


@app.command("ingest")
def ingest_command(
    source: Annotated[str, typer.Argument(help="Source connector name.")],
) -> None:
    """Run an ingestion source entrypoint."""

    progress_reporter = IngestionCliProgressReporter()
    _execute_operation(
        command_name="ingest",
        target=source,
        runner=lambda runtime: run_ingest_source(
            source=source,
            runtime=runtime,
            progress_callback=progress_reporter,
        ),
    )


@app.command("derive")
def derive_command(
    job: Annotated[str, typer.Argument(help="Derived job name.")],
    start_date: Annotated[
        str | None,
        typer.Option(
            "--start-date",
            help="Inclusive start date for a range recomputation (YYYY-MM-DD).",
        ),
    ] = None,
    end_date: Annotated[
        str | None,
        typer.Option(
            "--end-date",
            help="Inclusive end date for a range recomputation (YYYY-MM-DD).",
        ),
    ] = None,
) -> None:
    """Run a derived-data job entrypoint."""

    parsed_start_date = _parse_cli_date_option(
        option_name="start-date",
        raw_value=start_date,
    )
    parsed_end_date = _parse_cli_date_option(
        option_name="end-date",
        raw_value=end_date,
    )

    _execute_operation(
        command_name="derive",
        target=job,
        runner=lambda runtime: run_derive_job(
            job=job,
            runtime=runtime,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
        ),
    )


def main() -> None:
    """Run the CLI application."""

    app()


def _build_dev_process_specs(
    *,
    demo: bool,
    api_host: str,
    api_port: int,
    ui_host: str,
    ui_port: int,
) -> tuple[DevProcessSpec, DevProcessSpec]:
    """Return the child process specifications for local development."""

    if not UI_WORKSPACE.exists():
        raise ValueError(f"UI workspace not found at {UI_WORKSPACE}")

    npm_executable = _resolve_npm_executable()
    api_environment = os.environ.copy()
    if demo:
        api_environment["PIXELPAST_TIMELINE_PROJECTION_PROVIDER"] = "demo"

    return (
        DevProcessSpec(
            name="api",
            command=(
                sys.executable,
                "-m",
                "uvicorn",
                "pixelpast.api.main:app",
                "--app-dir",
                "src",
                "--reload",
                "--host",
                api_host,
                "--port",
                str(api_port),
            ),
            cwd=REPOSITORY_ROOT,
            env=api_environment,
        ),
        DevProcessSpec(
            name="ui",
            command=(
                npm_executable,
                "run",
                "dev",
                "--",
                "--host",
                ui_host,
                "--port",
                str(ui_port),
            ),
            cwd=UI_WORKSPACE,
            env=os.environ.copy(),
        ),
    )


def _resolve_npm_executable() -> str:
    """Return the available npm executable for the current platform."""

    for candidate in ("npm", "npm.cmd"):
        executable = shutil.which(candidate)
        if executable is not None:
            return executable

    raise ValueError("Could not find npm on PATH. Install Node.js first.")


def _run_dev_processes(process_specs: Sequence[DevProcessSpec]) -> None:
    """Start, supervise and stop the child processes for local development."""

    running_processes: list[RunningDevProcess] = []
    try:
        for spec in process_specs:
            process = subprocess.Popen(
                spec.command,
                cwd=spec.cwd,
                env=spec.env,
            )
            running_processes.append(RunningDevProcess(spec=spec, process=process))

        while True:
            for running_process in running_processes:
                exit_code = running_process.process.poll()
                if exit_code is not None:
                    raise DevProcessExitedError(
                        process_name=running_process.spec.name,
                        exit_code=exit_code,
                    )
            time.sleep(0.25)
    except KeyboardInterrupt as error:
        logger.info("dev stack interrupted")
        raise typer.Exit(code=ExitCode.SUCCESS) from error
    except ValueError as error:
        logger.error("dev stack failed", extra={"reason": str(error)})
        raise typer.Exit(code=ExitCode.INVALID_ARGUMENT) from error
    except DevProcessExitedError as error:
        logger.error(
            "dev child process exited",
            extra={
                "process_name": error.process_name,
                "exit_code": error.exit_code,
            },
        )
        raise typer.Exit(
            code=error.exit_code if error.exit_code != 0 else ExitCode.SUCCESS
        ) from error
    finally:
        _stop_dev_processes(running_processes)


def _stop_dev_processes(running_processes: Sequence[RunningDevProcess]) -> None:
    """Terminate and, if necessary, kill all development child processes."""

    for running_process in running_processes:
        if running_process.process.poll() is None:
            running_process.process.terminate()

    deadline = time.time() + 5
    while time.time() < deadline:
        if all(process.process.poll() is not None for process in running_processes):
            return
        time.sleep(0.1)

    for running_process in running_processes:
        if running_process.process.poll() is None:
            running_process.process.kill()


def _execute_operation(
    *,
    command_name: str,
    target: str,
    runner: Callable[[RuntimeContext], object | None],
) -> None:
    """Initialize shared runtime dependencies and execute a CLI operation."""

    runtime = create_runtime_context()
    try:
        configure_logging(debug=runtime.settings.debug)
        initialize_database(runtime)

        logger.info(
            "command started",
            extra={"command": command_name, "target": target},
        )
        try:
            runner(runtime)
        except ValueError as error:
            logger.error(
                "command failed",
                extra={
                    "command": command_name,
                    "target": target,
                    "reason": str(error),
                },
            )
            raise typer.Exit(code=ExitCode.INVALID_ARGUMENT) from error
        except Exception as error:
            logger.exception(
                "command failed",
                extra={
                    "command": command_name,
                    "target": target,
                    "reason": str(error),
                },
            )
            raise typer.Exit(code=ExitCode.FAILURE) from error

        logger.info(
            "command completed",
            extra={
                "command": command_name,
                "target": target,
                "exit_code": ExitCode.SUCCESS,
            },
        )
        raise typer.Exit(code=ExitCode.SUCCESS)
    finally:
        runtime.engine.dispose()


def _parse_cli_date_option(*, option_name: str, raw_value: str | None) -> date | None:
    """Parse an ISO date option into a Python date."""

    if raw_value is None:
        return None

    try:
        return date.fromisoformat(raw_value)
    except ValueError as error:
        raise ValueError(
            f"Invalid --{option_name} value '{raw_value}'. Expected YYYY-MM-DD."
        ) from error


def _format_total_suffix(total: int | None) -> str:
    """Return a human-readable optional total suffix for CLI progress lines."""

    if total is None:
        return ""
    return f" total={total}"


if __name__ == "__main__":
    main()
