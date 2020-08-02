import PyPDF2
import logging
import argparse
import time
from pdf_data import PdfData, page_sizes, get_units_from_parameter

EPILOG = """
PDF booklet generates booklet pages that can be folded and bound together to form a booklet.
Page layout is managed such that page 1 is printed next to the last page and so on so when
they are folded, they are in the correct order.

There are different sizes of booklets (--size parameter) and the pages will be scaled accoringly.
Depending on the width-to-height proportions, sometimes there is blank space to retain the proper
aspect.  Changing the source paper size can yield better results with more use of the paper. For
instance when printing either large or small size booklets on letter, using tabloid as a source
and making everything 4 times larger will fill out the booklet pages.

The "amount" parameters (--hoffset, --width, --height) are delta adjustments and must be made
using a unit suffix of: in, cm, or mm.

The --signature parameter specifies the maximum number of pages in each signature (or binding group)
and must be a multiple of 4. If omitted, the entire PDF will be printed as a single signature. By printing
the content into multiple signatures, this allows larger books to be bound that would normally not be
able to be folded over with so many pages.
"""
opt = None
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pdf_booklet")


class PdfSignatureReader(PyPDF2.PdfFileReader):
    """
    Adds signature properties and methods to the PDFFileReader to allow reading page ranges defined by
    each "signature" - Book binding term referring to page groups that are bound together.
    """

    def __init__(self, start_page, end_page, *args, **kwargs):
        self.signature_start = start_page
        self.signature_end = end_page
        super().__init__(*args, **kwargs)

    @property
    def signature_page_count(self):
        return (self.signature_end - self.signature_start) + 1

    def get_signature_page(self, pageNumber):
        physical_page = pageNumber + self.signature_start
        logger.debug(f"Signature page number called with {pageNumber} mapped to physical page {physical_page}")
        if physical_page < self.signature_start or physical_page > self.signature_end:
            raise RuntimeError(f"Page {pageNumber} out of range ({self.signature_start} to {self.signature_end})")
        return super().getPage(physical_page)


def get_options():
    """
    Parses the command line options
    """
    global opt

    # Create a parser object
    parser = argparse.ArgumentParser(description='Create PDF booklet', epilog=EPILOG)

    # Positional required arguments
    parser.add_argument('file_in',
                        help="Name of the input PDF file")
    parser.add_argument('file_out',
                        help="Name of the output PDF file")

    # Optional keyword arguments
    parser.add_argument('--paper', type=str, default='letter', required=False,
                        help="[opt] destination paper size: {}".format(", ".join(page_sizes.keys())))
    parser.add_argument('--blank', type=int, default=0, required=False,
                        help="number of blank pages to append")
    parser.add_argument('--signature', type=int, default=0, required=False,
                        help="max number of pages per signature (must be a multiple of 4")
    parser.add_argument('--hoffset', type=str, required=False,
                        help="amount to reduce/increase distance from edge")
    parser.add_argument('--width', type=str, required=False,
                        help="amount to reduce/increase width")
    parser.add_argument('--height', type=str, required=False,
                        help="amount to reduce/increase width")
    parser.add_argument('--size', type=str, default='large', required=False,
                        help="Booklet size (default=large)")
    parser.add_argument('--valign', type=str, default='center', required=False,
                        help="vertical alignment when scaled: top, center, bottom (default=center)")
    parser.add_argument('--debug', action="store_true", dest='debug', required=False,
                        help="Additional features for debugging")

    opt = parser.parse_args()

    if opt.signature % 4 > 1:
        raise ValueError("signature argument must be a multiple of 4!")


def determine_booklet_page_counts(sig_in):
    """
    Determines total pages needed and the front and back pointers needed for processing
    :param sig_in: PdfSignatureReader object
    :return: tuple - (front_pointer, back_pointer, output_page_count)
    """
    target_pages = sig_in.signature_page_count + opt.blank
    front_pointer = 0
    back_pointer = target_pages - 1
    if target_pages % 4 > 0:
        back_pointer += 4 - target_pages % 4
    output_page_count = back_pointer + 1
    logger.debug(f"source signature has {sig_in.signature_page_count} pages, add blank={opt.blank} "
                 f"setting back_pointer to {back_pointer}")
    logger.debug(f"Signature will have {output_page_count} pages")
    return front_pointer, back_pointer, output_page_count


def source_page_or_none(pdf_reader, page_number):
    if page_number >= pdf_reader.signature_page_count:
        return None
    return pdf_reader.get_signature_page(page_number)


def get_translation_offset(source_page, target_width, target_height):

    # Convert width and height adjusments from mm to units
    width_adjust = get_units_from_parameter(opt.width)
    height_adjust = get_units_from_parameter(opt.height)

    # Because of the decimal fixed point, we must now convert everything to float
    # when doing floating point arithmatic
    page_width = float(source_page.mediaBox.getWidth())
    page_height = float(source_page.mediaBox.getHeight())

    # Choose the smallest scale: height vs. width to maintain aspect and fit
    scale = min((
        (target_width + width_adjust) / page_width,
        (target_height + height_adjust) / page_height
    ))

    # Calculate x and y offsets to center the source page onto the section of the target page
    x_offset = round((target_width - page_width * scale) / 2)
    if opt.valign == 'center':
        y_offset = round((target_height - page_height * scale) / 2)
    elif opt.valign == 'top':
        y_offset = round(target_height - page_height * scale)
    elif opt.valign == 'bottom':
        y_offset = round(height_adjust / 2)
    else:
        raise ValueError(f"Invalid valign value '{opt.valign}'")

    # Adjust for horizontal offset value
    if opt.hoffset is not None:
        if source_page.pdf.getPageNumber(source_page) % 2 > 0:
            x_offset -= get_units_from_parameter(opt.hoffset)
        else:
            x_offset += get_units_from_parameter(opt.hoffset)

    return x_offset, y_offset, scale


def generate_large_booklet_pages(sig_in):
    """
    Generates a new 2-up PDF page for booklet printing
    :param sig_in: Source PDF Reader object
    :return: None
    """

    front_pointer, back_pointer, output_page_count = determine_booklet_page_counts(sig_in)

    # Calculate output paper values
    if opt.paper in page_sizes.keys():
        source_width, source_height = page_sizes[opt.paper]
    else:
        raise ValueError("--paper option not valid")
    rotated_width = source_height
    rotated_height = source_width
    logger.debug(f"Output paper height={rotated_height}, width={rotated_width}")

    while front_pointer < back_pointer:

        # Get the front page object
        front_page = sig_in.get_signature_page(front_pointer)

        # Get the back page object or None if the pointer has not reached it yet.
        if back_pointer >= sig_in.signature_page_count:
            source = " (blank page)"
            back_page = None
        else:
            source = ""
            back_page = sig_in.get_signature_page(back_pointer)

        # Create a rotated new page
        target_page = PyPDF2.pdf.PageObject.createBlankPage(
            height=rotated_height,
            width=rotated_width
        )

        tile_width = rotated_width / 2
        tile_height = rotated_height

        # Determine left/right page so that the front/back pages alternate
        if front_pointer % 2:
            left_page = front_page
            right_page = back_page
            logger.debug(f"Printing page {front_pointer + 1} and {back_pointer + 1}{source}")
        else:
            left_page = back_page
            right_page = front_page
            logger.debug(f"Printing page {back_pointer + 1}{source} and {front_pointer + 1}")

        if left_page is not None:
            width_offset, height_offset, scale = get_translation_offset(left_page, tile_width, tile_height)
            logger.debug(f"left: width_adjust={width_offset}, height_adjust={height_offset}, scale={scale}")
            target_page.mergeScaledTranslatedPage(left_page, scale, width_offset, height_offset)

        if right_page is not None:
            width_offset, height_offset, scale = get_translation_offset(right_page, tile_width, tile_height)
            logger.debug(f"right: width_adjust={width_offset}, height_adjust={height_offset}, scale={scale}")
            target_page.mergeScaledTranslatedPage(right_page, scale, rotated_width/2 + width_offset, height_offset)

        yield target_page

        back_pointer -= 1
        front_pointer += 1


def generate_small_booklet_pages(sig_in):
    """
    Generator function to yield each PDF page 8-up. Yields PDF Page ojbects
    :param sig_in: PDFSignatureReader object
    :return:
    """
    # Get the normal booklet layout pointers and page count
    front_pointer, back_pointer, output_page_count = determine_booklet_page_counts(sig_in)
    # Calculate output paper values
    if opt.paper in page_sizes.keys():
        source_width, source_height = page_sizes[opt.paper]
    else:
        raise ValueError("--paper option not valid")
    rotated_width = source_height
    rotated_height = source_width
    logger.debug(f"Output paper height={rotated_height}, width={rotated_width}")
    # Determine positions for column and row based on the destination paper size
    paper_rows = [round(rotated_height / 2), 0]
    logger.debug(f"rows at {paper_rows}")
    paper_columns = [
        0,
        round(rotated_width * .25),
        round(rotated_width * .5),
        round(rotated_width * .75)
    ]
    logger.debug(f"columns at {paper_columns}")
    # Determine the number of sheets needed. 8 per sheet (16 for both sides)
    sheets = (output_page_count // 16) * 2
    if (output_page_count % 16) > 0:
        sheets += 2
    logger.debug(f"Signature will be printed onto {sheets} sheets")

    # Create a list of pages in booklet order
    booklet_pages = []
    while front_pointer < back_pointer:

        # Pages for the front of the output sheet back on left, front on right
        for page_offset in (0, 2, 4, 6):
            back_page_no = back_pointer - page_offset
            front_page_no = front_pointer + page_offset
            if front_page_no < back_page_no:
                booklet_pages.append(source_page_or_none(sig_in, back_page_no))
                booklet_pages.append(source_page_or_none(sig_in, front_page_no))
            else:
                booklet_pages.extend((None, None))

        # Pages for the back of the output sheet back on right, front on left
        for page_offset in (3, 1, 7, 5):
            back_page_no = back_pointer - page_offset
            front_page_no = front_pointer + page_offset
            if front_page_no < back_page_no:
                booklet_pages.append(source_page_or_none(sig_in, front_page_no))
                booklet_pages.append(source_page_or_none(sig_in, back_page_no))
            else:
                booklet_pages.extend((None, None))

        # update pointers
        back_pointer -= 8
        front_pointer += 8

    logger.debug(f"Generating new pages from {len(booklet_pages)} images")

    scaled_width = round(rotated_width / 4)
    scaled_height = round(rotated_height / 2)

    for sheet in range(sheets):

        target_page = PyPDF2.pdf.PageObject.createBlankPage(
            height=rotated_height,
            width=rotated_width
        )

        # Loop through each row (y position)
        for row in paper_rows:
            # Loop through each column (x position)
            if len(booklet_pages) < 1:
                break
            # Loop through each column (x position)
            for column in paper_columns:
                # Break out when there are no more pages
                if len(booklet_pages) < 1:
                    break
                # Get the source page
                source_page = booklet_pages.pop(0)
                if source_page is None:
                    logger.debug(f"Skipping empty location x={column} y={row} sheet={sheet + 1}")
                    continue
                # Get the offset from lower left point for tile location and the scale factor
                x_offset, y_offset, scale = get_translation_offset(source_page, scaled_width, scaled_height)
                # Calculate x and y locations to center the source page onto the section of the target page
                x_location = column + x_offset
                y_location = row + y_offset
                # Translate and scale onto the target page
                logger.debug(f"Generating page {sig_in.getPageNumber(source_page) + 1} scale={scale:.2f} "
                              f"x={x_location} y={y_location} sheet={sheet + 1}")
                target_page.mergeScaledTranslatedPage(source_page, scale, x_location, y_location)

        # Add the target page to the pdf writer object
        yield target_page


def generate_signatures(input_file):
    """
    Generates signatures of pages.  If the max signature was not specified or the total pages of the PDF
    are <= the max signature then we can just yeild the pdf reader object.  Otherwise yield each
    PDFSignatureReader object for each range of signature pages.
    :param input_file:
    :return:
    """

    pdf_in = PyPDF2.PdfFileReader(input_file)

    source_data = PdfData(pdf_in)
    logger.debug(f"Source PDF name={opt.file_in} page_count={source_data.page_count}")

    if opt.signature < 1:
        logger.debug("signature option not supplied--single signature will be generated")
        yield PdfSignatureReader(0, pdf_in.numPages - 1, input_file)
    elif pdf_in.numPages <= opt.signature:
        logger.debug("pages not greater than max signature--single signature will be generated")
        yield PdfSignatureReader(0, pdf_in.numPages - 1, input_file)
    else:
        signature_number = 1
        for start_page in range(0, pdf_in.numPages, opt.signature):
            if start_page + opt.signature - 1 >= pdf_in.numPages:
                end_page = pdf_in.numPages - 1
            else:
                end_page = start_page + opt.signature - 1
            logger.debug(f"Generating signature number {signature_number} from pages {start_page}-{end_page}")
            yield PdfSignatureReader(start_page, end_page, input_file)
            signature_number += 1
    return


def main():

    global logger

    start_time = time.time()

    get_options()

    if opt.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Input file context
    with open(opt.file_in, 'rb') as input_file:

        if opt.size == 'large':
            page_generator = generate_large_booklet_pages
        elif opt.size == 'small':
            page_generator = generate_small_booklet_pages
        else:
            raise RuntimeError("Illegal page size")

        # Generate the new pages
        page_count = 0
        pdf_out = PyPDF2.PdfFileWriter()
        for sig_in in generate_signatures(input_file):
            for page in page_generator(sig_in):
                pdf_out.addPage(page)
                page_count += 1

        # Save the new file
        logger.debug("Writing new pages to output file")
        with open(opt.file_out, "wb") as output_file:
            pdf_out.write(output_file)

        et = time.time() - start_time
        logger.info(f"Processed {page_count} new pdf pages in {et:.2f}s")


if __name__ == '__main__':
    main()
