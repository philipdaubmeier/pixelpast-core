"""Typer-based operational CLI for PixelPast."""

import logging
import os
import shutil
import subprocess
import sys
import time
import traceback
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from enum import IntEnum
from pathlib import Path
from typing import IO, Annotated

import typer
from tqdm import tqdm

from pixelpast.analytics.entrypoints import (
    list_supported_derive_jobs,
    run_derive_job,
)
from pixelpast.api.openapi import (
    DEFAULT_OPENAPI_EXPORT_PATH,
    DEFAULT_OPENAPI_HTML_PATH,
    export_openapi_schema,
    openapi_contract_is_synced,
)
from pixelpast.ingestion.entrypoints import (
    list_supported_ingest_sources,
    run_ingest_source,
)
from pixelpast.shared.logging import configure_logging
from pixelpast.shared.progress import JobProgressSnapshot
from pixelpast.shared.runtime import (
    RuntimeContext,
    create_runtime_context,
    initialize_database,
)

logger = logging.getLogger(__name__)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
UI_WORKSPACE = REPOSITORY_ROOT / "ui"
SUPPORTED_INGEST_SOURCES = list_supported_ingest_sources()
SUPPORTED_DERIVE_JOBS = list_supported_derive_jobs()


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


class CliProgressReporter:
    """Render shared phase-aware job progress using one in-place tqdm bar."""

    def __init__(
        self,
        *,
        stream: IO[str] | None = None,
    ) -> None:
        self._stream = stream or typer.get_text_stream("stdout")
        self._progress_bar: tqdm[object] | None = None
        self._active_job: str | None = None
        self._active_phase: str | None = None
        self._active_completed: int | None = None
        self._active_total: int | None = None

    def __call__(self, snapshot: JobProgressSnapshot) -> None:
        """Refresh the current progress bar or print a terminal summary block."""

        if snapshot.event == "run_finished":
            self._sync_bar(snapshot)
            self.close()
            self._print_summary(snapshot)
            return

        if snapshot.event == "run_failed":
            self._sync_bar(snapshot)
            self.close()
            self._print_failure_summary(snapshot)
            return

        self._sync_bar(snapshot)

    @property
    def active_phase(self) -> str | None:
        """Expose the active phase label for CLI-focused tests."""

        return self._active_phase

    @property
    def active_completed(self) -> int | None:
        """Expose the active completed count for CLI-focused tests."""

        return self._active_completed

    @property
    def active_total(self) -> int | None:
        """Expose the active total count for CLI-focused tests."""

        return self._active_total

    def close(self) -> None:
        """Stop the active tqdm progress display if it was started."""

        if self._progress_bar is not None:
            self._progress_bar.close()
            self._progress_bar = None

    def _sync_bar(self, snapshot: JobProgressSnapshot) -> None:
        total = snapshot.total
        if (
            self._progress_bar is None
            or self._active_job != snapshot.job
            or self._active_phase != snapshot.phase
        ):
            self.close()
            self._progress_bar = tqdm(
                total=total,
                initial=snapshot.completed,
                desc=self._build_description(snapshot),
                file=self._stream,
                leave=False,
                dynamic_ncols=True,
                unit="item",
                colour="#00ffff",
            )
            if total is None:
                self._progress_bar.bar_format = (
                    "{desc}: {n_fmt} item [{elapsed}<?, ?item/s]"
                )
        else:
            if self._progress_bar.total != total:
                self._progress_bar.total = total
            delta = snapshot.completed - int(self._progress_bar.n)
            if delta != 0:
                self._progress_bar.update(delta)
            self._progress_bar.set_description_str(self._build_description(snapshot))
            self._progress_bar.refresh()

        self._active_job = snapshot.job
        self._active_phase = snapshot.phase
        self._active_completed = snapshot.completed
        self._active_total = snapshot.total

    def _build_description(self, snapshot: JobProgressSnapshot) -> str:
        return f"[{snapshot.job}] {snapshot.phase}"

    def _print_summary(self, snapshot: JobProgressSnapshot) -> None:
        typer.echo(f"[{snapshot.job}] completed", file=self._stream)
        self._echo_summary_value("run_id", snapshot.run_id)
        self._echo_summary_value("status", snapshot.status)
        self._echo_summary_value("inserted", snapshot.inserted)
        self._echo_summary_value("updated", snapshot.updated)
        self._echo_summary_value("unchanged", snapshot.unchanged)
        self._echo_summary_value("skipped", snapshot.skipped)
        self._echo_summary_value("failed", snapshot.failed)
        self._echo_summary_value(
            "missing_from_source",
            snapshot.missing_from_source,
        )

    def _print_failure_summary(self, snapshot: JobProgressSnapshot) -> None:
        typer.echo(f"[{snapshot.job}] failed", file=self._stream)
        self._echo_summary_value("run_id", snapshot.run_id)
        self._echo_summary_value("status", snapshot.status)
        self._echo_summary_value("phase", snapshot.phase)
        self._echo_summary_value(
            "progress",
            f"{snapshot.completed}/{_format_total_value(snapshot.total)}",
        )
        self._echo_summary_value("inserted", snapshot.inserted)
        self._echo_summary_value("updated", snapshot.updated)
        self._echo_summary_value("unchanged", snapshot.unchanged)
        self._echo_summary_value("skipped", snapshot.skipped)
        self._echo_summary_value("failed", snapshot.failed)
        self._echo_summary_value(
            "missing_from_source",
            snapshot.missing_from_source,
        )

    def _echo_summary_value(self, label: str, value: object) -> None:
        """Print one summary line with a neutral label and cyan value."""

        styled_value = typer.style(str(value), fg=typer.colors.BRIGHT_CYAN)
        typer.echo(f"{label}: {styled_value}", file=self._stream, color=None)


IngestionCliProgressReporter = CliProgressReporter


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
    source: Annotated[
        str,
        typer.Argument(
            help=(
                "Source connector name. "
                f"Available sources: {', '.join(SUPPORTED_INGEST_SOURCES)}."
            ),
        ),
    ],
) -> None:
    """Run an ingestion source entrypoint."""

    progress_reporter = CliProgressReporter()
    try:
        _execute_operation(
            command_name="ingest",
            target=source,
            runner=lambda runtime: run_ingest_source(
                source=source,
                runtime=runtime,
                progress_callback=progress_reporter,
            ),
        )
    finally:
        progress_reporter.close()


@app.command("derive")
def derive_command(
    job: Annotated[
        str,
        typer.Argument(
            help=(
                f"Derived job name. Available jobs: {', '.join(SUPPORTED_DERIVE_JOBS)}."
            ),
        ),
    ],
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

    progress_reporter = CliProgressReporter()
    try:
        _execute_operation(
            command_name="derive",
            target=job,
            runner=lambda runtime: run_derive_job(
                job=job,
                runtime=runtime,
                start_date=parsed_start_date,
                end_date=parsed_end_date,
                progress_callback=progress_reporter,
            ),
        )
    finally:
        progress_reporter.close()


@app.command("export-openapi")
def export_openapi_command(
    check: Annotated[
        bool,
        typer.Option(
            "--check",
            help=(
                "Fail when the committed OpenAPI contract is stale instead of "
                "rewriting it."
            ),
        ),
    ] = False,
    render: Annotated[
        bool,
        typer.Option(
            "--render/--no-render",
            help="Render static HTML documentation after the contract step.",
        ),
    ] = True,
) -> None:
    """Export or validate the OpenAPI contract and optionally render static HTML."""

    configure_logging(debug=False)
    if check:
        if not openapi_contract_is_synced(output_path=DEFAULT_OPENAPI_EXPORT_PATH):
            typer.secho(
                "error: OpenAPI contract is stale. Run `pixelpast export-openapi`.",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=ExitCode.FAILURE)

        typer.echo(
            f"OpenAPI contract is in sync at {DEFAULT_OPENAPI_EXPORT_PATH.as_posix()}"
        )
    else:
        output_path = export_openapi_schema(output_path=DEFAULT_OPENAPI_EXPORT_PATH)
        typer.echo(f"exported OpenAPI contract to {output_path.as_posix()}")

    if not render:
        return

    html_output_path = _render_openapi_html(
        input_path=DEFAULT_OPENAPI_EXPORT_PATH,
        output_path=DEFAULT_OPENAPI_HTML_PATH,
    )
    typer.echo(f"rendered OpenAPI HTML to {html_output_path.as_posix()}")


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

    return _resolve_node_tool_executable(("npm", "npm.cmd"), tool_name="npm")


def _resolve_npx_executable() -> str:
    """Return the available npx executable for the current platform."""

    return _resolve_node_tool_executable(("npx", "npx.cmd"), tool_name="npx")


def _resolve_node_tool_executable(
    candidates: Sequence[str],
    *,
    tool_name: str,
) -> str:
    """Return the first available Node.js package manager executable."""

    for candidate in candidates:
        executable = shutil.which(candidate)
        if executable is not None:
            return executable

    raise ValueError(f"Could not find {tool_name} on PATH. Install Node.js first.")


def _render_openapi_html(*, input_path: Path, output_path: Path) -> Path:
    """Render static HTML API documentation from the committed OpenAPI contract."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    npx_executable = _resolve_npx_executable()
    result = subprocess.run(
        (
            npx_executable,
            "@redocly/cli",
            "build-docs",
            input_path.as_posix(),
            "--output",
            output_path.as_posix(),
        ),
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        error_output = (result.stderr or result.stdout).strip()
        if not error_output:
            error_output = "Redocly CLI exited with a non-zero status."
        raise ValueError(f"OpenAPI HTML rendering failed: {error_output}")

    return output_path


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
            result = runner(runtime)
            _print_result_errors(result)
            _print_result_warnings(result)
            _print_result_metadata(result)
        except ValueError as error:
            logger.error(
                "command failed",
                extra={
                    "command": command_name,
                    "target": target,
                    "reason": str(error),
                },
            )
            typer.secho(f"error: {error}", fg=typer.colors.RED, err=True)
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
            typer.secho(f"error: {error}", fg=typer.colors.RED, err=True)
            typer.echo(traceback.format_exc(), err=True)
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


def _format_total_value(total: float | None) -> str:
    """Return a human-readable total value for progress output."""

    if total is None:
        return "?"
    return str(int(total))


def _print_result_errors(result: object | None) -> None:
    """Write non-fatal operation errors to the CLI when the result exposes them."""

    if result is None:
        return

    transform_errors = getattr(result, "transform_errors", ())
    for transform_error in transform_errors:
        origin = getattr(transform_error, "workbook", None) or getattr(
            transform_error,
            "document",
            None,
        )
        origin_label = getattr(origin, "origin_label", None)
        message = getattr(transform_error, "message", None)
        if origin_label and message:
            typer.secho(
                f"error: {origin_label}: {message}",
                fg=typer.colors.RED,
                err=True,
            )


def _print_result_metadata(result: object | None) -> None:
    """Write result-level summary fields not covered by progress snapshots."""

    if result is None:
        return

    skipped_json_file_count = getattr(result, "skipped_json_file_count", None)
    if skipped_json_file_count is not None:
        typer.echo(f"skipped_json_files: {skipped_json_file_count}")

    summary_fields = (
        "mode",
        "scanned_event_count",
        "qualifying_event_count",
        "unique_place_id_count",
        "remote_fetch_count",
        "cached_reuse_count",
        "inserted_place_count",
        "updated_place_count",
        "unchanged_place_count",
        "inserted_event_place_link_count",
        "updated_event_place_link_count",
        "unchanged_event_place_link_count",
    )
    for field_name in summary_fields:
        value = getattr(result, field_name, None)
        if value is not None:
            typer.echo(f"{field_name}: {value}")


def _print_result_warnings(result: object | None) -> None:
    """Write non-fatal operation warnings to the CLI."""

    if result is None:
        return

    warning_messages = getattr(result, "warning_messages", ())
    for warning_message in warning_messages:
        if warning_message:
            typer.secho(
                f"warning: {warning_message}",
                fg=typer.colors.YELLOW,
                err=True,
            )


if __name__ == "__main__":
    main()
