// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title Governor
 * @dev Governance contract with timelock functionality for Lucid RDP system
 * @notice This contract manages governance proposals, voting, and timelock execution
 */
contract Governor {
    struct Proposal {
        uint256 id;
        address proposer;
        string title;
        string description;
        address[] targets;
        uint256[] values;
        bytes[] calldatas;
        uint256 startBlock;
        uint256 endBlock;
        uint256 forVotes;
        uint256 againstVotes;
        uint256 abstainVotes;
        bool canceled;
        bool executed;
        uint256 eta;
        string reason;
    }
    
    struct Receipt {
        bool hasVoted;
        uint8 support;
        uint256 votes;
    }
    
    struct Timelock {
        uint256 delay;
        bool queued;
        uint256 eta;
        bool executed;
    }
    
    // Events
    event ProposalCreated(
        uint256 indexed proposalId,
        address indexed proposer,
        address[] targets,
        uint256[] values,
        string[] signatures,
        bytes[] calldatas,
        uint256 startBlock,
        uint256 endBlock,
        string description
    );
    
    event VoteCast(
        address indexed voter,
        uint256 indexed proposalId,
        uint8 support,
        uint256 votes,
        string reason
    );
    
    event ProposalCanceled(uint256 indexed proposalId);
    event ProposalQueued(uint256 indexed proposalId, uint256 eta);
    event ProposalExecuted(uint256 indexed proposalId);
    event TimelockDelayChanged(uint256 oldDelay, uint256 newDelay);
    event VotingDelayChanged(uint256 oldVotingDelay, uint256 newVotingDelay);
    event VotingPeriodChanged(uint256 oldVotingPeriod, uint256 newVotingPeriod);
    event ProposalThresholdChanged(uint256 oldProposalThreshold, uint256 newProposalThreshold);
    event QuorumVotesChanged(uint256 oldQuorumVotes, uint256 newQuorumVotes);
    
    // State variables
    mapping(uint256 => Proposal) public proposals;
    mapping(uint256 => mapping(address => Receipt)) public proposalReceipts;
    mapping(address => uint256) public votingPower;
    mapping(address => bool) public authorizedVoters;
    mapping(bytes32 => Timelock) public timelocks;
    
    address public owner;
    address public paramRegistry;
    uint256 public proposalCount;
    uint256 public votingDelay;
    uint256 public votingPeriod;
    uint256 public proposalThreshold;
    uint256 public quorumVotes;
    uint256 public timelockDelay;
    
    // Constants
    uint8 public constant VOTE_TYPE_AGAINST = 0;
    uint8 public constant VOTE_TYPE_FOR = 1;
    uint8 public constant VOTE_TYPE_ABSTAIN = 2;
    
    uint256 public constant BALLOT_TYPEHASH = keccak256("Ballot(uint256 proposalId,uint8 support)");
    bytes32 public constant DOMAIN_TYPEHASH = keccak256("EIP712Domain(string name,uint256 chainId,address verifyingContract)");
    
    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Governor: Only owner can call this function");
        _;
    }
    
    modifier onlyAuthorizedVoter() {
        require(authorizedVoters[msg.sender] || msg.sender == owner, "Governor: Only authorized voters can call this function");
        _;
    }
    
    modifier validProposalId(uint256 proposalId) {
        require(proposalId < proposalCount, "Governor: Invalid proposal ID");
        _;
    }
    
    modifier proposalExists(uint256 proposalId) {
        require(proposals[proposalId].proposer != address(0), "Governor: Proposal does not exist");
        _;
    }
    
    constructor(
        address _paramRegistry,
        uint256 _votingDelay,
        uint256 _votingPeriod,
        uint256 _proposalThreshold,
        uint256 _quorumVotes,
        uint256 _timelockDelay
    ) {
        owner = msg.sender;
        paramRegistry = _paramRegistry;
        votingDelay = _votingDelay;
        votingPeriod = _votingPeriod;
        proposalThreshold = _proposalThreshold;
        quorumVotes = _quorumVotes;
        timelockDelay = _timelockDelay;
        
        // Initialize owner as authorized voter
        authorizedVoters[owner] = true;
        votingPower[owner] = 1000; // Initial voting power
    }
    
    /**
     * @dev Propose a new governance proposal
     * @param targets The target addresses for the proposal
     * @param values The values to send with the proposal
     * @param signatures The function signatures
     * @param calldatas The calldata for the proposal
     * @param description The proposal description
     * @return proposalId The proposal ID
     */
    function propose(
        address[] memory targets,
        uint256[] memory values,
        string[] memory signatures,
        bytes[] memory calldatas,
        string memory description
    ) external onlyAuthorizedVoter returns (uint256 proposalId) {
        require(targets.length == values.length, "Governor: Mismatched targets and values length");
        require(targets.length == signatures.length, "Governor: Mismatched targets and signatures length");
        require(targets.length == calldatas.length, "Governor: Mismatched targets and calldatas length");
        require(targets.length > 0, "Governor: Must have at least one target");
        require(votingPower[msg.sender] >= proposalThreshold, "Governor: Insufficient voting power to propose");
        require(bytes(description).length > 0, "Governor: Description required");
        
        proposalId = proposalCount;
        proposalCount++;
        
        uint256 startBlock = block.number + votingDelay;
        uint256 endBlock = startBlock + votingPeriod;
        
        proposals[proposalId] = Proposal({
            id: proposalId,
            proposer: msg.sender,
            title: "", // Can be set separately
            description: description,
            targets: targets,
            values: values,
            calldatas: calldatas,
            startBlock: startBlock,
            endBlock: endBlock,
            forVotes: 0,
            againstVotes: 0,
            abstainVotes: 0,
            canceled: false,
            executed: false,
            eta: 0,
            reason: ""
        });
        
        emit ProposalCreated(
            proposalId,
            msg.sender,
            targets,
            values,
            signatures,
            calldatas,
            startBlock,
            endBlock,
            description
        );
        
        return proposalId;
    }
    
    /**
     * @dev Cast a vote on a proposal
     * @param proposalId The proposal ID
     * @param support The vote support (0=against, 1=for, 2=abstain)
     * @param reason The reason for the vote
     */
    function castVote(
        uint256 proposalId,
        uint8 support,
        string memory reason
    ) external onlyAuthorizedVoter validProposalId(proposalId) proposalExists(proposalId) {
        require(support <= 2, "Governor: Invalid vote type");
        require(block.number >= proposals[proposalId].startBlock, "Governor: Voting not started");
        require(block.number <= proposals[proposalId].endBlock, "Governor: Voting ended");
        require(!proposals[proposalId].canceled, "Governor: Proposal canceled");
        require(!proposals[proposalId].executed, "Governor: Proposal executed");
        require(!proposalReceipts[proposalId][msg.sender].hasVoted, "Governor: Already voted");
        
        uint256 votes = votingPower[msg.sender];
        require(votes > 0, "Governor: No voting power");
        
        proposalReceipts[proposalId][msg.sender] = Receipt({
            hasVoted: true,
            support: support,
            votes: votes
        });
        
        if (support == VOTE_TYPE_FOR) {
            proposals[proposalId].forVotes += votes;
        } else if (support == VOTE_TYPE_AGAINST) {
            proposals[proposalId].againstVotes += votes;
        } else if (support == VOTE_TYPE_ABSTAIN) {
            proposals[proposalId].abstainVotes += votes;
        }
        
        emit VoteCast(msg.sender, proposalId, support, votes, reason);
    }
    
    /**
     * @dev Queue a proposal for execution
     * @param proposalId The proposal ID
     */
    function queue(uint256 proposalId) external validProposalId(proposalId) proposalExists(proposalId) {
        require(block.number > proposals[proposalId].endBlock, "Governor: Voting not ended");
        require(!proposals[proposalId].canceled, "Governor: Proposal canceled");
        require(!proposals[proposalId].executed, "Governor: Proposal executed");
        require(proposals[proposalId].forVotes > proposals[proposalId].againstVotes, "Governor: Proposal not passed");
        require(proposals[proposalId].forVotes >= quorumVotes, "Governor: Quorum not met");
        
        uint256 eta = block.timestamp + timelockDelay;
        proposals[proposalId].eta = eta;
        
        bytes32 txHash = keccak256(abi.encodePacked(proposalId, eta));
        timelocks[txHash] = Timelock({
            delay: timelockDelay,
            queued: true,
            eta: eta,
            executed: false
        });
        
        emit ProposalQueued(proposalId, eta);
    }
    
    /**
     * @dev Execute a queued proposal
     * @param proposalId The proposal ID
     */
    function execute(uint256 proposalId) external validProposalId(proposalId) proposalExists(proposalId) {
        require(block.timestamp >= proposals[proposalId].eta, "Governor: Timelock not expired");
        require(proposals[proposalId].eta > 0, "Governor: Proposal not queued");
        require(!proposals[proposalId].executed, "Governor: Proposal already executed");
        require(!proposals[proposalId].canceled, "Governor: Proposal canceled");
        
        bytes32 txHash = keccak256(abi.encodePacked(proposalId, proposals[proposalId].eta));
        require(timelocks[txHash].queued, "Governor: Proposal not queued");
        require(!timelocks[txHash].executed, "Governor: Proposal already executed");
        
        timelocks[txHash].executed = true;
        proposals[proposalId].executed = true;
        
        // Execute the proposal
        for (uint256 i = 0; i < proposals[proposalId].targets.length; i++) {
            (bool success, ) = proposals[proposalId].targets[i].call{
                value: proposals[proposalId].values[i]
            }(proposals[proposalId].calldatas[i]);
            require(success, "Governor: Proposal execution failed");
        }
        
        emit ProposalExecuted(proposalId);
    }
    
    /**
     * @dev Cancel a proposal
     * @param proposalId The proposal ID
     * @param reason The cancellation reason
     */
    function cancel(
        uint256 proposalId,
        string memory reason
    ) external onlyOwner validProposalId(proposalId) proposalExists(proposalId) {
        require(!proposals[proposalId].executed, "Governor: Proposal already executed");
        require(!proposals[proposalId].canceled, "Governor: Proposal already canceled");
        require(bytes(reason).length > 0, "Governor: Cancellation reason required");
        
        proposals[proposalId].canceled = true;
        proposals[proposalId].reason = reason;
        
        emit ProposalCanceled(proposalId);
    }
    
    /**
     * @dev Set proposal title
     * @param proposalId The proposal ID
     * @param title The proposal title
     */
    function setProposalTitle(
        uint256 proposalId,
        string memory title
    ) external onlyOwner validProposalId(proposalId) proposalExists(proposalId) {
        require(bytes(title).length > 0, "Governor: Title cannot be empty");
        proposals[proposalId].title = title;
    }
    
    /**
     * @dev Add authorized voter
     * @param voter The voter address
     * @param power The voting power
     */
    function addAuthorizedVoter(address voter, uint256 power) external onlyOwner {
        require(voter != address(0), "Governor: Invalid voter address");
        require(power > 0, "Governor: Voting power must be greater than zero");
        
        authorizedVoters[voter] = true;
        votingPower[voter] = power;
    }
    
    /**
     * @dev Remove authorized voter
     * @param voter The voter address
     */
    function removeAuthorizedVoter(address voter) external onlyOwner {
        authorizedVoters[voter] = false;
        votingPower[voter] = 0;
    }
    
    /**
     * @dev Update voting power
     * @param voter The voter address
     * @param power The new voting power
     */
    function updateVotingPower(address voter, uint256 power) external onlyOwner {
        require(authorizedVoters[voter], "Governor: Voter not authorized");
        votingPower[voter] = power;
    }
    
    /**
     * @dev Update governance parameters
     * @param _votingDelay New voting delay
     * @param _votingPeriod New voting period
     * @param _proposalThreshold New proposal threshold
     * @param _quorumVotes New quorum votes
     * @param _timelockDelay New timelock delay
     */
    function updateGovernanceParameters(
        uint256 _votingDelay,
        uint256 _votingPeriod,
        uint256 _proposalThreshold,
        uint256 _quorumVotes,
        uint256 _timelockDelay
    ) external onlyOwner {
        require(_votingDelay > 0, "Governor: Invalid voting delay");
        require(_votingPeriod > 0, "Governor: Invalid voting period");
        require(_proposalThreshold > 0, "Governor: Invalid proposal threshold");
        require(_quorumVotes > 0, "Governor: Invalid quorum votes");
        require(_timelockDelay > 0, "Governor: Invalid timelock delay");
        
        uint256 oldVotingDelay = votingDelay;
        uint256 oldVotingPeriod = votingPeriod;
        uint256 oldProposalThreshold = proposalThreshold;
        uint256 oldQuorumVotes = quorumVotes;
        uint256 oldTimelockDelay = timelockDelay;
        
        votingDelay = _votingDelay;
        votingPeriod = _votingPeriod;
        proposalThreshold = _proposalThreshold;
        quorumVotes = _quorumVotes;
        timelockDelay = _timelockDelay;
        
        emit VotingDelayChanged(oldVotingDelay, _votingDelay);
        emit VotingPeriodChanged(oldVotingPeriod, _votingPeriod);
        emit ProposalThresholdChanged(oldProposalThreshold, _proposalThreshold);
        emit QuorumVotesChanged(oldQuorumVotes, _quorumVotes);
        emit TimelockDelayChanged(oldTimelockDelay, _timelockDelay);
    }
    
    /**
     * @dev Update param registry address
     * @param _paramRegistry The new param registry address
     */
    function updateParamRegistry(address _paramRegistry) external onlyOwner {
        require(_paramRegistry != address(0), "Governor: Invalid param registry address");
        paramRegistry = _paramRegistry;
    }
    
    /**
     * @dev Get proposal state
     * @param proposalId The proposal ID
     * @return state The proposal state
     */
    function getProposalState(uint256 proposalId) external view returns (string memory state) {
        require(proposalId < proposalCount, "Governor: Invalid proposal ID");
        
        Proposal memory proposal = proposals[proposalId];
        
        if (proposal.canceled) {
            return "Canceled";
        } else if (proposal.executed) {
            return "Executed";
        } else if (block.timestamp >= proposal.eta && proposal.eta > 0) {
            return "Ready";
        } else if (proposal.eta > 0) {
            return "Queued";
        } else if (block.number > proposal.endBlock) {
            return "Succeeded";
        } else if (block.number >= proposal.startBlock) {
            return "Active";
        } else {
            return "Pending";
        }
    }
    
    /**
     * @dev Get proposal details
     * @param proposalId The proposal ID
     * @return proposal The proposal details
     */
    function getProposal(uint256 proposalId) external view returns (Proposal memory proposal) {
        require(proposalId < proposalCount, "Governor: Invalid proposal ID");
        return proposals[proposalId];
    }
    
    /**
     * @dev Get vote receipt
     * @param proposalId The proposal ID
     * @param voter The voter address
     * @return receipt The vote receipt
     */
    function getReceipt(uint256 proposalId, address voter) external view returns (Receipt memory receipt) {
        require(proposalId < proposalCount, "Governor: Invalid proposal ID");
        return proposalReceipts[proposalId][voter];
    }
    
    /**
     * @dev Check if proposal can be executed
     * @param proposalId The proposal ID
     * @return canExecute Whether the proposal can be executed
     */
    function canExecute(uint256 proposalId) external view returns (bool canExecute) {
        if (proposalId >= proposalCount) return false;
        
        Proposal memory proposal = proposals[proposalId];
        
        return !proposal.canceled &&
               !proposal.executed &&
               proposal.eta > 0 &&
               block.timestamp >= proposal.eta &&
               proposal.forVotes > proposal.againstVotes &&
               proposal.forVotes >= quorumVotes;
    }
    
    /**
     * @dev Get total voting power
     * @return totalPower The total voting power
     */
    function getTotalVotingPower() external view returns (uint256 totalPower) {
        // This is a simplified implementation
        // In a real implementation, you might want to iterate through all voters
        return 10000; // Placeholder value
    }
    
    /**
     * @dev Emergency function to pause governance
     */
    function emergencyPause() external onlyOwner {
        // This would typically set a pause flag and emit an event
        // Implementation depends on specific emergency procedures
        emit ProposalCanceled(type(uint256).max); // Special event for emergency pause
    }
}
