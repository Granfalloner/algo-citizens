import beaker as bk
import pyteal as pt
from beaker.lib import storage
import typing

Asset_ID=pt.Int(1027)

class Proposal(pt.abi.NamedTuple):
    id: pt.abi.Field[pt.abi.Uint64]
    name: pt.abi.Field[pt.abi.String]
    author: pt.abi.Field[pt.abi.String]
    authorAddress: pt.abi.Field[pt.abi.Address]
    description: pt.abi.Field[pt.abi.String]
    isVotingActive: pt.abi.Field[pt.abi.Bool]
    yesVotes: pt.abi.Field[pt.abi.Uint64]


class User(pt.abi.NamedTuple):
    vote_count: pt.abi.Field[pt.abi.Uint64]
    vote_power: pt.abi.Field[pt.abi.Uint64]
    delegate: pt.abi.Field[pt.abi.Address]
    

class Vote(pt.abi.NamedTuple):
    proposalId: pt.abi.Field[pt.abi.Uint64]
    voter: pt.abi.Field[pt.abi.Address]

    
class AlgoState:
    proposal_counter = bk.GlobalStateValue(stack_type=pt.TealType.uint64, default=pt.Int(0))
    proposals = storage.BoxMapping(pt.abi.Uint64, Proposal)

    user_counter = bk.GlobalStateValue(stack_type=pt.TealType.uint64, default=pt.Int(0))
    users = storage.BoxMapping(pt.abi.Address, User)
    
    votes = storage.BoxMapping(pt.abi.String, Vote)

app = bk.Application("AlgoCitizens", state=AlgoState()) \
    .apply(bk.unconditional_create_approval, initialize_global_state=True)


# @app.external
# def testBox(name: pt.abi.String, value: pt.abi.String) -> pt.Expr:
#     return pt.App.box_put(name=name.get(), value=value.get())

# @app.external(read_only=True)
# def readTestBox(name: pt.abi.String, *, output: pt.abi.String) -> pt.Expr:
#     return pt.Seq(contents := pt.App.box_get(name.get()),
#                   pt.Assert(contents.hasValue()),
#                   output.set(contents.value()))


@app.external
# @app.external(authorize=bk.Authorize.holds_token(asset_id=Asset_ID))
def add_proposal(id: pt.abi.Uint64, name: pt.abi.String, author: pt.abi.String, description: pt.abi.String, *, output: Proposal) -> pt.Expr:
    authorAddress = pt.abi.Address()
    isVotingActive = pt.abi.Bool()
    yesVotes = pt.abi.Uint64()
    noVotes = pt.abi.Uint64()
    proposal = Proposal()

    return pt.Seq(
        pt.Assert(pt.Not(app.state.proposals[id].exists())),
        app.state.proposal_counter.increment(),
        authorAddress.set(pt.Txn.sender()),
        isVotingActive.set(False),
        yesVotes.set(0),
        noVotes.set(0),
        proposal.set(id, name, author, authorAddress, description, isVotingActive, yesVotes),
        app.state.proposals[id].set(proposal),
        app.state.proposals[id].store_into(output)
    )

@app.external(read_only=True)
def read_proposal(id: pt.abi.Uint64, *, output: Proposal) -> pt.Expr:
    return app.state.proposals[id].store_into(output)

@app.external
# @app.external(authorize=bk.Authorize.holds_token(asset_id=Asset_ID))
def vote(proposalId: pt.abi.Uint64, *, output: Proposal) -> pt.Expr:
    vote = Vote()
    key = pt.abi.String()
    address = pt.abi.Address()

    return pt.Seq(
        key.set(pt.Sha256(pt.Concat(pt.Txn.sender(), pt.Itob(proposalId.get())))),
        pt.Assert(pt.Not(app.state.votes[key].exists())),
        address.set(pt.Txn.sender()),
        vote.set(proposalId, address),
        app.state.votes[key].set(vote),
        app.state.votes[key].store_into(output)
    )


@app.external(read_only=True)
# @app.external(authorize=bk.Authorize.holds_token(asset_id=Asset_ID))
def get_vote(address: pt.abi.Address, proposalId: pt.abi.Uint64, *, output: Proposal) -> pt.Expr:
    key = pt.abi.String()

    return pt.Seq(
        key.set(pt.Sha256(pt.Concat(pt.Txn.sender(), pt.Itob(proposalId.get())))),
        pt.Assert(app.state.votes[key].exists()),
        app.state.votes[key].store_into(output)
    )
    
