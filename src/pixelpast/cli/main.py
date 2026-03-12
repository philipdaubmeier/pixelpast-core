"""Typer-based operational CLI for PixelPast."""

from collections.abc import Callable
import logging
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
) -> None:
    """Run a derived-data job entrypoint."""

    _execute_operation(
        command_name="derive",
        target=job,
        runner=lambda runtime: run_derive_job(job=job, runtime=runtime),
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

        logger.info("command started", extra={"command": command_name, "target": target})
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
