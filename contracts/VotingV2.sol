// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

/**
 * @title VotingV2 (Kiosk Model)
 * @notice Adapted from Voting.sol for a kiosk architecture. Votes are relayed
 *         by backend signer addresses instead of individual wallet users.
 * @dev    Stores raw voterId strings per specification. (Future improvement:
 *         replace voterId with a bytes32 hash for privacy & gas efficiency.)
 */
contract VotingV2 {
    struct Candidate {
        uint id;
        string name;
        uint voteCount;
    }

    // --- Admin & lifecycle ---
    address public admin;
    bool public electionEnded;

    // --- Signer authorization (trusted backend relayers) ---
    mapping(address => bool) public authorizedSigners;

    // --- Voter tracking (prevent double-votes by off-chain identifier) ---
    mapping(string => bool) public hasVoted; // voterId => true if already voted

    // --- Candidate & vote accounting ---
    uint public totalCandidates;
    uint public totalVotes;
    mapping(uint => Candidate) public candidates; // id => Candidate

    // --- Events ---
    event CandidateAdded(uint indexed candidateId, string name);
    event SignerAuthorized(address indexed signer);
    event SignerRevoked(address indexed signer);
    event VoteCast(address indexed signer, uint indexed candidateId, string voterId);
    event ElectionEnded(uint winnerCandidateId, string winnerName, uint winningVoteCount);
    event ElectionStarted();

    // --- Modifiers ---
    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin can perform this action.");
        _;
    }

    modifier onlySigner() {
        require(authorizedSigners[msg.sender], "Only authorized signer can perform this action.");
        _;
    }

    modifier electionActive() {
        require(!electionEnded, "Election has ended.");
        _;
    }

    modifier electionInactive() {
        require(electionEnded, "Election is still active.");
        _;
    }

    constructor() {
        admin = msg.sender;
        electionEnded = false; // starts active
    }

    // --- Signer management ---
    function authorizeSigner(address _signer) external onlyAdmin {
        require(_signer != address(0), "Invalid signer address.");
        require(!authorizedSigners[_signer], "Signer already authorized.");
        authorizedSigners[_signer] = true;
        emit SignerAuthorized(_signer);
    }

    function revokeSigner(address _signer) external onlyAdmin {
        require(authorizedSigners[_signer], "Signer not authorized.");
        authorizedSigners[_signer] = false;
        emit SignerRevoked(_signer);
    }

    // --- Election lifecycle ---
    function endElection() external onlyAdmin electionActive {
        require(totalCandidates > 0, "Cannot end election with no candidates.");
        electionEnded = true;
        uint winnerId = _computeWinner();
        if (winnerId > 0) {
            Candidate memory w = candidates[winnerId];
            emit ElectionEnded(winnerId, w.name, w.voteCount);
        } else {
            emit ElectionEnded(0, "", 0);
        }
    }

    function startElection() external onlyAdmin electionInactive {
        // Allow restarting an election cycle (clears nothing; only lifecycle toggle)
        electionEnded = false;
        emit ElectionStarted();
    }

    // --- Candidate management ---
    function addCandidate(string memory _name) external onlyAdmin electionActive {
        require(bytes(_name).length > 0, "Candidate name cannot be empty.");
        totalCandidates++;
        candidates[totalCandidates] = Candidate(totalCandidates, _name, 0);
        emit CandidateAdded(totalCandidates, _name);
    }

    // --- Voting (via authorized backend signer) ---
    function vote(uint256 _candidateId, string memory _voterId) external onlySigner electionActive {
        require(bytes(_voterId).length > 0, "voterId cannot be empty.");
        require(!hasVoted[_voterId], "Voter ID already used.");
        require(_candidateId > 0 && _candidateId <= totalCandidates, "Invalid candidate ID.");

        hasVoted[_voterId] = true;
        candidates[_candidateId].voteCount++;
        totalVotes++;

        emit VoteCast(msg.sender, _candidateId, _voterId);
    }

    // --- Views & getters ---
    function isElectionActive() external view returns (bool) {
        return !electionEnded;
    }

    function getCandidate(uint _candidateId) public view returns (uint, string memory, uint) {
        require(_candidateId > 0 && _candidateId <= totalCandidates, "Invalid candidate ID.");
        Candidate memory c = candidates[_candidateId];
        return (c.id, c.name, c.voteCount);
    }

    function getAllCandidates() external view returns (Candidate[] memory) {
        Candidate[] memory all = new Candidate[](totalCandidates);
        for (uint i = 1; i <= totalCandidates; i++) {
            all[i - 1] = candidates[i];
        }
        return all;
    }

    function getWinner() public view electionInactive returns (uint) {
        require(totalCandidates > 0, "No candidates available.");
        return _computeWinner();
    }

    function getWinnerDetails() external view electionInactive returns (uint, string memory, uint) {
        uint winnerId = getWinner();
        return getCandidate(winnerId);
    }

    // --- Internal winner computation ---
    function _computeWinner() internal view returns (uint) {
        uint winnerId = 0;
        uint highestVotes = 0;
        for (uint i = 1; i <= totalCandidates; i++) {
            uint vc = candidates[i].voteCount;
            if (vc > highestVotes) {
                highestVotes = vc;
                winnerId = i;
            }
        }
        return winnerId;
    }
}
