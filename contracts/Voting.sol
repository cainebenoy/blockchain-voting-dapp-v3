// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

contract Voting {
    struct Candidate {
        uint id;
        string name;
        uint voteCount;
    }

    struct Voter {
        bool isAuthorized;
        bool hasVoted;
        uint votedCandidateId;
    }

    // Admin and election state
    address public admin;
    bool public electionEnded;

    // Counters
    uint public totalCandidates;
    uint public totalVotes;

    // Storage
    mapping(uint => Candidate) public candidates;
    mapping(address => Voter) public voters;

    // Events
    event CandidateAdded(uint indexed candidateId, string name);
    event VoterAuthorized(address indexed voter);
    event VoteCast(address indexed voter, uint indexed candidateId);
    event ElectionEnded(uint winnerCandidateId, string winnerName, uint winningVoteCount);

    // Modifiers
    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin can perform this action.");
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
        electionEnded = false;
        totalCandidates = 0;
        totalVotes = 0;
    }

    // Admin functions
    function addCandidate(string memory _name) external onlyAdmin electionActive {
        require(bytes(_name).length > 0, "Candidate name cannot be empty.");
        totalCandidates++;
        candidates[totalCandidates] = Candidate(totalCandidates, _name, 0);
        emit CandidateAdded(totalCandidates, _name);
    }

    function authorizeVoter(address _voter) external onlyAdmin electionActive {
        require(_voter != address(0), "Invalid voter address.");
        require(!voters[_voter].isAuthorized, "Voter is already authorized.");
        voters[_voter] = Voter({isAuthorized: true, hasVoted: false, votedCandidateId: 0});
        emit VoterAuthorized(_voter);
    }

    function endElection() external onlyAdmin electionActive {
        require(totalCandidates > 0, "Cannot end election with no candidates.");
        electionEnded = true;

        uint winnerId = _computeWinner();
        if (winnerId > 0) {
            emit ElectionEnded(winnerId, candidates[winnerId].name, candidates[winnerId].voteCount);
        } else {
            emit ElectionEnded(0, "", 0);
        }
    }

    // Voter function
    function vote(uint _candidateId) external electionActive {
        Voter storage sender = voters[msg.sender];
        require(sender.isAuthorized, "You are not authorized to vote.");
        require(!sender.hasVoted, "You have already voted.");
        require(_candidateId > 0 && _candidateId <= totalCandidates, "Invalid candidate ID.");

        sender.hasVoted = true;
        sender.votedCandidateId = _candidateId;
        candidates[_candidateId].voteCount++;
        totalVotes++;

        emit VoteCast(msg.sender, _candidateId);
    }

    // Views
    function getCandidate(uint _candidateId) public view returns (uint, string memory, uint) {
        require(_candidateId > 0 && _candidateId <= totalCandidates, "Invalid candidate ID.");
        Candidate memory c = candidates[_candidateId];
        return (c.id, c.name, c.voteCount);
    }

    function getWinner() public view electionInactive returns (uint) {
        require(totalCandidates > 0, "No candidates available.");
        return _computeWinner();
    }

    function getWinnerDetails() external view electionInactive returns (uint, string memory, uint) {
        uint winnerId = getWinner();
        return getCandidate(winnerId);
    }

    function getAllCandidates() external view returns (Candidate[] memory) {
        Candidate[] memory all = new Candidate[](totalCandidates);
        for (uint i = 1; i <= totalCandidates; i++) {
            all[i - 1] = candidates[i];
        }
        return all;
    }

    function getVoterInfo(address _voter) external view returns (bool, bool, uint) {
        Voter memory v = voters[_voter];
        return (v.isAuthorized, v.hasVoted, v.votedCandidateId);
    }

    function isElectionActive() external view returns (bool) {
        return !electionEnded;
    }

    // Internal winner computation
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
