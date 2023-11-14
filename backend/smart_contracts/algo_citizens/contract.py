import beaker as bk
import pyteal as pt
from beaker.lib import storage
import typing

# Asset_ID=pt.Int(1027)
MAX_VOTES = 10

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
    entrusted_vote_power: pt.abi.Field[pt.abi.Uint64]
    

class Vote(pt.abi.NamedTuple):
    votePower: pt.abi.Field[pt.abi.Uint64]
    
    
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
def register() -> pt.Expr:
    user = User()
    address = pt.abi.Address()
    vote_count = pt.abi.Uint64()
    vote_power = pt.abi.Uint64()
    delegate = pt.abi.Address()
    delegated_vote_power = pt.abi.Uint64()

    return pt.Seq(
        address.set(pt.Txn.sender()),
        pt.Assert(app.state.users[address].exists() == pt.Int(0)),
        vote_count.set(pt.Int(MAX_VOTES)),
        vote_power.set(pt.Int(1)),
        delegate.set(pt.Global.zero_address()),
        user.set(vote_count, vote_power, delegate, delegated_vote_power),
        app.state.users[address].set(user)
    )

@app.external
# @app.external(authorize=bk.Authorize.holds_token(asset_id=Asset_ID))
def delegate_vote_right(to_address: pt.abi.Address) -> pt.Expr:
    user = User()
    delegate = User()

    return pt.Seq(
        # both to and from users must be registered already
        (user_address := pt.abi.Address()).set(pt.Txn.sender()),
        pt.Assert(to_address.get() != pt.Global.zero_address()),
        pt.Assert(app.state.users[user_address].exists()),
        pt.Assert(app.state.users[to_address].exists()),

        # fetch user info
        app.state.users[user_address].store_into(user),
        (vote_count := pt.abi.Uint64()).set(user.vote_count),
        (vote_power := pt.abi.Uint64()).set(user.vote_power),
        (delegate_address := pt.abi.Address()).set(user.delegate),
        (entrusted_vote_power := pt.abi.Uint64()).set(user.entrusted_vote_power),

        # user needs to withdraw existing delegation first if any
        pt.Assert(delegate_address.get() == pt.Global.zero_address()),

        # cannot delegate if has already voted
        pt.Assert(vote_count.get() == pt.Int(MAX_VOTES)),
        
        # update user
        delegate_address.set(to_address.get()),
        user.set(vote_count, vote_power, delegate_address, entrusted_vote_power),
        app.state.users[user_address].set(user),

        pt.While(delegate_address.get() != pt.Global.zero_address()).Do(
            # fetch delegate info
            app.state.users[delegate_address].store_into(delegate),
            (delegate_vote_count := pt.abi.Uint64()).set(delegate.vote_count),
            (delegate_vote_power := pt.abi.Uint64()).set(delegate.vote_power),
            delegate_address.set(delegate.delegate),
            (delegate_entrusted_vote_power := pt.abi.Uint64()).set(delegate.entrusted_vote_power),

            # cannot delegate if has already voted
            pt.Assert(delegate_vote_count.get() == pt.Int(MAX_VOTES)),

            # update delegate
            delegate_entrusted_vote_power.set(delegate_entrusted_vote_power.get() + vote_power.get() + entrusted_vote_power.get()),
            delegate.set(delegate_vote_count, delegate_vote_power, delegate_address, delegate_entrusted_vote_power),
            app.state.users[delegate_address].set(delegate),
        ),
    )

@app.external
# @app.external(authorize=bk.Authorize.holds_token(asset_id=Asset_ID))
def withdraw_vote_right() -> pt.Expr:
    user = User()
    delegate = User()

    return pt.Seq(
        # check if from_user is registered
        (user_address := pt.abi.Address()).set(pt.Txn.sender()),
        pt.Assert(app.state.users[user_address].exists()),
        
        # fetch user info
        app.state.users[user_address].store_into(user),
        (vote_count := pt.abi.Uint64()).set(user.vote_count),
        (vote_power := pt.abi.Uint64()).set(user.vote_power),
        (delegate_address := pt.abi.Address()).set(user.delegate),
        (entrusted_vote_power := pt.abi.Uint64()).set(user.entrusted_vote_power),

        # update user
        (zero_address := pt.abi.Address()).set(pt.Global.zero_address()),
        user.set(vote_count, vote_power, zero_address, entrusted_vote_power),
        app.state.users[user_address].set(user),

        pt.While(delegate_address.get() != pt.Global.zero_address()).Do(
            # fetch delegate info
            app.state.users[delegate_address].store_into(delegate),
            (delegate_vote_count := pt.abi.Uint64()).set(delegate.vote_count),
            (delegate_vote_power := pt.abi.Uint64()).set(delegate.vote_power),
            delegate_address.set(delegate.delegate),
            (delegate_entrusted_vote_power := pt.abi.Uint64()).set(delegate.entrusted_vote_power),
            
            # cannot revoke if voting has already started
            pt.Assert(delegate_vote_count.get() == pt.Int(MAX_VOTES)),

            # update delegate
            delegate_entrusted_vote_power.set(delegate_entrusted_vote_power.get() - vote_power.get() - entrusted_vote_power.get()),
            delegate.set(delegate_vote_count, delegate_vote_power, delegate_address, delegate_entrusted_vote_power),
            app.state.users[delegate_address].set(delegate),    
        )
    )

@app.external
# @app.external(authorize=bk.Authorize.holds_token(asset_id=Asset_ID))
def vote(proposalId: pt.abi.Uint64, *, output: Proposal) -> pt.Expr:
    vote = Vote()
    key = pt.abi.String()
    address = pt.abi.Address()
    votePower = pt.abi.Uint64()

    return pt.Seq(
        key.set(pt.Sha256(pt.Concat(pt.Txn.sender(), pt.Itob(proposalId.get())))),
        pt.Assert(pt.Not(app.state.votes[key].exists())),
        address.set(pt.Txn.sender()),
        votePower.set(pt.Int(1)),
        vote.set(votePower),
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
    
@app.external
def empty(*, output: pt.abi.Uint8) -> pt.Expr:
    return output.set(pt.Int(1))
    
@app.external
# @app.external(authorize=bk.Authorize.holds_token(asset_id=Asset_ID))
def get_vote_test(address: pt.abi.Address, proposalId: pt.abi.Uint64, *, output: pt.abi.String) -> pt.Expr:
    data = pt.abi.String()
    return pt.Seq( 
        data.set(pt.Sha256(pt.Concat(address.get(), pt.Itob(proposalId.get())))),
        # output.set(hexlify(data))
        output.set(data)
    )

@pt.Subroutine(pt.TealType.bytes)
def hexlify(data: pt.abi.String) -> pt.Expr:
    result = pt.abi.String()
    i = pt.ScratchVar(pt.TealType.uint64)
    byte = pt.abi.Byte()
    byteAsString = pt.abi.String()
    high = pt.abi.Uint8()
    low = pt.abi.Uint8()

    # pt.Len(data.get())
    return pt.Seq(
        result.set(''),
        pt.For(i.store(pt.Int(0)), i.load() < pt.Len(data.get()), i.store(i.load() + pt.Int(1))).Do(
            pt.Seq(
                byte.set(pt.GetByte(data.get(), i.load())),
                high.set(pt.Div(byte.get(), pt.Int(16))),
                low.set(pt.Mod(byte.get(), pt.Int(16))),
                byteAsString.set(pt.Concat(to_hex(high), to_hex(low))),
                result.set(pt.Concat(result.get(), byteAsString.get()))
            )
        ),
        result.get()
    )

@pt.Subroutine(pt.TealType.bytes)
def to_hex(input: pt.abi.Uint8):
    return pt.Cond(
        [input.get() == pt.Int(15), pt.Bytes('F')],
        [input.get() == pt.Int(14), pt.Bytes('E')],
        [input.get() == pt.Int(13), pt.Bytes('D')],
        [input.get() == pt.Int(12), pt.Bytes('C')],
        [input.get() == pt.Int(11), pt.Bytes('B')],
        [input.get() == pt.Int(10), pt.Bytes('A')],
        [input.get() == pt.Int(9), pt.Bytes('9')],
        [input.get() == pt.Int(8), pt.Bytes('8')],
        [input.get() == pt.Int(7), pt.Bytes('7')],
        [input.get() == pt.Int(6), pt.Bytes('6')],
        [input.get() == pt.Int(5), pt.Bytes('5')],
        [input.get() == pt.Int(4), pt.Bytes('4')],
        [input.get() == pt.Int(3), pt.Bytes('3')],
        [input.get() == pt.Int(2), pt.Bytes('2')],
        [input.get() == pt.Int(1), pt.Bytes('1')],
        [input.get() == pt.Int(0), pt.Bytes('0')],
    )
