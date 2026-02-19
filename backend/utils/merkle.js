
import { MerkleTree } from 'merkletreejs';
import keccak256 from 'keccak256';
import { ethers } from 'ethers';

// Helper to reliably hash a Leaf (Voter ID)
// Matches contract expectation (if we were verifying on-chain, but we are doing it mixed)
// In auditor.html we did: ethers.utils.keccak256(ethers.utils.toUtf8Bytes(voterId))
export function hashVoterId(voterId) {
    return keccak256(voterId);
}

export function generateMerkleTree(voterIds) {
    const leaves = voterIds.map(id => hashVoterId(id));
    const tree = new MerkleTree(leaves, keccak256, { sortPairs: true });
    return tree;
}

export function getProof(tree, voterId) {
    const leaf = hashVoterId(voterId);
    return tree.getProof(leaf);
}

export function getRoot(tree) {
    return tree.getHexRoot();
}
