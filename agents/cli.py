"""
Poll-Rover CLI
Command-line interface for managing the agentic pipeline.

Usage:
    python -m agents.cli pipeline           # Run full pipeline
    python -m agents.cli pipeline --dry-run # Preview mode
    python -m agents.cli harvest            # Run harvester only
    python -m agents.cli quality            # Run quality audit
    python -m agents.cli sre               # Run SRE checks
    python -m agents.cli query "Where do I vote in Chennai?"
    python -m agents.cli status            # System status
"""

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
def cli():
    """Poll-Rover: AI for Good -- Know Your Polling Station"""
    pass


@cli.command()
@click.option("--dry-run", is_flag=True, help="Preview mode, no writes")
@click.option("--states", default=None, help="Comma-separated state codes (e.g., TN,KL,PY)")
@click.option("--stages", default=None, help="Comma-separated stages (harvest,quality,generate,sre)")
def pipeline(dry_run, states, stages):
    """Run the full agentic pipeline."""
    from agents.orchestrator.orchestrator import AgentOrchestrator

    state_list = states.split(",") if states else None
    stage_list = stages.split(",") if stages else None

    orch = AgentOrchestrator()
    result = orch.run_pipeline(
        dry_run=dry_run,
        states=state_list,
        stages=stage_list,
    )

    _print_pipeline_report(result)


@cli.command()
@click.option("--dry-run", is_flag=True, help="Preview mode")
@click.option("--states", default=None, help="Comma-separated state codes")
def harvest(dry_run, states):
    """Run the Data Harvester Agent."""
    from agents.harvester.harvester_agent import DataHarvesterAgent

    state_list = states.split(",") if states else None
    agent = DataHarvesterAgent()
    result = agent.run(states=state_list, dry_run=dry_run)

    console.print(f"\n[bold green]Harvest complete![/bold green]")
    console.print(f"  Stations found: {result.get('stations_found', 0)}")
    console.print(f"  Stations added: {result.get('stations_added', 0)}")


@cli.command()
@click.option("--fix", is_flag=True, help="Auto-fix correctable issues")
def quality(fix):
    """Run the Data Quality Agent."""
    from agents.quality.quality_agent import DataQualityAgent

    agent = DataQualityAgent()
    result = agent.run(fix_issues=fix)

    table = Table(title="Data Quality Report")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Stations Audited", str(result.get("stations_audited", 0)))
    table.add_row("Passed", str(result.get("passed", 0)))
    table.add_row("Warnings", str(result.get("warnings", 0)))
    table.add_row("Errors", str(result.get("errors", 0)))
    console.print(table)


@cli.command()
def sre():
    """Run the SRE Ops Agent health checks."""
    from agents.sre_ops.sre_agent import SREOpsAgent

    agent = SREOpsAgent()
    result = agent.run()

    status_text = "HEALTHY" if result["overall_status"] == "healthy" else "WARNING"
    console.print(f"\n[bold]{status_text}[/bold] Overall Status")
    console.print(f"  Incidents: {len(result.get('incidents', []))}")
    console.print(f"  Remediations: {len(result.get('remediations', []))}")


@cli.command()
@click.argument("text")
@click.option("--lang", default="en", help="Language code (en/hi/ta/te/kn)")
@click.option("--lat", default=None, type=float, help="User latitude")
@click.option("--lng", default=None, type=float, help="User longitude")
def query(text, lang, lat, lng):
    """Ask the Citizen Assist Agent a question."""
    from agents.orchestrator.orchestrator import AgentOrchestrator

    orch = AgentOrchestrator()
    result = orch.query(
        user_query=text,
        language=lang,
        user_lat=lat,
        user_lng=lng,
    )

    console.print(f"\n[bold cyan][Citizen Assist]:[/bold cyan]")
    console.print(result.get("text", "No response"))
    console.print(f"\n[dim]Stations matched: {len(result.get('stations', []))}[/dim]")


@cli.command()
def status():
    """Show system status."""
    from agents.orchestrator.orchestrator import AgentOrchestrator

    orch = AgentOrchestrator()
    info = orch.status()

    table = Table(title="Poll-Rover Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_row("Version", info.get("version", "?"))
    table.add_row("Stations Loaded", str(info.get("stations_loaded", 0)))
    table.add_row("Pilot States", ", ".join(info.get("pilot_states", [])))

    for agent, enabled in info.get("agents", {}).items():
        table.add_row(f"Agent: {agent}", "enabled" if enabled else "disabled")

    console.print(table)


def _print_pipeline_report(result: dict) -> None:
    """Pretty-print a pipeline execution report."""
    table = Table(title="Pipeline Report")
    table.add_column("Stage", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details")

    for stage_name, stage_data in result.get("stages", {}).items():
        status = stage_data.get("status", "unknown")
        status_styled = (
            f"[green]{status}[/green]" if status == "success"
            else f"[red]{status}[/red]"
        )

        details = ""
        if stage_name == "harvest":
            details = f"Found: {stage_data.get('stations_found', 0)}, Added: {stage_data.get('stations_added', 0)}"
        elif stage_name == "quality":
            details = f"Audited: {stage_data.get('stations_audited', 0)}, Passed: {stage_data.get('passed', 0)}"
        elif stage_name == "sre":
            details = f"Incidents: {stage_data.get('incidents', 0)}, Fixes: {stage_data.get('remediations', 0)}"

        table.add_row(stage_name, status_styled, details)

    console.print(table)
    console.print(
        f"\nDuration: {result.get('duration_seconds', 0)}s | "
        f"Status: {result.get('overall_status', 'unknown')}"
    )


if __name__ == "__main__":
    cli()
