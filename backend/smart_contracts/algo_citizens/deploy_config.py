import logging

import algokit_utils
from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient
import binascii

logger = logging.getLogger(__name__)


# define deployment behaviour based on supplied app spec
def deploy(
    algod_client: AlgodClient,
    indexer_client: IndexerClient,
    app_spec: algokit_utils.ApplicationSpecification,
    deployer: algokit_utils.Account,
) -> None:
    from smart_contracts.artifacts.AlgoCitizens.client import (
        AlgoCitizensClient,
    )

    app_client = AlgoCitizensClient(
        algod_client,
        creator=deployer,
        indexer_client=indexer_client,
    )
    app_client.deploy(
        on_schema_break=algokit_utils.OnSchemaBreak.AppendApp,
        on_update=algokit_utils.OnUpdate.AppendApp,
    )

    address = "AM6VLI34GB7CUDQFTLSQT7G6NNKKJMPTS3V5GVWTHFCRV332AJS5BFMBYQ"
    try:
        response = app_client.get_vote_test(address=address, proposalId=1)
        logger.info(
            f"Called get_vote_test on {app_spec.contract.name} ({app_client.app_id}) "
            f"with name={address}, proposalId {1}, tx_id: {response.tx_id}, response: {binascii.hexlify(response.raw_value)}, result: {response.return_value}"
        )
    except:
        print('Call has failed')
        
    )
