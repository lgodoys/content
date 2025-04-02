"""
Chain Abuse Integration for Cortex XSOAR - Unit Tests file
"""

import pytest
from Packs.ChainAbuse.Integrations.ChainAbuse.ChainAbuse import ChainAbuseClient,\
    chainabuse_report_command,\
    chainabuse_get_report_command
from CommonServerPython import DemistoException, Dict, json

SERVER_URL = "https://api.chainabuse.com/v0/"
client = ChainAbuseClient(
    base_url=SERVER_URL,
    insecure=True,
    proxy=False,
    api_key='',
)


def util_load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.loads(f.read())


bitcoin_responses = util_load_json('test_data/bitcoin_responses.json')
report_address_scenarios = util_load_json('test_data/report_command.json')
successful_bitcoin_report_command_output = 'Chain address 12xfas41 by abuse bitcoin user ' \
                                           'blabla@blabla.net was reported to ' \
                                           'ChainAbuse service'
failure_bitcoin_report_command_output = 'bitcoin report address did not succeed: {}'.format(
    bitcoin_responses['failure']['response'])
get_indicators_scenarios = util_load_json('test_data/get_indicators_command.json')


@pytest.mark.parametrize('response, address_report, expected',
                         [(bitcoin_responses['success'],
                           report_address_scenarios['valid'],
                           successful_bitcoin_report_command_output
                           ),
                          (bitcoin_responses['success'],
                           report_address_scenarios['valid_other'],
                           successful_bitcoin_report_command_output)
                          ])
def test_report_address_successful_command(requests_mock, response: Dict, address_report: Dict, expected: str):
    """
        Given:
         - Chain address to report.

        When:
         - Reporting valid address to Chain Abuse service.

        Then:
         - When reporting to the API should return failure - the command fails and the correct output is given.
         - When reporting to the API should success - the command succeeds and the correct output is given.
        """
    requests_mock.post(
        'https://api.chainabuse.com/v0/reports/batch',
        json=response
    )
    assert chainabuse_report_command(client, address_report).readable_output == expected


@pytest.mark.parametrize('address_report, expected',
                         [(report_address_scenarios['other_type_missing'],
                           'Chain Abuse: abuse_type_other is mandatory when abuse type is other'),
                          (report_address_scenarios['unknown_type'],
                           'Chain Abuse: invalid type of abuse, please insert a correct abuse type')
                          ])
def test_report_address_command_invalid_arguments(address_report: Dict, expected: str):
    """
       Given:
        - Invalid bitcoin address report.

       When:
        - Trying to report the address to Chain Abuse service.

       Then:
        - Ensure the command throws an error.
        - Ensure the expected error with the expected error message is returned.
       """

    with pytest.raises(DemistoException, match=expected):
        chainabuse_report_command(client, address_report)


def test_failure_response_from_bitcoin_abuse(requests_mock):
    """
       Given:
        - bitcoin address report.

       When:
        - Trying to report the address to Chain Abuse Api, and receiving a failure response from Chain Abuse service.

       Then:
        - Ensure the command throws an error.
        - Ensure the expected error with the expected error message is returned.
       """
    requests_mock.post(
        'https://api.chainabuse.com/v0/reports/',
        json=bitcoin_responses['failure']
    )
    with pytest.raises(DemistoException, match=failure_bitcoin_report_command_output):
        chainabuse_report_command(client, report_address_scenarios['valid'])
