import click

from autobot_runtime import initialize_user_environment
from robotization.robot_editor import start_robot_recorder_process, validate_robot_name
from robotization.robot_manager import RobotManager


def _get_manager() -> RobotManager:
    initialize_user_environment()
    return RobotManager()


@click.group()
def cli() -> None:
    """Run and inspect Autobot robotizations from the terminal."""


@cli.command("list")
def list_robots() -> None:
    """List available robotizations."""
    robots = _get_manager().list_automations()

    if not robots:
        click.echo("No robotizations found.")
        return

    for robot_name in robots:
        click.echo(robot_name)


@cli.command()
@click.argument("robot_name")
def run(robot_name: str) -> None:
    """Run a robotization by name."""
    manager = _get_manager()

    try:
        success = manager.run_automation(robot_name)
    except Exception as exc:
        raise click.ClickException(
            f"Failed to execute robotization '{robot_name}': {exc}"
        ) from exc

    if not success:
        raise click.ClickException(
            f"Robotization '{manager.normalize_automation_name(robot_name)}' was not found."
        )


@cli.command()
@click.argument("robot_name")
def write(robot_name: str) -> None:
    """Open a robotization in the recorder editor."""
    initialize_user_environment()

    try:
        safe_robot_name = validate_robot_name(robot_name)
        start_robot_recorder_process(safe_robot_name, daemon=False)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:
        raise click.ClickException(
            f"Failed to open robotization '{safe_robot_name if 'safe_robot_name' in locals() else robot_name}': {exc}"
        ) from exc


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
