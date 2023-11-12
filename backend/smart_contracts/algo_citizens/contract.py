import beaker as bk
import pyteal as pt
from beaker.lib import storage

Asset_ID=pt.Int(1027)

class Proposal(pt.abi.NamedTuple):
    id: pt.abi.Field[pt.abi.String]
    name: pt.abi.Field[pt.abi.String]
    author: pt.abi.Field[pt.abi.String]
    authorAddress: pt.abi.Field[pt.abi.Address]
    description: pt.abi.Field[pt.abi.String]
    isVotingActive: pt.abi.Field[pt.abi.Bool]
    yesVotes: pt.abi.Field[pt.abi.Uint64]
    noVotes: pt.abi.Field[pt.abi.Uint64]


class AlgoState:
    proposal_counter = bk.GlobalStateValue(stack_type=pt.TealType.uint64, default=pt.Int(0))
    proposals = storage.BoxMapping(pt.abi.String, Proposal)

    user_vote_count = bk.LocalStateValue(stack_type=pt.TealType.uint64, default=pt.Int(5))
    user_vote_power = bk.LocalStateValue(stack_type=pt.TealType.uint64, default=pt.Int(1))


app = bk.Application("AlgoCitizens", state=AlgoState()) \
    .apply(bk.unconditional_create_approval, initialize_global_state=True) \
    .apply(bk.unconditional_opt_in_approval, initialize_local_state=True)


# @app.external(authorize=bk.Authorize.holds_token(asset_id=Asset_ID))
@app.external
# @app.external(authorize=bk.Authorize.holds_token(asset_id=Asset_ID))
def add_proposal(id: pt.abi.String, name: pt.abi.String, author: pt.abi.String, description: pt.abi.String, *, output: Proposal) -> pt.Expr:
    authorAddress = pt.abi.Address()
    isVotingActive = pt.abi.Bool()
    yesVotes = pt.abi.Uint64()
    noVotes = pt.abi.Uint64()
    proposal = Proposal()

    return pt.Seq(
        pt.Assert(pt.Not(app.state.proposals[id.get()].exists())),
        app.state.proposal_counter.increment(),
        authorAddress.set(pt.Txn.sender()),
        isVotingActive.set(False),
        yesVotes.set(0),
        noVotes.set(0),
        proposal.set(id, name, author, authorAddress, description, isVotingActive, yesVotes, noVotes),
        app.state.proposals[id.get()].set(proposal),
        app.state.proposals[id.get()].store_into(output)
    )

@app.external(read_only=True)
def read_proposal(id: pt.abi.String, *, output: Proposal) -> pt.Expr:
    return app.state.proposals[id.get()].store_into(output)

@app.external
def hello(name: pt.abi.String, *, output: pt.abi.String) -> pt.Expr:
    return output.set(pt.Concat(pt.Bytes("Hello, "), name.get()))
