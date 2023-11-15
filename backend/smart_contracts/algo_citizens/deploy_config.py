import logging

from algokit_utils import ApplicationSpecification, Account, TransactionParameters, OnSchemaBreak, OnUpdate
from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient
from algosdk import encoding, transaction
import binascii
import nacl.hash, nacl.encoding
from beaker import consts

logger = logging.getLogger(__name__)


# define deployment behaviour based on supplied app spec
def deploy(
    algod_client: AlgodClient,
    indexer_client: IndexerClient,
    app_spec: ApplicationSpecification,
    deployer: Account,
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
        on_schema_break=OnSchemaBreak.AppendApp,
        on_update=OnUpdate.AppendApp,
    )
    logger.info(f'Deployed with {deployer.address}, app_id {app_client.app_id}')
    
    
    suggested_params = algod_client.suggested_params()
    fund_txn = transaction.PaymentTxn(deployer.address, suggested_params, app_client.app_address, 1 * consts.algo)
    signed_fund_txn = fund_txn.sign(deployer.private_key)
    tx_id = algod_client.send_transaction(signed_fund_txn)
    result = transaction.wait_for_confirmation(algod_client, tx_id, 4)
    logger.info(f'Funded app')
    
    return app_client.app_id
