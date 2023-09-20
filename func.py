#
# oci-notifications-to-netcool-python version 1.0.
#
# Copyright (c) 2023, Oracle and/or its affiliates. All rights reserved.
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.

import io
import json
import logging
import os
import requests

"""
This sample OCI Function maps OCI Notifications to IBM® Tivoli® Netcool/OMNIbus Probe for Message Bus
See https://www.ibm.com/docs/en/SSSHTQ_int/pdf/messbuspr-pdf.pdf
"""


# Use OCI Application or Function configurations to override these environment variable defaults.

api_endpoint = os.getenv('API_ENDPOINT', 'not-configured')
api_key = os.getenv('API_KEY', 'not-configured')
is_forwarding = eval(os.getenv('FORWARD_TO_ENDPOINT', "True"))

# Set all registered loggers to the configured log_level

logging_level = os.getenv('LOGGING_LEVEL', 'INFO')
loggers = [logging.getLogger()] + [logging.getLogger(name) for name in logging.root.manager.loggerDict]
[logger.setLevel(logging.getLevelName(logging_level)) for logger in loggers]


def handler(ctx, data: io.BytesIO = None):
    """
    OCI Function Entry Point
    :param ctx: InvokeContext
    :param data: data payload
    :return: plain text response indicating success or error
    """

    preamble = " {} / notification event count = {} / logging level = {} / forwarding to endpoint = {}"

    try:
        event_list = json.loads(data.getvalue())
        logging.getLogger().info(preamble.format(ctx.FnName(), len(event_list), logging_level, is_forwarding))
        logging.getLogger().debug(event_list)
        send_payload(event_list=transform_payload(event_list=event_list), ctx=ctx)

    except (Exception, ValueError) as ex:
        logging.getLogger().error('error in handler: {}'.format(str(ex)))
        logging.getLogger().error(ex)


def transform_payload(event_list):
    """
    """

    if isinstance(event_list, list) is False:
        event_list = [event_list]

    result_list = []
    for event in event_list:
        single_result = transform_event(event=event)
        result_list.append(single_result)
        logging.getLogger().debug(single_result)

    return result_list


def transform_event(event: dict):
    """
    This is performing no transformation at the moment
    """

    return event

    # notifications = [{
    #     'receiver': get_receiver_name(event),
    #     'status': get_status(event),
    #     'alerts': get_alerts(event),
    #
    # }]
    #
    # result = {
    #     'notifications': notifications
    # }
    # return result


def send_payload(event_list, ctx):
    """
    """

    if is_forwarding is False:
        logging.getLogger().debug("Endpoint forwarding is disabled - nothing sent")
        return

    # creating a session and adapter to avoid recreating
    # a new connection pool between each POST call

    session = requests.Session()

    try:
        adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10)
        session.mount('https://', adapter)

        api_headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        add_custom_headers(headers=api_headers, ctx=ctx)

        for event in event_list:
            logging.getLogger().debug("json to netcool: {}".format(json.dumps(event)))
            response = session.post(api_endpoint, data=json.dumps(event), headers=api_headers)

            if response.status_code != 200:
                raise Exception('error {} sending to Netcool: {}'.format(response.status_code, response.reason))

    finally:
        session.close()


def add_custom_headers(headers, ctx):
    """
    header1 --- Authorization=Bearer ++Oauth.access_token++
    header2 --- Accept=application/json
    header3 --- Content-Type=application/json
    """

    if ctx is None:
        return

    fn_config = ctx.Config()
    logging.debug('fn_config: {} ... {}'.format(type(fn_config), fn_config))

    for x, y in fn_config.items():

        if x.startswith('header'):
            assignment_parts = y.split('=')

            if len(assignment_parts) != 2:
                continue

            lvalue = assignment_parts[0]
            rvalue = assignment_parts[1]
            headers[lvalue] = rvalue


def local_test_linebreak_events_file(filename):
    """
    """

    logging.getLogger().info("local_test_linebreak_events_file testing started")

    with open(filename, 'r') as f:
        transformed_results = list()

        for line in f:
            event = json.loads(line)
            logging.getLogger().debug(json.dumps(event, indent=4))
            transformed_result = transform_event(event)
            transformed_results.append(transformed_result)

        logging.getLogger().debug(json.dumps(transformed_results, indent=4))
        send_payload(event_list=transformed_results, ctx=None)

    logging.getLogger().info("local testing completed")


def local_test_single_event_file(filename):
    """
    """

    logging.getLogger().info("local_test_single_event_in_file testing started")

    with open(filename, 'r') as f:
        transformed_results = list()
        event = json.load(f)
        transformed_result = transform_event(event)
        transformed_results.append(transformed_result)

        logging.getLogger().debug(json.dumps(transformed_results, indent=4))
        send_payload(event_list=transformed_results, ctx=None)

    logging.getLogger().info("local testing completed")


"""
Local Debugging 
"""

if __name__ == "__main__":
    local_test_single_event_file('test/netcool.outbound.json')

