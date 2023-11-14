import beaker as bk
import pyteal as pt
from beaker.lib import storage
import typing

# ASSET_ID=pt.Int(xxxx)
# ADMIN_ASSET_ID=pt.Int(zzzz)
MAX_VOTES = pt.Int(10)

class Proposal(pt.abi.NamedTuple):
    id: pt.abi.Field[pt.abi.Uint64]
    name: pt.abi.Field[pt.abi.String]
    author: pt.abi.Field[pt.abi.String]
    author_address: pt.abi.Field[pt.abi.Address]
    description: pt.abi.Field[pt.abi.String]
    total_vote_power: pt.abi.Field[pt.abi.Uint64]
    is_archived: pt.abi.Field[pt.abi.Bool]


class User(pt.abi.NamedTuple):
    vote_count: pt.abi.Field[pt.abi.Uint64]
    vote_power: pt.abi.Field[pt.abi.Uint64]
    delegate: pt.abi.Field[pt.abi.Address]
    entrusted_vote_power: pt.abi.Field[pt.abi.Uint64]
    

class Vote(pt.abi.NamedTuple):
    vote_power: pt.abi.Field[pt.abi.Uint64]
    
    
class AlgoState:
    active_proposal_count = bk.GlobalStateValue(stack_type=pt.TealType.uint64, default=pt.Int(0))
    total_proposal_count = bk.GlobalStateValue(stack_type=pt.TealType.uint64, default=pt.Int(0))
    proposals = storage.BoxMapping(pt.abi.Uint64, Proposal)

    user_count = bk.GlobalStateValue(stack_type=pt.TealType.uint64, default=pt.Int(0))
    users = storage.BoxMapping(pt.abi.Address, User)
    
    is_voting_open = bk.GlobalStateValue(stack_type=pt.TealType.uint64, default=pt.Int(0))
    votes = storage.BoxMapping(pt.abi.String, Vote)


app = bk.Application("AlgoCitizens", state=AlgoState()) \
    .apply(bk.unconditional_create_approval, initialize_global_state=True)


@app.external
# @app.external(authorize=bk.Authorize.holds_token(asset_id=ASSET_ID))
def add_proposal(id: pt.abi.Uint64, name: pt.abi.String, author: pt.abi.String, description: pt.abi.String, *, output: Proposal) -> pt.Expr:
    proposal = Proposal()

    return pt.Seq(
        pt.Assert(app.state.proposals[id].exists() == pt.Int(0)),
        app.state.active_proposal_count.increment(),
        app.state.total_proposal_count.increment(),

        (author_address := pt.abi.Address()).set(pt.Txn.sender()),
        (total_vote_power := pt.abi.Uint64()).set(pt.Int(0)),
        (is_archived := pt.abi.Bool()).set(False),

        proposal.set(id, name, author, author_address, description, total_vote_power, is_archived),
        app.state.proposals[id].set(proposal),
        app.state.proposals[id].store_into(output)
    )

@app.external
# @app.external(authorize=bk.Authorize.holds_token(asset_id=ADMIN_ASSET_ID))
def archive_proposal(id: pt.abi.Uint64) -> pt.Expr:
    proposal = Proposal()

    return pt.Seq(
        pt.Assert(app.state.proposals[id].exists()),
        app.state.active_proposal_count.decrement(),
        app.state.proposals[id].store_into(proposal),

        (name := pt.abi.String()).set(proposal.name),
        (author := pt.abi.String()).set(proposal.author),
        (author_address := pt.abi.Address()).set(proposal.author_address),
        (description := pt.abi.String()).set(proposal.description),
        (total_vote_power := pt.abi.Uint64()).set(proposal.total_vote_power),
        (is_archived := pt.abi.Bool()).set(True),

        proposal.set(id, name, author, author_address, description, total_vote_power, is_archived),
        app.state.proposals[id].set(proposal),
    )


@app.external(read_only=True)
def read_proposal(id: pt.abi.Uint64, *, output: Proposal) -> pt.Expr:
    return app.state.proposals[id].store_into(output)

@app.external
# @app.external(authorize=bk.Authorize.holds_token(asset_id=ASSET_ID))
def register() -> pt.Expr:
    user = User()

    return pt.Seq(
        # check user is not yet registered
        (address := pt.abi.Address()).set(pt.Txn.sender()),
        pt.Assert(app.state.users[address].exists() == pt.Int(0)),
        app.state.user_count.increment(),

        # set defaults
        (vote_count := pt.abi.Uint64()).set(MAX_VOTES),
        (vote_power := pt.abi.Uint64()).set(pt.Int(1)),
        (delegate_address := pt.abi.Address()).set(pt.Global.zero_address()),
        (entrusted_vote_power := pt.abi.Uint64()).set(pt.Int(0)),

        # store user info
        user.set(vote_count, vote_power, delegate_address, entrusted_vote_power),
        app.state.users[address].set(user)
    )

@app.external
# @app.external(authorize=bk.Authorize.holds_token(asset_id=ASSET_ID))
def delegate_voting_right(to_address: pt.abi.Address) -> pt.Expr:
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
        pt.Assert(vote_count.get() == MAX_VOTES),
        
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
            pt.Assert(delegate_vote_count.get() == MAX_VOTES),

            # update delegate
            delegate_entrusted_vote_power.set(delegate_entrusted_vote_power.get() + vote_power.get() + entrusted_vote_power.get()),
            delegate.set(delegate_vote_count, delegate_vote_power, delegate_address, delegate_entrusted_vote_power),
            app.state.users[delegate_address].set(delegate),
        ),
    )

@app.external
# @app.external(authorize=bk.Authorize.holds_token(asset_id=ASSET_ID))
def withdraw_voting_right() -> pt.Expr:
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
            
            # cannot revoke if has already voted
            pt.Assert(delegate_vote_count.get() == MAX_VOTES),

            # update delegate
            delegate_entrusted_vote_power.set(delegate_entrusted_vote_power.get() - vote_power.get() - entrusted_vote_power.get()),
            delegate.set(delegate_vote_count, delegate_vote_power, delegate_address, delegate_entrusted_vote_power),
            app.state.users[delegate_address].set(delegate),    
        )
    )

@app.external
# @app.external(authorize=bk.Authorize.holds_token(asset_id=ADMIN_ASSET_ID))
def open_voting() -> pt.Expr:
    return pt.Seq(
        pt.Assert(pt.Not(app.state.is_voting_open)),
        app.state.is_voting_open.set(pt.Int(1))
    )

@app.external
# @app.external(authorize=bk.Authorize.holds_token(asset_id=ADMIN_ASSET_ID))
def close_voting() -> pt.Expr:
    return pt.Seq(
        pt.Assert(app.state.is_voting_open),
        app.state.is_voting_open.set(pt.Int(0))
    )

@app.external
# @app.external(authorize=bk.Authorize.holds_token(asset_id=ASSET_ID))
def vote(proposalId: pt.abi.Uint64, *, output: Proposal) -> pt.Expr:
    user = User()
    vote = Vote()
    proposal = Proposal()
    vote_key = pt.abi.String()

    return pt.Seq(
        # check if voting is open
        pt.Assert(app.state.is_voting_open),

        # fetch user info
        (address := pt.abi.Address()).set(pt.Txn.sender()),
        app.state.users[address].store_into(user),

        (vote_count := pt.abi.Uint64()).set(user.vote_count),
        (vote_power := pt.abi.Uint64()).set(user.vote_power),
        (delegate_address := pt.abi.Address()).set(user.delegate),
        (entrusted_vote_power := pt.abi.Uint64()).set(user.entrusted_vote_power),
        
        # check if user has not delegated his voting right
        pt.Assert(delegate_address.get() == pt.Global.zero_address()),

        # check if user has remaining votes
        pt.Assert(vote_count.get() > pt.Int(0)),
        
        # check if not voted before for this proposal
        vote_key.set(pt.Sha256(pt.Concat(pt.Txn.sender(), pt.Itob(proposalId.get())))),
        pt.Assert(app.state.votes[vote_key].exists() == pt.Int(0)),

        # check if proposal exists and not archived, fetch its info
        pt.Assert(app.state.proposals[proposalId].exists()),
        app.state.proposals[proposalId].store_into(proposal),

        (name := pt.abi.String()).set(proposal.name),
        (author := pt.abi.String()).set(proposal.author),
        (author_address := pt.abi.Address()).set(proposal.author_address),
        (description := pt.abi.String()).set(proposal.description),
        (total_vote_power := pt.abi.Uint64()).set(proposal.total_vote_power),
        (is_archived := pt.abi.Bool()).set(True),

        pt.Assert(pt.Not(is_archived.get())),
        
        # update proposal
        total_vote_power.set(total_vote_power.get() + vote_power.get() + entrusted_vote_power.get()),
        proposal.set(proposalId, name, author, author_address, description, total_vote_power, is_archived),
        app.state.proposals[proposalId].set(proposal),

        # update user
        vote_count.set(vote_count.get() - pt.Int(1)),
        user.set(vote_count, vote_power, delegate_address, entrusted_vote_power),
        app.state.users[address].set(user),

        # update vote
        (power := pt.abi.Uint64()).set(vote_power.get() + entrusted_vote_power.get()),
        vote.set(power),
        app.state.votes[vote_key].set(vote),
        app.state.votes[vote_key].store_into(output)
    )


@app.external(read_only=True)
def get_vote(address: pt.abi.Address, proposalId: pt.abi.Uint64, *, output: Proposal) -> pt.Expr:
    key = pt.abi.String()

    return pt.Seq(
        key.set(pt.Sha256(pt.Concat(pt.Txn.sender(), pt.Itob(proposalId.get())))),
        pt.Assert(app.state.votes[key].exists()),
        app.state.votes[key].store_into(output)
    )
    
@app.external(read_only=True)
def empty(*, output: pt.abi.Uint8) -> pt.Expr:
    return output.set(pt.Int(1))
    
@app.external(read_only=True)
def get_vote_box_key(address: pt.abi.Address, proposalId: pt.abi.Uint64, *, output: pt.abi.String) -> pt.Expr:
    key = pt.abi.String()
    return pt.Seq( 
        key.set(pt.Sha256(pt.Concat(address.get(), pt.Itob(proposalId.get())))),
        # output.set(hexlify(data))
        output.set(key)
    )

@pt.Subroutine(pt.TealType.bytes)
def hexlify(data: pt.abi.String) -> pt.Expr:
    result = pt.abi.String()
    i = pt.ScratchVar(pt.TealType.uint64)
    byte = pt.abi.Byte()
    byte_as_string = pt.abi.String()
    high_nibble = pt.abi.Uint8()
    low_nibble = pt.abi.Uint8()

    return pt.Seq(
        result.set(''),
        pt.For(i.store(pt.Int(0)), i.load() < pt.Len(data.get()), i.store(i.load() + pt.Int(1))).Do(
            byte.set(pt.GetByte(data.get(), i.load())),
            high_nibble.set(pt.Div(byte.get(), pt.Int(16))),
            low_nibble.set(pt.Mod(byte.get(), pt.Int(16))),
            byte_as_string.set(pt.Concat(to_hex(high_nibble), to_hex(low_nibble))),
            result.set(pt.Concat(result.get(), byte_as_string.get()))
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
