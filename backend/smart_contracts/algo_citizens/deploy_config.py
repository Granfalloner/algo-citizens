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
        

    from algosdk import transaction, encoding
    from algosdk.atomic_transaction_composer import (
        AtomicTransactionComposer,
        AccountTransactionSigner,
        TransactionWithSigner
    )


    print(f'app sender: {deployer.address}, app id: {app_client.app_id}')
    deployer = algokit_utils.get_account(algod_client, "DEPLOYER", fund_with_algos=0)

    atc = AtomicTransactionComposer()
    signer = AccountTransactionSigner(deployer.private_key)

    emptyTxns = [
        transaction.ApplicationNoOpTxn(deployer.address, algod_client.suggested_params(), app_client.app_id, [binascii.unhexlify('f7ca29da'), i])
        for i in range(0, 7)
    ]

    pk = encoding.decode_address(address)
    getVoteTxn = transaction.ApplicationNoOpTxn(deployer.address, algod_client.suggested_params(), app_client.app_id, [binascii.unhexlify('f2c07ee3'), pk, 1])
    getVoteTxnWithSigner = TransactionWithSigner(getVoteTxn, signer)

    atc.add_transaction(getVoteTxnWithSigner)
    for txn in emptyTxns:
        atc.add_transaction(TransactionWithSigner(txn, signer))

    response = atc.execute(algod_client, 4)
    print(f'Response: txn ids: {response.tx_ids}, results: {response.abi_results}')
    for res in response.abi_results:
        print(res.return_value)
