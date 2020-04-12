import os

from .parse_mt_6 import MtSixParser

MEDITECH_VERSION = 6
DEBUG_LOG = False
TABULAR_DISPLAY = False

coordinate_dictionary = {
    "name_image": {"top": {'x': 3, 'y': 28}, "bottom": {'x': 250, 'y': 47}},
    "dob_image": {"top": {'x': 25, 'y': 45}, "bottom": {'x': 230, 'y': 62}},
    "ward_image": {"top": {'x': 2, 'y': 62}, "bottom": {'x': 250, 'y': 80}},
    "mrn_image": {"top": {'x': 990, 'y': 26}, "bottom": {'x': 1115, 'y': 44}}
}
color_dictionary = {
    "table_outer_border_color": {'r': 102, 'g': 119, 'b': 204},
    "table_date_border_color": {'r': 150, 'g': 150, 'b': 150},
    "table_inner_border_color": {'r': 230, 'g': 230, 'b': 230},
    "patient_list_inner_border_color": {'r': 230, 'g': 230, 'b': 230},
    "patient_list_outer_border_color": {'r': 102, 'g': 119, 'b': 204},
    # not used yet. Maybe if current logic is not enough to extract all information
    "patient_list_header_bottom_color": {'r': 150, 'g': 150, 'b': 150},
    # not used yet. Maybe if current logic is not enough to extract all information
}

mrn_regex_match = "(\w\w\d\d\d\d\d\d\d\d\d\d)"

ward_list_name = ["1SOBS", "2SICU", "3NMEDONC", "3SCARD", "4MS4W", "4SSUR", "6PED", "5NMEDONC", "6NMEDSUR"]

ward_map = {
    "iSOBS": "1SOBS",
    "1S0BS": "1SOBS",
    "iS0BS": "1SOBS"
    }


def get_patient_icd_codes(parse_image_path, time_zone):
    """
    Parse patient icd table in body
    :return:
    """
    parser = MtSixParser(coordinate_dict=coordinate_dictionary,
                         color_dict=color_dictionary,
                         image_path=parse_image_path,
                         )
    return parser.parse_icd(parser.parse_table_data(), time_zone)


def get_patient_data(parse_image_path, time_zone):
    """
    Parse patient data table in body
    :return:
    """
    parser = MtSixParser(coordinate_dict=coordinate_dictionary,
                         color_dict=color_dictionary,
                         image_path=parse_image_path,
                         )
    return parser.create_array_to_post_to_parser(
        parser.parse_table_data(), time_zone)


def get_patient_header(parse_image_path):
    """
    Parse patient demographics
    :return:
    """
    parser = MtSixParser(coordinate_dict=coordinate_dictionary,
                         color_dict=color_dictionary,
                         image_path=parse_image_path)
    return parser.parse_header(ward_names=ward_list_name, ward_map=ward_map)


def get_patient_list(parse_image_path):
    """
    parse patient ID list
    :return:
    """
    parser = MtSixParser(coordinate_dict=coordinate_dictionary,
                         color_dict=color_dictionary,
                         image_path=parse_image_path)
    return parser.parse_patient_list()


def get_initial_date_of_birth_and_ward_check():
    """
    Check if current patient is above 18.
    :return: True if patient is above 18
    """
    parser = MtSixParser(coordinate_dict=coordinate_dictionary,
                         color_dict=color_dictionary)
    return parser.patient_age_and_ward_check_pass(ward_names=ward_list_name, ward_map=ward_map)
