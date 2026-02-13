// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VotingV2 {
    struct Candidate {
        uint id;
        string name;
        uint voteCount;
    }

    // The only address allowed to submit votes (Your Backend Server)
    address public officialSigner;
    address public admin;

    bool public electionActive;
    uint public totalCandidates;
    uint public totalVotes;

    mapping(uint => Candidate) public candidates;
    // Tracks if a specific Voter ID (e.g., Aadhaar Hash) has already voted on-chain
    mapping(bytes32 => bool) public hasVoted;
    // Tracks kiosk-level nonces to prevent backend replay / double-click submission
    mapping(bytes32 => bool) public kioskNonces;

    event VoteCast(bytes32 indexed voterHash, uint indexed candidateId);
    event ElectionStarted(uint256 timestamp);
    event ElectionEnded(uint totalVotes);

    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin can do this");
        _;
    }

    modifier onlySigner() {
        require(msg.sender == officialSigner, "Not authorized kiosk signer");
        _;
    }

    modifier whenActive() {
        require(electionActive, "Election is not active");
        _;
    }

    constructor() {
        admin = msg.sender;
        electionActive = false; // Starts inactive - admin must add candidates first
    }

    // --- SETUP FUNCTIONS ---
    // Tell the contract which backend server address to trust
    function setOfficialSigner(address _signer) external onlyAdmin {
        require(_signer != address(0), "Invalid signer address");
        officialSigner = _signer;
    }

    function addCandidate(string memory _name) external onlyAdmin {
        totalCandidates++;
        candidates[totalCandidates] = Candidate(totalCandidates, _name, 0);
    }

    // Start the election (can only be done once)
    function startElection() external onlyAdmin {
        require(!electionActive, "Election already active");
        require(totalCandidates > 0, "Must have at least one candidate");
        electionActive = true;
        emit ElectionStarted(block.timestamp);
    }

    // --- CORE VOTING ---
    // This is the magic function. Only your server can call it.
    function vote(uint _candidateId, bytes32 _voterHash, bytes32 _kioskNonce) external onlySigner whenActive {
        require(!kioskNonces[_kioskNonce], "This transaction nonce has already been used.");
        require(!hasVoted[_voterHash], "This voter ID has already voted.");
        require(_candidateId > 0 && _candidateId <= totalCandidates, "Invalid candidate.");

        kioskNonces[_kioskNonce] = true;
        hasVoted[_voterHash] = true;
        candidates[_candidateId].voteCount++;
        totalVotes++;

        emit VoteCast(_voterHash, _candidateId);
    }

    // --- LIFECYCLE ---
    function endElection() external onlyAdmin {
        electionActive = false;
        emit ElectionEnded(totalVotes);
    }

    // --- VIEW FUNCTIONS ---
    function getAllCandidates() external view returns (Candidate[] memory) {
        Candidate[] memory all = new Candidate[](totalCandidates);
        for (uint i = 1; i <= totalCandidates; i++) {
            all[i - 1] = candidates[i];
        }
        return all;
    }
}