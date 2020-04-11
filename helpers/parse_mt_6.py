"""

Image Analysis:

Demographics:
    Name , Age, and ward are always in the same place in the header of the EHR.

    Coordinates:
        Name : {x: 3,y: 28}, {x: 250,y: 43} // Names can be long strings
        Age : {x: 63,y: 45}, {x: 230,y: 62} // Gender is also in the same image.
        Ward : {x: 2,y: 62}, {x: 250,y: 80} // Ward name can be long strings
        MRN: {x, 990,y: 26}, {x: 1115,y: 44}


Information Table:
    Information table lies in coordinates {x: 0,y = 102},{x: 1120, y: 940}
    To extract information from this table, table needs to be analyzed for colors. Below are the list of
    observations that are important to be able to parse this table.

    The color of outer border i.e. Surrounding the entire table , the color of border above / below the dates
    and the color of divider between readings are distinct.

    List of colors :
        outer_border: {r: 102, g: 119,b: 204}
        date_upper_and_lower_border: {r: 150,g: 150,b: 150}
        inner_table_divider: {r: 230,g: 230,b: 230}

    My take on how to parse the table :
        1. The table will always me centered in the page's X axis.
            - A color check through y will always yield results if there is anything in the
             table.
            - Helps us limit the Y range to search  for horizontal search because if the table is small i.e. has
            very limited numbers of readings, the table might not be at the center of the page for X detections.

        2. Colors:
            Every table's outer border has same color. Detect the Y

"""
import os
import re

import cv2
from fuzzywuzzy import fuzz
from fuzzywuzzy import process as fprocess

import time
from datetime import datetime
from datetime import date
try:
    from helper_methods import *
    from parse_exceptions import PatientIsUnder18, PatientWardIsInvalid
except ModuleNotFoundError:
    from .helper_methods import *
    from .parse_exceptions import PatientIsUnder18, PatientWardIsInvalid


from mss import mss

from terminaltables import AsciiTable
import pytz


class MtSixParser:
    def __init__(self, coordinate_dict, color_dict, image_path=None,
                 key_dict=None, mrn_regex_match=r"(\w\w\d\d\d\d\d\d\d\d\d\d)"):
        self.DEBUG = 0
        self.DISPLAY_PARSED_TABLES = 0
        self.image = None
        self.coordinate_dict = coordinate_dict
        self.color_dict = color_dict
        self.mrn_regex_match = mrn_regex_match
        self.special_chars_regex = re.compile(r'[^0-9a-zA-Z#%() ]')
        if image_path is None:
            self.take_screen_shot_or_read()
        else:
            self.take_screen_shot_or_read(image_path)
        if key_dict is None:
            self.key_dictionary = {
                "Pulse": "HR",
                "Pulse Rate": "HR",
                "Temperature": "Temp",
                "Respiratory Rate": "RespRate",
                "O2 Saturation": "SpO2",
                "02 Saturation": "SpO2",
                "WBC": "WBC",
                "PIt Count": "Platelets",
                "Plt Count": "Platelets",
                "INR": "INR",
                "BUN": "BUN",
                "Creatinine": "Creatinine",
                "Glucose": "Glucose",
                "Lactic Acid": "Lactate",
                "ABG Lactic Acid": "Lactate",
                "_ABG Lactic Acid": "Lactate",
                "VBG Lactic Acid": "Lactate",
                "_VBG Lactic Acid": "Lactate",
                "Total Bilirubin": "Bilirubin",
                "ABG pH": "pH",
                "ABG pO2": "PaO2",
                "FiO2": "FiO2",
                "FIO2": "FiO2",
                "Blood Pressure": "Blood Pressure",
                "SysABP": "SysABP",
                "DiasABP": "DiasABP",
                'wBC': "WBC",
                'RBC': 'RBC',
                'MCV': 'MCV',
                'MCH': 'MCH',
                'MCHC': 'MCHC',
                'RDW': 'RDW',
                'MPV': 'MPV',
                'Basophils %': 'Basophils',
                'Basophils % (Manual)': 'Basophils',
                'Neutrophils %': 'Neutrophils',
                'Neutrophils % (Manual)': 'Neutrophils',
                'Lymphocytes %': 'Lymphocytes',
                'Lymphocytes % (Manual)': 'Lymphocytes',
                'Monocytes %': 'Monocytes',
                'Monocytes % (Manual)': 'Monocytes',
                'Eosinophils %': 'Eosinophils',
                'Eosinophils % (Manual)': 'Eosinophils',
                'Myelocytes %': 'Myelocytes',
                'Myelocytes % (Manual)': 'Myelocytes',
                'Basophils #': 'Basophils Absolute',
                'Basophils # (Manual)': 'Basophils Absolute',
                'Neutrophils #': 'Neutrophils Absolute',
                'Neutrophils # (Manual)': 'Neutrophils Absolute',
                'Lymphocytes #': 'Lymphocytes Absolute',
                'Lymphocytes # (Manual)': 'Lymphocytes Absolute',
                'Monocytes #': 'Monocytes Absolute',
                'Monocytes # (Manual)': 'Monocytes Absolute',
                'Eosinophils #': 'Eosinophils Absolute',
                'Eosinophils # (Manual)': 'Eosinophils Absolute',
                'Myelocytes #': 'Myelocytes Absolute',
                'Myelocytes # (Manual)': 'Myelocytes Absolute',
                'Band Neutrophils %': 'Bands'
            }
        else:
            self.key_dictionary = key_dict

    def take_screen_shot_or_read(self, image_path=None):
        """
        Loads an image as CV2 Image if a path is provided. Otherwise,
        Takes a screen-shot and loads the image .
        :param image_path:
        :return:
        """
        if image_path is not None:
            self.image = read_image(image_path)
        else:
            __path = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "sc.png")
            try:
                os.remove(__path)
            except FileNotFoundError:
                pass
            time.sleep(1)
            mss().shot(output=__path)
            time.sleep(2)
            self.image = read_image(__path)
            os.remove(__path)

    def parse_header(self, ward_names, ward_map):
        """
        Extract Name of patient , Ward of Patient and
        :return:
        """

        # Image containing Name
        name_image = crop_image(self.coordinate_dict['name_image']['top'],
                                self.coordinate_dict['name_image']['bottom'],
                                self.image)
        # Image containing Date Of Birth
        dob_image = crop_image(self.coordinate_dict['dob_image']['top'],
                               self.coordinate_dict['dob_image']['bottom'],
                               self.image)
        # Image containing patient location
        ward_image = crop_image(self.coordinate_dict['ward_image']['top'],
                                self.coordinate_dict['ward_image']['bottom'],
                                self.image)
        # Image containing patient MRN
        mrn_image = crop_image(self.coordinate_dict['mrn_image']['top'],
                               self.coordinate_dict['mrn_image']['bottom'],
                               self.image)

        name_data = re.sub('[^A-Za-z0-9, ]+', '',
                           parse_text_from_image(name_image))
        # print(name_data)
        name_dict = {
            'first': name_data.split(',')[1],
            'last': name_data.split(",")[0]
        }

        dob_and_gender_data = parse_text_from_image(
            dob_image).replace("\n", "").replace('O', '0').replace('l', '1')

        # print(dob_and_gender_data)
        if "M" in dob_and_gender_data:
            gender_data = 'M'
            dob_and_gender_data.replace("M", "")
        else:
            gender_data = "F"
            dob_and_gender_data.replace("F", "")

        DOB_data_match = re.search(
            r'(\d\d/\d\d/\d\d\d\d)', dob_and_gender_data)
        DOB = None
        parsed_dob_data = None
        if DOB_data_match:
            DOB = DOB_data_match.group()
            # print(DOB)
        if DOB is not None:
            divided_dob = DOB.split("/")
            parsed_dob_data = datetime(year=int(divided_dob[-1]),
                                       day=int(divided_dob[-2]),
                                       month=int(divided_dob[-3])) \
                .isoformat()
        bed = None
        room = None
        ward_data = parse_text_from_image(
            ward_image, erode=False, scale=3, psm=3).replace("—", '-')

        # Remove admission status from ward

        ward_data = ward_data.replace("ADM INO", "")
        ward_data = ward_data.replace("ADM IN", "")
        ward_data = ward_data.replace("DIS INO", "")
        ward_data = ward_data.replace("DIS IN", "")
        ward_data = ward_data.replace("REG SDC", "")

        ward_data = ward_data.strip()
        # print(ward_data)
        # regex match bed information
        bed_information = re.search(r'(\d*-\d*)', ward_data)

        if bed_information:
            # if bed information is present
            bed_gr = bed_information.group()
            # remove bed number from ward
            room, bed = bed_gr.split("-")
            ward_name = ward_data.replace(bed_gr, "")
            # replace repetitive strings
            ward_name = ward_name.strip().replace("0", 'O')
            ward_name = ward_name.strip().replace("SS5S", "S5")
            ward_name = ward_name.strip().replace("S5S", 'S5')
            ward_name = ward_name.strip().replace("OO", "O")

        else:
            # If no bed number found. e.g ER
            ward_name = ward_data

        # See if this is in the ward_map - if so, use that value
        if ward_name in ward_map:
            ward_name = ward_map[ward_name]
        else:
            ward_name, score = fprocess.extractOne(
                ward_name, ward_names, scorer=fuzz.partial_ratio)
            # CHECK FOR CORRECT WARD
            if score < 90:
                raise PatientWardIsInvalid(
                    "Patient ward is not eligible to be parsed")
        # cv2.imshow("Original ", name_image)
        # solved_image = create_image_for_horizontal_addition(30, width=400, character=name_data)
        # cv2.imshow("parsed_image", solved_image)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        #
        # cv2.imshow("Original ", dob_image)
        # solved_image = create_image_for_horizontal_addition(30, width=400, character=parsed_dob_data)
        # cv2.imshow("parsed_image", solved_image)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        #
        # cv2.imshow("Original ", ward_image)
        # solved_image = create_image_for_horizontal_addition(30, width=400, character=ward_name)
        # cv2.imshow("parsed_image", solved_image)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        #
        # cv2.imshow("Original ", ward_image)
        # solved_image = create_image_for_horizontal_addition(30, width=400, character=bed)
        # cv2.imshow("parsed_image", solved_image)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()

        mrn_data = parse_text_from_image(mrn_image).replace("\n", "")\
            .replace('O', '0').replace('l', '1')

        if self.DEBUG:
            parsed_information = [["Title", "Value"],
                                  ["Name", name_data],
                                  ['DOB', parsed_dob_data],
                                  ['Gender', gender_data],
                                  ["Ward", ward_name],
                                  ["Bed", bed],
                                  ["Room", room],
                                  ["MRN", mrn_data]
                                  ]

            table = AsciiTable(parsed_information)
            print(table.table)
        # return ward_data
        extracted_information = [
            create_demographic_dict_structure("name", name_dict),
            create_demographic_dict_structure("DOB", parsed_dob_data),
            create_demographic_dict_structure("gender", gender_data),
            create_demographic_dict_structure("ward", ward_name),
            create_demographic_dict_structure('MRN', mrn_data)

        ]
        if bed is not None:
            extracted_information.append(
                create_demographic_dict_structure("bed", bed))
            extracted_information.append(
                create_demographic_dict_structure("room", room))
        # print(extracted_information)
        return extracted_information

    def patient_age_and_ward_check_pass(self, ward_names, ward_map):
        """
        check if the patient is under 18
        :return: False if patient is under 18
        """

        # remove to allow 18 and under patients to be parsed
        # dob_image = crop_image(self.coordinate_dict['dob_image']['top'],
        #                        self.coordinate_dict['dob_image']['bottom'],
        #                        self.image)

        ward_image = crop_image(self.coordinate_dict['ward_image']['top'],
                                self.coordinate_dict['ward_image']['bottom'],
                                self.image)
        ward_data = parse_text_from_image(
            ward_image, erode=False, scale=3, psm=3).replace("—", '-')

        # Remove admission status from ward

        ward_data = ward_data.replace("ADM INO", "")
        ward_data = ward_data.replace("ADM IN", "")
        ward_data = ward_data.replace("DIS INO", "")
        ward_data = ward_data.replace("DIS IN", "")
        ward_data = ward_data.replace("REG SDC", "")

        ward_data = ward_data.strip()
        # regex match bed information
        bed_information = re.search(r'(\d*-\d*)', ward_data)

        if bed_information:
            # if bed information is present
            bed = bed_information.group()
            # remove bed number from ward
            ward_name = ward_data.replace(bed, "")
            # replace repetitive strings
            ward_name = ward_name.strip().replace("0", 'O')
            ward_name = ward_name.strip().replace("SS5S", "S5")
            ward_name = ward_name.strip().replace("S5S", 'S5')
            ward_name = ward_name.strip().replace("OO", "O")

        else:
            # If no bed number found. e.g ER
            ward_name = ward_data

        # See if this is in the ward_map - if so, use that value
        if ward_name in ward_map:
            ward_name = ward_map[ward_name]
        else:
            ward_name, score = fprocess.extractOne(
                ward_name, ward_names, scorer=fuzz.partial_ratio)
            # CHECK FOR CORRECT WARD
            if score < 90:
                raise PatientWardIsInvalid(
                    "Patient ward is not eligible to be parsed")

        # Else continue to check for date
        # dob_and_gender_data = parse_text_from_image(dob_image).replace("\n", "")
        #
        # DOB_regex = re.compile(r'(\d\d/\d\d/\d\d\d\d)')
        # DOB_data_match = DOB_regex.search(dob_and_gender_data)
        #
        # # If we did not have a match, try replacing O with 0, then try again
        # if not DOB_data_match:
        #     replaced_dob_string = dob_and_gender_data.replace('O', '0').replace('o', '0')
        #     DOB_data_match = DOB_regex.search(replaced_dob_string)
        #
        # DOB = None
        # if DOB_data_match:
        #     DOB = DOB_data_match.group()
        #     # print(DOB)
        # if DOB is not None:
        #     timezone = pytz.timezone(hospital_timezone)
        #     divided_dob = DOB.split("/")
        #     dob_obj = datetime(year=int(divided_dob[-1]),
        #                        day=int(divided_dob[-2]),
        #                        month=int(divided_dob[-3]))
        #     utc_dob_obj = timezone.localize(dob_obj).astimezone(pytz.utc)
        #     today_date = datetime.utcnow()
        #     if (today_date.year - utc_dob_obj.year - (
        #             (today_date.month, today_date.day) < (utc_dob_obj.month, utc_dob_obj.day))) >= 18:
        #         return True
        #     else:
        #         raise PatientIsUnder18("Patient is under the age of 18")
        # else:
        #     # No DOB found
        #     raise PatientIsUnder18("No DOB found - patient may be under 18")

    def parse_table_data(self):
        """
        Parse the table inside the main body of an image provided
        and return a list of measurement dicts.
        :return:
        """
        image_size = get_image_size(self.image)
        # print(image_size)

        table_outer_border_color = {'r': 102, 'g': 119, 'b': 204}
        table_date_border_color = {'r': 150, 'g': 150, 'b': 150}
        table_inner_border_color = {'r': 230, 'g': 230, 'b': 230}

        # we need to find a upper and lower Y bound in order to control
        # how much area we have to search for lines running in y axis.

        color_location_result = detect_color_location(
            table_outer_border_color, self.image, 'y')

        # No table was detected - return empty list
        if not color_location_result:
            return []

        upper_table_bound = color_location_result[0]

        cropped_image_for_lines_on_y_axis = crop_image({
            'x': 0,
            'y': upper_table_bound
            }, {
            'x': image_size['width'],
            'y': upper_table_bound + 50
            }, self.image)

        table_vertical_bounds = detect_color_location(
            table_outer_border_color, cropped_image_for_lines_on_y_axis, 'x')
        right_table_bound = None
        if len(table_vertical_bounds) >= 2:
            right_table_bound = table_vertical_bounds[1]
        left_table_bound = table_vertical_bounds[0]

        inner_table_lines_running_along_y_axis = detect_color_location(
            table_inner_border_color,
            cropped_image_for_lines_on_y_axis,
            'x')

        # x coordinate of lines running from top tp bottom inside the table
        inner_table_lines_running_along_x_axis = detect_color_location(
            table_inner_border_color,
            self.image,
            'y')
        # y coordinate of lines running from left to right inside the table
        table_lines_surrounding_date_along_x_axis = detect_color_location(
            table_date_border_color,
            self.image,
            'y')
        # Y coordinates of lines running from lef tot right
        # inside the table around the dates column

        if inner_table_lines_running_along_x_axis:
            final_vertical_coordinates_list = \
                table_lines_surrounding_date_along_x_axis + \
                inner_table_lines_running_along_x_axis + \
                [inner_table_lines_running_along_x_axis[-1] + 19]
        else:
            final_vertical_coordinates_list = \
                table_lines_surrounding_date_along_x_axis + \
                [table_lines_surrounding_date_along_x_axis[-1] + 19]

        # final vertical coordinates = coordinates around the dates +
        #                              coordinates of lines running inside the table +
        #                              coordinates of end of table
        if right_table_bound and \
           right_table_bound > inner_table_lines_running_along_y_axis[-1]:
            last_horizontal_coordinate = right_table_bound
        else:
            last_horizontal_coordinate = \
                inner_table_lines_running_along_y_axis[-1] + 112

        final_horizontal_coordinates_list = [left_table_bound] +\
            inner_table_lines_running_along_y_axis +\
            [last_horizontal_coordinate]

        # final horizontal coordiantes = coordinate of left beginning of the table +
        #                                coordinates of lines running inside the table +
        #                                coordinates of right most border of the table

        img_arr = create_image_array(
            final_horizontal_coordinates_list,
            final_vertical_coordinates_list,
            self.image)
        # create a 2D array of images
        final_information_array = []
        length_counter = None
        for row in img_arr:
            img = stitch_image(row, character="END")
            # create a single image and use 'END' as the filler in the images
            # show_image(img)

            information_parsed_from_image = parse_text_from_image(
                img, scale=3).replace("—", "").replace("\n", " ") \
                .replace("©", "O").strip()

            split_information_from_image = information_parsed_from_image.\
                split("END")
            # divide the returned text into a list of information
            final_information_array.append(split_information_from_image)
            if self.DEBUG:
                print("Length of parsed Information: {}".format(
                    len(split_information_from_image)))

        if self.DISPLAY_PARSED_TABLES:
            table = AsciiTable(final_information_array)
            print(table.table)
        return final_information_array

    def divide_time_stamp(self, time_stamp_string):
        """

        :param time_stamp_string:
        :return:
        """
        # print("Incoming time stamp: {}".format(time_stamp_string))
        try:
            time_stamp_string = " ".join(
                re.sub("[^0-9a-zA-Z /:]", "", time_stamp_string)
                .strip().split())
            date_string, time_string = time_stamp_string.strip().split(" ")
            # print("DS: {}".format(date_string))
            # print("TS: {}".format(time_string))
            month, day, year = date_string.split("/")
            hour, minute = time_string.split(":")
            if len(year) == 2:
                year = "20" + year
            time_dictionary = {
                "month": int(month),
                "year": int(year),
                "day": int(day),
                "hour": int(hour),
                "minute": int(minute)
            }
            return time_dictionary
        except Exception:
            # print("TS Conversion Failed.")
            return None

    def create_array_to_post_to_parser(self, list_of_parsed_data_lists,
                                       time_zone):
        """
        create an array of information that is acceptable by the controller
        i.e. list of patient info dicts
        :param list_of_parsed_data_lists:
        :return:
        """
        final_information_array = []
        # iterate over list of readings
        for list_counter in range(1, len(list_of_parsed_data_lists)):
            # iterate over hourly readings
            for counter in range(1, len(list_of_parsed_data_lists[0])):
                parsed_data = create_measurement_dict_structure(
                    self.special_chars_regex.sub(
                        "", list_of_parsed_data_lists[0][counter]).strip(),
                    list_of_parsed_data_lists[list_counter][counter],
                    self.divide_time_stamp(
                        list_of_parsed_data_lists[list_counter][0]),
                    self.key_dictionary)
                if isinstance(parsed_data, list) and None not in parsed_data:
                    final_information_array = final_information_array +\
                        parsed_data
        # make sure to convert every value to float

        for measurement_dictionary in final_information_array:
            measurement_dictionary['data']['val'] = float(
                measurement_dictionary['data']['val'])
            ts = pytz.timezone(time_zone).localize(
                measurement_dictionary["data"]["ts"])
            ts = ts.astimezone(pytz.utc)
            ts = ts.replace(tzinfo=None)
            measurement_dictionary["data"]["ts"] = ts

        if self.DEBUG:
            len(final_information_array)
            for info in final_information_array:
                print(info)

        return final_information_array

    def parse_patient_list(self):
        """
        Parse a patient list image
        :return:
        """
        list_of_images = []
        list_of_ids = []
        image_size = get_image_size(self.image)
        patient_list_outer_border_color = self.color_dict[
            'patient_list_outer_border_color']
        patient_list_inner_border_color = self.color_dict[
            'patient_list_inner_border_color']
        patient_list_header_bottom_color = self.color_dict[
            'patient_list_header_bottom_color']

        # detect the outer top and bottom border of the patient list
        # to limit the search image for x axis
        grid_y_locations = detect_color_location(
            patient_list_inner_border_color,
            self.image,
            'y')
        if grid_y_locations is None:
            grid_y_locations = []
        if len(grid_y_locations) > 1:
            # when there are more than two patients in a list
            y_grid_detection_image = crop_image({
                'x': 0,
                'y': grid_y_locations[0]
                }, {
                'x': image_size['width'],
                'y': grid_y_locations[-1]
                }, self.image)
            grid_x_locations = detect_color_location(
                patient_list_inner_border_color, y_grid_detection_image, 'x')

        elif len(grid_y_locations) == 1:
            # where there are two patients in a list or less

            y_grid_detection_image = crop_image({
                'x': 0,
                'y': grid_y_locations[0] - 5
                }, {
                'x': image_size['width'],
                'y': grid_y_locations[0] + 10
                }, self.image)
            grid_x_locations = detect_color_location(
                patient_list_inner_border_color, y_grid_detection_image, 'x')
        else:
            # when there is only one patient is a list
            # detect the line under the date
            header_location = detect_color_location(
                patient_list_header_bottom_color, self.image, 'y')
            # crop image to detect the lines along y axis
            y_grid_detection_image = crop_image({
                'x': 0,
                'y': header_location[0] - 5
                }, {
                'x': image_size['width'],
                'y': header_location[0] + 10
                }, self.image)
            grid_x_locations = detect_color_location(
                patient_list_inner_border_color, y_grid_detection_image, 'x')
            # extract image where MRN is present
            image_to_parse = crop_image({
                'x': grid_x_locations[-2],
                'y': header_location[0]
                }, {
                'x': grid_x_locations[-1],
                'y': header_location[0] + 17
                }, self.image)
            # push to be parsed
            list_of_images.append(image_to_parse)

        # iterate through y coordinates and extract images of patient IDs
        if len(grid_y_locations) > 0:
            for y in grid_y_locations:
                image_to_parse = crop_image({
                    'x': grid_x_locations[-2],
                    'y': y - 17
                    }, {
                    'x': grid_x_locations[-1],
                    'y': y
                    }, self.image)
                list_of_images.append(image_to_parse)

            # last patient is a special case. It will need to be
            # added separately as its below the coordinates of detected line

            last_patient_image = crop_image({
                'x': grid_x_locations[-2],
                'y': grid_y_locations[-1] + 1
                }, {
                'x': grid_x_locations[-1],
                'y': grid_y_locations[-1] + 17
                }, self.image)
            list_of_images.append(last_patient_image)
        else:
            pass
        # send extracted images one by one to tesseract for parsing
        for img in list_of_images:
            # show_image(img)
            parsed_data = parse_text_from_image_simple(img)
            match = re.search(self.mrn_regex_match, parsed_data)
            if match:
                list_of_ids.append(match.group())
        if self.DEBUG:
            for ids in list_of_ids:
                print(ids)
        return [{"account_num": _id.strip()} for _id in list_of_ids]


if __name__ == "__main__":
    start = time.time()

    coordinate_dictionary = {
        "name_image": {
            "top": {'x': 3, 'y': 28}, "bottom": {'x': 250, 'y': 47}},
        "dob_image": {
            "top": {'x': 25, 'y': 45}, "bottom": {'x': 230, 'y': 62}},
        "ward_image": {
            "top": {'x': 2, 'y': 62}, "bottom": {'x': 250, 'y': 80}}
    }
    color_dictionary = {
        "table_outer_border_color": {'r': 102, 'g': 119, 'b': 204},
        "table_date_border_color": {'r': 150, 'g': 150, 'b': 150},
        "table_inner_border_color": {'r': 230, 'g': 230, 'b': 230},
        "patient_list_inner_border_color": {'r': 230, 'g': 230, 'b': 230},
        "patient_list_outer_border_color": {'r': 102, 'g': 119, 'b': 204},
        # not used yet. Maybe if current logic is not enough
        # to extract all information
        "patient_list_header_bottom_color": {'r': 150, 'g': 150, 'b': 150},
    }

    ward_list_name = [
        "4MS4W", "5MS5E", "DEP ER EC", "REG ER EC", "3OBS",
        "6PED", "5ONC", "6SEL", "3SUR", "6ICU"
    ]

    for root, dirs, files in os.walk("test_images/v6"):
        counter = 0
        for file in files:
            if file.endswith('.png'):
                print("FILE: {}".format(file))
                sixParser = MtSixParser(
                    image_path=os.path.join("test_images/v6", file),
                    coordinate_dict=coordinate_dictionary,
                    color_dict=color_dictionary)
                sixParser.DISPLAY_PARSED_TABLES = True
                sixParser.DEBUG = True
                # if sixParser.patient_age_check_pass():
                sixParser.parse_header("00000", ward_list_name, ward_map={
                    "iSOBS": "1SOBS",
                    "1S0BS": "1SOBS",
                    "iS0BS": "1SOBS"
                })
                # sixParser.create_array_to_post_to_parser(sixParser.parse_table_data())
                # print()
                # try:
                #     sixParser.create_array_to_post_to_parser(sixParser.parse_table_data())
                # except:
                #     print("Error in file : {}".format(file))
                #     pass
                # counter += 1
                # print(sixParser.parse_patient_list())
    # print(list(set(ward_list)))
    end = time.time()
    print(end - start)
