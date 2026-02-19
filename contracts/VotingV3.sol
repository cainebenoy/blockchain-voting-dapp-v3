// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "./VotingV2.sol";

contract VotingV3 is VotingV2 {
    bytes32 public voterListRoot;

    event VoterListRootSet(bytes32 root);

    function setVoterListRoot(bytes32 _root) external {
        require(msg.sender == admin, "Only admin can set root");
        require(voterListRoot == bytes32(0), "Root already set");
        voterListRoot = _root;
        emit VoterListRootSet(_root);
    }
}
