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


    # address = "AM6VLI34GB7CUDQFTLSQT7G6NNKKJMPTS3V5GVWTHFCRV332AJS5BFMBYQ"
    params = TransactionParameters(boxes=[(app_client.app_id, encoding.decode_address(deployer.address))])
    response = app_client.is_registered(address=deployer.address, transaction_parameters=params)
    logger.info(f'User is registered already: {response.return_value}')

    if not response.return_value:
        response = app_client.register(transaction_parameters=params)
        logger.info(f'User registered')

    proposal_id = 0
    params = TransactionParameters(boxes=[(app_client.app_id, proposal_id)])
    response = app_client.proposal_exists(id=proposal_id, transaction_parameters=params)
    logger.info(f'Proposal exists already: {response.return_value}')
    
    if not response.return_value:
        response = app_client.add_proposal(
            id=proposal_id, 
            name='First Proposal', 
            author='Developer', 
            description='This is a development proposal', 
            transaction_parameters=params
        )
        logger.info(f'Added proposal: {response.return_value}')

    response = app_client.read_proposal(id=proposal_id, transaction_parameters=params)
    logger.info(f'Read proposal: {response.return_value}')

    # voting

    response = app_client.is_voting_open()
    logger.info(f'Voting is open: {response.return_value}')

    if not response.return_value:
        response = app_client.open_voting()
        logger.info(f'Opened voting: {response.return_value}')
        
    proposal_data = str(proposal_id).zfill(16) 
    message = encoding.decode_address(deployer.address) + binascii.unhexlify(proposal_data)
    vote_key = binascii.unhexlify('0020') + nacl.hash.sha256(message, nacl.encoding.RawEncoder)
    
    params = TransactionParameters(boxes=[(app_client.app_id, vote_key)])
    response = app_client.has_voted(address=deployer.address, proposalId=proposal_id, transaction_parameters=params)
    logger.info(f'Has voted already: {response.return_value}')

    try:
        params = TransactionParameters(boxes=[
            (app_client.app_id, deployer.public_key),
            (app_client.app_id, proposal_id),
            (app_client.app_id, vote_key),
        ])
        response = app_client.vote(proposalId=proposal_id, transaction_parameters=params)
        logger.info(f'Voted for proposal {proposal_id}, result: {response.return_value}')
    except Exception as e:
        logger.error(f'Voting error {e}')
    
    
    