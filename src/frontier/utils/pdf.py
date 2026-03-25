"""PDF rendering utilities."""

from pathlib import Path

import fitz  # PyMuPDF


def render_pdf(pdf_path: str, dpi: int = 300, output_dir: str | None = None) -> Path:
    """Render all pages of a PDF to PNG images.

    Args:
        pdf_path: Path to the PDF file.
        dpi: Resolution for rendering. 300 for drawings, 150 for text-heavy docs.
        output_dir: Where to save images. Defaults to datasets/rendered/<pdf_stem>/.

    Returns:
        Path to the output directory containing rendered images.
    """
    pdf_path = Path(pdf_path)
    if output_dir is None:
        output_dir = Path("datasets/rendered") / pdf_path.stem
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(matrix=matrix)
        out_path = output_dir / f"page_{page_num + 1:03d}.png"
        pix.save(str(out_path))

    doc.close()
    return output_dir
