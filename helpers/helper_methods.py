import pytz
import copy
from datetime import datetime
import re

import pytesseract
import pytz
from PIL import Image
import cv2
import numpy as np
import inspect

DEBUG = 0  # textual debug information
DEBUG_IMAGES = 0  # Display images that are to be processed or being used in some form of parsing
DEBUG_IMAGES_DEV = 0  # Display Images with visual cues to be used in development.
#  e.g. placing markers on initial image to help with coordinates and shit
IMG_SHOT_WAIT = False
# Destroy the image being displayed in 200 MS. to use keyboard, Use False
float_regex = re.compile(r'\-?\d+\.?\d*')


def get_image_size(image):
    height, width, channels = image.shape
    return {'height': height, "width": width}


def read_image(image_path):
    """
    Read an image in cv2 format
    CV2 reads image as BGR (NOT RGB)
    :param image_path: location of image
    :return:
    """
    image = cv2.imread(image_path)
    return image


def color_dict(color):
    """
    Change RGB dictionary to list of RGB
    :param color: {'r': int, 'g': int, 'b': int}
    :return: [r,g,b]
    """
    return [color['b'], color['g'], color['r']]


def crop_image(top_left, bottom_right, image):
    """
    crop and return a subsection of an image
    :param top_left:
    :param bottom_right:
    :param image:
    :return:
    """

    img = image[top_left['y']:bottom_right['y'], top_left['x']:bottom_right['x']]
    if DEBUG_IMAGES:
        show_image(img, "Cropped Image: ")
    return img


def convert_color(color_from, color_to, image):
    """
    Find a color and replace it with another color
    :param color_from: {'r': int, 'g': int,'b':int}
    :param color_to: {'r': int, 'g': int,'b':int}
    :param image: Image to do replacement in. If no image specified, original image is altered .
    :return:
    """

    image[np.where((image == color_dict(color_from)).all(axis=2))] = color_dict(color_to)
    return image


def is_consecutive(int_list):
    """
    Sometimes, though the probability is 1/1280 for this to happen, The middle of a page can be a straight line
    where we are trying to detect the colors.
    Since @joe will ask me again anyway, if we try 3 times to search for x moving 5 pixels to the left, I believe
    the probability of hitting a straight line three times is 1/2097152000, Hope this is a satisfactory number for you.
    :param int_list: list to check for consecutive numbers in.
    :return:
    """
    if len(int_list) < 1 or len(int_list) == 1:
        return False
    for counter in range(len(int_list) - 1):
        if int_list[counter + 1] - int_list[counter] < 3:
            return True
    return False


def detect_color_location(color, image, axis):
    """
    runs through the middle of a provided image and looks for a color.
    Returns all the x / y coordinates of a color's location.
    :param color: {'r':int[0,255], 'g':int[0,255], 'b':int[0,255]}
    :param image: Image to do an x / y search in
    :param axis: [x,y] axis
    :return: [int] pixel locations
    """

    # if DEBUG_IMAGES:
    #     show_image(image)
    try_count = 0  # in case of three consecutive searches in which straight lines are returned, stop
    detected_pixel_location = []  # array of pixel x or y where a particular color is located
    color = color_dict(color)  # color being searched for.
    image_x = image.shape[1]  # x size of image [width]
    image_y = image.shape[0]  # y size of image [height]

    if DEBUG:
        print("Image Size : x = {} y = {}".format(image_x, image_y))
    image_x_middle = int(image_x / 2)
    image_y_middle = int(image_y / 2)
    if DEBUG:
        print("Middle Of Image: x = {} y = {}".format(image_x_middle, image_y_middle))

    if axis not in ['x', 'y']:
        return None  # No axis was provided
    else:
        if axis in ['x', 'X']:

            if DEBUG_IMAGES_DEV:
                im_temp = copy.deepcopy(image)
                cv2.line(im_temp, (0, image_y_middle), (image_x, image_y_middle), (0, 0, 0), 1)
                show_image(im_temp, "detect_color_location__X")
            while not detected_pixel_location and try_count < 3:  # empty pixel array
                for x in range(0, image_x):
                    color_at_location = image[image_y_middle, x].tolist()  # get color value as list of 3 integers
                    if color_at_location == color:
                        if DEBUG:
                            print("Found color at : [{}, {}] : {}".format(x, image_y_middle, color_at_location))
                        detected_pixel_location.append(x)
                        # if color at current location is a match to the one searching for,
                        # add the x location to list.

                if is_consecutive(detected_pixel_location) or len(detected_pixel_location) == 0:
                    # if the current search took place and ended up on a line, do the search again
                    # Reset the detected_pixel_location to empty and subtract 5 pixels from y axis to more the
                    # line a bit to the right and run same logic again.

                    if DEBUG:
                        print("Inside debug. Pizel locations: {}".format(detected_pixel_location))
                        print("Consecutive\nRe-checking ")
                    detected_pixel_location = []
                    try_count += 1
                    image_y_middle = image_y_middle - 5
                    if try_count == 3:
                        if DEBUG:
                            print("Try Count Exceeded 3.\n Failure")
                        return None

            if DEBUG_IMAGES:
                im_temp = copy.deepcopy(image)
                for x in detected_pixel_location:
                    cv2.circle(im_temp, (x, image_y_middle), 3, (0, 0, 0))
                show_image(im_temp, "detect_color_location_X_LOCATIONS")

        elif axis in ['y', 'Y']:
            im_temp = copy.deepcopy(image)
            if DEBUG_IMAGES_DEV:
                cv2.line(im_temp, (image_x_middle, 0), (image_x_middle, image_y), (0, 0, 0), 1)
                show_image(im_temp, "detect_color_location__Y")
            while not detected_pixel_location and try_count < 3:
                for y in range(0, image_y):
                    color_at_location = image[y, image_x_middle].tolist()
                    if color_at_location == color:
                        if DEBUG:
                            print("Found color at : [{}, {}] : {}".format(y, image_x_middle, color_at_location))
                        detected_pixel_location.append(y)
                if is_consecutive(detected_pixel_location) or len(detected_pixel_location) < 1:
                    if DEBUG:
                        print("Consecutive\nRe-checking ")
                    detected_pixel_location = []
                    try_count += 1
                    image_x_middle = image_x_middle - 5
                    if try_count == 3:
                        if DEBUG:
                            print("Try Count Exceeded 3. \nFailure")
                        return None

            if DEBUG_IMAGES:
                im_temp = copy.deepcopy(image)
                for y in detected_pixel_location:
                    cv2.circle(im_temp, (image_x_middle, y), 3, (0, 0, 0))
                show_image(im_temp, "detect_color_location_Y_LOCATIONS")
        return detected_pixel_location


def create_image_for_vertical_addition(width, height=17, character='END'):
    """
    Creates an Image with word "END" written in it as a delimiter for readings.
    :param width:
    :param height:
    :param character:
    :return:
    """
    img = np.ones((height, width, 3), np.uint8) * 255
    font = cv2.FONT_HERSHEY_DUPLEX
    bottom_left_corner_of_text = (int(width / 2) - int((width / 100) * 40), int(height / 2)
                                  + int((height / 100) * 40))
    font_scale = .5
    font_color = (0, 0, 0)
    line_type = 1
    cv2.putText(img, character,
                bottom_left_corner_of_text,
                font,
                font_scale,
                font_color,
                line_type)
    return img


def create_image_for_horizontal_addition(height, width=40, character="END"):
    """
    Create a image of specified height in white back ground and plain text written on it.
    :param height: Height of image to create
    :param width:
    :param character: Text to type
    :return:
    """
    img = np.ones((height, width, 3), np.uint8) * 255
    font = cv2.FONT_HERSHEY_DUPLEX
    bottom_left_corner_of_text = (int(width / 2) - int((width / 100) * 40), int(height / 2))
    font_scale = .5
    font_color = (0, 0, 0)
    line_type = 1
    cv2.putText(img, character,
                bottom_left_corner_of_text,
                font,
                font_scale,
                font_color,
                line_type)
    return img


def stitch_image(array_of_images, orientation="vertical", character='END'):
    """
    Takes in an array of image of SAME WIDTH OR SAME HEIGHT and joins them together
    using the orientation.
    :param array_of_images:
    :param orientation:
    :param character:
    :return:
    """
    if orientation == "vertical":
        height, width, _ = array_of_images[0].shape
        filler = create_image_for_vertical_addition(width, character=character)
        image = array_of_images[0]
        for images in range(1, len(array_of_images)):
            image = np.concatenate((image, filler), axis=0)
            image = np.concatenate((image, array_of_images[images]), axis=0)
        if DEBUG_IMAGES:
            show_image(image)
        return image


def parse_text_from_image(image, scale=2, erode=True, erode_iteration=1, erode_kernel=2, psm=6):
    """
    OCR the crap out of an image to extract all text in it.
    :param psm:
    :param erode_kernel:
    :param erode_iteration:
    :param erode:
    :param image: image to parse text from
    :param scale: size the image needs to be magnified to
    :return:
    """
    if DEBUG:
        print("Parsing Image")
        print("Called from Method: {}".format(inspect.stack()[1][3]))
    img = cv2.resize(image, (0, 0), fx=scale, fy=scale)
    if erode:
        img = apply_erode_filter(img, erode_iteration, erode_kernel)
    if DEBUG_IMAGES:
        show_image(img)
    data = pytesseract.image_to_string(Image.fromarray(img), config='--psm {}'.format(psm))

    if DEBUG:
        print("Identified String: \n{}\n      ------------      ".format(data))
    return data


def parse_text_from_image_simple(image, psm=6):
    """
    Simpler OCR of an image
    :param psm:
    :param image: image to parse text from
    :return:
    """
    grayscale_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    big_img = cv2.resize(grayscale_img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    tess_result = pytesseract.image_to_string(Image.fromarray(big_img), config='--psm {}'.format(psm))

    if DEBUG:
        print("Identified String: \n{}\n      ------------      ".format(tess_result))
    return tess_result


def apply_erode_filter(t, iterations, kernel):
    """
    Apply erode filter to the image.
    :param t:
    :param iterations: Number of erode iterations
    :param kernel: size of erode kernel
    :return:
    """
    b_w_img = cv2.cvtColor(t, cv2.COLOR_BGR2GRAY)
    ret, thresh = cv2.threshold(b_w_img, 127, 255, cv2.THRESH_BINARY)
    kernel = np.ones((kernel, kernel), np.uint8)
    img = cv2.erode(thresh, kernel, iterations=iterations)
    return img


def create_image_array(x_coordinates, y_coordinates, image):
    """
    divide an image in array of images [[img, img, img, img],
                                        [img, img, img, img],
                                        [img, img, img, img]]
    arrays are oriented along the y axis.
    i.e. images is divided in array from top to bottom,
     then to the next x coordinate and again divided from top to bottom

    :param x_coordinates:
    :param y_coordinates:
    :param image:
    :return:
    """
    array_of_array_of_images = []
    for x in range(len(x_coordinates) - 1):
        array_of_images = []
        for y in range(len(y_coordinates) - 1):
            img = image[y_coordinates[y]:y_coordinates[y + 1], x_coordinates[x]:x_coordinates[x + 1]]
            array_of_images.append(img)
        array_of_array_of_images.append(array_of_images)
    return array_of_array_of_images


def show_image(img, title="Image"):
    cv2.imshow(title, img)
    if IMG_SHOT_WAIT:
        cv2.waitKey(200)
    else:
        cv2.waitKey(0)
    cv2.destroyAllWindows()


def create_demographic_dict_structure(header, value):
    """

    :param header:
    :param value:
    :return:
    """
    d = {"type": "demographics", 'data': {}}
    d['data']['prop'] = header
    d['data']['value'] = value
    return d


def manage_keys(header, dict_of_headers):
    """
    Checks if header is convertable in
    :param header:
    :param dict_of_headers:
    :return:
    """
    # print("Header being searched: {}".format(header))
    if header.strip() in dict_of_headers.keys():
        return dict_of_headers[header.strip()]
    else:
        return None


def create_dictionary(header, value, ts):
    """
    Create a dictionary acceptable by the core.

    :param header:
    :param value:
    :param ts:
    :return: If time stamp check passes, Dictionary otherwise None
    """
    # print("Header: {} Valye: {} ts : {}".format(header, value, ts))

    # This is pretty hacky but will work for now
    # Leave blood pressure and temp values raw for now. Convert all others to float
    # or return if no float (shouldn't ever happen)
    value = value.strip() if value else None
    if not value:
        return
    float_exceptions = {'temp', 'blood pressure', 'o2 delivery method', 'covid-19 pcr'}
    if header.lower() not in float_exceptions:
        re_result = float_regex.search(value)
        if not re_result:
            return
        value = re_result[0]
    measurement_dict = {"type": "measurement", 'data': {}}
    measurement_dict['data']['mmt'] = header
    measurement_dict['data']['rt'] = datetime.utcnow()
    measurement_dict['data']['val'] = value
    if isinstance(ts, dict):
        try:
            # print(ts)
            parsed_time = datetime(year=ts['year'],
                                   month=ts['month'],
                                   day=ts['day'],
                                   hour=ts['hour'],
                                   minute=ts['minute'])

            measurement_dict['data']['ts'] = parsed_time
            # print("Inside create dict: {}".format(measurement_dict))
            return measurement_dict
        except Exception:
            return None
    else:
        measurement_dict['data']['ts'] = ts

        return measurement_dict


def manage_special_keys(data):
    """
    Manage temp and blood pressure keys
    :param data:
    :return:
    """
    if data['data']['mmt'].lower() == 'temp' and data['data']['val'] is not "":
        # Make sure we just have the float value
        re_result = float_regex.search(data['data']['val'])
        data['data']['val'] = round((float(re_result[0]) - 32) * 5 / 9, 2)
        return data
    elif data['data']['mmt'].lower() == 'blood pressure':
        if data['data']['val'] is not "" and "/" in data['data']['val']:
            split_val = data['data']['val'].split('/')
            ret = [create_dictionary('SysABP', split_val[0], data['data']['ts']),
                   create_dictionary('DiasABP', split_val[1], data['data']['ts'])]
            return ret
    else:
        return data


def create_measurement_dict_structure(header, value, ts, dict_of_acceptable_keys):
    """
    convert parsed strings to dictionary structure acceptable by the controller
    :param dict_of_acceptable_keys:
    :param header:
    :param value:
    :param ts:
    :return:
    """
    if DEBUG:
        print("Incoming values : Header : {} \nValue: {} \nTs: :{}".format(header, value, ts))

    # Check if header is acceptable i.e. its in the dictionary
    header_val_for_database = manage_keys(header, dict_of_acceptable_keys)
    if header_val_for_database is None:
        if DEBUG:
            print("Key {} not found in provided dict_for_acceptable_keys".format(header))
        return None

    # Check all values are provided
    if header is None or value is None or ts is None:
        if DEBUG:
            print("None Value provided: \nHeader: {}\nValue: {}\nTS: {}".format(header, value, ts))
        return None
    float_exceptions = ['o2 delivery', '02 delivery', 'coronavirus']
    if not any(i in header.lower() for i in float_exceptions):
        # Make sure there is at least one float in the value
        # (to accomodate Blood Pressure)
        re_result = float_regex.search(value)
        if not re_result:
            return None

    # Create a dictionary that can be submitted to the controller
    measurement_dict = create_dictionary(header_val_for_database, value, ts)
    if measurement_dict is None:
        if DEBUG:
            print(f'{header_val_for_database} and {value} resulted in None')
        return None
    # Manage keys that need changes to values. i.e. Temp and BP

    measurement_dict = manage_special_keys(measurement_dict)
    if type(measurement_dict) is type([]):
        return measurement_dict
    else:
        return [measurement_dict]


def parse_icd_codes_from_table(list_of_parsed_data_lists, time_zone):
    """
    convert list_of_parsed_data_lists to list of dicts
    acceptable by the controller
    :param list_of_parsed_data_lists:
    :param time_zone:
    :return:
    """
    problems = list_of_parsed_data_lists[1]
    collection_ts = list_of_parsed_data_lists[5]
    values = list_of_parsed_data_lists[6]
    parsed_data = list()
    for problem, ts, value in zip(problems, collection_ts, values):
        ts = get_date_object(ts, time_zone)
        """
        one limitation of scraper-worker at present is that
        if a ts of None is supplied, rt will not be automatically
        isoformatted. This will cause a JSON serialization error
        when submitting the data to the controller.
        Therefore, if you ever have a None ts, the rt must be isoformatted
        before returning the mmt object.
        """
        rt = datetime.utcnow() if ts else datetime.utcnow().isoformat()

        data = {
            'rt': rt,
            'ts': ts,
            'mmt': 'Diagnosis Codes',
            'val': value.strip() if value else None,
        }
        if problem:
            data.update({
                'text': problem.strip()
            })
        parsed_data.append({
            'type': 'measurement',
            'data': data
        })
    return parsed_data


def get_date_object(ts, time_zone):
    """
    Convert ts to UTC date object
    :param: ts:
    :return:
    """
    if not ts:
        return
    try:
        date_format = '%m/%d/%Y %H:%M'
        ts = datetime.strptime(ts.strip(), date_format)
    except ValueError:
        return

    ts = pytz.timezone(time_zone).localize(ts)
    ts = ts.astimezone(pytz.utc)
    ts = ts.replace(tzinfo=None)
    return ts
