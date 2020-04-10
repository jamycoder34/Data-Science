from helpers.parser import get_initial_date_of_birth_and_ward_check
from helpers.parse_exceptions import PatientWardIsInvalid


def throw_patient_absent_error(data=None):
    return {
        "data": {
            "task_data": {
                "status": "patient_absent"
            }
        }
    }


def parse_patient_header_for_age_and_ward(context=None):
    try:
        parse_patient = get_initial_date_of_birth_and_ward_check()
    except (PatientWardIsInvalid):
        return False
    return True


def report_upcoming_citrix_password_change_slack(context):
    """
    Report upcoming Citrix password change requirement to slack channel
    :param context: worker context
    :return:
    """
    try:
        import requests
        payload = {}
        payload["text"] = context["config"]["worker name"] + "@" + context["config"]["hospital name"] + " needs a Citrix password change - expiring soon" 
        # Sends notification to the scraper-failures slack room
        url = "https://hooks.slack.com/services/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"
        r = requests.post(url=url,
                          json=payload,
                          timeout=1)
    except:
        print("Uh oh something's not right in report_to_slack_channel through a custom function")


if __name__ == "__main__":
    import time
    time.sleep(5)
    print(parse_patient_header_for_age_and_ward({'config': {'hospital timezone': 'America/New_York'}}))
