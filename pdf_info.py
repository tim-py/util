import PyPDF2
import logging
import argparse
from pdf_data import PdfData

opt = None
units_per_mm = 420.0 / 148.0
units_per_inch = 612.0 / 8.5
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pdf_info")


def get_options():
    """
    Parses the command line options
    """
    global opt

    # Create a parser object
    parser = argparse.ArgumentParser(description='Create PDF booklet')

    # Positional required arguments
    parser.add_argument('file_in',
                        help="Name of the input PDF file")

    # Optional keyword arguments
    parser.add_argument('--debug', action="store_true", dest='debug', required=False,
                        help="Additional features for debugging")
    opt = parser.parse_args()


def units_mm_in(width_units, height_units):
    mm_width = width_units / units_per_mm
    mm_height = height_units / units_per_mm
    inch_width = width_units / units_per_inch
    inch_height = height_units / units_per_inch
    return f"{width_units}x{height_units}/{mm_width:.2f}x{mm_height:.2f}mm/{inch_width:.2f}x{inch_height:.2f}in"

def main():

    get_options()

    with open(opt.file_in, 'rb') as fh:
        pdf_in = PyPDF2.PdfFileReader(fh)
        source_data = PdfData(pdf_in)
        print(f"Source PDF name '{opt.file_in}'")
        print(f"    page_count: {source_data.page_count}")
        print(f"    format: {source_data.format}")
        print(f"    description: {source_data.description}")
        print(f"    type: {source_data.type}")
        print(f"    subject: {source_data.subject}")
        print(f"    creator: {source_data.creator}")
        print(f"    date: {source_data.date}")
        print(f"    title: {source_data.title}")
        print(f"    version: {source_data.version}")

        # Largest page size
        largest_height, largest_width  = source_data.largest_page
        print(f"    largest page (width x height) {units_mm_in(largest_width, largest_height)}")

        # Page distributions
        print(f"    page size distributions:")
        page_dist = {}
        for page in source_data.pages:
            # size = f"{page.mediaBox.getWidth()}x{page.mediaBox.getHeight()}"
            size = (page.mediaBox.getWidth(), page.mediaBox.getHeight())
            if size not in page_dist.keys():
                page_dist[size] = []
            page_dist[size].append(f"{pdf_in.getPageNumber(page) + 1}")
        for size, page_numbers in page_dist.items():
            page_string = ",".join(page_numbers)
            print(f"        {units_mm_in(*size)}: {page_string}")


if __name__ == '__main__':
    main()