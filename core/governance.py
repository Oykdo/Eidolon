"""
Governance System pour Poly-Spinor Nexus 7D
DAO, Token de Gouvernance, et Incentives Validateurs

Features:
- DAO pour evolution du protocole
- Token de gouvernance PSNX
- Propositions et votes on-chain
- Staking et delegation
- Incentives pour validateurs/noeuds P2P
- Treasury management
"""

import os
import json
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from decimal import Decimal


# ============================================================================
# ENUMERATIONS
# ============================================================================

class ProposalType(Enum):
    """Types de propositions"""
    PARAMETER_CHANGE = "parameter_change"
    UPGRADE = "upgrade"
    TREASURY_SPEND = "treasury_spend"
    EMERGENCY = "emergency"
    GRANT = "grant"
    TEXT = "text"  # Signal proposal


class ProposalStatus(Enum):
    """Statut des propositions"""
    DRAFT = "draft"
    PENDING = "pending"
    ACTIVE = "active"
    PASSED = "passed"
    REJECTED = "rejected"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class VoteType(Enum):
    """Types de votes"""
    FOR = "for"
    AGAINST = "against"
    ABSTAIN = "abstain"


class StakeStatus(Enum):
    """Statut du staking"""
    ACTIVE = "active"
    UNBONDING = "unbonding"
    WITHDRAWN = "withdrawn"


class ValidatorStatus(Enum):
    """Statut des validateurs"""
    ACTIVE = "active"
    JAILED = "jailed"
    INACTIVE = "inactive"


# ============================================================================
# GOVERNANCE PARAMETERS
# ============================================================================

@dataclass
class GovernanceParams:
    """Parametres de gouvernance"""
    # Voting
    voting_period_days: int = 7
    quorum_percentage: Decimal = Decimal("10.0")  # 10% of total supply
    pass_threshold: Decimal = Decimal("50.0")     # 50% + 1 to pass
    veto_threshold: Decimal = Decimal("33.33")    # 33.33% to veto
    
    # Proposals
    min_deposit: int = 1000  # PSNX tokens
    max_deposit_period_days: int = 14
    
    # Staking
    unbonding_period_days: int = 21
    min_stake: int = 100
    max_validators: int = 100
    
    # Rewards
    block_reward: int = 10  # PSNX per block
    validator_commission_max: Decimal = Decimal("20.0")  # Max 20%
    
    # Treasury
    community_tax: Decimal = Decimal("2.0")  # 2% of rewards


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class PSNXToken:
    """Token de gouvernance PSNX"""
    total_supply: int = 1_000_000_000  # 1 billion
    circulating_supply: int = 0
    staked_supply: int = 0
    treasury_balance: int = 0
    
    # Distribution
    initial_distribution: Dict[str, int] = field(default_factory=lambda: {
        "community": 400_000_000,      # 40%
        "team": 150_000_000,           # 15% (vested)
        "treasury": 200_000_000,       # 20%
        "validators": 100_000_000,     # 10%
        "ecosystem": 150_000_000       # 15%
    })
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TokenHolder:
    """Detenteur de tokens"""
    address: str
    balance: int
    staked: int = 0
    delegated: int = 0
    
    # Vesting
    vesting_amount: int = 0
    vesting_end: Optional[str] = None
    
    # Voting power
    voting_power: int = 0
    
    def update_voting_power(self):
        """Met a jour le pouvoir de vote"""
        self.voting_power = self.balance + self.staked
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Proposal:
    """Proposition de gouvernance"""
    proposal_id: str
    proposer: str
    proposal_type: ProposalType
    title: str
    description: str
    created_at: str
    
    # Deposit
    deposit: int = 0
    deposit_end: str = ""
    
    # Voting
    voting_start: Optional[str] = None
    voting_end: Optional[str] = None
    
    # Votes
    votes_for: int = 0
    votes_against: int = 0
    votes_abstain: int = 0
    voters: List[str] = field(default_factory=list)
    
    # Status
    status: ProposalStatus = ProposalStatus.DRAFT
    
    # Execution
    execution_payload: Dict[str, Any] = field(default_factory=dict)
    executed_at: Optional[str] = None
    execution_result: Optional[str] = None
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['proposal_type'] = self.proposal_type.value
        d['status'] = self.status.value
        return d
    
    @property
    def total_votes(self) -> int:
        return self.votes_for + self.votes_against + self.votes_abstain
    
    def get_result(self, total_supply: int, params: GovernanceParams) -> Tuple[bool, str]:
        """Determine le resultat du vote"""
        if self.total_votes == 0:
            return False, "No votes"
        
        # Check quorum
        quorum = int(total_supply * params.quorum_percentage / 100)
        if self.total_votes < quorum:
            return False, f"Quorum not met ({self.total_votes}/{quorum})"
        
        # Check veto
        veto_threshold = int(self.total_votes * params.veto_threshold / 100)
        if self.votes_against >= veto_threshold:
            return False, f"Vetoed ({self.votes_against} against)"
        
        # Check pass threshold
        pass_threshold = int(self.total_votes * params.pass_threshold / 100)
        if self.votes_for > pass_threshold:
            return True, f"Passed ({self.votes_for} for)"
        
        return False, f"Not enough support ({self.votes_for}/{pass_threshold})"


@dataclass
class Vote:
    """Vote sur une proposition"""
    vote_id: str
    proposal_id: str
    voter: str
    vote_type: VoteType
    voting_power: int
    timestamp: str
    
    # Optional
    justification: str = ""
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['vote_type'] = self.vote_type.value
        return d


@dataclass
class Stake:
    """Stake de tokens"""
    stake_id: str
    staker: str
    validator: str
    amount: int
    created_at: str
    
    # Status
    status: StakeStatus = StakeStatus.ACTIVE
    
    # Unbonding
    unbonding_at: Optional[str] = None
    unbonding_complete: Optional[str] = None
    
    # Rewards
    pending_rewards: int = 0
    claimed_rewards: int = 0
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['status'] = self.status.value
        return d


@dataclass
class Validator:
    """Validateur du reseau"""
    validator_id: str
    address: str
    name: str
    description: str
    website: str = ""
    
    # Staking
    self_stake: int = 0
    delegated_stake: int = 0
    commission_rate: Decimal = Decimal("10.0")  # 10%
    
    # Status
    status: ValidatorStatus = ValidatorStatus.ACTIVE
    jailed_until: Optional[str] = None
    
    # Performance
    blocks_produced: int = 0
    blocks_missed: int = 0
    uptime: Decimal = Decimal("100.0")
    
    # Rewards
    total_rewards: int = 0
    commission_earned: int = 0
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['status'] = self.status.value
        d['commission_rate'] = str(self.commission_rate)
        d['uptime'] = str(self.uptime)
        return d
    
    @property
    def total_stake(self) -> int:
        return self.self_stake + self.delegated_stake


@dataclass
class Reward:
    """Recompense distribuee"""
    reward_id: str
    recipient: str
    amount: int
    reward_type: str  # staking, validation, grant
    timestamp: str
    
    # Source
    source: str = ""  # block, treasury, etc.
    
    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================================
# DAO GOVERNANCE
# ============================================================================

class DAOGovernance:
    """Systeme de gouvernance DAO"""
    
    def __init__(self, data_dir: str = "./governance_data"):
        self.data_dir = data_dir
        self.proposals_dir = f"{data_dir}/proposals"
        self.votes_dir = f"{data_dir}/votes"
        self.holders_dir = f"{data_dir}/holders"
        
        for d in [self.proposals_dir, self.votes_dir, self.holders_dir]:
            os.makedirs(d, exist_ok=True)
        
        self.params = GovernanceParams()
        self.token = PSNXToken()
        
        # Cache
        self._holders: Dict[str, TokenHolder] = {}
        self._proposals: Dict[str, Proposal] = {}
    
    # === TOKEN MANAGEMENT ===
    
    def get_holder(self, address: str) -> TokenHolder:
        """Recupere ou cree un holder"""
        if address in self._holders:
            return self._holders[address]
        
        path = f"{self.holders_dir}/{address}.json"
        
        if os.path.exists(path):
            with open(path, 'r') as f:
                d = json.load(f)
                holder = TokenHolder(**d)
                self._holders[address] = holder
                return holder
        
        holder = TokenHolder(address=address, balance=0)
        self._save_holder(holder)
        return holder
    
    def _save_holder(self, holder: TokenHolder):
        """Sauvegarde un holder"""
        holder.update_voting_power()
        self._holders[holder.address] = holder
        
        with open(f"{self.holders_dir}/{holder.address}.json", 'w') as f:
            json.dump(holder.to_dict(), f, indent=2)
    
    def transfer_tokens(self, from_addr: str, to_addr: str, amount: int) -> bool:
        """Transfere des tokens"""
        sender = self.get_holder(from_addr)
        
        if sender.balance < amount:
            return False
        
        receiver = self.get_holder(to_addr)
        
        sender.balance -= amount
        receiver.balance += amount
        
        self._save_holder(sender)
        self._save_holder(receiver)
        
        return True
    
    def mint_tokens(self, to_addr: str, amount: int, reason: str = "") -> bool:
        """Mint de nouveaux tokens"""
        if self.token.circulating_supply + amount > self.token.total_supply:
            return False
        
        holder = self.get_holder(to_addr)
        holder.balance += amount
        self.token.circulating_supply += amount
        
        self._save_holder(holder)
        
        return True
    
    # === PROPOSALS ===
    
    def create_proposal(self, proposer: str, proposal_type: ProposalType,
                       title: str, description: str,
                       execution_payload: Dict = None) -> Proposal:
        """Cree une nouvelle proposition"""
        proposal_id = secrets.token_hex(16)
        now = datetime.now()
        
        proposal = Proposal(
            proposal_id=proposal_id,
            proposer=proposer,
            proposal_type=proposal_type,
            title=title,
            description=description,
            created_at=now.isoformat(),
            deposit_end=(now + timedelta(days=self.params.max_deposit_period_days)).isoformat(),
            execution_payload=execution_payload or {}
        )
        
        self._save_proposal(proposal)
        return proposal
    
    def deposit_to_proposal(self, proposal_id: str, depositor: str, amount: int) -> bool:
        """Ajoute un depot a une proposition"""
        proposal = self.get_proposal(proposal_id)
        holder = self.get_holder(depositor)
        
        if not proposal or proposal.status != ProposalStatus.DRAFT:
            return False
        
        if holder.balance < amount:
            return False
        
        # Transfer tokens to proposal
        holder.balance -= amount
        proposal.deposit += amount
        
        # Check if deposit threshold met
        if proposal.deposit >= self.params.min_deposit:
            proposal.status = ProposalStatus.PENDING
        
        self._save_holder(holder)
        self._save_proposal(proposal)
        
        return True
    
    def start_voting(self, proposal_id: str) -> bool:
        """Demarre la periode de vote"""
        proposal = self.get_proposal(proposal_id)
        
        if not proposal or proposal.status != ProposalStatus.PENDING:
            return False
        
        now = datetime.now()
        proposal.status = ProposalStatus.ACTIVE
        proposal.voting_start = now.isoformat()
        proposal.voting_end = (now + timedelta(days=self.params.voting_period_days)).isoformat()
        
        self._save_proposal(proposal)
        return True
    
    def vote(self, proposal_id: str, voter: str, vote_type: VoteType,
            justification: str = "") -> Optional[Vote]:
        """Vote sur une proposition"""
        proposal = self.get_proposal(proposal_id)
        holder = self.get_holder(voter)
        
        if not proposal or proposal.status != ProposalStatus.ACTIVE:
            return None
        
        if voter in proposal.voters:
            return None  # Already voted
        
        if holder.voting_power == 0:
            return None
        
        # Create vote
        vote_id = secrets.token_hex(16)
        vote = Vote(
            vote_id=vote_id,
            proposal_id=proposal_id,
            voter=voter,
            vote_type=vote_type,
            voting_power=holder.voting_power,
            timestamp=datetime.now().isoformat(),
            justification=justification
        )
        
        # Update proposal
        if vote_type == VoteType.FOR:
            proposal.votes_for += holder.voting_power
        elif vote_type == VoteType.AGAINST:
            proposal.votes_against += holder.voting_power
        else:
            proposal.votes_abstain += holder.voting_power
        
        proposal.voters.append(voter)
        
        self._save_vote(vote)
        self._save_proposal(proposal)
        
        return vote
    
    def finalize_proposal(self, proposal_id: str) -> Tuple[bool, str]:
        """Finalise une proposition apres la periode de vote"""
        proposal = self.get_proposal(proposal_id)
        
        if not proposal or proposal.status != ProposalStatus.ACTIVE:
            return False, "Invalid proposal status"
        
        now = datetime.now()
        voting_end = datetime.fromisoformat(proposal.voting_end)
        
        if now < voting_end:
            return False, "Voting period not ended"
        
        # Calculate result
        passed, reason = proposal.get_result(self.token.circulating_supply, self.params)
        
        if passed:
            proposal.status = ProposalStatus.PASSED
        else:
            proposal.status = ProposalStatus.REJECTED
        
        self._save_proposal(proposal)
        
        return passed, reason
    
    def execute_proposal(self, proposal_id: str) -> Tuple[bool, str]:
        """Execute une proposition passee"""
        proposal = self.get_proposal(proposal_id)
        
        if not proposal or proposal.status != ProposalStatus.PASSED:
            return False, "Proposal not passed"
        
        try:
            # Execute based on type
            if proposal.proposal_type == ProposalType.PARAMETER_CHANGE:
                self._execute_parameter_change(proposal.execution_payload)
            elif proposal.proposal_type == ProposalType.TREASURY_SPEND:
                self._execute_treasury_spend(proposal.execution_payload)
            
            proposal.status = ProposalStatus.EXECUTED
            proposal.executed_at = datetime.now().isoformat()
            proposal.execution_result = "Success"
            
            self._save_proposal(proposal)
            return True, "Executed successfully"
        
        except Exception as e:
            proposal.execution_result = f"Failed: {e}"
            self._save_proposal(proposal)
            return False, str(e)
    
    def _execute_parameter_change(self, payload: Dict):
        """Execute un changement de parametre"""
        for param, value in payload.items():
            if hasattr(self.params, param):
                setattr(self.params, param, value)
    
    def _execute_treasury_spend(self, payload: Dict):
        """Execute une depense de tresorerie"""
        recipient = payload.get('recipient')
        amount = payload.get('amount', 0)
        
        if self.token.treasury_balance >= amount:
            self.token.treasury_balance -= amount
            self.mint_tokens(recipient, amount, "Treasury spend")
    
    def get_proposal(self, proposal_id: str) -> Optional[Proposal]:
        """Recupere une proposition"""
        if proposal_id in self._proposals:
            return self._proposals[proposal_id]
        
        path = f"{self.proposals_dir}/{proposal_id}.json"
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'r') as f:
            d = json.load(f)
            d['proposal_type'] = ProposalType(d['proposal_type'])
            d['status'] = ProposalStatus(d['status'])
            proposal = Proposal(**d)
            self._proposals[proposal_id] = proposal
            return proposal
    
    def _save_proposal(self, proposal: Proposal):
        """Sauvegarde une proposition"""
        self._proposals[proposal.proposal_id] = proposal
        
        with open(f"{self.proposals_dir}/{proposal.proposal_id}.json", 'w') as f:
            json.dump(proposal.to_dict(), f, indent=2)
    
    def _save_vote(self, vote: Vote):
        """Sauvegarde un vote"""
        with open(f"{self.votes_dir}/{vote.vote_id}.json", 'w') as f:
            json.dump(vote.to_dict(), f, indent=2)
    
    def list_proposals(self, status: ProposalStatus = None) -> List[Proposal]:
        """Liste les propositions"""
        proposals = []
        
        for filename in os.listdir(self.proposals_dir):
            if filename.endswith('.json'):
                proposal = self.get_proposal(filename[:-5])
                if proposal and (status is None or proposal.status == status):
                    proposals.append(proposal)
        
        return sorted(proposals, key=lambda p: p.created_at, reverse=True)


# ============================================================================
# STAKING SYSTEM
# ============================================================================

class StakingSystem:
    """Systeme de staking"""
    
    def __init__(self, dao: DAOGovernance, data_dir: str = "./governance_data"):
        self.dao = dao
        self.data_dir = data_dir
        self.stakes_dir = f"{data_dir}/stakes"
        self.validators_dir = f"{data_dir}/validators"
        
        for d in [self.stakes_dir, self.validators_dir]:
            os.makedirs(d, exist_ok=True)
        
        # Cache
        self._validators: Dict[str, Validator] = {}
        self._stakes: Dict[str, Stake] = {}
    
    # === VALIDATORS ===
    
    def register_validator(self, address: str, name: str, description: str,
                          self_stake: int, commission_rate: Decimal) -> Optional[Validator]:
        """Enregistre un nouveau validateur"""
        holder = self.dao.get_holder(address)
        
        if holder.balance < self_stake:
            return None
        
        if commission_rate > self.dao.params.validator_commission_max:
            return None
        
        validator_id = hashlib.sha256(address.encode()).hexdigest()[:32]
        
        validator = Validator(
            validator_id=validator_id,
            address=address,
            name=name,
            description=description,
            self_stake=self_stake,
            commission_rate=commission_rate
        )
        
        # Lock self-stake
        holder.balance -= self_stake
        holder.staked += self_stake
        self.dao._save_holder(holder)
        
        self._save_validator(validator)
        
        return validator
    
    def get_validator(self, validator_id: str) -> Optional[Validator]:
        """Recupere un validateur"""
        if validator_id in self._validators:
            return self._validators[validator_id]
        
        path = f"{self.validators_dir}/{validator_id}.json"
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'r') as f:
            d = json.load(f)
            d['status'] = ValidatorStatus(d['status'])
            d['commission_rate'] = Decimal(d['commission_rate'])
            d['uptime'] = Decimal(d['uptime'])
            validator = Validator(**d)
            self._validators[validator_id] = validator
            return validator
    
    def _save_validator(self, validator: Validator):
        """Sauvegarde un validateur"""
        self._validators[validator.validator_id] = validator
        
        with open(f"{self.validators_dir}/{validator.validator_id}.json", 'w') as f:
            json.dump(validator.to_dict(), f, indent=2)
    
    def list_validators(self, active_only: bool = True) -> List[Validator]:
        """Liste les validateurs"""
        validators = []
        
        for filename in os.listdir(self.validators_dir):
            if filename.endswith('.json'):
                validator = self.get_validator(filename[:-5])
                if validator:
                    if not active_only or validator.status == ValidatorStatus.ACTIVE:
                        validators.append(validator)
        
        return sorted(validators, key=lambda v: v.total_stake, reverse=True)
    
    # === STAKING ===
    
    def stake(self, staker: str, validator_id: str, amount: int) -> Optional[Stake]:
        """Stake des tokens aupres d'un validateur"""
        holder = self.dao.get_holder(staker)
        validator = self.get_validator(validator_id)
        
        if not validator or validator.status != ValidatorStatus.ACTIVE:
            return None
        
        if holder.balance < amount:
            return None
        
        if amount < self.dao.params.min_stake:
            return None
        
        stake_id = secrets.token_hex(16)
        
        stake = Stake(
            stake_id=stake_id,
            staker=staker,
            validator=validator_id,
            amount=amount,
            created_at=datetime.now().isoformat()
        )
        
        # Update balances
        holder.balance -= amount
        holder.staked += amount
        validator.delegated_stake += amount
        
        self.dao._save_holder(holder)
        self._save_validator(validator)
        self._save_stake(stake)
        
        # Update token stats
        self.dao.token.staked_supply += amount
        
        return stake
    
    def unstake(self, stake_id: str) -> bool:
        """Demarre le unbonding d'un stake"""
        stake = self.get_stake(stake_id)
        
        if not stake or stake.status != StakeStatus.ACTIVE:
            return False
        
        now = datetime.now()
        stake.status = StakeStatus.UNBONDING
        stake.unbonding_at = now.isoformat()
        stake.unbonding_complete = (
            now + timedelta(days=self.dao.params.unbonding_period_days)
        ).isoformat()
        
        self._save_stake(stake)
        
        return True
    
    def withdraw(self, stake_id: str) -> bool:
        """Retire un stake apres unbonding"""
        stake = self.get_stake(stake_id)
        
        if not stake or stake.status != StakeStatus.UNBONDING:
            return False
        
        if datetime.now() < datetime.fromisoformat(stake.unbonding_complete):
            return False
        
        holder = self.dao.get_holder(stake.staker)
        validator = self.get_validator(stake.validator)
        
        # Return tokens + rewards
        total_return = stake.amount + stake.pending_rewards
        holder.balance += total_return
        holder.staked -= stake.amount
        
        if validator:
            validator.delegated_stake -= stake.amount
            self._save_validator(validator)
        
        stake.status = StakeStatus.WITHDRAWN
        
        self.dao._save_holder(holder)
        self._save_stake(stake)
        
        # Update token stats
        self.dao.token.staked_supply -= stake.amount
        
        return True
    
    def claim_rewards(self, stake_id: str) -> int:
        """Reclame les recompenses d'un stake"""
        stake = self.get_stake(stake_id)
        
        if not stake or stake.pending_rewards == 0:
            return 0
        
        holder = self.dao.get_holder(stake.staker)
        rewards = stake.pending_rewards
        
        holder.balance += rewards
        stake.claimed_rewards += rewards
        stake.pending_rewards = 0
        
        self.dao._save_holder(holder)
        self._save_stake(stake)
        
        return rewards
    
    def distribute_rewards(self, total_rewards: int):
        """Distribue les recompenses aux stakers"""
        validators = self.list_validators(active_only=True)
        
        if not validators:
            return
        
        total_stake = sum(v.total_stake for v in validators)
        
        if total_stake == 0:
            return
        
        # Community tax
        tax = int(total_rewards * self.dao.params.community_tax / 100)
        self.dao.token.treasury_balance += tax
        distributable = total_rewards - tax
        
        for validator in validators:
            # Validator share
            validator_share = int(distributable * validator.total_stake / total_stake)
            
            # Commission
            commission = int(validator_share * validator.commission_rate / 100)
            validator.commission_earned += commission
            validator.total_rewards += commission
            
            # Staker rewards
            staker_rewards = validator_share - commission
            
            # Distribute to stakers
            stakes = self.get_stakes_for_validator(validator.validator_id)
            for stake in stakes:
                if stake.status == StakeStatus.ACTIVE:
                    stake_share = int(staker_rewards * stake.amount / validator.total_stake)
                    stake.pending_rewards += stake_share
                    self._save_stake(stake)
            
            self._save_validator(validator)
    
    def get_stake(self, stake_id: str) -> Optional[Stake]:
        """Recupere un stake"""
        if stake_id in self._stakes:
            return self._stakes[stake_id]
        
        path = f"{self.stakes_dir}/{stake_id}.json"
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'r') as f:
            d = json.load(f)
            d['status'] = StakeStatus(d['status'])
            stake = Stake(**d)
            self._stakes[stake_id] = stake
            return stake
    
    def _save_stake(self, stake: Stake):
        """Sauvegarde un stake"""
        self._stakes[stake.stake_id] = stake
        
        with open(f"{self.stakes_dir}/{stake.stake_id}.json", 'w') as f:
            json.dump(stake.to_dict(), f, indent=2)
    
    def get_stakes_for_validator(self, validator_id: str) -> List[Stake]:
        """Recupere tous les stakes pour un validateur"""
        stakes = []
        
        for filename in os.listdir(self.stakes_dir):
            if filename.endswith('.json'):
                stake = self.get_stake(filename[:-5])
                if stake and stake.validator == validator_id:
                    stakes.append(stake)
        
        return stakes
    
    def get_stakes_for_staker(self, staker: str) -> List[Stake]:
        """Recupere tous les stakes d'un staker"""
        stakes = []
        
        for filename in os.listdir(self.stakes_dir):
            if filename.endswith('.json'):
                stake = self.get_stake(filename[:-5])
                if stake and stake.staker == staker:
                    stakes.append(stake)
        
        return stakes


# ============================================================================
# VALIDATOR INCENTIVES
# ============================================================================

class ValidatorIncentives:
    """Systeme d'incentives pour validateurs"""
    
    def __init__(self, staking: StakingSystem):
        self.staking = staking
    
    def record_block_production(self, validator_id: str):
        """Enregistre la production d'un bloc"""
        validator = self.staking.get_validator(validator_id)
        
        if validator:
            validator.blocks_produced += 1
            self._update_uptime(validator)
            self.staking._save_validator(validator)
    
    def record_block_miss(self, validator_id: str):
        """Enregistre un bloc manque"""
        validator = self.staking.get_validator(validator_id)
        
        if validator:
            validator.blocks_missed += 1
            self._update_uptime(validator)
            
            # Check for jailing
            if validator.uptime < Decimal("95.0"):
                self.jail_validator(validator_id, hours=24)
            
            self.staking._save_validator(validator)
    
    def _update_uptime(self, validator: Validator):
        """Met a jour l'uptime"""
        total = validator.blocks_produced + validator.blocks_missed
        if total > 0:
            validator.uptime = Decimal(validator.blocks_produced * 100 / total)
    
    def jail_validator(self, validator_id: str, hours: int = 24):
        """Jail un validateur"""
        validator = self.staking.get_validator(validator_id)
        
        if validator:
            validator.status = ValidatorStatus.JAILED
            validator.jailed_until = (
                datetime.now() + timedelta(hours=hours)
            ).isoformat()
            self.staking._save_validator(validator)
    
    def unjail_validator(self, validator_id: str) -> bool:
        """Unjail un validateur"""
        validator = self.staking.get_validator(validator_id)
        
        if not validator or validator.status != ValidatorStatus.JAILED:
            return False
        
        if validator.jailed_until:
            if datetime.now() < datetime.fromisoformat(validator.jailed_until):
                return False
        
        validator.status = ValidatorStatus.ACTIVE
        validator.jailed_until = None
        self.staking._save_validator(validator)
        
        return True
    
    def calculate_apr(self, validator_id: str) -> Decimal:
        """Calcule l'APR estime pour un validateur"""
        validator = self.staking.get_validator(validator_id)
        
        if not validator or validator.total_stake == 0:
            return Decimal("0")
        
        # Simplified APR calculation
        annual_rewards = self.staking.dao.params.block_reward * 365 * 24 * 60  # ~1 block/min
        validators = self.staking.list_validators()
        total_stake = sum(v.total_stake for v in validators)
        
        if total_stake == 0:
            return Decimal("0")
        
        validator_share = validator.total_stake / total_stake
        validator_rewards = annual_rewards * float(validator_share)
        
        apr = Decimal(validator_rewards * 100 / validator.total_stake)
        
        # Subtract commission
        apr = apr * (1 - validator.commission_rate / 100)
        
        return apr.quantize(Decimal("0.01"))


# ============================================================================
# GOVERNANCE FACADE
# ============================================================================

class GovernanceSystem:
    """Facade pour le systeme de gouvernance complet"""
    
    def __init__(self, data_dir: str = "./governance_data"):
        self.data_dir = data_dir
        self.dao = DAOGovernance(data_dir)
        self.staking = StakingSystem(self.dao, data_dir)
        self.incentives = ValidatorIncentives(self.staking)
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtient les statistiques globales"""
        validators = self.staking.list_validators()
        proposals = self.dao.list_proposals()
        
        return {
            "token": {
                "total_supply": self.dao.token.total_supply,
                "circulating_supply": self.dao.token.circulating_supply,
                "staked_supply": self.dao.token.staked_supply,
                "treasury_balance": self.dao.token.treasury_balance
            },
            "validators": {
                "total": len(validators),
                "active": len([v for v in validators if v.status == ValidatorStatus.ACTIVE]),
                "total_stake": sum(v.total_stake for v in validators)
            },
            "proposals": {
                "total": len(proposals),
                "active": len([p for p in proposals if p.status == ProposalStatus.ACTIVE]),
                "passed": len([p for p in proposals if p.status == ProposalStatus.PASSED])
            },
            "params": {
                "voting_period_days": self.dao.params.voting_period_days,
                "quorum_percentage": str(self.dao.params.quorum_percentage),
                "unbonding_period_days": self.dao.params.unbonding_period_days
            }
        }


# ============================================================================
# FACTORY
# ============================================================================

def create_governance_system(data_dir: str = "./governance_data") -> GovernanceSystem:
    """Cree un systeme de gouvernance complet"""
    return GovernanceSystem(data_dir)
