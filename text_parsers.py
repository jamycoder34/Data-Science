def parse_patientid(text_to_parse, context):
    """
    Parse patientID from worker context

    :param text_to_parse: text to parse (will be empty)
    :param context: worker context

    :return: list containing demographics object containing patientID
    """
    patientID = context['task_state']['current_patient']['account_num']
    demo_object = {
        'type': 'demographics',
        'data': {
            'prop': 'patientID',
            'value': patientID
        }
    }
    return [demo_object]