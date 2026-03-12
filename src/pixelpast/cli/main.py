"""Typer-based operational CLI for PixelPast."""

import logging
from collections.abc import Callable
from datetime import date
from enum import IntEnum
from typing import Annotated

import typer

from pixelpast.analytics.entrypoints import run_derive_job
from pixelpast.ingestion.entrypoints import run_ingest_source
from pixelpast.shared.logging import configure_logging
from pixelpast.shared.runtime import (
    RuntimeContext,
    create_runtime_context,
    initialize_database,
)

logger = logging.getLogger(__name__)


class ExitCode(IntEnum):
    """Explicit CLI exit codes."""

    SUCCESS = 0
    FAILURE = 1
    INVALID_ARGUMENT = 2


app = typer.Typer(
    help="Operational CLI for PixelPast ingestion and derived jobs.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)


@app.command("ingest")
def ingest_command(
    source: Annotated[str, typer.Argument(help="Source connector name.")],
) -> None:
    """Run an ingestion source entrypoint."""

    _execute_operation(
        command_name="ingest",
        target=source,
        runner=lambda runtime: run_ingest_source(source=source, runtime=runtime),
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


def _execute_operation(
    *,
    command_name: str,
    target: str,
    runner: Callable[[RuntimeContext], None],
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
