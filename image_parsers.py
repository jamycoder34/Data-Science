from helpers.parser import get_patient_list, get_patient_header, get_patient_data


def parse_patient_list(parse_image_path, context):
    """
    Parse patient list

    :param parse_image_path: Path of image to parse
    :param context: Worker context

    :return:
    """
    list_of_patients = get_patient_list(parse_image_path)
    return list_of_patients


def parse_patient_header(parse_image_path, context):
    """
    Parse patient header - parses demographics information for patient

    :param parse_image_path: Path of image to parse
    :param context: Worker context

    :return:
    """
    patient_header_information = get_patient_header(
        parse_image_path
    )
    return patient_header_information


def parse_patient_information_table(parse_image_path, context):
    """
    Parse patient information table - parses labs and vitals for patient

    :param parse_image_path: Path of image to parse
    :param context: Worker context

    :return:
    """
    patient_table_information = get_patient_data(
        parse_image_path,
        context['config']['hospital timezone'],
        context['config']['parse_icd_codes']
        )
    return patient_table_information


if __name__ == "__main__":
    import time
    import pprint
    import os
    pp = pprint.PrettyPrinter()
    time.sleep(1)
    # This MRN is just dummy data, not patient info.
    context = {
        'config': {
            'hospital timezone': 'America/New_York',
            'parse_icd_codes': True
        },
        'task_state': {
            'current_patient': {'account_num': 'M000123123'}
            }
        }
    image_path = os.path.realpath('./test_data/image_parsers/parse_patient_information_table/labs6.png')
    parse_result = parse_patient_information_table(None, context)
    pp.pprint(parse_result)
    """
    results_by_key = {}
    results_by_key['demographics'] = []
    for item in parse_result:
        if item['type'] == 'measurement':
            if item['data']['mmt'] not in results_by_key:
                results_by_key[item['data']['mmt']] = [item]
            else:
                results_by_key[item['data']['mmt']].append(item)
        else:
            results_by_key['demographics'].append(item)
    pp.pprint(results_by_key)
    #print("No test defined.")
    """