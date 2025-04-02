import demistomock as demisto  # noqa: F401
from CSVFeedApiModule import *
from CommonServerPython import *  # noqa: F401

# disable insecure warnings
urllib3.disable_warnings()

""" CONSTANTS """
SERVER_URL = "https://api.chainabuse.com/v0/"


class ChainAbuseClient(BaseClient):
    def __init__(self, base_url, insecure, proxy, api_key):
        super().__init__(base_url=base_url, verify=not insecure, proxy=proxy)
        self.server_url = base_url
        self.api_key = api_key
        self.insecure = insecure

    def report_address(self, args: Dict) -> Dict:
        """
        Sends a post request to report an abuse to ChainAbuse servers.
        """
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authentication": f"Basic {base64.b64encode(f'{self.api_key}:{self.api_key}'.encode()).decode()}"
        }

        body = [
            {
                "accusedScammers": [{}],
                "addresses": [{}],
                "tokens": [{}],
                "transactionHashes": [{}],
                "agreedToBeContactedData": {},
                "categoryDescription": None,
                "compromiseIndicators": [{}],
                "description": "",
                "evidences": [{}],
                "losses": [{}],
                "scamCategory": None,
            }
        ]

        for k, v in args:
            if "cntc" in k:
                if k == "cntc" and v or v == "true":
                    body["agreedToBeContactedData"]["agreed"] = v  # type: ignore
                    if k == "cntcLaw":
                        body["agreedToBeContactedData"]["agreedToBeContactedByLawEnforcement"] = v  # type: ignore
                    elif k == "cntcName":
                        body["agreedToBeContactedData"]["name"] = v  # type: ignore
                    elif k == "cntcEmail":
                        body["agreedToBeContactedData"]["email"] = v  # type: ignore
                elif k == "cntc" and not v or v == "false":
                    body["agreedToBeContactedData"]["agreed"] = v  # type: ignore
            elif "add" in k:
                if k == "add_address":
                    body["addresses"][0]["address"] = v  # type: ignore
                elif k == "add_domain":
                    body["addresses"][0]["domain"] = v  # type: ignore
                elif k == "add_chain":
                    body["addresses"][0]["chain"] = v  # type: ignore
                elif k == "add_label":
                    body["addresses"][0]["label"] = v  # type: ignore
            elif "accused" in k:
                if k == "accusedContact":
                    body["accusedScammers"][0]["contact"] = v  # type: ignore
                elif k == "accusedType":
                    body["accusedScammers"][0]["type"] = v  # type: ignore
            elif "tokens" in k:
                body["tokens"][0]["tokenId"] = v  # type: ignore
            elif "transact" in k:
                if k == "transactHash":
                    body["transactionHashes"][0]["hash"] = v  # type: ignore
                elif k == "transactChain":
                    body["transactionHashes"][0]["chain"] = v  # type: ignore
                elif k == "transactLabel":
                    body["transactionHashes"][0]["label"] = v  # type: ignore
            elif "comp" in k:
                if k == "compValue":
                    body["compromiseIndicators"][0]["value"] = v  # type: ignore
                elif k == "compType":
                    body["compromiseIndicators"][0]["type"] = v  # type: ignore
            elif "evidence" in k:
                body["evidences"][0]["source"] = v  # type: ignore
            elif "loss" in k:
                if k == "lossAsset":
                    body["losses"][0]["asset"] = v  # type: ignore
                elif k == "lossAmount":
                    body["losses"][0]["amount"] = v  # type: ignore
            else:
                body[k] = v  # type: ignore

        return self._http_request(method="POST",url_suffix="reports/batch",json_data=body,headers=headers)

    def get_report(self, args) -> Tuple[List[Dict], bool]:
        """
        Builds CSV module client and performs the API call to Chain Abuse service.
        If the call was successful, returns list of indicators.
        Args:

        Returns:
            - Throws exception if an invalid api key was given or error occurred during the call to
              Chain Abuse service.
            - Returns indicators list if the call to Chain Abuse service was successful.
        """

        return self._http_request(
            method="GET",
            url_suffix="reports",
            params=args,
        )


""" COMMAND FUNCTIONS """


def chainabuse_report_command(cCoin_client: ChainAbuseClient, args: Dict) -> CommandResults:
    """|
    Reports a bitcoin abuse to Chain Abuse service.

    Args:
        cCoin_client (ChainAbuseClient): Client object to perform request.
        args (Dict): Demisto args for report address command.

    Returns:
        str: 'bitcoin address (address reported) by abuser (abuser reported) was
        reported to ChainAbuse API' if http request was successful'.
    """
    address = args.get("add_address")
    domain = args.get("add_domain")
    abuser = args.get("accusedContact")

    http_response = cCoin_client.report_address(args)

    if argToBoolean(http_response.get("success", False)):
        return CommandResults(
            readable_output=f"Chain address {address} or domain {domain} by abuse bitcoin user {abuser}"
            f" was reported to ChainAbuse service"
        )
    else:
        failure_message = http_response.get("response", "Unknown failure reason")
        raise DemistoException(f"Chain report address did not succeed: {failure_message}")


def test_module_command(cCoin_client: ChainAbuseClient):
    """
    Performs a fetch indicators flow to validate the configuration params.

    Args:
        cCoin_client (ChainAbuseClient): Client object.

    Returns:
        'ok' if the call to Chain Abuse service was successful and command is test_module.
    """
    cCoin_client.get_report(args={})
    return "ok"


def chainabuse_get_report_command(cCoin_client: ChainAbuseClient, args: Dict):
    """
    Wrapper for retrieving indicators from the feed to the war-room.

    Args:
        cCoin_client (ChainAbuseClient): Client object.
        args (Dict): Demisto args.

    Returns:
        CommandResults.
    """
    indicators, _ = cCoin_client.get_report(args)
    limit = arg_to_number(args.get("limit", 50), "limit")
    truncated_indicators_list = indicators[:limit]
    return CommandResults(
        readable_output=tableToMarkdown("Indicators", truncated_indicators_list, headers=["value", "type", "fields"]),
        raw_response=truncated_indicators_list,
    )


def main() -> None:
    params = demisto.params()
    command = demisto.command()

    demisto.debug(f"Chain Abuse: Command being called is {demisto.command()}")

    api_key = params.get("credentials_api_key", {}).get("password") or params.get("api_key", "")
    if not api_key:
        raise DemistoException("API Key must be provided.")
    insecure = params.get("insecure", False)
    proxy = params.get("proxy", False)

    try:
        cCoin_client = ChainAbuseClient(base_url=SERVER_URL, insecure=insecure, proxy=proxy, api_key=api_key)

        if command == "test-module":
            return_results(test_module_command(cCoin_client))
        elif command == "chainabuse_report_command":
            return_results(chainabuse_report_command(cCoin_client, demisto.args()))

        elif command == 'chainabuse-get-report':
            return_results(chainabuse_get_report_command(cCoin_client, demisto.args()))

    # Log exceptions and return errors
    except Exception as e:
        return_error(f"Failed to execute {demisto.command()} command.\nError:\n{str(e)}")


if __name__ in ("__main__", "__builtin__", "builtins"):
    main()
