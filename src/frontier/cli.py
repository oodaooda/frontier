"""CLI entry point for Frontier benchmark suite."""

import click


@click.group()
@click.version_option()
def main():
    """Frontier — benchmark AI models on construction document understanding."""
    pass


@main.command()
@click.option("--dpi", default=300, help="DPI for rendering PDF pages.")
@click.argument("pdf_path", type=click.Path(exists=True))
def render(pdf_path: str, dpi: int):
    """Render PDF pages to images for model consumption."""
    from frontier.utils.pdf import render_pdf

    output_dir = render_pdf(pdf_path, dpi=dpi)
    click.echo(f"Rendered pages to {output_dir}")


@main.command()
@click.option("--model", "-m", multiple=True, required=True, help="Model(s) to evaluate.")
@click.option("--dataset", "-d", default="datasets/ground_truth", help="Path to ground truth dir.")
def run(model: tuple[str, ...], dataset: str):
    """Run benchmark evaluation against one or more models."""
    click.echo(f"Running evaluation with models: {', '.join(model)}")
    click.echo(f"Dataset: {dataset}")
    # TODO: Wire up runner pipeline in M2


@main.command()
@click.argument("results_path", type=click.Path(exists=True))
def report(results_path: str):
    """Generate a comparison report from evaluation results."""
    click.echo(f"Generating report from {results_path}")
    # TODO: Wire up reporting in M4


if __name__ == "__main__":
    main()
