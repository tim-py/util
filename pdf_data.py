import re

units_per_mm = 420.0 / 148.0
units_per_inch = 612.0 / 8.5
re_units = re.compile("(?P<value>[+\-]?[\d]*\.?[\d]+)(?P<suffix>cm|mm|in)")
page_sizes = {
    'letter':  (612, 792),
    'legal':   (612, 1008),
    'tabloid': (792, 1224),
    'a5':      (420, 595),
    'a4':      (595, 842)
}


def get_units_from_parameter(param):
    """
    Parses command line argument string, extracting the value and converting it to units recognized
    by PDF objects.
    :param param: str
    :return: int
    """
    if param is None:
        return 0
    units_match = re_units.match(param)
    if not units_match:
        raise ValueError(f"Unable to parse parameter '{param}'")
    if units_match.group('suffix') == "cm":
        return round(units_per_mm * 10 * float(units_match.group('value')))
    elif units_match.group('suffix') == 'mm':
        return round(units_per_mm * float(units_match.group('value')))
    elif units_match.group('suffix') == 'in':
        return round(units_per_inch * float(units_match.group('value')))
    else:
        raise RuntimeError("Script error: non-supported option")


class PdfData:

    def __init__(self, pdf_reader):
        self.pdf_reader = pdf_reader

    def get_xmp_attribute_safe(self, attribute):
        try:
            return getattr(self.pdf_reader.getXmpMetadata(), attribute)
        except:
            pass
        return None

    def get_document_info_safe(self, attribute):
        try:
            return self.pdf_reader.getDocumentInfo()[attribute]
        except:
            pass
        return None

    @property
    def title(self):
        value = self.get_document_info_safe('/Title')
        if value is None:
            value = self.get_xmp_attribute_safe('dc_title')
        return value

    @property
    def creator(self):
        return self.get_xmp_attribute_safe('dc_creator')

    @property
    def date(self):
        return self.get_xmp_attribute_safe('dc_date')

    @property
    def description(self):
        return self.get_xmp_attribute_safe('dc_description')

    @property
    def subject(self):
        return self.get_xmp_attribute_safe('dc_subject')

    @property
    def type(self):
        return self.get_xmp_attribute_safe('dc_type')

    @property
    def version(self):
        return self.get_xmp_attribute_safe('pdf_version')

    @property
    def format(self):
        return self.get_xmp_attribute_safe('dc_format')

    @property
    def page_count(self):
        return self.pdf_reader.numPages

    @property
    def pages(self):
        for page_no in range(self.page_count):
            yield self.pdf_reader.getPage(page_no)
        return

    @property
    def largest_page(self):
        height = 0
        width = 0
        area = 0
        for page in self.pages:
            current_area =  page.mediaBox.getWidth() * page.mediaBox.getHeight()
            if current_area > area:
                height = page.mediaBox.getHeight()
                width = page.mediaBox.getWidth()
                area = current_area
        return height, width
