import logging
import argparse
import PyPDF2
from pdf_data import get_units_from_parameter

opt = None
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pdf_crop")


def get_options():
    """
    Parses the command line options
    """
    global opt

    # Create a parser object
    parser = argparse.ArgumentParser(description='Crop PDF File')

    # Positional required arguments
    parser.add_argument('file_in',
                        help="Name of the input PDF file")
    parser.add_argument('file_out',
                        help="Name of the output PDF file")

    # Optional keyword arguments
    parser.add_argument('--left', type=str, required=False,
                        help="Crop in left side <value>mm|cm|in")
    parser.add_argument('--right', type=str, required=False,
                        help="Crop in right side <value>mm|cm|in")
    parser.add_argument('--top', type=str, required=False,
                        help="Crop in from top <value>mm|cm|in")
    parser.add_argument('--bottom', type=str, required=False,
                        help="Crop in from bottom <value>mm|cm|in")
    parser.add_argument('--debug', action="store_true", dest='debug',
                        required=False,
                        help="Additional features for debugging")
    opt = parser.parse_args()


def main():

    get_options()

    if opt.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    found_param = False
    left_units = 0
    right_units = 0
    top_units = 0
    bottom_units = 0
    if opt.left:
        left_units = get_units_from_parameter(opt.left)
        found_param = True
    if opt.right:
        right_units = get_units_from_parameter(opt.right)
        found_param = True
    if opt.top:
        top_units = get_units_from_parameter(opt.top)
        found_param = True
    if opt.bottom:
        bottom_units = get_units_from_parameter(opt.bottom)
        found_param = True

    # Input file context
    with open(opt.file_in, 'rb') as input_file:

        pdf_in = PyPDF2.PdfFileReader(input_file)
        pdf_out = PyPDF2.PdfFileWriter()

        for page in pdf_in.pages:
            left, bottom = page.mediaBox.lowerLeft
            right, top = page.mediaBox.upperRight
            left += left_units
            right -= right_units
            top -= top_units
            bottom += bottom_units
            page.mediaBox.setLowerLeft((left, bottom))
            page.mediaBox.setUpperRight((right, top))
            pdf_out.addPage(page)

        # Save the new file
        logger.debug("Writing new pages to output file")
        with open(opt.file_out, "wb") as output_file:
            pdf_out.write(output_file)


if __name__ == '__main__':
    main()